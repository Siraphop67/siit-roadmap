"""เดินครบวงจรฝั่ง "ยังไม่รู้ว่าอยากเป็นอะไร" ผ่าน API จริง

แบบทดสอบกิจกรรม → ผลระหว่างทาง → ผลจับคู่ → เลือกเป้าหมาย → roadmap

เทสต์ในไฟล์นี้ไม่ได้ตรวจแค่ว่า endpoint ตอบ 200 — ตรวจว่ากติกาที่เราประกาศไว้
ยังเป็นจริงอยู่ โดยเฉพาะสามข้อที่พังง่ายที่สุดเวลามีคนไปแก้:
  · คะแนนดิบต้องไม่หลุดออกไปที่หน้าจอ
  · ยังแยกไม่ออกต้องบอกว่ายังแยกไม่ออก
  · คำตอบแบบทดสอบต้องไม่กลายเป็นทักษะที่ระบบเชื่อว่าผู้ใช้ทำได้
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api_discover import FEEDBACK_EVERY, MAX_ITEMS, MIN_ITEMS
from app.db import get_db
from app.main import app
from app.seed.loader import create_all, seed


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "discover.db"
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
    return client.post("/api/session", json={"entry": "unsure"}).json()["user_id"]


def take_test(client, user: str, answer_for, limit: int = MAX_ITEMS) -> dict:
    """ตอบแบบทดสอบจนกว่าจะจบ · `answer_for(item) -> -1|0|1`"""
    last = client.get("/api/discover/next", params={"user_id": user}).json()
    steps = 0
    while not last["done"] and steps < limit:
        item = last["item"]
        client.post("/api/discover/answer", json={
            "user_id": user, "item_id": item["item_id"], "answer": answer_for(item),
        })
        steps += 1
        last = client.get("/api/discover/next", params={"user_id": user}).json()
    return last


# ── คนที่ชอบงานลงมือกับของจริง ──
HANDS_ON = ("เครื่อง", "ซ่อม", "ประกอบ", "ติดตั้ง", "วัสดุ", "โครงสร้าง", "หน้างาน", "มือ")
# ── คนที่ชอบงานกับข้อมูลและระบบ ──
DESK = ("ข้อมูล", "คำนวณ", "วิเคราะห์", "เขียนโปรแกรม", "ระบบ", "เอกสาร", "ตัวเลข")


def likes(words):
    def pick(item) -> int:
        text = f"{item['prompt_th']} {item.get('context_th') or ''}"
        return 1 if any(w in text for w in words) else -1
    return pick


# ═════════════ เดินครบเส้น ═════════════


def test_เดินแบบทดสอบจนจบแล้วได้ผลจับคู่(client, user):
    last = take_test(client, user, likes(HANDS_ON))
    assert last["done"]
    assert last["answered"] >= MIN_ITEMS

    r = client.get("/api/discover/result", params={"user_id": user})
    assert r.status_code == 200
    body = r.json()
    assert body["targets"], "ตอบครบแล้วต้องมีอาชีพให้ดูอย่างน้อย 1 อัน"
    assert len(body["targets"]) <= 5


def test_มีอาชีพให้ดูต้องไม่มีempty_messageและกลับกัน(client, user):
    take_test(client, user, likes(HANDS_ON))
    body = client.get("/api/discover/result", params={"user_id": user}).json()
    assert bool(body["targets"]) != bool(body["empty_message"]), (
        "มีผล = ไม่มีข้อความว่าง · ไม่มีผล = ต้องมีข้อความว่า ทำไม"
    )


def test_ยังไม่ตอบอะไรเลยขอผลไม่ได้(client, user):
    r = client.get("/api/discover/result", params={"user_id": user})
    assert r.status_code == 409


def test_ไม่พบผู้ใช้ตอบ404(client):
    assert client.get("/api/discover/next", params={"user_id": "ไม่มีจริง"}).status_code == 404


# ═════════════ 🔴 คะแนนดิบห้ามหลุดออกไป ═════════════


def test_ไม่มีคะแนนดิบในผลลัพธ์(client, user):
    take_test(client, user, likes(DESK))
    body = client.get("/api/discover/result", params={"user_id": user}).json()

    for card in body["targets"]:
        assert "score" not in card, "คะแนนดิบกองกันที่ 0.88–0.96 ห้ามส่งออกไปที่หน้าจอ"
        assert "score_activity" not in card
        assert 0 <= card["relative_score"] <= 100

    assert body["scale_note"], "ส่งตัวเลขออกไปต้องมีคำกำกับว่ามันคืออะไรเสมอ"
    assert "ไม่ใช่เปอร์เซ็นต์" in body["scale_note"]


def test_คะแนนสัมพัทธ์เรียงตามอันดับ(client, user):
    take_test(client, user, likes(HANDS_ON))
    cards = client.get("/api/discover/result", params={"user_id": user}).json()["targets"]
    ranks = [c["rank_no"] for c in cards]
    rel = [c["relative_score"] for c in cards]
    assert ranks == sorted(ranks)
    assert rel == sorted(rel, reverse=True)
    assert rel[0] == 100, "อันดับ 1 คือ 100 เสมอ เพราะเป็นค่าเทียบในกลุ่ม ไม่ใช่ % ความเหมาะสม"


# ═════════════ 🔒 ยังแยกไม่ออกต้องพูดว่ายังแยกไม่ออก ═════════════


def test_ตอบเฉยๆทุกข้อแล้วต้องไม่ยัดอันดับให้ดูมั่นใจ(client, user):
    last = take_test(client, user, lambda item: 0)
    assert last["done"]
    assert last["answered"] >= MAX_ITEMS, "ตอบเฉย ๆ หมดต้องถามจนครบเพดาน ไม่ใช่สรุปเร็ว"

    body = client.get("/api/discover/result", params={"user_id": user}).json()
    assert body["separated"] is False
    assert body["targets"] == [], (
        "ตอบเฉย ๆ ทุกข้อ = ไม่มีอะไรใช้เทียบ · กติกา “ย้อนที่มาไม่ได้ = ไม่แสดง” ต้องตัดออกหมด"
    )
    # 🔴 เคสที่เคยพัง: ตอบครบ 24 ข้อแล้วระบบบอกว่า "ยังตอบไม่พอ" ซึ่งไม่จริงและไม่บอกทางออก
    msg = body["empty_message"]
    assert msg, "รายการว่างต้องมีคำอธิบาย ไม่ใช่หน้าจอเปล่า"
    assert "ยังตอบไม่พอ" not in msg
    assert str(body["answered"]) in msg, "ต้องบอกว่าเขาตอบไปแล้วกี่ข้อจริง ๆ"
    assert "อยากทำ" in msg, "ต้องบอกทางออกว่าให้กลับไปทำอะไร"


def test_ยังไม่ถึงจำนวนขั้นต่ำห้ามสรุป(client, user):
    pick = likes(HANDS_ON)
    for _ in range(MIN_ITEMS - 1):
        nxt = client.get("/api/discover/next", params={"user_id": user}).json()
        assert not nxt["done"], f"ตอบยังไม่ถึง {MIN_ITEMS} ข้อ ห้ามจบแบบทดสอบ"
        client.post("/api/discover/answer", json={
            "user_id": user, "item_id": nxt["item"]["item_id"], "answer": pick(nxt["item"]),
        })


def test_บอกได้ว่าทำไมยังถามต่อและอ้างชื่ออาชีพจริง(client, user):
    pick = likes(HANDS_ON)
    for _ in range(4):
        nxt = client.get("/api/discover/next", params={"user_id": user}).json()
        client.post("/api/discover/answer", json={
            "user_id": user, "item_id": nxt["item"]["item_id"], "answer": pick(nxt["item"]),
        })
    nxt = client.get("/api/discover/next", params={"user_id": user}).json()
    assert not nxt["done"]
    assert "ยังแยกกันไม่ชัด" in nxt["reason"]
    assert "ขอถามอีก" in nxt["reason"]

    titles = [t["title_th"] for t in client.get("/api/targets").json()["targets"]]
    assert any(t in nxt["reason"] for t in titles), "ต้องอ้างชื่ออาชีพจริง ไม่ใช่รหัส SW-DEV"


# ═════════════ 🔴 D3 ในคราบใหม่ — "เสนอเพราะคุณไม่อยากทำ" ═════════════


def test_เหตุผลที่เสนอมีแต่ข้อที่ผู้ใช้อยากทำ(client, user):
    """เคสจริงที่เจอ: อันดับ 1 ขึ้นเหตุผลแรกว่า "คุณไม่อยากขายของ แต่งานนี้ต้องขายเยอะ"

    หน้าจอที่พิมพ์ reasons[0] จะกลายเป็น "เสนองานนี้เพราะคุณไม่อยากขายของ"
    ซึ่งคือปัญหาเดียวกับ DECISIONS D3 แค่เปลี่ยนคำ
    """
    take_test(client, user, likes(HANDS_ON))
    body = client.get("/api/discover/result", params={"user_id": user}).json()

    for card in body["targets"]:
        for r in card["reasons"]:
            assert r["direction"] == "wants_and_does", (
                f"“{r['label']}” เป็น {r['direction']} — ห้ามอยู่ในลิสต์เหตุผลที่เสนอ"
            )
        for h in card["heads_up"]:
            assert h["direction"] == "unwanted_but_core"

    # และต้องไม่ทิ้งข้อมูลนั้นไป — แค่ย้ายไปอีกฟิลด์
    assert any(c["heads_up"] for c in body["targets"]), (
        "unwanted_but_core มีค่าต่อคนกำลังตัดสินใจ ต้องยังส่งออกไป ไม่ใช่ตัดทิ้ง"
    )


# ═════════════ ⭐ ผลระหว่างทาง ═════════════


def test_แสดงผลระหว่างทางทุก6ข้อ(client, user):
    pick = likes(DESK)
    seen = 0
    for i in range(1, FEEDBACK_EVERY * 2 + 1):
        nxt = client.get("/api/discover/next", params={"user_id": user}).json()
        client.post("/api/discover/answer", json={
            "user_id": user, "item_id": nxt["item"]["item_id"], "answer": pick(nxt["item"]),
        })
        after = client.get("/api/discover/next", params={"user_id": user}).json()
        if i % FEEDBACK_EVERY == 0:
            assert after["interim"], f"ตอบครบ {i} ข้อแล้วต้องเห็นผลระหว่างทาง"
            assert after["interim"]["top"]
            assert after["interim"]["scale_note"]
            seen += 1
        else:
            assert after["interim"] is None
    assert seen == 2


# ═════════════ 🔒 ข้อคำถามต้องไม่เผยชื่ออาชีพ ═════════════


def test_ข้อคำถามไม่มีชื่ออาชีพปนมา(client, user):
    titles = [t["title_th"] for t in client.get("/api/targets").json()["targets"]]
    pick = likes(HANDS_ON)
    for _ in range(FEEDBACK_EVERY):
        nxt = client.get("/api/discover/next", params={"user_id": user}).json()
        item = nxt["item"]
        assert "target_id" not in item and "career" not in item
        text = f"{item['prompt_th']} {item.get('context_th') or ''}"
        for title in titles:
            assert title not in text, "ผู้ใช้ต้องตอบต่อกิจกรรม ไม่ใช่ต่อชื่ออาชีพ"
        client.post("/api/discover/answer", json={
            "user_id": user, "item_id": item["item_id"], "answer": pick(item),
        })


# ═════════════ 🔒 คำตอบแบบทดสอบ ≠ หลักฐานว่าทำเป็น ═════════════


def test_ตอบแบบทดสอบแล้วไม่กลายเป็นทักษะที่ระบบเชื่อ(client, user):
    take_test(client, user, likes(DESK))
    me = client.get("/api/me", params={"user_id": user}).json()
    assert me["skills_from_cv"] == [], (
        "ความอยากทำกิจกรรมไม่ใช่หลักฐานว่าทำเป็น — ห้ามไหลเข้า ExtractedSkill"
    )
    assert me["skills_self_reported"] == []


# ═════════════ ตอบซ้ำ = แก้คำตอบ ═════════════


def test_ตอบข้อเดิมซ้ำคือแก้คำตอบไม่ใช่เพิ่มแถว(client, user):
    nxt = client.get("/api/discover/next", params={"user_id": user}).json()
    item_id = nxt["item"]["item_id"]
    first = client.post("/api/discover/answer", json={
        "user_id": user, "item_id": item_id, "answer": 1}).json()
    second = client.post("/api/discover/answer", json={
        "user_id": user, "item_id": item_id, "answer": -1}).json()
    assert first["answered"] == 1
    assert second["answered"] == 1


def test_ค่าคำตอบนอกช่วงถูกปฏิเสธ(client, user):
    nxt = client.get("/api/discover/next", params={"user_id": user}).json()
    r = client.post("/api/discover/answer", json={
        "user_id": user, "item_id": nxt["item"]["item_id"], "answer": 5})
    assert r.status_code == 422


# ═════════════ อาชีพที่คุณอาจไม่เคยคิดถึง ═════════════


def test_เสนออาชีพที่อยู่นอกสาขาที่เรียน(client, user):
    client.post("/api/profile", json={"user_id": user, "field": "ME", "education_level": "ปี 2"})
    take_test(client, user, likes(DESK))
    body = client.get("/api/discover/result", params={"user_id": user}).json()
    un = body["unconsidered"]
    if un:                       # ถ้า 5 อันดับแรกอยู่ในสาขาที่เรียนหมด จะไม่มี และถูกต้องแล้ว
        assert "ME" not in un["field_whitelist"]
        assert body["unconsidered_note"]


# ═════════════ 🔴 ติดเงื่อนไขทุน = ติดป้าย ไม่ใช่หายไป ═════════════


def test_ทุนรัฐบาลไม่ทำให้อาชีพหายจากผลแต่ติดป้ายบอก(client, user):
    client.post("/api/profile", json={
        "user_id": user, "field": "CPE", "education_level": "ปี 2", "obligation_id": "gov"})
    take_test(client, user, likes(DESK))
    body = client.get("/api/discover/result", params={"user_id": user}).json()

    assert len(body["targets"]) >= 2, (
        "กรองก่อนจับคู่จะเหลืออาชีพเดียวจนแบบทดสอบไร้ความหมาย — ต้องจับคู่ทั้งหมดแล้วติดป้าย"
    )
    blocked = [c for c in body["targets"] if c["blocked_reasons"]]
    assert blocked, "ทุนรัฐบาลต้องทำให้อาชีพเอกชนติดป้ายเหตุผล"
    assert blocked[0]["blocked_reasons"][0]["message"]


# ═════════════ เริ่มใหม่ ═════════════


def test_เริ่มใหม่ล้างคำตอบแต่ไม่แตะโปรไฟล์(client, user):
    client.post("/api/profile", json={"user_id": user, "field": "CPE", "education_level": "ปี 2"})
    take_test(client, user, likes(HANDS_ON))

    cleared = client.post("/api/discover/reset", json={"user_id": user}).json()
    assert cleared["cleared"] > 0
    assert client.get("/api/discover/result", params={"user_id": user}).status_code == 409
    assert client.get("/api/profile", params={"user_id": user}).json()["field"] == "CPE"


# ═════════════ บรรจบกับฝั่ง "รู้แล้ว" ═════════════


def test_เลือกอาชีพจากผลแล้วไปต่อroadmapได้(client, user):
    take_test(client, user, likes(DESK))
    top = client.get("/api/discover/result", params={"user_id": user}).json()["targets"][0]

    client.post("/api/goal", json={"user_id": user, "target_id": top["target_id"]})
    rm = client.get("/api/roadmap", params={"user_id": user})
    assert rm.status_code == 200
    body = rm.json()
    assert body["target"]["id"] == top["target_id"]
    assert body["steps"], "สองฝั่งต้องบรรจบที่ roadmap เดียวกัน"
