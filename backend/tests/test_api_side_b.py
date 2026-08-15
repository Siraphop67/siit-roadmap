"""เดินครบวงจรฝั่ง "รู้แล้วว่าอยากไปไหน" ผ่าน API จริง

หน้าแรก → คลังอาชีพ → โปรไฟล์ → ส่งผลงาน → ตรวจผลสกัด → เลือกเป้าหมาย → ROADMAP → ลบข้อมูล
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
- ทำ dashboard ด้วย Power BI ให้หัวหน้าไลน์ดูของเสียรายวัน
- ใช้ Docker และ Linux ในการ deploy
TOEIC 780
"""


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "sideb.db"
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


# ═══════════ ข้อมูลตั้งต้น ═══════════


def test_health_reports_what_actually_loaded(client):
    h = client.get("/api/health").json()
    assert h["skills"] == 73
    assert h["skill_edges"] == 105
    assert h["career_targets"] == 8
    assert h["learning_resources"] == 72
    assert h["extractor_is_real_llm"] is False, "ยังไม่มี LLM key — ต้องรายงานตามจริง"


def test_character_build_and_quest_progress_are_separate_from_skill_evidence(client, user):
    build = client.put("/api/character-build", json={
        "user_id": user, "archetype": "builder", "playstyle": "create",
        "intensity": "steady", "completed_missions": 4,
    })
    assert build.status_code == 200
    assert client.get("/api/character-build", params={"user_id": user}).json()["build"]["archetype"] == "builder"

    started = client.post("/api/quests/C-PY-INTRO/start", json={"user_id": user})
    assert started.status_code == 200 and started.json()["status"] == "started"
    completed = client.post("/api/quests/C-PY-INTRO/complete", json={"user_id": user})
    assert completed.status_code == 200 and completed.json()["status"] == "completed"
    assert completed.json()["unlocked_preview"]

    progress = client.get("/api/quests", params={"user_id": user}).json()
    assert progress["counts"] == {"started": 1, "completed": 1}
    assert {b["id"] for b in progress["badges"]} >= {"first-quest", "quest-finisher"}
    assert client.get("/api/resources/C-PY-INTRO", params={"user_id": user}).json()["quest"]["status"] == "completed"


def test_meta_states_plainly_what_is_not_real_yet(client):
    m = client.get("/api/meta").json()
    assert len(m["fields"]) == 7
    assert "ประกาศงานจริง" in m["notes"]["data"]
    assert "ไม่ใช่ LLM" in m["notes"]["extractor"]


def test_meta_reports_the_real_extractor(client, monkeypatch):
    """🔒 กติกาข้อ 5 — สลับไปใช้ LLM จริงแล้ว หน้าจอต้องเลิกพูดว่า "ไม่ใช่ LLM"

    เจอตอนสลับ LLM_PROVIDER=local เพื่อทดสอบ: /health บอกว่าเป็น LLM แล้ว
    แต่ข้อความใน /meta ยังเขียนตายตัวว่าใช้การจับคำสำคัญ — ซึ่งขึ้นจอตรง ๆ
    """
    from app.config import settings

    monkeypatch.setattr(settings, "llm_provider", "local")
    monkeypatch.setattr(settings, "local_llm_model", "gemma4:26b")
    m = client.get("/api/meta").json()

    assert m["extractor"] == "local"
    assert "ไม่ใช่ LLM" not in m["notes"]["extractor"], "ใช้ LLM อยู่ ห้ามบอกว่าไม่ใช่"
    assert "gemma4:26b" in m["notes"]["extractor"], "ต้องบอกด้วยว่าอ่านด้วยรุ่นไหน"
    # ⭐ ต่อให้เป็น LLM จริง กติกาข้อ 2 กับ 3 ก็ยังต้องถูกย้ำบนหน้าจอ
    assert "ยืนยัน" in m["notes"]["extractor"]


# ═══════════ คลังอาชีพ ═══════════


def test_targets_list_covers_every_field(client):
    data = client.get("/api/targets").json()
    covered = {f for t in data["targets"] for f in t["field_whitelist"]}
    assert covered == {"CE", "CPE", "ChE", "EE", "IE", "ME", "DE"}


