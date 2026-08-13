"""ท่อขั้นที่ 2 — ประกาศงานจริงกลายเป็น requirement

ตัวเชื่อมระหว่าง "🅴 เก็บประกาศงานเสร็จ" กับ "ข้อมูลนั้นมีผลกับหน้าจอ"
ถ้าท่อนี้พังเงียบ ๆ ทีมจะเก็บประกาศงาน 50 อันแล้วไม่มีอะไรเปลี่ยนบนจอ โดยไม่มีใครรู้
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.llm.base import ExtractedSpan
from app.models import CareerTarget, TargetRequirement
from app.seed.careers import CAREER_TARGETS
from app.seed.postings import parse
from app.seed.loader import create_all, seed

REPO = Path(__file__).resolve().parents[2]
TARGET = "PROCESS-ENG"
CURATED_SKILLS = {
    skill_id
    for t in CAREER_TARGETS if t["id"] == TARGET
    for skill_id, _, _ in t["requirements"]
}


def load_stage2():
    """สคริปต์ขึ้นต้นด้วยตัวเลข จึง import ตรง ๆ ไม่ได้"""
    path = REPO / "pipeline" / "2_extract_postings.py"
    spec = importlib.util.spec_from_file_location("stage2", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


stage2 = load_stage2()


def test_ผลของท่อO_NETอยู่ในrepoจริง():
    """🔴 เคยพังมาแล้วและไม่มีใครเห็น

    `.gitignore` มีบรรทัด `out/` ที่ตั้งใจกัน next export แต่มันกลืน `pipeline/out/` ไปด้วย
    ผลของท่อ O*NET จึงไม่เคยเข้า repo สักครั้ง ทั้งที่คอมเมนต์ใน .gitignore บอกเองว่าเก็บ

    อาการที่ตามมา — และเหตุผลที่ไม่มีใครเห็นบนเครื่องตัวเอง (เพราะ make setup สร้างให้):
      · clone ใหม่แล้วฝั่ง "ยังไม่รู้" ใช้ไม่ได้เลย ไม่มีโปรไฟล์กิจกรรมให้จับคู่
      · เทสต์ 20 ตัวถูก skip เงียบ ๆ แทนที่จะแดง
      · docker build ล้มที่ COPY pipeline/out

    เทสต์นี้ทำให้อาการนั้นเป็นสีแดง ไม่ใช่ความเงียบ
    """
    out = REPO / "pipeline" / "out"
    required = ["target_activity_profiles.json", "onet_skills.json", "work_activities.json"]
    missing = [f for f in required if not (out / f).exists()]
    assert not missing, (
        f"ไม่มี {missing} ใน pipeline/out/ — ถ้าเพิ่ง clone มาแปลว่าไฟล์หลุดจาก repo อีกแล้ว "
        "(เช็ค .gitignore) · ถ้าเป็นเครื่องตัวเองให้รัน make pipeline"
    )


BODY_HEAD = """---
org: บริษัททดสอบ จำกัด
title: Process Engineer
url: https://example.com/1
collected_at: 2026-08-13
collected_by: เทสต์
sector: private
employment_type: new_grad
target_id: {target}
---

