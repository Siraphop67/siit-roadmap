"""ตัวสกัดด้วย Gemini (Google AI Studio) — ชั้นฟรีใช้ได้จริง ไม่ต้องผูกบัตร

    LLM_PROVIDER=gemini
    GOOGLE_API_KEY=...            # ขอที่ https://aistudio.google.com/apikey
    GEMINI_MODEL=gemini-2.5-flash # ค่าเริ่มต้น

ทำไมถึงเพิ่มตัวนี้ทั้งที่มี `local` อยู่แล้ว — **เรื่องความเร็ว ไม่ใช่เรื่องความแม่น**
D13 วัดไว้ว่า LLM ในเครื่องใช้ ~78 วินาทีต่อ CV 1 ใบ ซึ่งช้าเกินกว่าจะสาธิตสดได้
แผนเดิมจึงเป็น "วันสาธิตใช้ keyword แล้วโชว์ผล LLM เป็นภาพที่เตรียมไว้"
Flash ตอบในไม่กี่วินาที — สาธิต LLM จริงสดบนเวทีได้

🛡 span guard เหมือนกันทุก provider — ผ่าน `parse_payload()` ตัวเดียวกับ Anthropic
   และ local · Gemini บังคับรูปแบบ JSON ให้ได้ก็จริง แต่ **บังคับให้ไม่แต่งข้อความไม่ได้**
   guard จึงยังเป็นด่านที่ขาดไม่ได้ ห้ามผ่อนให้ตัวไหนทั้งนั้น

🔴 ข้อควรรู้ก่อนใช้กับ CV ของผู้ใช้จริง
   · **ชั้นฟรีของ Google ระบุว่านำข้อมูลไปพัฒนาผลิตภัณฑ์ของเขา** (ชั้นเสียเงินไม่นำไป)
     CV เป็นข้อมูลส่วนบุคคล — ก่อนเปิดรับ CV จริงในวัน Hack Days ทีมต้องเลือกว่าจะ
     เปิดชั้นเสียเงิน ใช้ `local` หรือเขียนบอกไว้ในหน้าขอความยินยอม
   · **ตัวกรองความปลอดภัยบล็อกได้** โดยไม่โยน error — คืน text ว่างเฉย ๆ
     เราแปลงเป็น ExtractorError เสมอ ไม่ปล่อยให้กลายเป็น "อ่านแล้วไม่เจอทักษะ"
   · ชั้นฟรีมีเพดานต่อนาที/ต่อวัน — สาธิตพร้อมกันหลายคนอาจชนเพดาน
"""

from __future__ import annotations

import time

from app.config import settings
from app.llm.base import (
    SYSTEM_PROMPT,
    ExtractedSpan,
    ExtractorError,
    parse_payload,
)
from app.seed.skills import SKILLS

# 🔴 สูงกว่าฝั่ง Anthropic เพราะ Gemini 2.5 ขึ้นไปเป็น thinking model —
#    ส่วนคิดใช้โควตา output ร่วมกับคำตอบ เหมือนบั๊กข้อ 2 ใน D13 เป๊ะ
#    (ค่าเริ่มต้นเราปิดส่วนคิดไว้อยู่แล้ว นี่คือเผื่อไว้ให้คนที่เปิดมันกลับมา)
MAX_TOKENS = 8000

#: หน่วงก่อนลองใหม่ครั้งแรก แล้วคูณสองไปเรื่อย ๆ (2 วินาที → 4 วินาที)
#: ไม่ใส่ค่าสุ่ม (jitter) เพราะเรามีเครื่องเดียวยิง ไม่ได้มีหลายตัวแย่งกันกลับมาพร้อมกัน
BACKOFF_SECONDS = 2.0


def _sleep(seconds: float) -> None:
    """แยกออกมาเป็นฟังก์ชันเพื่อให้เทสต์แทนได้ — เทสต์ต้องไม่รอจริง"""
    time.sleep(seconds)


def _is_busy(exc: Exception) -> bool:
    """เซิร์ฟเวอร์แน่นชั่วคราวหรือเปล่า — อย่างเดียวที่ลองใหม่แล้วมีความหมาย

    🔒 ห้ามรวม 429 เข้ามา — นั่นคือเราส่งเกินโควตา ยิงซ้ำยิ่งทำให้แย่ลง
       และห้ามรวม 400/404 — คำขอผิดตั้งแต่แรก ยิงกี่รอบก็ผิดเหมือนเดิม
    """
    raw = str(exc)
    return "503" in raw or "UNAVAILABLE" in raw

#: โครงคำตอบที่บังคับกับโมเดล — ตัดปัญหา "ตอบไม่เป็น JSON" ทิ้งไปทั้งชุด
#: แต่ยังส่งต่อให้ parse_payload() ตรวจอยู่ดี เพราะ schema กันการ "แต่งข้อความ" ไม่ได้
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "skill_id": {"type": "string"},
                    "span_text": {"type": "string"},
                    "level": {"type": "integer"},
                    "confidence": {"type": "number"},
                },
                "required": ["skill_id", "span_text"],
            },
        }
    },
    "required": ["skills"],
}


