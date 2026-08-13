"""ตัวสกัดด้วย LLM — เตรียมไว้ให้พร้อมก่อนได้ API key

🔴 ทีมยังไม่มี key ณ วันที่เขียนเทสต์นี้ จึงยังไม่เคยยิง API จริงเลย
   แต่ส่วนที่พังได้จริงคือ **การแปลงคำตอบของ LLM เป็น span** ไม่ใช่การเรียก API
   เทสต์ชุดนี้จึงคุมส่วนนั้นให้ครบ วันที่ได้ key มา สิ่งที่ต้องทดสอบจริงเหลือแค่
   "เรียกติดไหม" ไม่ใช่ "แปลงถูกไหม" — จะได้ไม่ต้องนั่งดีบั๊กตอนใกล้ Demo Day

🛡 หัวใจของไฟล์นี้: LLM จะแต่งข้อความขึ้นมาเมื่อไหร่ก็ได้ และเราต้องทิ้งทุกครั้ง
   ไฮไลต์ที่ชี้ไปผิดที่ แย่กว่าไม่มีไฮไลต์เลย
"""

from __future__ import annotations

import json

import pytest

from app.llm.anthropic import (
    AnthropicExtractor,
    ExtractorError,
    parse_payload,
)
from app.seed.skills import SKILLS

KNOWN = {s["id"] for s in SKILLS}
REAL_SKILL = "T-PY"
OTHER_SKILL = "T-GIT"

CV = """สมชาย ใจดี — วิศวกรรมคอมพิวเตอร์ ปี 3

- ทำระบบวิเคราะห์ข้อมูลการใช้ห้องเรียนด้วย Python และ pandas
- ดูแลโค้ดด้วย Git เขียน unit test ทุกฟีเจอร์
- ทำให้สองระบบคุยกันได้ผ่านการออกแบบสัญญาเรียกใช้ระหว่างกัน
"""


def payload(*rows: dict) -> str:
    return json.dumps({"skills": list(rows)}, ensure_ascii=False)


def row(skill_id=REAL_SKILL, span_text="Python และ pandas", level=2, confidence=0.8):
    return {
        "skill_id": skill_id, "span_text": span_text,
        "level": level, "confidence": confidence,
    }


# ═════════════ เคสปกติ ═════════════


def test_แปลงคำตอบปกติเป็นspanที่ชี้กลับได้():
    spans = parse_payload(payload(row()), CV, KNOWN)
    assert len(spans) == 1
    s = spans[0]
    assert s.skill_id == REAL_SKILL
    assert s.level == 2
    # 🛡 หัวใจทั้งหมด — ตำแหน่งที่บอกต้องตัดออกมาได้ข้อความเดิมเป๊ะ
    assert CV[s.span_start:s.span_end] == "Python และ pandas"


def test_หลายทักษะในคำตอบเดียว():
    spans = parse_payload(
        payload(row(), row(skill_id=OTHER_SKILL, span_text="Git")), CV, KNOWN)
    assert {s.skill_id for s in spans} == {REAL_SKILL, OTHER_SKILL}


def test_ไม่เจอทักษะเลยคืนรายการว่างไม่ใช่error():
    """"อ่านแล้วไม่เจอ" ต้องต่างจาก "เรียกไม่สำเร็จ" """
    assert parse_payload(payload(), CV, KNOWN) == []


# ═════════════ 🛡 LLM แต่งข้อความขึ้นมา ═════════════


def test_ข้อความที่ไม่มีในเอกสารถูกทิ้ง():
    """เคสที่อันตรายที่สุด — LLM เรียบเรียงใหม่แทนที่จะคัดลอก"""
    faked = row(span_text="มีประสบการณ์ Python อย่างช่ำชอง")   # ไม่มีประโยคนี้ใน CV
    assert parse_payload(payload(faked), CV, KNOWN) == []


def test_แต่งข้อความปนกับของจริงทิ้งเฉพาะที่แต่ง():
    spans = parse_payload(
        payload(row(), row(skill_id=OTHER_SKILL, span_text="เชี่ยวชาญ Git มาก")),
        CV, KNOWN)
    assert [s.skill_id for s in spans] == [REAL_SKILL]


