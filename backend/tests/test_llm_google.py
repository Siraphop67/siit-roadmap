"""ตัวสกัดด้วย Gemini (Google AI Studio) — ชั้นฟรีมีจริง เรียกได้ทันทีที่มี key

🔴 ไฟล์นี้ไม่ทดสอบ `parse_payload()` ซ้ำ — `test_llm_anthropic.py` คุมไว้ครบแล้ว
   และทั้งสอง provider เรียกฟังก์ชันตัวเดียวกัน ที่นี่จึงคุมเฉพาะ **การต่อสาย
   เข้ากับ SDK ของ Google** ซึ่งพังคนละแบบกับ Anthropic:

   · Gemini คืน `text` เป็น None ได้โดยไม่โยน error — ตัวกรองความปลอดภัยบล็อก
     หรือคิดจนหมดโควตา · ทั้งสองกรณีต้องกลายเป็น ExtractorError ไม่ใช่ "ไม่เจอทักษะ"
     (กติกาข้อ 5 — CV เป็นข้อมูลส่วนบุคคล ตัวกรองของ Google บล็อกได้จริง)
   · เป็น thinking model — โควตา output แชร์กับส่วนคิด เหมือนบั๊กข้อ 2 ใน D13
"""

from __future__ import annotations

import json

import pytest

from app.llm.base import ExtractorError
from app.llm.google import GeminiExtractor
from app.seed.skills import SKILLS

KNOWN = {s["id"] for s in SKILLS}
REAL_SKILL = "T-PY"
OTHER_SKILL = "T-GIT"

CV = """สมชาย ใจดี — วิศวกรรมคอมพิวเตอร์ ปี 3

- ทำระบบวิเคราะห์ข้อมูลการใช้ห้องเรียนด้วย Python และ pandas
- ดูแลโค้ดด้วย Git เขียน unit test ทุกฟีเจอร์
"""


def payload(*rows: dict) -> str:
    return json.dumps({"skills": list(rows)}, ensure_ascii=False)


def row(skill_id=REAL_SKILL, span_text="Python และ pandas", level=2, confidence=0.8):
    return {
        "skill_id": skill_id, "span_text": span_text,
        "level": level, "confidence": confidence,
    }


# ── ตัวปลอมที่เลียนรูปร่างของ google-genai จริง ──
#    client.models.generate_content(model=..., contents=..., config=...) → response.text


class FakeCandidate:
    def __init__(self, finish_reason=None):
        self.finish_reason = finish_reason


class FakeFeedback:
    def __init__(self, block_reason=None):
        self.block_reason = block_reason


class FakeResponse:
    def __init__(self, text=None, finish_reason="STOP", block_reason=None):
        self.text = text
        self.candidates = [FakeCandidate(finish_reason)] if finish_reason else []
        self.prompt_feedback = FakeFeedback(block_reason) if block_reason else None


class FakeClient:
    def __init__(self, response):
        self._response = response
        self.calls: list[dict] = []
        self.models = self

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self._response


def extractor(response) -> GeminiExtractor:
    return GeminiExtractor(client=FakeClient(response))


# ═════════════ เคสปกติ ═════════════


def test_แปลงคำตอบเป็นspanที่ชี้กลับไปที่เอกสารได้():
    spans = extractor(FakeResponse(payload(row()))).extract(CV)
    assert len(spans) == 1
    assert CV[spans[0].span_start:spans[0].span_end] == "Python และ pandas"


def test_ไม่เจอทักษะคืนรายการว่างไม่ใช่error():
    """"อ่านแล้วไม่เจอ" ต้องต่างจาก "เรียกไม่สำเร็จ" เสมอ"""
    assert extractor(FakeResponse(payload())).extract(CV) == []


