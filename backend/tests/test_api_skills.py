"""กราฟทักษะทั้งใบ — `GET /api/skills` · `GET /api/skills/{id}`

เทสต์ในไฟล์นี้ไม่ได้ตรวจแค่ว่า endpoint ตอบ 200 — ตรวจว่ากราฟที่หน้าจอได้รับ
เป็นกราฟจริง และกติกาที่พังง่ายที่สุดเวลามีคนไปแก้ยังเป็นจริงอยู่:
  · เส้นทุกเส้นต้องมีปลายทั้งสองข้างอยู่ในชุด node ที่ส่งไปด้วยกัน
  · ทักษะจาก CV กับที่กรอกเองต้องอยู่คนละฟิลด์ ไม่มีตัวเลขไหนรวมสองอย่างนี้
  · ทักษะที่สกัดมาแล้วแต่ผู้ใช้ยังไม่ยืนยัน ต้องไม่ขึ้นกราฟ
  · node ที่ยังไม่มีชื่ออังกฤษจาก O*NET ต้องบอกว่ามันเป็น placeholder
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import get_db
from app.main import app
from app.seed.loader import create_all, seed

CV = """สมชาย ใจดี — นักศึกษาวิศวกรรมคอมพิวเตอร์ ปี 3

โครงงานและประสบการณ์
- ทำระบบวิเคราะห์ข้อมูลการใช้ห้องเรียนด้วย Python และ pandas
- สร้าง REST API ด้วย FastAPI ต่อกับ PostgreSQL ใช้ SQL ดึงข้อมูล
- ดูแลโค้ดด้วย Git เขียน unit test ด้วย pytest ทุกฟีเจอร์
"""


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "skills.db"
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


@pytest.fixture(scope="module")
def graph(client) -> dict:
    r = client.get("/api/skills")
    assert r.status_code == 200, r.text
    return r.json()


# ═══════════ กราฟต้องเป็นกราฟจริง ═══════════


def test_graph_has_nodes_and_edges(graph):
    assert graph["counts"]["skills"] == len(graph["nodes"]) > 0
    assert graph["counts"]["edges"] == len(graph["edges"]) > 0


def test_every_edge_lands_on_a_node_we_actually_sent(graph):
    """🔴 เส้นที่ชี้ไปยัง node ที่ไม่ได้ส่งไปด้วย = หน้าจอวาดเส้นลอย"""
    ids = {n["id"] for n in graph["nodes"]}
    for e in graph["edges"]:
        assert e["from"] in ids, e
        assert e["to"] in ids, e


def test_graph_has_roots_to_start_drawing_from(graph):
    roots = [n for n in graph["nodes"] if n["prereq_count"] == 0]
    assert roots, "ไม่มีทักษะที่เริ่มได้เลย แปลว่ากราฟเป็นวง"
    assert graph["counts"]["roots"] == len(roots)


def test_categories_cover_every_node(graph):
    """หมวดที่ส่งไปทำ legend ต้องบวกกันได้เท่าจำนวน node พอดี ไม่ตกหล่น"""
    assert sum(c["count"] for c in graph["categories"]) == len(graph["nodes"])
    for c in graph["categories"]:
        assert c["label_th"] != c["id"], f"หมวด {c['id']} ยังไม่มีชื่อไทย"


def test_placeholder_labels_are_declared(graph):
    """🔒 กติกาข้อ 5 — ทักษะที่ไม่มีตัวตรงใน O*NET ชื่ออังกฤษจะเท่ากับรหัส ต้องบอกไว้"""
    fake = [n for n in graph["nodes"] if n["name_en"] == n["id"]]
    for n in graph["nodes"]:
        assert n["name_en_is_placeholder"] == (n["name_en"] == n["id"])
        assert n["name_th"], f"{n['id']} ไม่มีชื่อไทย จะไม่เหลืออะไรให้ขึ้นจอ"
    if fake:
        assert str(len(fake)) in graph["notes"]["labels"]


# ═══════════ ยังไม่ล็อกอินก็ต้องดูกราฟได้ ═══════════


def test_anonymous_sees_the_graph_without_any_levels(graph):
    assert graph["you"] is None
    for n in graph["nodes"]:
        assert n["level_from_cv"] is None
        assert n["level_self_reported"] is None


def test_unknown_user_is_refused(client):
    assert client.get("/api/skills", params={"user_id": "ไม่มีคนนี้"}).status_code == 404


# ═══════════ กติกาข้อ 1 — CV กับที่กรอกเอง แยกกันเสมอ ═══════════


def test_self_reported_never_shows_up_as_cv_evidence(client, user):
    """🔒 กรอกเองว่าทำ Python ได้ ต้องไม่ทำให้ช่อง "จาก CV" มีค่าขึ้นมา"""
    client.post("/api/profile", json={
        "user_id": user, "field": "ce", "self_reported_skills": {"T-PY": 3}})

    nodes = {n["id"]: n for n in client.get(
        "/api/skills", params={"user_id": user}).json()["nodes"]}
    assert nodes["T-PY"]["level_self_reported"] == 3
    assert nodes["T-PY"]["level_from_cv"] is None

    detail = client.get("/api/skills/T-PY", params={"user_id": user}).json()
    assert detail["you"]["level_self_reported"] == 3
    assert detail["you"]["level_from_cv"] is None
    assert detail["you"]["evidence"] == []


def test_no_field_merges_the_two_kinds_of_evidence(client, user):
    """ถ้ามีใครเพิ่มฟิลด์รวมเข้ามาในอนาคต เทสต์นี้จะแดง — ตั้งใจให้แดง"""
    client.post("/api/profile", json={
        "user_id": user, "self_reported_skills": {"T-PY": 2}})
    node = next(n for n in client.get(
        "/api/skills", params={"user_id": user}).json()["nodes"] if n["id"] == "T-PY")
    assert "level" not in node
    assert {k for k in node if k.startswith("level_")} == {
        "level_from_cv", "level_self_reported"}


# ═══════════ กติกาข้อ 3 — ยังไม่ยืนยัน = ยังไม่นับ ═══════════


def test_pending_extraction_stays_off_the_graph_until_confirmed(client, user):
    doc = client.post("/api/portfolio/text", json={
        "user_id": user, "text": CV, "consent": True}).json()
    doc_id = doc["document_id"]
    extracted = client.get(f"/api/portfolio/{doc_id}").json()["extracted"]
    assert extracted, "สกัดอะไรไม่ได้เลย เทสต์นี้ก็ไม่ได้ตรวจอะไร"

    target = extracted[0]
    before = next(n for n in client.get(
        "/api/skills", params={"user_id": user}).json()["nodes"]
        if n["id"] == target["skill_id"])
    assert before["level_from_cv"] is None, "ยัง pending อยู่ ห้ามนับ"

    client.post(f"/api/portfolio/{doc_id}/confirm", json={
        "user_id": user, "decisions": {target["id"]: "confirmed"}})

    after = next(n for n in client.get(
        "/api/skills", params={"user_id": user}).json()["nodes"]
        if n["id"] == target["skill_id"])
    assert after["level_from_cv"] == target["level"]

    detail = client.get(f"/api/skills/{target['skill_id']}",
                        params={"user_id": user}).json()
    # 🔒 กติกาข้อ 2 — หลักฐานจาก CV ต้องชี้กลับไปที่ข้อความจริงได้เสมอ
    assert detail["you"]["evidence"]
    assert detail["you"]["evidence"][0]["span_text"]


# ═══════════ รายละเอียดทักษะรายตัว ═══════════


def test_detail_lists_careers_and_resources(client):
    d = client.get("/api/skills/T-PY").json()
    assert d["id"] == "T-PY"
    assert d["supported_careers"], "ทักษะนี้ไม่มีอาชีพไหนต้องการเลย น่าจะผิด"
    assert d["resources"], "ไม่มีทางไปถึงทักษะนี้เลย roadmap จะตัน"
    for c in d["supported_careers"]:
        assert c["title_th"]
        # 🔒 กติกาข้อ 5 — ต้องแยกออกว่าข้อไหนยืนยันจากประกาศจริง ข้อไหนทีมเขียนเอง
        assert c["source"] in {"curated", "postings", "both"}
    for r in d["resources"]:
        assert r["kind_label"] != r["kind"], "ยังไม่ได้แปลชนิดแหล่งเรียนเป็นไทย"
        assert 1 <= r["reaches_level"] <= 3


def test_detail_matches_the_graph_edges(client, graph):
    """prereq / unlock ที่ส่งในหน้ารายละเอียด ต้องตรงกับเส้นในกราฟใหญ่เป๊ะ"""
    d = client.get("/api/skills/T-GIT").json()
    prereqs = {e["from"] for e in graph["edges"] if e["to"] == "T-GIT"}
    unlocks = {e["to"] for e in graph["edges"] if e["from"] == "T-GIT"}
    assert {p["id"] for p in d["prereqs"]} == prereqs
    assert {u["id"] for u in d["unlocks"]} == unlocks
    assert d["unlocks_total"] >= len(d["unlocks"])


def test_detail_of_a_leaf_skill_is_still_valid(client, graph):
    leaf = next(n for n in graph["nodes"] if n["unlock_count"] == 0)
    d = client.get(f"/api/skills/{leaf['id']}").json()
    assert d["unlocks"] == []
    assert d["unlocks_total"] == 0


def test_unknown_skill_is_404(client):
    r = client.get("/api/skills/ไม่มีทักษะนี้")
    assert r.status_code == 404
    assert "ไม่พบทักษะ" in r.json()["detail"]