def test_เรียบเรียงใหม่แม้ความหมายถูกก็ยังถูกทิ้ง():
    """"ทำให้สองระบบคุยกัน" มีอยู่จริงใน CV — แต่ถ้า LLM เขียนกลับมาเป็นคำอื่น ต้องทิ้ง

    นี่คือราคาที่เรายอมจ่ายเพื่อให้ไฮไลต์ชี้ถูกที่เสมอ
    """
    assert parse_payload(
        payload(row(span_text="ออกแบบ API เชื่อมสองระบบ")), CV, KNOWN) == []


# ═════════════ LLM อ้างทักษะนอกคลัง ═════════════


def test_ทักษะที่ไม่มีในคลัง73ตัวถูกทิ้ง():
    assert parse_payload(
        payload(row(skill_id="SKILL-ที่แต่งขึ้น")), CV, KNOWN) == []


def test_ทักษะนอกคลังไม่ทำให้ข้ออื่นหายไปด้วย():
    spans = parse_payload(
        payload(row(skill_id="ไม่มีจริง"), row()), CV, KNOWN)
    assert [s.skill_id for s in spans] == [REAL_SKILL]


# ═════════════ คำตอบผิดรูปแบบ ═════════════


def test_ตอบไม่ใช่jsonโยนextractorerrorไม่ใช่คืนว่าง():
    """🔒 กติกาข้อ 5 — ถ้ากลืนเป็น "ไม่เจอทักษะ" ผู้ใช้จะเข้าใจว่าผลงานตัวเองไม่มีอะไร
    ทั้งที่จริงคือระบบเรียก LLM ไม่สำเร็จ
    """
    with pytest.raises(ExtractorError) as exc:
        parse_payload("ขอโทษครับ ผมช่วยเรื่องนี้ไม่ได้", CV, KNOWN)
    assert "JSON" in str(exc.value)


def test_ตอบเป็นjsonแต่ไม่ใช่objectโยนerror():
    with pytest.raises(ExtractorError):
        parse_payload('["a", "b"]', CV, KNOWN)


def test_ห่อด้วยmarkdownfenceยังอ่านได้():
    """LLM ชอบห่อ ```json แม้สั่งว่าห้าม — ถ้าไม่ลอกออก จะพังทุกครั้งที่มันเผลอ"""
    for wrapped in (
        f"```json\n{payload(row())}\n```",
        f"```\n{payload(row())}\n```",
        f"  ```json\n{payload(row())}\n```  ",
    ):
        assert len(parse_payload(wrapped, CV, KNOWN)) == 1


@pytest.mark.parametrize("bad", [
    {"span_text": "Python และ pandas"},                       # ไม่มี skill_id
    {"skill_id": REAL_SKILL},                                 # ไม่มี span_text
    {"skill_id": REAL_SKILL, "span_text": ""},                # span_text ว่าง
    {"skill_id": 123, "span_text": "Python และ pandas"},      # skill_id ไม่ใช่สตริง
    "ไม่ใช่ dict เลย",
])
def test_แถวที่ผิดรูปแบบถูกข้ามทีละแถวไม่ทำให้ทั้งชุดพัง(bad):
    spans = parse_payload(payload(bad, row(skill_id=OTHER_SKILL, span_text="Git")),
                          CV, KNOWN)
    assert [s.skill_id for s in spans] == [OTHER_SKILL], (
        "LLM พลาดบางข้อเป็นเรื่องปกติ แต่ทิ้งผลทั้งชุดเพราะข้อเดียวไม่ใช่"
    )


@pytest.mark.parametrize("given,expected", [
    ("high", 3), ("medium", 2), ("low", 1), ("สูง", 3),   # โมเดลชอบตอบเป็นคำ
    ("ไม่รู้", 1), (None, 1),                              # อ่านไม่ออก → ค่าตั้งต้น ไม่ใช่ทิ้งแถว
])
def test_ระดับที่ตอบเป็นคำแปลให้แทนที่จะทิ้งทั้งแถว(given, expected):
    """🔴 เคยพลาดมาแล้ว: gemma4 ตอบ confidence:"high" แล้วทั้ง 15 แถวถูกทิ้ง

    ทั้งที่ skill_id กับ span_text ถูกต้องทุกแถวและชี้กลับไปที่เอกสารได้
    หลักฐานที่แท้จริงคือ span ไม่ใช่ตัวเลขระดับ — ทิ้งของดีเพราะฟิลด์รองผิดรูปแบบคือแพงเกินไป
    """
    spans = parse_payload(payload(row(level=given)), CV, KNOWN)
    assert len(spans) == 1, "แถวต้องไม่ถูกทิ้งเพราะระดับอ่านไม่ออก"
    assert spans[0].level == expected