"""

FILLER = (
    "หน้าที่ความรับผิดชอบ\n"
    "- ดูแลกระบวนการผลิตประจำวันและติดตามค่าที่วิ่งอยู่บนหน้าจอควบคุมตลอดกะ\n"
    "- ประสานกับฝ่ายซ่อมบำรุงเพื่อวางแผนหยุดเครื่องและติดตามผลหลังเดินเครื่องใหม่\n"
    "- จัดทำรายงานสรุปผลการผลิตรายสัปดาห์ และนำเสนอต่อหัวหน้าฝ่ายในที่ประชุม\n"
    "คุณสมบัติผู้สมัคร\n"
    "- จบปริญญาตรีวิศวกรรมเคมี เครื่องกล หรืออุตสาหการ เกรดเฉลี่ยไม่ต่ำกว่า 2.75\n"
    "- ทำงานเป็นทีมได้ดี พร้อมประจำที่โรงงานจังหวัดระยอง\n"
)


def make(tmp_path, name: str, extra: str = "", target: str = TARGET):
    path = tmp_path / f"{name}.md"
    path.write_text(BODY_HEAD.format(target=target) + FILLER + extra, encoding="utf-8")
    p = parse(path, {t["id"] for t in CAREER_TARGETS})
    assert p.ok, p.errors
    return p


class FakeExtractor:
    """ตัวสกัดปลอมที่กำหนดผลได้ — เทสต์ท่อ ไม่ได้เทสต์ตัวสกัด"""

    name = "fake"

    def __init__(self, plan: dict[str, list[tuple[str, str, int]]]):
        self.plan = plan          # posting ที่มีคำนี้ → [(skill_id, ข้อความที่อ้าง, level)]

    def extract(self, raw_text: str) -> list[ExtractedSpan]:
        out = []
        for marker, entries in self.plan.items():
            if marker not in raw_text:
                continue
            for skill_id, needle, level in entries:
                start = raw_text.find(needle)
                out.append(ExtractedSpan(
                    skill_id=skill_id,
                    span_start=start, span_end=start + len(needle) if start >= 0 else -1,
                    span_text=needle, level=level, confidence=0.8,
                ))
        return out


REAL_SKILL = next(iter(CURATED_SKILLS))
OTHER_SKILL = "T-PY"


# ═════════════ นับข้ามประกาศ ═════════════


def test_ทักษะที่พบหลายประกาศถูกนับรวมกัน(tmp_path):
    ex = FakeExtractor({"หน้าที่": [(REAL_SKILL, "กระบวนการผลิต", 2)]})
    postings = [make(tmp_path, f"p{i}") for i in range(3)]
    out = stage2.aggregate(postings, ex, min_postings=2)

    req = out["targets"][TARGET]["requirements"]
    assert len(req) == 1
    assert req[0]["appears_in_n_postings"] == 3
    assert req[0]["share"] == 1.0
    assert req[0]["in_curated_set"] is True


def test_ทักษะที่พบประกาศเดียวไม่ถึงเกณฑ์(tmp_path):
    """ทักษะที่ประกาศเดียวพูดถึงคือเสียงรบกวน ไม่ใช่ requirement ของอาชีพ"""
    ex = FakeExtractor({
        "หน้าที่": [(REAL_SKILL, "กระบวนการผลิต", 2)],
        "เฉพาะอันนี้": [(OTHER_SKILL, "เฉพาะอันนี้", 2)],
    })
    postings = [make(tmp_path, "p1"), make(tmp_path, "p2"),
                make(tmp_path, "p3", extra="\nเฉพาะอันนี้\n")]
    out = stage2.aggregate(postings, ex, min_postings=2)
    t = out["targets"][TARGET]

    assert [r["skill_id"] for r in t["requirements"]] == [REAL_SKILL]
    assert [r["skill_id"] for r in t["below_threshold"]] == [OTHER_SKILL]
    # ไม่ได้หายไป แค่ยังไม่ถูกใช้ — เก็บประกาศเพิ่มแล้วอาจผ่านเกณฑ์
    assert t["below_threshold"][0]["appears_in_n_postings"] == 1


def test_ทักษะเดิมซ้ำในประกาศเดียวนับครั้งเดียว(tmp_path):
    ex = FakeExtractor({"หน้าที่": [
        (REAL_SKILL, "กระบวนการผลิต", 2),
        (REAL_SKILL, "การผลิตราย", 2),
    ]})
    out = stage2.aggregate([make(tmp_path, "p1"), make(tmp_path, "p2")], ex, min_postings=2)
    assert out["targets"][TARGET]["requirements"][0]["appears_in_n_postings"] == 2


# ═════════════ ระดับที่สรุปได้ ═════════════


def test_ระดับใช้ค่ากลางไม่ใช่ค่าสูงสุด(tmp_path):
    """ประกาศเดียวที่ขอระดับ 3 ไม่ควรลากทั้งอาชีพขึ้นไป"""
    ex = FakeExtractor({
        "ระดับสูง": [(REAL_SKILL, "กระบวนการผลิต", 3)],
        "หน้าที่": [(REAL_SKILL, "กระบวนการผลิต", 1)],
    })
    postings = [make(tmp_path, "p1"), make(tmp_path, "p2"),
                make(tmp_path, "p3", extra="\nระดับสูง\n")]
    out = stage2.aggregate(postings, ex, min_postings=2)
    r = out["targets"][TARGET]["requirements"][0]
    assert r["levels"] == [1, 1, 3]
    assert r["min_level"] == 1, "ค่าสูงสุดคือ 3 แต่ค่ากลางคือ 1 — ต้องใช้ค่ากลาง"


# ═════════════ 🛡 span guard ═════════════


def test_ทักษะที่ชี้กลับไปที่ประกาศไม่ได้ถูกทิ้ง(tmp_path):
    """กติกาข้อ 2 — เหมือนตอนอ่าน CV ไม่มีข้อยกเว้นให้ประกาศงาน"""
    ex = FakeExtractor({"หน้าที่": [
        (REAL_SKILL, "กระบวนการผลิต", 2),
        (OTHER_SKILL, "ข้อความที่ไม่มีอยู่ในประกาศนี้เลย", 2),
    ]})
    out = stage2.aggregate([make(tmp_path, "p1"), make(tmp_path, "p2")], ex, min_postings=2)
    assert out["spans_dropped_by_guard"] == 2
    assert [r["skill_id"] for r in out["targets"][TARGET]["requirements"]] == [REAL_SKILL]


def test_หลักฐานที่เก็บไว้ตัดจากประกาศจริงได้ตรงตัว(tmp_path):
    """ต้องเปิดให้กรรมการดูได้ว่า requirement ข้อนี้มาจากประโยคไหน"""
    ex = FakeExtractor({"หน้าที่": [(REAL_SKILL, "กระบวนการผลิต", 2)]})
    postings = [make(tmp_path, "p1"), make(tmp_path, "p2")]
    out = stage2.aggregate(postings, ex, min_postings=2)
    ev = out["targets"][TARGET]["requirements"][0]["example"]

    body = next(p.body for p in postings if p.id == ev["posting_id"])
    assert body[ev["span_start"]:ev["span_end"]] == ev["span_text"]


def test_ทักษะที่ไม่มีในคลัง73ตัวถูกทิ้ง(tmp_path):
    ex = FakeExtractor({"หน้าที่": [("SKILL-ที่ไม่มีจริง", "กระบวนการผลิต", 2)]})
    out = stage2.aggregate([make(tmp_path, "p1"), make(tmp_path, "p2")], ex, min_postings=2)
    assert out["spans_unknown_skill"] == 2

    t = out["targets"][TARGET]
    assert t["posting_count"] == 2, "จำนวนประกาศยังต้องนับ แม้จะสกัดอะไรไม่ได้เลย"
    assert t["requirements"] == []
    assert t["below_threshold"] == []


# ═════════════ ประกาศที่ยังไม่ได้ระบุอาชีพ ═════════════


def test_ประกาศที่ไม่มีtarget_idถูกรายงานไม่ใช่หายเงียบ(tmp_path):
    ex = FakeExtractor({"หน้าที่": [(REAL_SKILL, "กระบวนการผลิต", 2)]})
    p = make(tmp_path, "ไม่ระบุ")
    p.meta["target_id"] = None
    out = stage2.aggregate([p, make(tmp_path, "p2")], ex, min_postings=1)

    assert out["postings_without_target"] == ["ไม่ระบุ"]
    assert out["targets"][TARGET]["posting_count"] == 1, "ประกาศที่ไม่ระบุอาชีพต้องไม่ถูกนับรวม"


# ═════════════ 🔒 กติกาข้อ 5 — ไฟล์ผลลัพธ์ต้องบอกความจริงเรื่องตัวเอง ═════════════


def test_ไฟล์ผลลัพธ์บอกว่าสร้างด้วยอะไรและมีข้อจำกัดอะไร(tmp_path):
    ex = FakeExtractor({"หน้าที่": [(REAL_SKILL, "กระบวนการผลิต", 2)]})
    out = stage2.aggregate([make(tmp_path, "p1"), make(tmp_path, "p2")], ex, min_postings=2)

    assert out["extractor"] == "fake"
    assert out["extractor_is_real_llm"] is False
    assert "ขอบล่าง" in out["caveat"], (
        "ตัวสกัดคำสำคัญจับได้ไม่หมด ไฟล์ต้องบอกเองว่าตัวเลขเป็นขอบล่าง"
    )


def test_requirementที่ทีมเขียนแต่ประกาศไม่พูดถึงถูกรายงาน(tmp_path):
    """ไม่ได้ลบ แต่ต้องเห็นว่ามีข้อไหนบ้างที่ยังยืนยันจากตลาดไม่ได้"""
    ex = FakeExtractor({"หน้าที่": [(REAL_SKILL, "กระบวนการผลิต", 2)]})
    out = stage2.aggregate([make(tmp_path, "p1"), make(tmp_path, "p2")], ex, min_postings=2)
    missing = out["targets"][TARGET]["curated_not_found_in_postings"]
    assert set(missing) == CURATED_SKILLS - {REAL_SKILL}


# ═════════════ loader ผสมสองชุดเข้าด้วยกัน ═════════════


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    """seed ฐานข้อมูลโดยแกล้งว่าท่อขั้นที่ 2 เคยรันมาแล้ว"""
    def build(artifact: dict | None):
        out_dir = tmp_path / "out"
        out_dir.mkdir(exist_ok=True)
        if artifact is not None:
            (out_dir / "posting_requirements.json").write_text(
                json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
        monkeypatch.setattr("app.config.settings.pipeline_out", out_dir)

        engine = create_engine(f"sqlite:///{tmp_path / 'x.db'}",
                               connect_args={"check_same_thread": False})
        create_all(engine)
        Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        db = Session()
        seed(db)
        return db
    return build


ARTIFACT = {
    "targets": {
        TARGET: {
            "posting_count": 5,
            "requirements": [
                {"skill_id": REAL_SKILL, "appears_in_n_postings": 4,
                 "share": 0.8, "min_level": 2},
                {"skill_id": OTHER_SKILL, "appears_in_n_postings": 3,
                 "share": 0.6, "min_level": 2},
            ],
        }
    }
}


def test_ของที่ทีมเขียนไม่ถูกลบเมื่อประกาศไม่ได้พูดถึง(seeded):
    db = seeded(ARTIFACT)
    rows = {r.skill_id: r for r in db.query(TargetRequirement).filter(
        TargetRequirement.target_id == TARGET).all()}
    for skill_id in CURATED_SKILLS:
        assert skill_id in rows, (
            f"{skill_id} ที่ทีมเขียนไว้หายไป — ตัวสกัดจับได้เฉพาะคำที่เขียนตรงตัว "
            "ถ้าแทนที่ทั้งชุด requirement ที่จริงแต่เขียนอ้อมจะหายหมด"
        )


def test_ติดป้ายว่าrequirementมาจากไหน(seeded):
    db = seeded(ARTIFACT)
    rows = {r.skill_id: r for r in db.query(TargetRequirement).filter(
        TargetRequirement.target_id == TARGET).all()}

    assert rows[REAL_SKILL].source == "both", "ทีมเขียน + ประกาศยืนยัน = แข็งแรงที่สุด"
    assert rows[REAL_SKILL].appears_in_n_postings == 4
    assert rows[OTHER_SKILL].source == "postings", "พบในประกาศ แต่ทีมไม่ได้เขียนไว้"
    untouched = CURATED_SKILLS - {REAL_SKILL}
    assert all(rows[s].source == "curated" for s in untouched)
    assert all(rows[s].appears_in_n_postings == 0 for s in untouched)


def test_ไม่มีไฟล์ผลท่อระบบยังเดินได้และรายงานว่าศูนย์(seeded):
    """🔒 กติกาข้อ 5 — ยังไม่ได้รันท่อ ต้องไม่แกล้งว่ามีข้อมูลจริงแล้ว"""
    db = seeded(None)
    rows = db.query(TargetRequirement).filter(TargetRequirement.target_id == TARGET).all()
    assert rows, "ไม่มีไฟล์ผลท่อ ก็ยังต้องมี requirement ชุดที่ทีมเขียนไว้"
    assert all(r.source == "curated" for r in rows)
    assert all(r.appears_in_n_postings == 0 for r in rows)
    assert db.get(CareerTarget, TARGET).data_status == "placeholder"


def test_สถานะข้อมูลเปลี่ยนเมื่อมีประกาศยืนยัน(seeded):
    db = seeded(ARTIFACT)
    assert db.get(CareerTarget, TARGET).data_status == "from_postings"
    other = next(t["id"] for t in CAREER_TARGETS if t["id"] != TARGET)
    assert db.get(CareerTarget, other).data_status == "placeholder", (
        "อาชีพที่ยังไม่มีประกาศต้องยังเป็น placeholder — ห้ามเหมารวม"
    )