def test_target_detail_shows_requirements_and_admits_missing_data(client):
    d = client.get("/api/targets/SW-DEV").json()
    assert d["requirements"]
    assert d["data_status"] == "placeholder"
    assert all(r["appears_in_n_postings"] == 0 for r in d["requirements"]), (
        "ยังไม่ได้เก็บประกาศงานจริง จำนวนต้องเป็น 0 ไม่ใช่ตัวเลขที่แต่งขึ้น"
    )


def test_cards_carry_their_top_skills_in_importance_order(client):
    """ป้ายทักษะบนการ์ด — เรียงตามความสำคัญ ไม่ใช่ตามตัวอักษร"""
    data = client.get("/api/targets").json()
    for t in data["targets"]:
        top = t["top_skills"]
        assert 0 < len(top) <= 3
        assert len(top) <= t["requirement_count"]
        assert [s["importance"] for s in top] == sorted(
            (s["importance"] for s in top), reverse=True)
        for s in top:
            assert s["name_th"], f"{s['skill_id']} ไม่มีชื่อไทย จะไม่เหลืออะไรให้ขึ้นป้าย"
            # 🔒 กติกาข้อ 5 — ชื่ออังกฤษที่เท่ากับรหัสต้องติดป้ายบอก ห้ามให้หน้าจอเดาเอง
            assert s["name_en_is_placeholder"] == (s["name_en"] == s["skill_id"])


def test_card_top_skills_are_a_subset_of_the_full_requirements(client):
    """การ์ดกับหน้ารายละเอียดต้องพูดตรงกัน ไม่ใช่คนละชุด"""
    card = next(t for t in client.get("/api/targets").json()["targets"]
                if t["id"] == "SW-DEV")
    detail = client.get("/api/targets/SW-DEV").json()
    full = {r["skill_id"] for r in detail["requirements"]}
    assert {s["skill_id"] for s in card["top_skills"]} <= full
    assert card["requirement_count"] == len(detail["requirements"])


def test_scholarship_obligation_filters_targets_with_a_reason(client, user):
    client.post("/api/profile", json={
        "user_id": user, "education_level": "ปี 3", "obligation_id": "gov"})
    data = client.get("/api/targets", params={"user_id": user}).json()
    assert data["filtered_out"], "เงื่อนไขชดใช้ทุนไม่ได้กรองอะไรออกเลย"
    for f in data["filtered_out"]:
        assert f["reasons"] and any("ชดใช้ทุน" in r["message"] for r in f["reasons"])


def test_being_year_one_does_not_hide_targets(client, user):
    client.post("/api/profile", json={
        "user_id": user, "education_level": "ปี 1", "year": 1, "obligation_id": "none"})
    data = client.get("/api/targets", params={"user_id": user}).json()
    assert len(data["targets"]) == 8
    assert any(t["conditions_at_application"] for t in data["targets"])


# ═══════════ ส่งผลงาน + ตรวจผลสกัด ═══════════


def test_document_is_refused_without_consent(client, user):
    r = client.post("/api/portfolio/text", json={
        "user_id": user, "text": CV, "consent": False})
    assert r.status_code == 400
    assert "ยินยอม" in r.json()["detail"]


def test_short_text_is_refused(client, user):
    r = client.post("/api/portfolio/text", json={
        "user_id": user, "text": "Python", "consent": True})
    assert r.status_code == 400


@pytest.fixture
def with_cv(client, user) -> tuple[str, str]:
    r = client.post("/api/portfolio/text", json={
        "user_id": user, "text": CV, "consent": True})
    assert r.status_code == 200, r.text
    return user, r.json()["document_id"]


def test_extraction_finds_skills_and_every_span_is_real(client, with_cv):
    """🔒 ทุกหลักฐานต้องชี้กลับไปที่ข้อความจริงใน CV"""
    _user_id, doc_id = with_cv
    d = client.get(f"/api/portfolio/{doc_id}").json()
    assert d["extracted"], "สกัดอะไรไม่ได้เลย"
    raw = d["raw_text"]
    for e in d["extracted"]:
        assert raw[e["span_start"]:e["span_end"]] == e["span_text"]
        assert e["user_status"] == "pending", "ต้องรอผู้ใช้ยืนยันก่อนถึงนับ"