def test_ส่งเอกสารระบบพรอมต์และรายการทักษะไปครบ():
    client = FakeClient(FakeResponse(payload(row())))
    GeminiExtractor(client=client).extract(CV)

    sent = client.calls[0]
    assert sent["model"], "ต้องระบุรุ่นเสมอ"
    assert CV in sent["contents"], "ต้องส่งเอกสารทั้งฉบับไป"
    assert REAL_SKILL in sent["contents"], "ต้องส่งรายการทักษะที่รู้จักไปด้วย"
    assert "คัดลอก" in sent["config"]["system_instruction"], (
        "system prompt ต้องย้ำกติกาการคัดลอกตรงตัว ไม่งั้น guard จะตัดทิ้งหมด"
    )


def test_ไม่ส่งthinking_configโดยค่าเริ่มต้น(monkeypatch):
    """🔴 วัดจริงแล้ว: gemini-3.6-flash กับ 3.5-flash-lite ตอบ 400 INVALID_ARGUMENT
       ทันทีที่ส่ง thinking_budget=0 ไปด้วย — รุ่นใหม่ไม่ให้ปิดส่วนคิด

    ค่าเริ่มต้นจึงต้อง "ไม่ส่งเลย" ปล่อยให้โมเดลตัดสินใจเอง ซึ่งใช้ได้กับทุกรุ่น
    ใครอยากบีบค่อยตั้ง GEMINI_THINKING_BUDGET เอง
    """
    monkeypatch.setattr("app.config.settings.gemini_thinking_budget", -1)
    client = FakeClient(FakeResponse(payload(row())))
    GeminiExtractor(client=client).extract(CV)
    assert "thinking_config" not in client.calls[0]["config"]


def test_ตั้งงบส่วนคิดเองแล้วส่งไปให้(monkeypatch):
    monkeypatch.setattr("app.config.settings.gemini_thinking_budget", 512)
    client = FakeClient(FakeResponse(payload(row())))
    GeminiExtractor(client=client).extract(CV)
    assert client.calls[0]["config"]["thinking_config"] == {"thinking_budget": 512}


def test_รุ่นที่ไม่ให้ปิดส่วนคิดบอกให้ไปแก้ตัวแปรที่ถูก():
    """400 ของ Google ไม่บอกว่าฟิลด์ไหนผิด — เราเสียเวลาไล่หาเองมาแล้ว ครั้งเดียวพอ"""
    err = Exception("400 INVALID_ARGUMENT. Request contains an invalid argument.")
    with pytest.raises(ExtractorError) as exc:
        GeminiExtractor(client=RaisingClient(err)).extract(CV)
    assert "GEMINI_THINKING_BUDGET" in str(exc.value)


def test_ขอคำตอบเป็นjsonและอุณหภูมิศูนย์():
    """ต้องได้ผลเดิมทุกครั้ง ไม่งั้นวัด before/after ไม่ได้ (เหตุผลเดียวกับฝั่ง local)"""
    client = FakeClient(FakeResponse(payload(row())))
    GeminiExtractor(client=client).extract(CV)

    config = client.calls[0]["config"]
    assert config["response_mime_type"] == "application/json"
    assert config["temperature"] == 0


# ═════════════ 🛡 span guard ต้องทำงานเหมือน provider อื่นทุกประการ ═════════════


def test_ข้อความที่ไม่มีในเอกสารถูกทิ้ง():
    faked = row(span_text="มีประสบการณ์ Python อย่างช่ำชอง")   # ไม่มีประโยคนี้ใน CV
    assert extractor(FakeResponse(payload(faked))).extract(CV) == []


def test_ทักษะนอกคลังถูกทิ้งแต่ข้ออื่นรอด():
    spans = extractor(FakeResponse(
        payload(row(skill_id="ไม่มีจริง"), row()))).extract(CV)
    assert [s.skill_id for s in spans] == [REAL_SKILL]


def test_ห่อด้วยmarkdownfenceยังอ่านได้():
    """ขอ JSON mode ไว้แล้วก็จริง แต่ห้ามพึ่งมันอย่างเดียว"""
    spans = extractor(FakeResponse(f"```json\n{payload(row())}\n```")).extract(CV)
    assert len(spans) == 1


