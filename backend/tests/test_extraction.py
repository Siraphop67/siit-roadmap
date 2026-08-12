"""เทสต์การสกัดทักษะจาก CV + การรับผลงานเข้ามา

🔒 กติกาที่สำคัญที่สุดในไฟล์นี้: span guard
   ข้อความที่ระบบอ้างว่าเป็นหลักฐาน ต้องอยู่ในเอกสารจริงตรงตำแหน่งที่บอก
   ถ้าข้อนี้พัง หน้าไฮไลต์จะชี้ไปผิดที่ ซึ่งแย่กว่าไม่มีไฮไลต์เลย
"""

from __future__ import annotations

import pytest

from app.ingest import IngestError, from_github, from_linkedin, from_text, parse_github
from app.llm import get_extractor
from app.llm.base import ExtractedSpan, enforce_span_guard
from app.llm.keyword import KEYWORDS, KeywordExtractor
from app.seed.skills import SKILL_IDS

CV_TH = """สมชาย ใจดี
นักศึกษาวิศวกรรมคอมพิวเตอร์ ชั้นปีที่ 3

ประสบการณ์
- ทำโปรเจกต์วิเคราะห์ข้อมูลการใช้ห้องเรียนด้วย Python และ pandas
- สร้าง REST API ให้ระบบจองห้อง ใช้ FastAPI ต่อกับ PostgreSQL
- ดูแล repo ด้วย Git และเขียน unit test ด้วย pytest
- ฝึกงานที่โรงงาน ทำ dashboard ด้วย Power BI ให้หัวหน้าไลน์ดูของเสียรายวัน

ทักษะ
Python, SQL, Docker, Linux, การแก้ปัญหา
TOEIC 780
"""

CV_ME = """นางสาวมานี รักเรียน — วิศวกรรมเครื่องกล ปี 4

โครงงาน
- ออกแบบชุดเฟืองทดด้วย SolidWorks แล้วพิมพ์ 3 มิติมาทดสอบจริง
- วิเคราะห์ความเค้นด้วย ANSYS เทียบกับการคำนวณมือ
- ทำงานในโรงประลอง กลึงและเชื่อมชิ้นส่วนเอง
- ศึกษาการถ่ายเทความร้อนของตู้อบพลังแสงอาทิตย์
"""


@pytest.fixture(scope="module")
def extractor() -> KeywordExtractor:
    return KeywordExtractor()


# ═══════════ 🔒 span guard ═══════════


@pytest.mark.parametrize("cv", [CV_TH, CV_ME], ids=["cv-computer", "cv-mechanical"])
def test_every_span_is_really_in_the_document(extractor, cv):
    """ทุกหลักฐานต้องชี้กลับไปที่ข้อความจริงในเอกสาร ณ ตำแหน่งที่บอก"""
    spans = extractor.extract(cv)
    assert spans, "สกัดอะไรไม่ได้เลยจาก CV ที่มีเนื้อหาชัดเจน"
    for s in spans:
        assert s.verify(cv), f"{s.skill_id}: span ชี้ผิดที่ ({s.span_text!r})"
        assert cv[s.span_start:s.span_end] == s.span_text


def test_guard_throws_away_invented_text():
    raw = "ผมเขียน Python มาสามปี"
    fake = ExtractedSpan("T-SQL", 0, 10, "ใช้ SQL ทุกวัน", 3, 0.9)
    real = ExtractedSpan("T-PY", 8, 14, "Python", 2, 0.7)
    kept = enforce_span_guard([fake, real], raw)
    assert [s.skill_id for s in kept] == ["T-PY"], "ข้อความที่แต่งขึ้นต้องถูกทิ้ง"


def test_guard_rejects_out_of_range_positions():
    raw = "Python"
    assert enforce_span_guard([ExtractedSpan("T-PY", 0, 999, "Python", 2, 0.5)], raw) == []
    assert enforce_span_guard([ExtractedSpan("T-PY", 3, 1, "Py", 2, 0.5)], raw) == []


# ═══════════ คุณภาพของการสกัด ═══════════