def test_pending_skills_do_not_count_until_confirmed(client, with_cv):
    user_id, _doc = with_cv
    me = client.get("/api/me", params={"user_id": user_id}).json()
    assert me["skills_from_cv"] == [], "ยังไม่ยืนยัน ต้องยังไม่นับ"


def test_confirming_makes_skills_count(client, with_cv):
    user_id, doc_id = with_cv
    d = client.get(f"/api/portfolio/{doc_id}").json()
    decisions = {e["id"]: "confirmed" for e in d["extracted"]}
    r = client.post(f"/api/portfolio/{doc_id}/confirm",
                    json={"user_id": user_id, "decisions": decisions})
    assert r.status_code == 200
    assert r.json()["confirmed_skills"]

    me = client.get("/api/me", params={"user_id": user_id}).json()
    got = {s["skill_id"] for s in me["skills_from_cv"]}
    for expected in ("T-PY", "T-SQL", "T-GIT", "SW-API"):
        assert expected in got


def test_rejecting_removes_a_skill(client, with_cv):
    user_id, doc_id = with_cv
    d = client.get(f"/api/portfolio/{doc_id}").json()
    target = next(e for e in d["extracted"] if e["skill_id"] == "T-PY")
    client.post(f"/api/portfolio/{doc_id}/confirm",
                json={"user_id": user_id, "decisions": {target["id"]: "rejected"}})
    me = client.get("/api/me", params={"user_id": user_id}).json()
    assert "T-PY" not in {s["skill_id"] for s in me["skills_from_cv"]}


def test_github_link_is_accepted(client, user):
    r = client.post("/api/portfolio/github", json={
        "user_id": user, "url": "https://github.com/psf/requests", "consent": True})
    if r.status_code == 400 and "ต่อ GitHub" in r.json().get("detail", ""):
        pytest.skip("ไม่มีเน็ตหรือโดนจำกัดอัตราการเรียก")
    assert r.status_code == 200
    assert r.json()["char_count"] > 200


# ═══════════ ROADMAP ═══════════


@pytest.fixture
def ready(client, with_cv) -> str:
    user_id, doc_id = with_cv
    d = client.get(f"/api/portfolio/{doc_id}").json()
    client.post(f"/api/portfolio/{doc_id}/confirm", json={
        "user_id": user_id, "decisions": {e["id"]: "confirmed" for e in d["extracted"]}})
    client.post("/api/profile", json={
        "user_id": user_id, "field": "CPE", "education_level": "ปี 3", "year": 3,
        "hours_per_week": 8, "budget_baht": 2000, "obligation_id": "none",
        "self_reported_skills": {"F-SOLVE": 2}})
    client.post("/api/goal", json={"user_id": user_id, "target_id": "SW-DEV"})
    return user_id


def test_roadmap_needs_a_goal_first(client, user):
    r = client.get("/api/roadmap", params={"user_id": user})
    assert r.status_code == 409


def test_roadmap_walks_end_to_end(client, ready):
    rm = client.get("/api/roadmap", params={"user_id": ready}).json()
    assert rm["target"]["id"] == "SW-DEV"
    assert rm["steps"], "roadmap ว่างเปล่า"
    assert rm["total_steps"] == len(rm["steps"])
    assert any(s["actionable"] for s in rm["steps"])


def test_course_detail_explains_its_effect_on_the_active_roadmap(client, ready):
    """กด card จาก Roadmap แล้วต้องรู้ว่า course เพิ่มทักษะใดและพาไปต่อไหน."""
    data = client.get("/api/resources/C-PY-INTRO", params={
        "user_id": ready, "target_id": "SW-DEV"}).json()
    assert data["id"] == "C-PY-INTRO"
    assert data["roadmap_context"]["target_id"] == "SW-DEV"
    assert data["teaches"]
    assert all("roadmap_status" in skill for skill in data["teaches"])
    assert len(data["example_learning_flow"]) == 3
    assert data["example_learning_flow"][-1]["detail"] == data["proof_of_done"]


def test_course_detail_is_readable_without_a_session(client):
    data = client.get("/api/resources/C-PY-INTRO").json()
    assert data["roadmap_context"] is None
    assert data["teaches"]


def test_every_step_offers_at_least_one_way_forward(client, ready):
    rm = client.get("/api/roadmap", params={"user_id": ready}).json()
    for s in rm["steps"]:
        assert s["options"], f'ก้าว {s["skill_id"]} ไม่มีทางไปถึงเลย'


