"""ให้ผู้ใช้เลือกเองว่าจะให้อ่าน repo ไหน — ชั้น API

สองขั้น แยกกันโดยตั้งใจ:

    POST /portfolio/github/list   ขอรายชื่อมาให้เลือก  🔓 ไม่เก็บอะไร ไม่ต้องยินยอม
    POST /portfolio/github        อ่านเฉพาะที่เลือก     🔒 ต้องยินยอมก่อน

🔴 เหตุผลที่ขั้นแรกไม่ต้องขอความยินยอม — มันยังไม่ได้อ่านผลงานของใคร แค่ถามว่ามี repo
   อะไรบ้าง · ถ้าไปบังคับให้ยินยอมตั้งแต่ตอนนั้น เท่ากับขอความยินยอมก่อนที่ผู้ใช้จะรู้ว่า
   กำลังยินยอมให้อ่านอะไร ซึ่งกลับหัวกลับหางกับทั้งฟีเจอร์นี้
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import get_db
from app.main import app
from app.seed.loader import create_all, seed

OWNER = "nicha-example"

REPO_LIST = [
    {"name": "cv-analyzer", "description": "อ่าน CV", "language": "Python",
     "updated_at": "2026-08-01T00:00:00Z", "fork": False},
    {"name": "math-notes", "description": "", "language": None,
     "updated_at": "2026-05-01T00:00:00Z", "fork": False},
    {"name": "forked-thing", "description": "", "language": "Go",
     "updated_at": "2026-09-01T00:00:00Z", "fork": True},
]

README = ("ดูแลโค้ดด้วย Git และเขียน unit test ด้วย pytest ทุกฟีเจอร์ "
          "สร้าง REST API ด้วย FastAPI ต่อกับ PostgreSQL")


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == f"/users/{OWNER}/repos":
        return httpx.Response(200, json=REPO_LIST)
    if path.endswith("/languages"):
        return httpx.Response(200, json={"Python": 1})
    if path.endswith("/readme"):
        return httpx.Response(200, text=f"# {path.split('/')[3]}\n{README}")
    if path.startswith(f"/repos/{OWNER}/"):
        return httpx.Response(200, json={"description": "คำอธิบาย"})
    return httpx.Response(404, json={"message": "Not Found"})


@pytest.fixture(autouse=True)
def _no_real_github(monkeypatch):
    """ไม่ยิง GitHub จริงสักครั้ง — เทสต์ต้องได้ผลเดิมทุกครั้งและไม่ง้อเน็ต"""
    real = httpx.Client

    def fake(*args, **kwargs):
        kwargs.pop("transport", None)
        return real(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr("app.ingest.httpx.Client", fake)


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "ghselect.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    create_all(engine)
    with TestingSession() as db:
        seed(db)

    def override():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def user(client) -> str:
    return client.post("/api/session", json={"entry": "known"}).json()["user_id"]


URL = f"https://github.com/{OWNER}"


# ═════════════ ขั้นที่ 1 — ขอรายชื่อมาเลือก ═════════════


def test_คืนรายชื่อrepoให้เลือก(client):
    r = client.post("/api/portfolio/github/list", json={"url": URL})
    assert r.status_code == 200, r.text
    assert [x["name"] for x in r.json()["repos"]] == ["cv-analyzer", "math-notes"]


def test_ขั้นขอรายชื่อไม่ต้องส่งความยินยอมมา(client):
    """ยังไม่ได้อ่านผลงานของใคร จึงยังไม่ถึงเวลาขอความยินยอม"""
    assert client.post("/api/portfolio/github/list", json={"url": URL}).status_code == 200


def test_ขั้นขอรายชื่อไม่เก็บเอกสารลงฐานข้อมูล(client, user):
    before = client.get("/api/me", params={"user_id": user}).json()
    client.post("/api/portfolio/github/list", json={"url": URL})
    after = client.get("/api/me", params={"user_id": user}).json()
    assert before.get("documents") == after.get("documents")


def test_บอกด้วยว่าrepoส่วนตัวไม่แสดงที่นี่(client):
    """🔒 กติกาข้อ 5 — ผู้ใช้ต้องไม่เข้าใจว่ารายการนี้คือผลงานทั้งหมดที่เขามี"""
    note = client.post("/api/portfolio/github/list", json={"url": URL}).json()["note"]
    assert "ส่วนตัว" in note


def test_ลิงก์ที่ไม่ใช่githubตอบ400พร้อมบอกรูปแบบที่ถูก(client):
    r = client.post("/api/portfolio/github/list", json={"url": "https://gitlab.com/x"})
    assert r.status_code == 400
    assert "github" in r.json()["detail"].lower()


# ═════════════ ขั้นที่ 2 — อ่านเฉพาะที่เลือก ═════════════


def test_อ่านเฉพาะrepoที่เลือก(client, user):
    r = client.post("/api/portfolio/github", json={
        "user_id": user, "url": URL, "repos": ["math-notes"], "consent": True})
    assert r.status_code == 200, r.text

    doc = client.get(f"/api/portfolio/{r.json()['document_id']}").json()
    assert "math-notes" in doc["raw_text"]
    assert "cv-analyzer" not in doc["raw_text"]


def test_ไม่ส่งrepoมาทำงานเหมือนเดิม(client, user):
    """ของเดิมต้องไม่พัง — หน้าจอเก่าที่ยังไม่ได้อัปเดตยังใช้ได้"""
    r = client.post("/api/portfolio/github", json={
        "user_id": user, "url": URL, "consent": True})
    assert r.status_code == 200, r.text
    assert r.json()["extracted_count"] >= 1


def test_เลือกศูนย์อันตอบ400ไม่ใช่เงียบๆอ่านทั้งหมด(client, user):
    """🔴 ถ้าตีความลิสต์ว่างว่า "ไม่ได้เลือก = เอาหมด" ระบบจะอ่านทุก repo
    ทั้งที่ผู้ใช้ไม่ได้ติ๊กอะไรเลย ซึ่งตรงข้ามกับทั้งฟีเจอร์นี้
    """
    r = client.post("/api/portfolio/github", json={
        "user_id": user, "url": URL, "repos": [], "consent": True})
    assert r.status_code == 400
    assert "เลือก" in r.json()["detail"]


def test_ยังบังคับความยินยอมเหมือนเดิม(client, user):
    """เลือก repo แล้วก็ยังต้องยินยอมอยู่ดี — คนละเรื่องกัน"""
    r = client.post("/api/portfolio/github", json={
        "user_id": user, "url": URL, "repos": ["math-notes"], "consent": False})
    assert r.status_code == 400
    assert "ยินยอม" in r.json()["detail"]


@pytest.mark.parametrize("evil", ["../../users/someone", "name with space", "x?y=1"])
def test_ชื่อrepoที่ผิดรูปแบบตอบ400(client, user, evil):
    r = client.post("/api/portfolio/github", json={
        "user_id": user, "url": URL, "repos": [evil], "consent": True})
    assert r.status_code == 400


def test_repoที่ไม่ใช่ของบัญชีนี้ตอบ400(client, user):
    r = client.post("/api/portfolio/github", json={
        "user_id": user, "url": URL, "repos": ["ไม่ใช่ของเขา"], "consent": True})
    assert r.status_code == 400


def test_noteบอกว่าอ่านตามที่ผู้ใช้เลือก(client, user):
    """🔒 กติกาข้อ 5 — "คุณเลือก" กับ "ระบบเลือกให้" ต้องไม่เขียนเหมือนกัน"""
    r = client.post("/api/portfolio/github", json={
        "user_id": user, "url": URL, "repos": ["math-notes"], "consent": True})
    assert "เลือก" in r.json()["note"]
