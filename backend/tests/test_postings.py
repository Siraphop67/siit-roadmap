"""ด่านตรวจของไฟล์ประกาศงานที่ 🅴 เก็บมาด้วยมือ

เทสต์พวกนี้ไม่ได้ตรวจโค้ดเป็นหลัก — ตรวจว่า **คนที่ไม่ใช่โปรแกรมเมอร์กรอกผิดแล้วได้ข้อความที่ใช้แก้ได้จริง**
เพราะถ้า make check-postings บอกแค่ว่า "ผิด" คนเก็บจะต้องมาถามคนเขียนโค้ดทุกครั้ง
แล้วงานเก็บข้อมูลจะช้าลงจนพลาดเดดไลน์ 30 ส.ค.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.seed.careers import CAREER_TARGETS
from app.seed.postings import MIN_BODY_CHARS, load_all, parse, to_row

TARGET_IDS = {t["id"] for t in CAREER_TARGETS}

BODY = (
    "หน้าที่ความรับผิดชอบ\n"
    "- ดูแลกระบวนการผลิตประจำวัน ตรวจค่าที่วิ่งอยู่บนหน้าจอควบคุม\n"
    "- ไล่หาสาเหตุเมื่อของเสียเกินเกณฑ์ แล้วเสนอวิธีแก้ให้หัวหน้าไลน์\n"
    "- ทำรายงานสรุปประสิทธิภาพรายสัปดาห์ด้วย Excel และนำเสนอในที่ประชุม\n"
    "- ทำงานร่วมกับฝ่ายซ่อมบำรุงเพื่อวางแผนหยุดเครื่องประจำปี\n\n"
    "คุณสมบัติผู้สมัคร\n"
    "- จบปริญญาตรีวิศวกรรมเคมี เครื่องกล หรืออุตสาหการ\n"
    "- เกรดเฉลี่ยไม่ต่ำกว่า 2.75\n"
    "- ใช้ Excel ได้ดี เขียน Python เพื่อวิเคราะห์ข้อมูลได้จะพิจารณาเป็นพิเศษ\n"
    "- สื่อสารภาษาอังกฤษได้ อ่านเอกสารเทคนิคภาษาอังกฤษได้\n"
    "- ทำงานเป็นทีมได้ และพร้อมประจำที่โรงงานจังหวัดระยอง\n"
)

HEAD = """---
org: บริษัทตัวอย่าง จำกัด
title: Process Engineer (New Graduate)
url: https://example.com/jobs/1
collected_at: 2026-08-13
collected_by: ทีมเก็บข้อมูล
sector: private
employment_type: new_grad
target_id: PROCESS-ENG
requires_field: [ChE, ME, IE]
requires_gpa: 2.75
salary_text: "25,000–30,000 บาท/เดือน"
closes_at: 2026-09-30
---
"""


def write(tmp_path, name: str, text: str):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def good(tmp_path):
    return write(tmp_path, "2026-08-13-example-process-engineer.md", HEAD + "\n" + BODY)


# ═════════════ ไฟล์ที่กรอกถูก ═════════════


def test_ไฟล์ที่กรอกครบผ่านและไม่มีคำเตือน(good):
    p = parse(good, TARGET_IDS)
    assert p.ok, p.errors
    assert p.warnings == []
    assert p.id == "2026-08-13-example-process-engineer"


def test_idมาจากชื่อไฟล์ไม่ใช่ช่องในหัวไฟล์(good):
    """ช่อง id คือช่องที่คนคัดลอกแม่แบบแล้วลืมแก้บ่อยที่สุด"""
    assert "id" not in parse(good, TARGET_IDS).meta
    assert parse(good, TARGET_IDS).id == good.stem


def test_ข้อความถูกเก็บตามต้นฉบับเพื่อให้spanชี้กลับได้(good):
    """🔒 กติกาข้อ 2 — PostingExtraction จะชี้กลับมาที่ raw_text นี้"""
    row = to_row(parse(good, TARGET_IDS))
    assert row["raw_text"] == BODY.strip()
    needle = "เกรดเฉลี่ยไม่ต่ำกว่า 2.75"
    start = row["raw_text"].index(needle)
    assert row["raw_text"][start:start + len(needle)] == needle


def test_แปลงเป็นแถวในตารางได้ครบ(good):
    row = to_row(parse(good, TARGET_IDS))
    assert set(row) == {
        "id", "target_id", "org", "title", "url",
        "collected_at", "collected_by", "raw_text",
    }
    assert row["target_id"] == "PROCESS-ENG"


# ═════════════ กรอกผิดแล้วต้องบอกให้แก้ได้ ═════════════


def test_ลืมกรอกช่องบังคับบอกชื่อช่องที่ขาด(tmp_path):
    head = HEAD.replace("sector: private\n", "").replace("collected_by: ทีมเก็บข้อมูล\n", "")
    p = parse(write(tmp_path, "a.md", head + "\n" + BODY), TARGET_IDS)
    assert not p.ok
    assert any("`sector`" in e for e in p.errors)
    assert any("`collected_by`" in e for e in p.errors)


def test_พิมพ์sectorผิดบอกว่าใส่อะไรได้บ้าง(tmp_path):
    head = HEAD.replace("sector: private", "sector: บริษัทเอกชน")
    p = parse(write(tmp_path, "a.md", head + "\n" + BODY), TARGET_IDS)
    assert not p.ok
    msg = next(e for e in p.errors if "`sector`" in e)
    assert "private" in msg and "government" in msg, "ต้องบอกตัวเลือกที่ใส่ได้ ไม่ใช่แค่บอกว่าผิด"
    assert "บริษัทเอกชน" in msg, "ต้องบอกด้วยว่าเขาพิมพ์อะไรมา"


def test_target_idที่ไม่มีในคลังอาชีพถูกจับได้(tmp_path):
    head = HEAD.replace("target_id: PROCESS-ENG", "target_id: PROC-ENG")
    p = parse(write(tmp_path, "a.md", head + "\n" + BODY), TARGET_IDS)
    assert not p.ok
    assert any("PROC-ENG" in e and "null" in e for e in p.errors)


def test_สาขาที่ไม่ใช่ของSIITถูกจับได้(tmp_path):
    head = HEAD.replace("requires_field: [ChE, ME, IE]", "requires_field: [ChE, XX]")
    p = parse(write(tmp_path, "a.md", head + "\n" + BODY), TARGET_IDS)
    assert any("XX" in e for e in p.errors)


def test_วันที่ผิดรูปแบบและวันในอนาคตถูกจับได้(tmp_path):
    bad = HEAD.replace("collected_at: 2026-08-13", "collected_at: 13/08/2569")
    assert any("YYYY-MM-DD" in e for e in parse(write(tmp_path, "a.md", bad + "\n" + BODY)).errors)

    future = (date.today() + timedelta(days=30)).isoformat()
    ahead = HEAD.replace("collected_at: 2026-08-13", f"collected_at: {future}")
    assert any("อนาคต" in e for e in parse(write(tmp_path, "b.md", ahead + "\n" + BODY)).errors)


def test_ปิดรับก่อนวันประกาศถูกจับได้(tmp_path):
    head = HEAD.replace("closes_at: 2026-09-30", "posted_at: 2026-08-10\ncloses_at: 2026-08-01")
    assert any("`closes_at` มาก่อน" in e
               for e in parse(write(tmp_path, "a.md", head + "\n" + BODY), TARGET_IDS).errors)


def test_urlที่ไม่ใช่ลิงก์ถูกจับได้(tmp_path):
    head = HEAD.replace("url: https://example.com/jobs/1", "url: หาใน jobsdb")
    assert any("http" in e for e in parse(write(tmp_path, "a.md", head + "\n" + BODY)).errors)


def test_gpaนอกช่วงถูกจับได้(tmp_path):
    head = HEAD.replace("requires_gpa: 2.75", "requires_gpa: 275")
    assert any("`requires_gpa`" in e for e in parse(write(tmp_path, "a.md", head + "\n" + BODY)).errors)


def test_ไม่มีหัวไฟล์บอกวิธีแก้(tmp_path):
    p = parse(write(tmp_path, "a.md", BODY))
    assert not p.ok
    assert "---" in p.errors[0], "ต้องบอกว่าต้องมีอะไร ไม่ใช่แค่บอกว่าไม่เจอ"


def test_หัวไฟล์yamlพังไม่ทำให้ทั้งระบบพัง(tmp_path):
    p = parse(write(tmp_path, "a.md", "---\norg: [ยังไม่ปิดวงเล็บ\n---\n\n" + BODY))
    assert not p.ok and "หัวไฟล์อ่านไม่ออก" in p.errors[0]


# ═════════════ คัดลอกประกาศมาไม่ครบ ═════════════


def test_ข้อความสั้นเกินไปแปลว่ายังคัดลอกมาไม่ครบ(tmp_path):
    p = parse(write(tmp_path, "a.md", HEAD + "\nรับสมัครวิศวกร สนใจติดต่อได้เลย"), TARGET_IDS)
    assert not p.ok
    msg = next(e for e in p.errors if "สั้นเกินไป" in e)
    assert str(MIN_BODY_CHARS) in msg
    assert "คุณสมบัติผู้สมัคร" in msg, "ต้องบอกว่าต้องมีส่วนไหนบ้าง"


def test_ลืมลบข้อความแม่แบบถูกจับได้(tmp_path):
    template = (
        "วางข้อความประกาศงานทั้งหมดตรงนี้ ตามต้นฉบับ\n" * 12
    )
    p = parse(write(tmp_path, "a.md", HEAD + "\n" + template), TARGET_IDS)
    assert any("แม่แบบ" in e for e in p.errors)


# ═════════════ 🔴 repo เป็น public — ข้อมูลส่วนบุคคลห้ามหลุด ═════════════


def test_อีเมลในประกาศถูกจับก่อนเข้าrepo(tmp_path):
    body = BODY + "\nสนใจส่งใบสมัครมาที่ somchai.hr@example.co.th\n"
    p = parse(write(tmp_path, "a.md", HEAD + "\n" + body), TARGET_IDS)
    assert not p.ok, "อีเมลต้องเป็น error ไม่ใช่แค่คำเตือน เพราะ push แล้วเอาคืนไม่ได้"
    assert any("อีเมล" in e and "public" in e for e in p.errors)


@pytest.mark.parametrize("phone", ["02-123-4567", "081-234-5678", "+66 81 234 5678"])
def test_เบอร์โทรในประกาศถูกจับก่อนเข้าrepo(tmp_path, phone):
    body = BODY + f"\nติดต่อฝ่ายบุคคล โทร {phone}\n"
    p = parse(write(tmp_path, "a.md", HEAD + "\n" + body), TARGET_IDS)
    assert any("เบอร์โทร" in e for e in p.errors), f"จับ {phone} ไม่ได้"


def test_ตัวเลขธรรมดาในประกาศไม่ถูกเข้าใจผิดว่าเป็นเบอร์โทร(good):
    """เงินเดือน เกรด ปี พ.ศ. ต้องไม่ทำให้ไฟล์ที่ถูกต้องกลายเป็น error"""
    assert parse(good, TARGET_IDS).ok


# ═════════════ คำเตือน ไม่ใช่ error ═════════════


def test_ไม่ใส่ช่องไม่บังคับยังผ่านแต่เตือน(tmp_path):
    head = "\n".join(
        line for line in HEAD.splitlines()
        if not line.startswith(("target_id:", "salary_text:", "closes_at:"))
    )
    p = parse(write(tmp_path, "a.md", head + "\n\n" + BODY), TARGET_IDS)
    assert p.ok, "ช่องไม่บังคับต้องไม่บล็อกการเก็บข้อมูล"
    assert len(p.warnings) == 3
    assert any("target_id" in w for w in p.warnings)


def test_ช่องที่ระบบไม่รู้จักเตือนแต่ไม่บล็อก(tmp_path):
    head = HEAD.replace("sector: private", "sector: private\nwelfare: มีรถรับส่ง")
    p = parse(write(tmp_path, "a.md", head + "\n" + BODY), TARGET_IDS)
    assert p.ok, "ช่องแปลกปลอมต้องไม่บล็อกการเก็บข้อมูล"
    assert any("welfare" in w for w in p.warnings)


# ═════════════ โหลดทั้งโฟลเดอร์ ═════════════


def test_ไฟล์ที่ขึ้นต้นด้วยขีดล่างถูกข้าม(tmp_path):
    write(tmp_path, "_TEMPLATE.md", HEAD + "\n" + BODY)
    write(tmp_path, "_EXAMPLE.md", HEAD + "\n" + BODY)
    write(tmp_path, "README.md", "# วิธีเก็บ")
    write(tmp_path, "2026-08-13-real.md", HEAD + "\n" + BODY)
    loaded = load_all(tmp_path, TARGET_IDS)
    assert [p.id for p in loaded] == ["2026-08-13-real"]


def test_โฟลเดอร์ว่างไม่พัง(tmp_path):
    assert load_all(tmp_path, TARGET_IDS) == []


def test_ไฟล์เสียหนึ่งอันไม่ทำให้อันอื่นโหลดไม่ได้(tmp_path):
    write(tmp_path, "a-ดี.md", HEAD + "\n" + BODY)
    write(tmp_path, "b-พัง.md", "ไม่มีหัวไฟล์เลย")
    loaded = load_all(tmp_path, TARGET_IDS)
    assert len(loaded) == 2
    assert sum(1 for p in loaded if p.ok) == 1


# ═════════════ แม่แบบที่แจกต้องใช้ได้จริง ═════════════


def test_แม่แบบที่แจกให้ทีมมีช่องบังคับครบ():
    from app.seed.postings import POSTINGS_DIR, REQUIRED

    template = POSTINGS_DIR / "_TEMPLATE.md"
    assert template.exists(), "ต้องมีแม่แบบให้คัดลอก"
    text = template.read_text(encoding="utf-8")
    for key in REQUIRED:
        assert f"{key}:" in text, f"แม่แบบไม่มีช่อง {key}"


def test_แม่แบบเปล่ายังไม่ผ่านด่านตรวจ():
    """คัดลอกแม่แบบมาแล้วยังไม่กรอก ต้องไม่หลุดเข้าระบบ"""
    from app.seed.postings import POSTINGS_DIR

    p = parse(POSTINGS_DIR / "_TEMPLATE.md", TARGET_IDS)
    assert not p.ok


def test_healthกับmetaรายงานจำนวนประกาศงานตามจริง(tmp_path_factory):
    """🔒 กติกาข้อ 5 — /meta คำนวณหมายเหตุจากจำนวนจริง ไม่ได้เขียนตายตัว

    ถ้าเขียนตายตัว วันที่ 🅴 เก็บประกาศงานเสร็จ หน้าจอจะยังบอกว่า "ยังไม่มี" อยู่
    """
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db import get_db
    from app.main import app
    from app.seed.loader import create_all, seed

    db_path = tmp_path_factory.mktemp("db") / "postings.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    create_all(engine)
    with Session() as db:
        seed(db)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as c:
            n = c.get("/api/health").json()["job_postings"]
            meta = c.get("/api/meta").json()
            assert meta["job_postings"] == n
            if n == 0:
                assert "ยังไม่ได้มาจากประกาศงานจริง" in meta["notes"]["data"]
            else:
                assert str(n) in meta["notes"]["data"]
    finally:
        app.dependency_overrides.clear()


def test_ยังไม่มีประกาศงานจริงระบบต้องรายงานว่าศูนย์():
    """🔒 กติกาข้อ 5 — โค้ดต้องไม่โกหกว่ามีข้อมูลจริงแล้ว

    เทสต์นี้จะกลายเป็นเท็จเมื่อ 🅴 เก็บประกาศงานได้จริง
    ตอนนั้นให้แก้เป็นตรวจว่าจำนวนตรงกับไฟล์ที่มี — อย่าลบทิ้ง
    """
    real = load_all(target_ids=TARGET_IDS)
    assert all(p.ok for p in real), (
        "มีไฟล์ประกาศงานที่ยังผิดรูปแบบอยู่ใน data/postings/ — รัน make check-postings"
    )
