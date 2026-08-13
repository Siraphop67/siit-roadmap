"""ชั้นเชื่อมต่อตัวสกัดข้อมูล — สลับ provider ได้โดยไม่แตะ logic ที่ไหน

provider:
  keyword    ตัวสกัดด้วยคำสำคัญ กำหนดผลได้ ไม่ต้องมี API key  ← ค่าเริ่มต้น
  anthropic  เรียก LLM จริง เมื่อมี ANTHROPIC_API_KEY

🛡 span guard — กติกาที่ทั้งสอง provider ต้องผ่านเหมือนกัน
   `span_text` ต้องเป็นข้อความที่ตัดมาจาก `raw_text` ตรงตัว
   ถ้าหาไม่เจอในต้นฉบับ = ทิ้ง ไม่ว่าจะมาจากตัวไหน
   นี่คือสิ่งที่ทำให้หน้าจอไฮไลต์กลับไปที่บรรทัดใน CV ได้จริง และเป็นเหตุผลที่
   ผู้ใช้ยืนยันผลได้อย่างมีความหมาย
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Protocol

from app.config import settings


@dataclass(frozen=True)
class ExtractedSpan:
    skill_id: str
    span_start: int
    span_end: int
    span_text: str
    level: int
    confidence: float

    def verify(self, raw_text: str) -> bool:
        """ข้อความที่อ้างต้องอยู่ในต้นฉบับจริง ณ ตำแหน่งที่บอก"""
        if not self.span_text:
            return False
        if not (0 <= self.span_start < self.span_end <= len(raw_text)):
            return False
        return raw_text[self.span_start:self.span_end] == self.span_text


class SkillExtractor(Protocol):
    name: str

    def extract(self, raw_text: str) -> list[ExtractedSpan]:
        ...


def enforce_span_guard(spans: list[ExtractedSpan], raw_text: str) -> list[ExtractedSpan]:
    """ทิ้งทุกอันที่อ้างข้อความซึ่งไม่มีอยู่จริงในเอกสาร

    🔴 ห้ามข้ามขั้นนี้ไม่ว่าจะเชื่อ provider แค่ไหน — ถ้า LLM แต่งข้อความขึ้นมา
       แล้วเราปล่อยผ่าน ผู้ใช้จะเห็นไฮไลต์ที่ชี้ไปผิดที่ ซึ่งแย่กว่าไม่มีไฮไลต์เลย
    """
    return [s for s in spans if s.verify(raw_text)]


MAX_TOKENS = 4000

SYSTEM_PROMPT = """คุณคือตัวสกัดหลักฐานความสามารถจากเรซูเม่ของนักศึกษาวิศวกรรม

หน้าที่: อ่านเอกสาร แล้วบอกว่ามีหลักฐานของทักษะใดในรายการบ้าง

กติกาที่ห้ามละเมิด:
1. span_text ต้องคัดลอกจากเอกสารต้นฉบับแบบ "ตรงตัวอักษรต่ออักษร" ห้ามเรียบเรียงใหม่
2. ถ้าไม่มีข้อความในเอกสารที่รองรับทักษะนั้น ห้ามใส่ทักษะนั้นลงไป
3. ระดับ: 1 = เอ่ยถึงหรือเคยเรียน · 2 = เคยใช้ในงานหรือโครงงาน · 3 = ใช้เป็นหลักและมีผลลัพธ์
4. ห้ามเดาจากสาขาที่เรียน ให้ดูจากสิ่งที่เขียนไว้ในเอกสารเท่านั้น