def test_ความมั่นใจที่ตอบเป็นคำก็แปลให้():
    spans = parse_payload(payload(row(confidence="high")), CV, KNOWN)
    assert len(spans) == 1
    assert spans[0].confidence == 1.0


def test_skillsหายไปทั้งคีย์ถือว่าไม่เจอทักษะ():
    assert parse_payload('{"note":"ไม่พบทักษะ"}', CV, KNOWN) == []


# ═════════════ ค่าที่อยู่นอกช่วง ═════════════


@pytest.mark.parametrize("given,expected", [(0, 1), (-5, 1), (2, 2), (9, 3)])
def test_ระดับถูกบีบให้อยู่ในช่วง1ถึง3(given, expected):
    spans = parse_payload(payload(row(level=given)), CV, KNOWN)
    assert spans[0].level == expected


@pytest.mark.parametrize("given,expected", [(-1.0, 0.0), (0.5, 0.5), (7.0, 1.0)])
def test_ความมั่นใจถูกบีบให้อยู่ในช่วง0ถึง1(given, expected):
    spans = parse_payload(payload(row(confidence=given)), CV, KNOWN)
    assert spans[0].confidence == expected


# ═════════════ การต่อสายเข้ากับ SDK ═════════════


class FakeMessage:
    def __init__(self, blocks):
        self.content = blocks


class FakeBlock:
    def __init__(self, text=None):
        if text is not None:
            self.text = text


class FakeClient:
    """เลียนรูปร่างที่ SDK ใช้จริง — client.messages.create(...)"""

    def __init__(self, message):
        self._message = message
        self.calls: list[dict] = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._message


def test_ส่งเอกสารและรายการทักษะไปให้llmครบ():
    client = FakeClient(FakeMessage([FakeBlock(payload(row()))]))
    spans = AnthropicExtractor(client=client).extract(CV)

    assert len(spans) == 1
    sent = client.calls[0]
    assert sent["model"], "ต้องระบุรุ่นเสมอ"
    body = sent["messages"][0]["content"]
    assert CV in body, "ต้องส่งเอกสารทั้งฉบับไป"
    assert REAL_SKILL in body, "ต้องส่งรายการทักษะที่รู้จักไปด้วย"
    assert "คัดลอก" in sent["system"], "system prompt ต้องย้ำกติกาการคัดลอกตรงตัว"


def test_บล็อกที่ไม่ใช่ข้อความถูกข้ามไปหาบล็อกที่เป็นข้อความ():
    client = FakeClient(FakeMessage([FakeBlock(), FakeBlock(payload(row()))]))
    assert len(AnthropicExtractor(client=client).extract(CV)) == 1


def test_ตอบกลับมาไม่มีข้อความเลยโยนerror():
    client = FakeClient(FakeMessage([]))
    with pytest.raises(ExtractorError):
        AnthropicExtractor(client=client).extract(CV)


def test_ไม่มีkeyและไม่มีclientสร้างไม่ได้พร้อมบอกทางออก(monkeypatch):
    monkeypatch.setattr("app.config.settings.anthropic_api_key", None)
    with pytest.raises(RuntimeError) as exc:
        AnthropicExtractor()
    assert "keyword" in str(exc.value), "ต้องบอกว่ากลับไปใช้ตัวไหนได้"


# ═════════════ 🔒 ทั้งสอง provider ต้องผ่านด่านเดียวกัน ═════════════


def test_ทั้งสองprovider_คืนโครงเดียวกันและผ่านguardเหมือนกัน():
    """หน้าจอกับ API ไม่ควรต้องรู้ว่าใช้ provider ไหนอยู่"""
    from app.llm.keyword import KeywordExtractor

    kw = KeywordExtractor().extract(CV)
    llm = AnthropicExtractor(
        client=FakeClient(FakeMessage([FakeBlock(payload(row()))]))).extract(CV)

    for spans in (kw, llm):
        for s in spans:
            assert CV[s.span_start:s.span_end] == s.span_text
            assert s.skill_id in KNOWN
            assert 1 <= s.level <= 3