def test_roadmap_separates_cv_evidence_from_self_reported(client, ready):
    """จุดขายของผลิตภัณฑ์ — ต้องบอกได้ว่าทักษะไหนพิสูจน์ได้"""
    rm = client.get("/api/roadmap", params={"user_id": ready}).json()
    assert rm["evidence_summary"]["from_cv"] > 0
    assert rm["evidence_summary"]["self_reported"] > 0
    kinds = {s["evidence_kind"] for s in rm["steps"] if s["evidence_kind"]}
    assert kinds <= {"extracted", "self_reported", "both"}


def test_roadmap_marks_flexible_steps(client, ready):
    """กลไก "ทำเมื่อไหร่ก็ได้" จาก roadmap.sh"""
    rm = client.get("/api/roadmap", params={"user_id": ready}).json()
    assert any(s["status"] == "flexible" for s in rm["steps"])
    assert "flexible" in rm["legend"]


def test_roadmap_sends_both_order_and_edges(client, ready):
    """หน้าเว็บต้องเลือกวาดเป็นรายการหรือกราฟก็ได้ — UI ยังไม่ตัดสินใจ"""
    rm = client.get("/api/roadmap", params={"user_id": ready}).json()
    ids = {s["skill_id"] for s in rm["steps"]}
    assert all(s["order_no"] > 0 for s in rm["steps"])
    for e in rm["edges"]:
        assert e["from"] in ids and e["to"] in ids


def test_options_that_do_not_fit_say_why(client, ready):
    rm = client.get("/api/roadmap", params={"user_id": ready}).json()
    blocked = [o for s in rm["steps"] for o in s["options"] if not o["fits"]]
    for o in blocked:
        assert o["blocked_reason"]


def test_having_more_skills_shortens_the_roadmap(client, ready):
    """เทียบคนที่ยืนยันทักษะจาก CV แล้ว กับคนที่เพิ่งเข้ามาใหม่"""
    fresh = client.post("/api/session", json={"entry": "known"}).json()["user_id"]
    client.post("/api/goal", json={"user_id": fresh, "target_id": "SW-DEV"})

    long_one = client.get("/api/roadmap", params={"user_id": fresh}).json()
    short_one = client.get("/api/roadmap", params={"user_id": ready}).json()
    assert short_one["total_steps"] < long_one["total_steps"]
    assert short_one["coverage"] > long_one["coverage"]


# ═══════════ เส้นทางที่เคยเปิดดู ═══════════


def test_roadmap_list_is_empty_before_opening_any(client, user):
    r = client.get("/api/roadmaps", params={"user_id": user}).json()
    assert r["roadmaps"] == []
    assert r["empty_message"], "ว่างเปล่าเงียบ ๆ ไม่ได้ ต้องบอกว่าให้ไปทำอะไรต่อ"


def test_opening_a_roadmap_puts_it_in_the_list(client, ready):
    rm = client.get("/api/roadmap", params={"user_id": ready}).json()
    listed = client.get("/api/roadmaps", params={"user_id": ready}).json()["roadmaps"]

    assert len(listed) == 1
    row = listed[0]
    assert row["target_id"] == "SW-DEV"
    assert row["is_primary_goal"], "อาชีพที่ตั้งเป็นเป้าหมายอยู่ต้องถูกทำเครื่องหมาย"
    assert (row["total_steps"], row["steps_done"], row["coverage"]) == (
        rm["total_steps"], rm["steps_done"], rm["coverage"])


def test_next_step_in_the_list_is_the_step_the_engine_would_hand_over(client, ready):
    """🔒 กติกาข้อ 4 — ก้าวที่การ์ดโฆษณา ต้องเป็นก้าวเดียวกับที่ระบบจัดอันดับให้"""
    rm = client.get("/api/roadmap", params={"user_id": ready}).json()
    row = client.get("/api/roadmaps", params={"user_id": ready}).json()["roadmaps"][0]

    expected = next((s for s in rm["steps"] if s["status"] == "current"), None)
    if expected is None:
        assert row["next_step"] is None
    else:
        assert row["next_step"]["skill_id"] == expected["skill_id"]
        assert row["next_step"]["name_th"] == expected["name_th"]