ตอบเป็น JSON เท่านั้น ห้ามมีข้อความอื่นนอก JSON:
{"skills":[{"skill_id","span_text","level","confidence"}]}"""

# LLM ชอบห่อ JSON ด้วย ```json ... ``` แม้จะสั่งว่าห้าม — ลอกออกก่อน parse
FENCE = re.compile(r"\A\s*```(?:json)?\s*(.*?)\s*```\s*\Z", re.S)


class ExtractorError(RuntimeError):
    """ตัวสกัดทำงานไม่สำเร็จ — คนละเรื่องกับ "อ่านแล้วไม่เจอทักษะ"

    🔒 ห้ามกลืนเป็น "ไม่เจอทักษะ" เด็ดขาด เพราะผู้ใช้จะเห็นผลว่าง แล้วเข้าใจว่า
       ผลงานตัวเองไม่มีอะไรเลย ทั้งที่จริงคือระบบเรียก LLM ไม่สำเร็จ
       (กติกาข้อ 5 — ระบบต้องรายงานตามจริง)
    """


#: คำบอกระดับที่โมเดลชอบตอบเป็นข้อความแทนตัวเลข — แปลให้แทนที่จะทิ้งทั้งแถว
_WORDS = {
    "high": 3, "medium": 2, "moderate": 2, "low": 1,
    "strong": 3, "expert": 3, "advanced": 3, "intermediate": 2, "beginner": 1, "basic": 1,
    "สูง": 3, "ปานกลาง": 2, "กลาง": 2, "ต่ำ": 1,
}


def _clamp_int(value, lo: int, hi: int, *, default: int) -> int:
    if isinstance(value, str) and (w := _WORDS.get(value.strip().lower())):
        value = w
    try:
        return max(lo, min(hi, int(float(value))))
    except (TypeError, ValueError):
        return default


def _clamp_float(value, lo: float, hi: float, *, default: float) -> float:
    if isinstance(value, str) and (w := _WORDS.get(value.strip().lower())):
        value = w / 3          # high → 1.0 · medium → 0.67 · low → 0.33
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return default


def parse_payload(text: str, raw_text: str, known_skills: set[str]) -> list[ExtractedSpan]:
    """แปลงคำตอบ LLM เป็น span ที่ผ่าน guard แล้ว — ฟังก์ชันบริสุทธิ์ เทสต์ได้โดยไม่ต้องมี key

    แถวที่ผิดรูปแบบจะถูกข้ามทีละแถว ไม่ทำให้ทั้งเอกสารพัง —
    LLM พลาดบางข้อเป็นเรื่องปกติ แต่ทิ้งผลทั้งชุดเพราะข้อเดียวไม่ใช่
    """
    if fenced := FENCE.match(text):
        text = fenced.group(1)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExtractorError(f"LLM ตอบกลับมาไม่ใช่ JSON ที่อ่านได้: {exc}") from exc

    if not isinstance(payload, dict):
        raise ExtractorError("LLM ตอบกลับมาไม่ใช่ object ที่มีคีย์ skills")

    spans: list[ExtractedSpan] = []
    for row in payload.get("skills") or []:
        if not isinstance(row, dict):
            continue
        skill_id = row.get("skill_id")
        span_text = row.get("span_text")
        if not isinstance(skill_id, str) or not isinstance(span_text, str) or not span_text:
            continue
        if skill_id not in known_skills:
            continue                       # อ้างทักษะนอกคลัง 73 ตัว → ทิ้ง

        start = raw_text.find(span_text)   # LLM ไม่ต้องนับตำแหน่งเอง เราหาให้
        if start < 0:
            continue                       # แต่งข้อความที่ไม่มีในเอกสาร → ทิ้ง

        # 🔴 ระดับกับความมั่นใจไม่ใช่ของที่ต้องสมบูรณ์ถึงจะใช้แถวนี้ได้
        #    หลักฐานที่แท้จริงคือ skill_id + span_text ซึ่งผ่านมาแล้วข้างบน
        #    เคยพลาดมาแล้ว: gemma4 ตอบ confidence:"high" เป็นข้อความ แล้วทั้ง 15 แถวถูกทิ้ง
        #    ทั้งที่ทุกแถวชี้กลับไปที่เอกสารได้ถูกต้อง — ทิ้งของดีเพราะฟิลด์รองผิดรูปแบบ
        level = _clamp_int(row.get("level"), 1, settings.max_level, default=1)
        confidence = _clamp_float(row.get("confidence"), 0.0, 1.0, default=0.5)

        spans.append(ExtractedSpan(
            skill_id=skill_id,
            span_start=start, span_end=start + len(span_text), span_text=span_text,
            level=level, confidence=max(0.0, min(1.0, confidence)),
        ))

    # 🛡 ด่านสุดท้าย — ต่อให้ทุกอย่างข้างบนพลาด ข้อความที่ชี้ไม่ได้จะไม่รอดออกไป
    return enforce_span_guard(spans, raw_text)