# ═════════════ 🔒 กติกาข้อ 5 — พังต้องบอกว่าพัง ═════════════


def test_ตัวกรองความปลอดภัยบล็อกโยนerrorไม่ใช่คืนว่าง():
    """CV เป็นข้อมูลส่วนบุคคล ตัวกรองของ Google บล็อกได้จริง

    ถ้ากลืนเป็น "ไม่เจอทักษะ" ผู้ใช้จะเข้าใจว่าผลงานตัวเองไม่มีอะไรเลย
    """
    with pytest.raises(ExtractorError) as exc:
        extractor(FakeResponse(None, finish_reason=None,
                               block_reason="SAFETY")).extract(CV)
    assert "SAFETY" in str(exc.value)


def test_คิดจนหมดโควตาโยนerrorที่บอกวิธีแก้():
    """บั๊กข้อ 2 ใน D13 ซ้ำรอย — thinking model ใช้โควตา output ร่วมกับส่วนคิด

    ตอนนั้นได้ content ว่างโดยไม่มี error อะไรบอก เสียเวลาไล่หาสาเหตุนาน
    """
    with pytest.raises(ExtractorError) as exc:
        extractor(FakeResponse(None, finish_reason="MAX_TOKENS")).extract(CV)
    assert "โควตา" in str(exc.value)


def test_ตอบกลับมาไม่มีข้อความเลยโยนerror():
    with pytest.raises(ExtractorError):
        extractor(FakeResponse(None)).extract(CV)


def test_ตอบไม่ใช่jsonโยนerrorไม่ใช่คืนว่าง():
    with pytest.raises(ExtractorError):
        extractor(FakeResponse("ขอโทษครับ ผมช่วยเรื่องนี้ไม่ได้")).extract(CV)


# ═════════════ เรียก API ไม่สำเร็จ — ต้องบอกสาเหตุที่แก้ต่อได้ ═════════════
#
# 🔴 เจอจริงตอนยิงครั้งแรก: gemini-2.5-flash ถูกปิดสำหรับ key ใหม่ แล้ว SDK โยน
#    ClientError ทะลุขึ้นมาเป็น traceback 40 บรรทัด ซึ่งไม่ได้บอกว่าต้องไปแก้ตรงไหน
#    มาตรฐานของ repo นี้คือข้อความ error ต้องชี้ทางออก (ดู local.py ที่แยก 404
#    ออกจาก timeout ออกจากต่อไม่ติด) — ฝั่ง gemini ต้องทำแบบเดียวกัน


class RaisingClient:
    def __init__(self, exc):
        self._exc = exc
        self.models = self

    def generate_content(self, **kwargs):
        raise self._exc


def test_รุ่นที่เรียกไม่ได้บอกให้เปลี่ยนGEMINI_MODEL():
    err = Exception("404 NOT_FOUND. This model models/gemini-2.5-flash is no "
                    "longer available to new users.")
    with pytest.raises(ExtractorError) as exc:
        GeminiExtractor(client=RaisingClient(err)).extract(CV)
    assert "GEMINI_MODEL" in str(exc.value), "ต้องบอกว่าไปแก้ตัวแปรไหน"


def test_ชนเพดานชั้นฟรีบอกว่าเป็นเพดานไม่ใช่ระบบพัง():
    """เพดานต่อนาทีของชั้นฟรีจะชนตอนสาธิตพร้อมกันหลายคน — ต้องอ่านออกทันที"""
    err = Exception("429 RESOURCE_EXHAUSTED. Quota exceeded.")
    with pytest.raises(ExtractorError) as exc:
        GeminiExtractor(client=RaisingClient(err)).extract(CV)
    assert "เพดาน" in str(exc.value)


def test_keyผิดบอกให้ไปดูGOOGLE_API_KEY():
    err = Exception("400 INVALID_ARGUMENT. API key not valid.")
    with pytest.raises(ExtractorError) as exc:
        GeminiExtractor(client=RaisingClient(err)).extract(CV)
    assert "GOOGLE_API_KEY" in str(exc.value)