class GeminiExtractor:
    name = "gemini"

    #: ยิงได้มากสุดกี่ครั้งต่อการอ่านหนึ่งเอกสาร (รวมครั้งแรก)
    #: 🔴 3 ครั้งเพราะวัดแล้วว่า 503 ของชั้นฟรีมักหายใน 2–3 วินาที (D17)
    #:    ตั้งสูงกว่านี้ผู้ใช้จะรอนานโดยไม่รู้ว่าเกิดอะไรขึ้น — 2+4 = ช้าสุด 6 วินาที
    MAX_ATTEMPTS = 3

    def __init__(self, client=None) -> None:
        """`client` มีไว้ให้เทสต์ยัดตัวปลอมเข้ามา — ใช้งานจริงปล่อยเป็น None"""
        self._client = client
        self.model = settings.gemini_model
        if client is None and not settings.google_api_key:
            raise RuntimeError(
                "ตั้ง LLM_PROVIDER=gemini แต่ไม่มี GOOGLE_API_KEY — "
                "ขอ key ฟรีที่ https://aistudio.google.com/apikey "
                "หรือกลับไปใช้ LLM_PROVIDER=keyword"
            )

    def _skill_catalogue(self) -> str:
        return "\n".join(f'{s["id"]} = {s["name_th"]}' for s in SKILLS)

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from google import genai   # นำเข้าตรงนี้ ระบบจะได้รันได้แม้ยังไม่ได้ติดตั้ง
        except ImportError as exc:
            raise ExtractorError(
                "ยังไม่ได้ติดตั้งไลบรารี google-genai — "
                "pip install -r backend/requirements.txt"
            ) from exc
        self._client = genai.Client(api_key=settings.google_api_key)
        return self._client

    def _config(self) -> dict:
        config: dict = {
            "system_instruction": SYSTEM_PROMPT,
            "max_output_tokens": MAX_TOKENS,
            "temperature": 0,        # ต้องได้ผลเดิมทุกครั้ง จะได้วัด before/after ได้
            "response_mime_type": "application/json",
            "response_schema": RESPONSE_SCHEMA,
        }
        # ปิดส่วนคิดโดยค่าเริ่มต้น — เร็วกว่ามากและผลนิ่งกว่า ซึ่งคือเหตุผลทั้งหมด
        # ที่เพิ่ม provider นี้ · ตั้ง GEMINI_THINKING_BUDGET=-1 เพื่อคืนค่าให้โมเดลคิดเอง
        if settings.gemini_thinking_budget >= 0:
            config["thinking_config"] = {
                "thinking_budget": settings.gemini_thinking_budget
            }
        return config

    def _text_or_explain(self, response) -> str:
        """ดึงข้อความออกมา หรือบอกให้ชัดว่าทำไมไม่มี

        🔒 กติกาข้อ 5 — Gemini คืนข้อความว่างได้โดยไม่โยน error สักตัว
           ถ้าปล่อยผ่าน ผู้ใช้จะเห็นผลว่างแล้วเข้าใจว่าผลงานตัวเองไม่มีอะไรเลย
        """
        try:
            text = response.text
        except (ValueError, AttributeError):
            text = None                       # SDK บางรุ่นโยนเมื่อคำตอบถูกบล็อก

        if isinstance(text, str) and text.strip():
            return text

        blocked = getattr(getattr(response, "prompt_feedback", None), "block_reason", None)
        if blocked:
            raise ExtractorError(
                f"Gemini ปฏิเสธเอกสารนี้ด้วยเหตุผล {blocked} — "
                "ตัวกรองความปลอดภัยของ Google บล็อก ไม่ใช่ว่าเอกสารไม่มีทักษะ"
            )

        candidates = getattr(response, "candidates", None) or []
        reason = str(getattr(candidates[0], "finish_reason", "")) if candidates else ""
        if "MAX_TOKENS" in reason:
            raise ExtractorError(
                f"Gemini ใช้โควตา {MAX_TOKENS} โทเคนหมดก่อนตอบจบ — "
                "ถ้าเปิดส่วนคิดไว้ (GEMINI_THINKING_BUDGET) ให้ลดลงหรือปิดเป็น 0"
            )
        if "SAFETY" in reason or "RECITATION" in reason:
            raise ExtractorError(
                f"Gemini หยุดกลางคันด้วยเหตุผล {reason} — ไม่ใช่ว่าเอกสารไม่มีทักษะ"
            )
        raise ExtractorError(
            f"Gemini ตอบกลับมาโดยไม่มีข้อความ (finish_reason={reason or 'ไม่ทราบ'})"
        )

    def _explain_api_error(self, exc: Exception, *, attempts: int = 1) -> str:
        """แปลง error ของ SDK เป็นข้อความที่บอกว่าต้องไปแก้ตรงไหน

        🔴 เจอจริงตอนยิงครั้งแรก — SDK โยน ClientError ทะลุขึ้นมาเป็น traceback
           40 บรรทัดที่ไม่ได้บอกว่าต้องแก้อะไร · local.py แยกกรณีไว้ให้ดูเป็นตัวอย่างแล้ว
        """
        raw = str(exc)
        if "404" in raw or "NOT_FOUND" in raw:
            return (
                f"Google ไม่ให้ใช้รุ่น {self.model!r} ด้วย key นี้ — "
                "บางรุ่นถูกปิดสำหรับ key ที่สร้างใหม่ · เปลี่ยน GEMINI_MODEL "
                "เป็นรุ่นที่ใหม่กว่า (เช่น gemini-3.5-flash)"
            )
        if "429" in raw or "RESOURCE_EXHAUSTED" in raw:
            return (
                "ชนเพดานของชั้นฟรี (429) ไม่ใช่ระบบพัง — "
                "รอสักครู่แล้วลองใหม่ หรือลดจำนวนคนที่ยิงพร้อมกัน"
            )
        if "API key" in raw or "API_KEY" in raw or "PERMISSION_DENIED" in raw or "403" in raw:
            return (
                "Google ปฏิเสธ key นี้ — ตรวจ GOOGLE_API_KEY ใน backend/.env "
                "(ขอใหม่ได้ที่ https://aistudio.google.com/apikey)"
            )
        if "INVALID_ARGUMENT" in raw or "400" in raw:
            # 🔴 400 ของ Google ไม่บอกว่าฟิลด์ไหนผิด — เราไล่หาเองมาแล้วครั้งหนึ่ง
            #    สาเหตุที่เจอจริงคือ thinking_budget=0 กับรุ่นที่ไม่ให้ปิดส่วนคิด
            return (
                f"Google ปฏิเสธคำขอ (400) กับรุ่น {self.model!r} — "
                "สาเหตุที่พบบ่อยคือ GEMINI_THINKING_BUDGET ตั้งเป็น 0 แต่รุ่นใหม่ "
                "ไม่ให้ปิดส่วนคิด · ตั้งเป็น -1 เพื่อไม่ส่งค่านี้ไปเลย"
            )
        if "503" in raw or "UNAVAILABLE" in raw:
            # 🔒 กติกาข้อ 5 — ยอมแพ้ได้ แต่ต้องบอกตามจริงว่าพยายามไปกี่ครั้งแล้ว
            #    ไม่งั้นผู้ใช้จะไม่รู้ว่าระบบลองให้แล้ว และกดซ้ำเองอีกโดยเปล่าประโยชน์
            return (
                f"รุ่น {self.model!r} คนใช้แน่นอยู่ (503) ไม่ใช่ระบบเราพัง — "
                f"ลองให้แล้ว {attempts} ครั้งยังไม่ผ่าน "
                "รอสักครู่แล้วลองใหม่ หรือสลับไปรุ่นอื่นด้วย GEMINI_MODEL"
            )
        return f"เรียก Gemini ไม่สำเร็จ — {type(exc).__name__}: {raw[:300]}"

    def _call(self, raw_text: str):
        """ยิงจริง พร้อมลองใหม่เมื่อเซิร์ฟเวอร์แน่น

        🔴 503 ไม่ใช่ความผิดของเราและมักหายเองในไม่กี่วินาที (วัดไว้ใน D17 ว่า
           gemini-3.5-flash ตอบ 503 ไป 2 ใน 3 ครั้ง) — ถ้าไม่ลองใหม่ให้ ก็เท่ากับ
           โยนภาระให้ผู้ใช้กดเองซ้ำ ๆ เพื่อแก้ปัญหาที่ฝั่ง Google
        """
        contents = (
            f"รายการทักษะที่รู้จัก:\n{self._skill_catalogue()}\n\n"
            f"เอกสารของผู้ใช้:\n<document>\n{raw_text}\n</document>"
        )
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                return self._get_client().models.generate_content(
                    model=self.model, contents=contents, config=self._config())
            except ExtractorError:
                raise                  # ของเราเอง (เช่นยังไม่ได้ติดตั้งไลบรารี) ปล่อยผ่าน
            except Exception as exc:   # noqa: BLE001 — ในบล็อกนี้มีแค่การเรียก API
                if not _is_busy(exc) or attempt == self.MAX_ATTEMPTS:
                    raise ExtractorError(
                        self._explain_api_error(exc, attempts=attempt)) from exc
                _sleep(BACKOFF_SECONDS * 2 ** (attempt - 1))

    def extract(self, raw_text: str) -> list[ExtractedSpan]:
        response = self._call(raw_text)
        return parse_payload(
            self._text_or_explain(response), raw_text, {s["id"] for s in SKILLS}
        )