def test_computer_cv_finds_computer_skills(extractor):
    got = {s.skill_id for s in extractor.extract(CV_TH)}
    for expected in ("T-PY", "T-SQL", "T-GIT", "SW-API", "SW-TEST", "T-VIZ", "F-ENG"):
        assert expected in got, f"ควรเจอ {expected} ใน CV สายคอมพิวเตอร์"


def test_mechanical_cv_finds_mechanical_skills(extractor):
    got = {s.skill_id for s in extractor.extract(CV_ME)}
    for expected in ("T-CAD3D", "ME-FEA", "ME-FAB", "ME-THERMO"):
        assert expected in got, f"ควรเจอ {expected} ใน CV สายเครื่องกล"


def test_two_different_cvs_give_two_different_skill_sets(extractor):
    a = {s.skill_id for s in extractor.extract(CV_TH)}
    b = {s.skill_id for s in extractor.extract(CV_ME)}
    assert a != b
    assert len(a ^ b) >= 6, "CV คนละสายควรได้ทักษะต่างกันชัดเจน"


def test_empty_document_yields_nothing(extractor):
    assert extractor.extract("") == []
    assert extractor.extract("   \n  ") == []


def test_extraction_is_deterministic(extractor):
    runs = [[(s.skill_id, s.span_start, s.level) for s in extractor.extract(CV_TH)]
            for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]


def test_mentioning_something_once_scores_lower_than_using_it_a_lot(extractor):
    once = extractor.extract("เคยได้ยินเรื่อง Docker มาบ้าง")
    many = extractor.extract("ใช้ Docker ทุกวัน · Docker compose · เขียน Dockerfile เอง · Docker registry")
    lvl_once = next(s.level for s in once if s.skill_id == "SW-CONTAINER")
    lvl_many = next(s.level for s in many if s.skill_id == "SW-CONTAINER")
    assert lvl_many > lvl_once


def test_every_keyword_maps_to_a_real_skill():
    unknown = set(KEYWORDS) - set(SKILL_IDS)
    assert not unknown, f"คำสำคัญชี้ไปทักษะที่ไม่มีอยู่: {unknown}"


def test_keyword_coverage_is_reported_honestly():
    """ทักษะที่ไม่มีคำสำคัญเลย = สกัดจาก CV ไม่ได้ ต้องรู้ว่ามีกี่ตัว"""
    missing = set(SKILL_IDS) - set(KEYWORDS)
    assert not missing, f"ทักษะที่ยังไม่มีคำสำคัญ ({len(missing)}): {sorted(missing)}"


def test_default_provider_needs_no_api_key():
    assert get_extractor().name == "keyword"


# ═══════════ การรับผลงานเข้ามา ═══════════


def test_text_ingest_rejects_something_too_short():
    with pytest.raises(IngestError):
        from_text("Python")


def test_text_ingest_keeps_the_document_intact():
    r = from_text(CV_TH)
    assert r.kind == "text"
    assert r.raw_text.strip() == CV_TH.strip()
    assert r.char_count > 100


def test_linkedin_says_plainly_why_it_is_not_automatic():
    r = from_linkedin(CV_TH, url="https://linkedin.com/in/somchai")
    assert r.kind == "linkedin"
    assert "อัตโนมัติ" in r.note


@pytest.mark.parametrize("url,owner,repo", [
    ("https://github.com/torvalds", "torvalds", None),
    ("github.com/psf/requests", "psf", "requests"),
    ("https://github.com/psf/requests/tree/main", "psf", "requests"),
])
def test_github_url_parsing(url, owner, repo):
    assert parse_github(url) == (owner, repo)


def test_github_rejects_a_url_that_is_not_github():
    with pytest.raises(IngestError):
        parse_github("https://gitlab.com/someone/repo")


def test_github_ingest_reads_readme_and_languages():
    """ยิง GitHub API จริง — ข้ามถ้าเครื่องไม่มีเน็ต"""
    httpx = pytest.importorskip("httpx")
    try:
        r = from_github("https://github.com/psf/requests")
    except Exception as exc:  # noqa: BLE001 — ไม่มีเน็ตหรือโดนจำกัดอัตราการเรียก
        pytest.skip(f"ต่อ GitHub ไม่ได้: {exc}")
    assert r.kind == "github"
    assert r.char_count > 200
    assert "requests" in r.source_ref