def test_เรียกไม่สำเร็จแบบไม่รู้จักก็ยังเป็นExtractorErrorไม่ใช่tracebackดิบ():
    with pytest.raises(ExtractorError):
        GeminiExtractor(client=RaisingClient(Exception("อะไรสักอย่าง"))).extract(CV)


# ═════════════ ลองใหม่เมื่อเซิร์ฟเวอร์แน่น ═════════════
#
# 🔴 วัดจริงแล้ว: gemini-3.5-flash ตอบ 503 ไป 2 ใน 3 ครั้ง (ดู DECISIONS D17)
#    503 ไม่ใช่ความผิดของเรา และมักหายเองในไม่กี่วินาที — ปล่อยให้ผู้ใช้เห็น error
#    ทั้งที่กดใหม่แล้วผ่าน เป็นการโยนภาระให้ผู้ใช้แก้ปัญหาของ Google
#
# 🔒 แต่ห้ามลองใหม่กับทุกอย่าง — 429 คือเราส่งเกินโควตา ยิงซ้ำยิ่งแย่
#    400/404 คือคำขอผิดตั้งแต่แรก ยิงกี่รอบก็ผิดเหมือนเดิม


class FlakyClient:
    """ล้มไปก่อน `fail_times` ครั้ง แล้วค่อยสำเร็จ — นับจำนวนครั้งที่ถูกเรียกจริง"""

    def __init__(self, exc, fail_times: int, response=None):
        self._exc, self._fail_times, self._response = exc, fail_times, response
        self.calls = 0
        self.models = self

    def generate_content(self, **kwargs):
        self.calls += 1
        if self.calls <= self._fail_times:
            raise self._exc
        return self._response


def unavailable() -> Exception:
    return Exception("503 UNAVAILABLE. This model is currently experiencing high demand.")


@pytest.fixture(autouse=True)
def _no_real_waiting(monkeypatch):
    """เทสต์ต้องไม่รอจริง — เก็บไว้ตรวจว่าหน่วงเพิ่มขึ้นจริงไหม"""
    slept: list[float] = []
    monkeypatch.setattr("app.llm.google._sleep", slept.append)
    return slept


def test_เจอ503แล้วลองใหม่จนสำเร็จผู้ใช้ไม่เห็นerrorเลย():
    client = FlakyClient(unavailable(), fail_times=1,
                         response=FakeResponse(payload(row())))
    spans = GeminiExtractor(client=client).extract(CV)

    assert len(spans) == 1, "ครั้งที่สองสำเร็จแล้ว ต้องได้ผลปกติ"
    assert client.calls == 2


def test_ลองใหม่ได้หลายรอบ():
    client = FlakyClient(unavailable(), fail_times=2,
                         response=FakeResponse(payload(row())))
    assert len(GeminiExtractor(client=client).extract(CV)) == 1
    assert client.calls == 3


def test_แน่นตลอดสุดท้ายก็ยอมแพ้แต่บอกว่าลองมากี่ครั้งแล้ว():
    """🔒 กติกาข้อ 5 — ยอมแพ้ได้ แต่ต้องบอกตามจริงว่าพยายามไปเท่าไหร่"""
    client = FlakyClient(unavailable(), fail_times=99)
    with pytest.raises(ExtractorError) as exc:
        GeminiExtractor(client=client).extract(CV)

    assert client.calls == GeminiExtractor.MAX_ATTEMPTS
    assert str(client.calls) in str(exc.value), "ต้องบอกจำนวนครั้งที่ลอง"


