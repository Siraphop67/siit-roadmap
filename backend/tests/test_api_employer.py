"""ฝั่งบริษัทลงประกาศรับสมัคร

สองข้อที่เทสต์ในไฟล์นี้เฝ้าอยู่ และเป็นสองข้อที่ถ้าหลุดแล้วเสียหายจริง:

  ① ประกาศจากบริษัทต้องไม่ขึ้นถึงนักศึกษาโดยไม่มีคนตรวจ
     ระบบนี้ไม่มีการยืนยันตัวตนองค์กร ฟอร์มเปิดโล่งที่ขึ้นจอทันทีคือช่องทาง
     ประกาศงานปลอมที่เล็งนักศึกษา ซึ่งเป็นการหลอกลวงที่เกิดขึ้นจริง

  ② บริษัทต้องไม่เห็นข้อมูลนักศึกษาเลย
     ไม่มีรายชื่อ ไม่มีโปรไฟล์ ไม่มี CV — ระบบนี้เป็นทางเดียวโดยการออกแบบ
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api_employer import ADMIN_TOKEN_ENV
from app.db import get_db
from app.main import app
from app.seed.loader import create_all, seed

# 🔴 token ต้องเป็น ASCII — HTTP header ส่งอักษรไทยไม่ได้
TOKEN = "test-review-token-abc123"

BODY = (
    "หน้าที่ความรับผิดชอบ\n"
    "- ดูแลกระบวนการผลิตประจำวัน ตรวจค่าที่วิ่งอยู่บนหน้าจอควบคุมตลอดกะ\n"
    "- ไล่หาสาเหตุเมื่อของเสียเกินเกณฑ์ แล้วเสนอวิธีแก้ต่อหัวหน้าไลน์\n"
    "- ทำรายงานสรุปประสิทธิภาพรายสัปดาห์ด้วย Excel และนำเสนอในที่ประชุม\n"
    "คุณสมบัติผู้สมัคร\n"
    "- จบปริญญาตรีวิศวกรรมเคมี เครื่องกล หรืออุตสาหการ เกรดไม่ต่ำกว่า 2.75\n"
    "- เขียน Python วิเคราะห์ข้อมูลได้จะพิจารณาเป็นพิเศษ ทำงานเป็นทีมได้ดี\n"
)

SUBMISSION = {
    "org": "บริษัททดสอบ จำกัด",
    "title": "Process Engineer",
    "url": "https://example.com/jobs/1",
    "sector": "private",
    "employment_type": "new_grad",
    "raw_text": BODY,
    "target_id": "PROCESS-ENG",
    "submitted_by": "ฝ่ายบุคคล",
    "contact_email": "jobs@example.com",
}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "employer.db"
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
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def admin(monkeypatch):
    monkeypatch.setenv(ADMIN_TOKEN_ENV, TOKEN)
    return {"X-Review-Token": TOKEN}


def submit(client, **overrides) -> dict:
    r = client.post("/api/employer/posting", json={**SUBMISSION, **overrides})
    assert r.status_code == 200, r.json()
    return r.json()


# ═════════════ ① ต้องมีคนตรวจก่อนขึ้นจอ ═════════════


def test_ประกาศที่ส่งเข้ามาเริ่มที่รออนุมัติเสมอ(client):
    r = submit(client)
    assert r["status"] == "pending"
    assert "ยังไม่ขึ้น" in r["message"]

    got = client.get(f"/api/employer/posting/{r['posting_id']}").json()
    assert got["status"] == "pending"
    assert got["status_th"] == "รอทีมตรวจ"


def test_posting_idเป็นasciiล้วนแม้ชื่อบริษัทเป็นไทย(client):
    """id ไปอยู่ใน URL path — อักษรไทยในนั้นทำให้ curl/urllib/log พังหรืออ่านไม่ออก

    เจอตอนเดินจริง: ชื่อ "บริษัทเดโม จำกัด" ทำให้ id มีอักษรไทย แล้ว urllib
    โยน UnicodeEncodeError ทันทีตอนจะเรียก endpoint รีวิว
    """
    pid = submit(client, org="บริษัทชื่อไทยล้วน จำกัด")["posting_id"]
    assert pid.isascii(), f"id มีอักษรนอก ASCII: {pid}"
    assert client.get(f"/api/employer/posting/{pid}").status_code == 200

    # ชื่อที่มีอังกฤษปนยังอ่านออกอยู่
    assert "scg-chemicals" in submit(client, org="SCG Chemicals จำกัด")["posting_id"]


def test_ข้อความที่บริษัทเห็นไม่ใช้ชื่อฟิลด์ในโค้ด(client):
    """คำเตือนที่โชว์ HR ต้องเป็นชื่อช่องบนฟอร์ม ไม่ใช่ `target_id`

    คลาสเดียวกับข้อความ "repo เป็น public" — ข้อความที่เขียนไว้สำหรับทีม
    ไม่ควรหลุดไปถึงคนนอกที่ไม่มีบริบท
    """
    r = client.post("/api/employer/posting", json={
        k: v for k, v in SUBMISSION.items() if k != "target_id"})
    warnings = r.json()["warnings"]
    assert warnings
    for w in warnings:
        assert "`" not in w, f"คำเตือนยังใช้ชื่อฟิลด์ในโค้ด: {w}"
    assert any("อาชีพที่ตรงที่สุด" in w for w in warnings), "ต้องใช้ชื่อช่องเดียวกับบนฟอร์ม"


def test_ไม่มีทางลัดให้ส่งมาแล้วอนุมัติเลย(client):
    """ส่ง status มาเองต้องไม่มีผล"""
    r = client.post("/api/employer/posting", json={**SUBMISSION, "status": "approved"})
    assert r.status_code == 200
    assert r.json()["status"] == "pending"


def test_ประกาศที่รออนุมัติไม่ถูกนับให้อาชีพ(client):
    """ถ้านับตั้งแต่รอคิว ใครก็ดัน requirement ของอาชีพได้โดยไม่ต้องผ่านใคร"""
    before = client.get("/api/targets/PROCESS-ENG").json()
    submit(client)
    after = client.get("/api/targets/PROCESS-ENG").json()
    assert before["requirements"] == after["requirements"]


def test_อนุมัติแล้วสถานะเปลี่ยนและบอกขั้นตอนต่อ(client, admin):
    pid = submit(client)["posting_id"]
    r = client.post(f"/api/employer/review/{pid}",
                    json={"decision": "approved"}, headers=admin)
    assert r.status_code == 200
    assert r.json()["status"] == "approved"
    assert "make postings" in r.json()["next_step"], "ต้องบอกว่าต้องรันท่อขั้นที่ 2 ต่อ"

    got = client.get(f"/api/employer/posting/{pid}").json()
    assert got["status_th"] == "ผ่านแล้ว — นักศึกษาเห็นประกาศนี้ได้"
    assert got["reviewed_at"]


def test_ปฏิเสธได้พร้อมเหตุผล(client, admin):
    pid = submit(client, org="บริษัทน่าสงสัย จำกัด")["posting_id"]
    client.post(f"/api/employer/review/{pid}",
                json={"decision": "rejected", "note": "หาองค์กรนี้ไม่เจอ"}, headers=admin)
    got = client.get(f"/api/employer/posting/{pid}").json()
    assert got["status"] == "rejected"
    assert got["review_note"] == "หาองค์กรนี้ไม่เจอ"


# ═════════════ 🔒 หน้ารีวิวต้องมี token ═════════════


def test_ไม่มีtokenเข้าคิวรีวิวไม่ได้(client, admin):
    assert client.get("/api/employer/review").status_code == 401
    assert client.get("/api/employer/review",
                      headers={"X-Review-Token": "wrong-guess"}).status_code == 401
    assert client.get("/api/employer/review", headers=admin).status_code == 200


def test_ไม่ตั้งtokenในenvหน้ารีวิวปิดสนิท(client, monkeypatch):
    """ปิดไว้ปลอดภัยกว่าเปิดทิ้งโดยไม่มีใครรู้"""
    monkeypatch.delenv(ADMIN_TOKEN_ENV, raising=False)
    r = client.get("/api/employer/review", headers={"X-Review-Token": ""})
    assert r.status_code == 503
    assert ADMIN_TOKEN_ENV in r.json()["detail"]


def test_คิวรีวิวมีข้อความเต็มและรายการที่ต้องตรวจ(client, admin):
    submit(client, org="บริษัทรอตรวจ จำกัด")
    q = client.get("/api/employer/review", headers=admin).json()
    assert q["count"] >= 1
    row = q["postings"][0]
    assert row["raw_text"], "คนตรวจต้องอ่านของจริง ไม่ใช่อ่านสรุป"
    assert any("เงิน" in c or "บัตรประชาชน" in c for c in q["checklist"]), (
        "รายการตรวจต้องเตือนเรื่องกลโกงที่พบบ่อย"
    )


# ═════════════ ② บริษัทไม่เห็นข้อมูลนักศึกษา ═════════════


def test_ไม่มีendpointไหนของบริษัทคืนข้อมูลนักศึกษา(client, admin):
    """เทสต์นี้จะแดงทันทีถ้ามีใครเพิ่ม endpoint ที่ส่งข้อมูลนักศึกษาให้ฝั่งบริษัท"""
    student = client.post("/api/session", json={"entry": "known"}).json()["user_id"]
    client.post("/api/profile", json={"user_id": student, "field": "CPE", "gpa": 3.5})
    client.post("/api/portfolio/text", json={
        "user_id": student, "text": BODY + "ใช้ Python และ Git ทำโปรเจกต์", "consent": True})

    pid = submit(client)["posting_id"]
    responses = [
        client.get(f"/api/employer/posting/{pid}").text,
        client.get("/api/employer/review", headers=admin).text,
        client.get("/api/employer/meta").text,
    ]
    for text in responses:
        assert student not in text, "user_id ของนักศึกษาห้ามโผล่ในฝั่งบริษัท"
        for leak in ("skills_from_cv", "self_reported", "raw_text_cv", "extracted"):
            assert leak not in text, f"ฟิลด์ '{leak}' รั่วไปฝั่งบริษัท"


def test_บริษัทอื่นดูประกาศของกันไม่ได้ถ้าไม่มีid(client):
    """id ที่สุ่มมาเป็นกุญแจ — เดาไม่ได้ และไม่มี endpoint ที่ list ประกาศทั้งหมดโดยไม่มี token"""
    assert client.get("/api/employer/posting/emp-2026-08-13-มั่ว-abc123").status_code == 404
    assert client.get("/api/employer/review").status_code in (401, 503)


# ═════════════ ด่านตรวจชุดเดียวกับไฟล์ที่ทีมเก็บ ═════════════


def test_ใช้ด่านตรวจชุดเดียวกับไฟล์ไม่ใช่ชุดที่หลวมกว่า(client):
    """ถ้าฝั่งฟอร์มหลวมกว่า มันจะกลายเป็นประตูหลังทันที"""
    r = client.post("/api/employer/posting", json={**SUBMISSION, "raw_text": "รับสมัครวิศวกร"})
    assert r.status_code == 422
    assert any("สั้นเกินไป" in e for e in r.json()["detail"]["errors"])

    r = client.post("/api/employer/posting", json={**SUBMISSION, "sector": "บริษัทเอกชน"})
    assert r.status_code == 422
    assert any("`sector`" in e for e in r.json()["detail"]["errors"])

    r = client.post("/api/employer/posting", json={**SUBMISSION, "target_id": "ไม่มีจริง"})
    assert r.status_code == 422


def test_อีเมลในตัวประกาศถูกปฏิเสธแต่ช่องติดต่อแยกใส่ได้(client):
    """คนละเรื่องกัน — ในตัวประกาศคือข้อมูลที่อาจไม่ได้ยินยอม ในช่องติดต่อคือเจ้าของกรอกเอง"""
    r = client.post("/api/employer/posting", json={
        **SUBMISSION, "raw_text": BODY + "\nส่งใบสมัครมาที่ hr@example.com"})
    assert r.status_code == 422
    msg = next(e for e in r.json()["detail"]["errors"] if "อีเมล" in e)
    # 🔴 ข้อความต้องเขียนถึงบริษัท ไม่ใช่ถึงทีม — บริษัทไม่รู้จัก repo
    #    และประกาศที่เขาส่งไม่ได้เข้า repo ด้วยซ้ำ
    assert "repo" not in msg, f"ข้อความเขียนถึงคนผิดกลุ่ม: {msg}"
    assert "ช่องอีเมลติดต่อ" in msg, "ต้องบอกทางออกว่าให้ย้ายไปช่องไหน"

    assert submit(client, contact_email="hr@example.com")["status"] == "pending"


def test_อีเมลติดต่อผิดรูปแบบถูกจับ(client):
    r = client.post("/api/employer/posting", json={**SUBMISSION, "contact_email": "ไม่ใช่อีเมล"})
    assert r.status_code == 422
    assert any("contact_email" in e for e in r.json()["detail"]["errors"])


def test_ส่งข้อผิดพลาดกลับทุกข้อพร้อมกัน(client):
    """คนกรอกจะได้แก้รอบเดียว ไม่ใช่แก้ทีละข้อแล้วส่งใหม่ห้ารอบ"""
    r = client.post("/api/employer/posting", json={
        **SUBMISSION, "sector": "มั่ว", "employment_type": "มั่ว", "raw_text": "สั้น"})
    assert len(r.json()["detail"]["errors"]) >= 3


# ═════════════ meta สำหรับหน้าฟอร์ม ═════════════


def test_metaบอกตัวเลือกและบอกกติกาความเป็นส่วนตัว(client):
    m = client.get("/api/employer/meta").json()
    assert set(m["sectors"]) == {"private", "government", "state_enterprise", "academic"}
    assert m["employment_types"]
    assert len(m["targets"]) == 8
    assert "ไม่เห็นข้อมูลนักศึกษา" in m["notes"]["privacy"], (
        "หน้าฟอร์มต้องบอกบริษัทตรง ๆ ว่าจะไม่ได้เห็นข้อมูลนักศึกษา"
    )
    assert "ตรวจ" in m["notes"]["review"]
