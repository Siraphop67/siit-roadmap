"""ตัวสกัดด้วย LLM จริง — ใช้เมื่อมี ANTHROPIC_API_KEY

    LLM_PROVIDER=anthropic
    ANTHROPIC_API_KEY=...

🔴 ยังไม่เคยยิง API จริงสักครั้ง เพราะทีมยังไม่มี key
   แต่ส่วนที่พังได้จริงคือ **การแปลงคำตอบเป็น span** ไม่ใช่การเรียก API
   ส่วนนั้นจึงแยกออกมาเป็น `parse_payload()` ที่เป็นฟังก์ชันบริสุทธิ์ และมีเทสต์คุมครบ
   วันที่ได้ key มา สิ่งที่ต้องทดสอบจริงจึงเหลือแค่ "เรียกติดไหม" ไม่ใช่ "แปลงถูกไหม"

สิ่งที่ตัวนี้ทำได้ดีกว่าตัวสกัดด้วยคำสำคัญ:
   · เข้าใจการบรรยายที่ไม่ได้ใช้คำตรง — "ทำให้สองระบบคุยกันได้" → SW-API
   · แยกได้ว่า "อยากเรียน Python" ต่างจาก "ใช้ Python ทำโปรเจกต์จริง"
   · ประเมินระดับจากบริบทแทนที่จะนับจำนวนครั้ง

สิ่งที่ตัวนี้ **ไม่** ทำให้ดีขึ้น — อย่าสัญญาเกินนี้:
   · อ่านได้เฉพาะทักษะที่มีในคลัง 73 ตัว · CV สายอื่นยังไม่มีที่ให้ลง
   · PDF ที่เป็นภาพสแกนยังได้ข้อความว่าง (เส้นทางนี้เป็น text-only ไม่ได้ส่งภาพ)
   · LinkedIn ยังต้องให้ผู้ใช้วางเอง — เป็นเรื่อง ToS ไม่ใช่เรื่อง key

🛡 span guard เหมือนกันทั้งสอง provider
   LLM ต้องคัดลอกข้อความจากเอกสารมาตรงตัว ถ้าแต่งขึ้นเอง เราทิ้ง
   ห้ามผ่อนข้อนี้ให้ LLM ไม่ว่ากรณีใด — ไฮไลต์ที่ชี้ผิดที่แย่กว่าไม่มีไฮไลต์
"""

from __future__ import annotations

import json
import re

from app.config import settings
from app.llm.base import ExtractedSpan, enforce_span_guard
from app.seed.skills import SKILLS

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


def _first_text_block(message) -> str:
    """ดึงข้อความจากคำตอบ — content เป็นลิสต์ของ block ที่อาจไม่ใช่ text ทั้งหมด"""
    for block in getattr(message, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            return text
    raise ExtractorError("LLM ตอบกลับมาโดยไม่มีข้อความ")


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

        try:
            level = max(1, min(settings.max_level, int(row.get("level", 1))))
            confidence = float(row.get("confidence", 0.5))
        except (TypeError, ValueError):
            continue                       # ระดับหรือความมั่นใจไม่ใช่ตัวเลข → ทิ้งแถวนี้

        spans.append(ExtractedSpan(
            skill_id=skill_id,
            span_start=start, span_end=start + len(span_text), span_text=span_text,
            level=level, confidence=max(0.0, min(1.0, confidence)),
        ))

    # 🛡 ด่านสุดท้าย — ต่อให้ทุกอย่างข้างบนพลาด ข้อความที่ชี้ไม่ได้จะไม่รอดออกไป
    return enforce_span_guard(spans, raw_text)


class AnthropicExtractor:
    name = "anthropic"

    def __init__(self, client=None) -> None:
        """`client` มีไว้ให้เทสต์ยัดตัวปลอมเข้ามา — ใช้งานจริงปล่อยเป็น None"""
        self._client = client
        if client is None and not settings.anthropic_api_key:
            raise RuntimeError(
                "ตั้ง LLM_PROVIDER=anthropic แต่ไม่มี ANTHROPIC_API_KEY — "
                "ใส่ key หรือกลับไปใช้ LLM_PROVIDER=keyword"
            )

    def _skill_catalogue(self) -> str:
        return "\n".join(f'{s["id"]} = {s["name_th"]}' for s in SKILLS)

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import anthropic       # นำเข้าตรงนี้ ระบบจะได้รันได้แม้ยังไม่ได้ติดตั้งไลบรารี
        except ImportError as exc:
            raise ExtractorError(
                "ยังไม่ได้ติดตั้งไลบรารี anthropic — pip install -r backend/requirements.txt"
            ) from exc
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def extract(self, raw_text: str) -> list[ExtractedSpan]:
        message = self._get_client().messages.create(
            model=settings.llm_model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"รายการทักษะที่รู้จัก:\n{self._skill_catalogue()}\n\n"
                    f"เอกสารของผู้ใช้:\n<document>\n{raw_text}\n</document>"
                ),
            }],
        )
        return parse_payload(
            _first_text_block(message), raw_text, {s["id"] for s in SKILLS}
        )