def test_second_career_is_listed_without_stealing_the_primary_goal(client, ready):
    client.get("/api/roadmap", params={"user_id": ready})
    client.get("/api/roadmap", params={"user_id": ready, "target_id": "DATA-ENG"})

    listed = client.get("/api/roadmaps", params={"user_id": ready}).json()["roadmaps"]
    assert [r["target_id"] for r in listed] == ["DATA-ENG", "SW-DEV"], "ล่าสุดต้องมาก่อน"
    # 🔴 แค่เปิดดูอาชีพอื่นไม่ใช่การเปลี่ยนเป้าหมาย — เป้าหมายเปลี่ยนที่ /goal เท่านั้น
    assert [r["is_primary_goal"] for r in listed] == [False, True]


def test_roadmap_list_refuses_an_unknown_user(client):
    assert client.get("/api/roadmaps", params={"user_id": "ไม่มีคนนี้"}).status_code == 404


# ═══════════ กลับมาทำต่อ ═══════════


def test_resume_points_a_brand_new_user_at_the_first_step(client, user):
    r = client.get("/api/me/resume", params={"user_id": user}).json()
    assert r["next"]["id"] == "profile"
    assert all(not s["done"] for s in r["steps"])
    assert r["summary"]["skills_from_cv"] == 0


def test_resume_moves_forward_as_the_user_actually_progresses(client, with_cv):
    """ลำดับต้องเดินตามสิ่งที่ผู้ใช้ทำจริง ไม่ใช่ลำดับที่หน้าจอเดา"""
    user_id, doc_id = with_cv
    client.post("/api/profile", json={
        "user_id": user_id, "field": "CPE", "education_level": "ปี 3", "year": 3})

    # ส่งผลงานแล้วแต่ยังไม่ยืนยัน → ต้องพาไปหน้าตรวจ ไม่ใช่ข้ามไปเลือกอาชีพ
    r = client.get("/api/me/resume", params={"user_id": user_id}).json()
    assert r["next"]["id"] == "confirm"
    assert doc_id in r["next"]["href"], "ต้องพากลับไปที่เอกสารฉบับที่ค้างอยู่"
    assert r["summary"]["pending_skills"] > 0

    d = client.get(f"/api/portfolio/{doc_id}").json()
    client.post(f"/api/portfolio/{doc_id}/confirm", json={
        "user_id": user_id, "decisions": {e["id"]: "confirmed" for e in d["extracted"]}})

    r = client.get("/api/me/resume", params={"user_id": user_id}).json()
    assert r["next"]["id"] == "goal", "ยืนยันครบแล้วต้องไปขั้นถัดไป"
    assert r["summary"]["pending_skills"] == 0
    assert r["summary"]["skills_from_cv"] > 0


def test_resume_has_nothing_left_when_the_walk_is_done(client, ready):
    client.get("/api/roadmap", params={"user_id": ready})
    r = client.get("/api/me/resume", params={"user_id": ready}).json()
    assert all(s["done"] for s in r["steps"]), [s["id"] for s in r["steps"] if not s["done"]]
    assert r["next"] is None, "เดินครบแล้วต้องไม่มีปุ่ม 'ทำต่อ' ลอย ๆ"


def test_resume_keeps_the_two_kinds_of_skills_apart(client, ready):
    """🔒 กติกาข้อ 1 — สรุปหน้าโปรไฟล์ก็ห้ามบวกรวมสองแหล่ง"""
    r = client.get("/api/me/resume", params={"user_id": ready}).json()
    assert "skills_from_cv" in r["summary"] and "skills_self_reported" in r["summary"]
    assert "skills" not in r["summary"]


def test_resume_refuses_an_unknown_code(client):
    """รหัสที่ใช้กู้คืนต้องตอบชัดว่าใช้ไม่ได้ ไม่ใช่คืนหน้าเปล่า"""
    r = client.get("/api/me/resume", params={"user_id": "รหัสมั่ว"})
    assert r.status_code == 404


# ═══════════ PDPA ═══════════


def test_delete_removes_everything(client, ready):
    r = client.delete("/api/me", params={"user_id": ready})
    assert r.status_code == 200
    assert r.json()["deleted"]
    assert r.json()["rows"]["user_document"] >= 1
    assert client.get("/api/me", params={"user_id": ready}).status_code == 404