def test_หน่วงนานขึ้นทุกรอบไม่ใช่ยิงรัวติดกัน(_no_real_waiting):
    """ยิงรัวตอนเซิร์ฟเวอร์แน่นคือการซ้ำเติม — ต้องถอยห่างขึ้นเรื่อย ๆ"""
    with pytest.raises(ExtractorError):
        GeminiExtractor(client=FlakyClient(unavailable(), fail_times=99)).extract(CV)

    assert len(_no_real_waiting) == GeminiExtractor.MAX_ATTEMPTS - 1, "รอบสุดท้ายไม่ต้องหน่วง"
    assert _no_real_waiting == sorted(_no_real_waiting)
    assert _no_real_waiting[0] < _no_real_waiting[-1], "ต้องนานขึ้นจริง"


@pytest.mark.parametrize("raw,why", [
    ("429 RESOURCE_EXHAUSTED. Quota exceeded.", "โควตาหมด ยิงซ้ำยิ่งแย่"),
    ("400 INVALID_ARGUMENT. Request contains an invalid argument.", "คำขอผิดตั้งแต่แรก"),
    ("404 NOT_FOUND. This model is no longer available.", "รุ่นนี้เรียกไม่ได้"),
    ("400 INVALID_ARGUMENT. API key not valid.", "key ผิด"),
])
def test_ไม่ลองใหม่กับความผิดพลาดที่ยิงซ้ำก็ไม่หาย(raw, why):
    client = FlakyClient(Exception(raw), fail_times=99)
    with pytest.raises(ExtractorError):
        GeminiExtractor(client=client).extract(CV)
    assert client.calls == 1, f"{why} — ต้องเลิกตั้งแต่ครั้งแรก"


def test_ข้อความ503ยังบอกสาเหตุเดิมหลังยอมแพ้():
    with pytest.raises(ExtractorError) as exc:
        GeminiExtractor(client=FlakyClient(unavailable(), fail_times=99)).extract(CV)
    assert "503" in str(exc.value) or "แน่น" in str(exc.value)


def test_ไม่มีkeyและไม่มีclientสร้างไม่ได้พร้อมบอกทางออก(monkeypatch):
    monkeypatch.setattr("app.config.settings.google_api_key", None)
    with pytest.raises(RuntimeError) as exc:
        GeminiExtractor()
    assert "keyword" in str(exc.value), "ต้องบอกว่ากลับไปใช้ตัวไหนได้"


# ═════════════ ต่อเข้ากับระบบ ═════════════


def test_get_extractorรู้จักgemini(monkeypatch):
    from app.llm import get_extractor

    monkeypatch.setattr("app.config.settings.llm_provider", "gemini")
    monkeypatch.setattr("app.config.settings.google_api_key", "ทดสอบ")
    assert get_extractor().name == "gemini"


def test_metaรายงานชื่อรุ่นจริงไม่ใช่คำว่าgemini(monkeypatch):
    """🔒 กติกาข้อ 5 — /meta เอาค่านี้ไปขึ้นจอว่า "กำลังอ่านด้วยอะไร"

    เคยพลาดตอนเพิ่ม local มาแล้ว (ดูคอมเมนต์ใน api.py) — หน้าจอบอกชื่อ provider
    แทนชื่อรุ่น ผู้ใช้จึงไม่รู้ว่าอ่านด้วยอะไรจริง ๆ
    """
    from app.config import settings

    monkeypatch.setattr("app.config.settings.llm_provider", "gemini")
    monkeypatch.setattr("app.config.settings.gemini_model", "gemini-2.5-flash")
    assert settings.llm_model_in_use == "gemini-2.5-flash"
    assert settings.llm_is_real is True


def test_โครงผลลัพธ์เหมือนกับตัวจับคำสำคัญทุกประการ():
    """หน้าจอกับ API ไม่ควรต้องรู้ว่าใช้ provider ไหนอยู่"""
    from app.llm.keyword import KeywordExtractor

    kw = KeywordExtractor().extract(CV)
    gem = extractor(FakeResponse(payload(row()))).extract(CV)

    for spans in (kw, gem):
        for s in spans:
            assert CV[s.span_start:s.span_end] == s.span_text
            assert s.skill_id in KNOWN
            assert 1 <= s.level <= 3
