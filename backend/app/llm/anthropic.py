"""ตัวสกัดด้วย LLM จริง — ใช้เมื่อมี ANTHROPIC_API_KEY

🔴 ยังไม่ได้ทดสอบกับ API จริง เพราะยังไม่มี key
   โครงเขียนไว้ให้สลับได้ทันทีที่ได้ key มา โดยไม่ต้องแก้ที่อื่นเลย
   ตั้ง LLM_PROVIDER=anthropic แล้วใส่ ANTHROPIC_API_KEY

สิ่งที่ตัวนี้ทำได้ดีกว่าตัวสกัดด้วยคำสำคัญ:
   · เข้าใจการบรรยายที่ไม่ได้ใช้คำตรง — "ทำให้สองระบบคุยกันได้" → SW-API
   · แยกได้ว่า "อยากเรียน Python" ต่างจาก "ใช้ Python ทำโปรเจกต์จริง"
   · ประเมินระดับจากบริบทแทนที่จะนับจำนวนครั้ง

🛡 ที่เหมือนกันทั้งสองตัว: span guard
   LLM ต้องคัดลอกข้อความจาก CV มาตรงตัว ถ้าแต่งขึ้นเอง เราทิ้ง
   ห้ามผ่อนข้อนี้ให้ LLM ไม่ว่ากรณีใด
"""

from __future__ import annotations

import json

from app.config import settings
from app.llm.base import ExtractedSpan, enforce_span_guard
from app.seed.skills import SKILLS

SYSTEM_PROMPT = """คุณคือตัวสกัดหลักฐานความสามารถจากเรซูเม่ของนักศึกษาวิศวกรรม

หน้าที่: อ่านเอกสาร แล้วบอกว่ามีหลักฐานของทักษะใดในรายการบ้าง

กติกาที่ห้ามละเมิด:
1. span_text ต้องคัดลอกจากเอกสารต้นฉบับแบบ "ตรงตัวอักษรต่ออักษร" ห้ามเรียบเรียงใหม่
2. ถ้าไม่มีข้อความในเอกสารที่รองรับทักษะนั้น ห้ามใส่ทักษะนั้นลงไป
3. ระดับ: 1 = เอ่ยถึงหรือเคยเรียน · 2 = เคยใช้ในงานหรือโครงงาน · 3 = ใช้เป็นหลักและมีผลลัพธ์
4. ห้ามเดาจากสาขาที่เรียน ให้ดูจากสิ่งที่เขียนไว้ในเอกสารเท่านั้น

ตอบเป็น JSON เท่านั้น: {"skills":[{"skill_id","span_text","level","confidence"}]}"""


class AnthropicExtractor:
    name = "anthropic"

    def __init__(self) -> None:
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ตั้ง LLM_PROVIDER=anthropic แต่ไม่มี ANTHROPIC_API_KEY — "
                "ใส่ key หรือกลับไปใช้ LLM_PROVIDER=keyword"
            )

    def _skill_catalogue(self) -> str:
        return "\n".join(f'{s["id"]} = {s["name_th"]}' for s in SKILLS)

    def extract(self, raw_text: str) -> list[ExtractedSpan]:
        import anthropic  # นำเข้าตรงนี้เพื่อให้ระบบรันได้แม้ยังไม่ได้ติดตั้งไลบรารี

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model=settings.llm_model,
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"รายการทักษะที่รู้จัก:\n{self._skill_catalogue()}\n\n"
                    f"เอกสารของผู้ใช้:\n<document>\n{raw_text}\n</document>"
                ),
            }],
        )
        payload = json.loads(message.content[0].text)

        spans: list[ExtractedSpan] = []
        for row in payload.get("skills", []):
            text = row.get("span_text", "")
            start = raw_text.find(text)       # LLM ไม่ต้องนับตำแหน่งเอง เราหาให้
            if start < 0:
                continue                      # แต่งข้อความขึ้นมา → ทิ้ง
            spans.append(ExtractedSpan(
                skill_id=row["skill_id"],
                span_start=start, span_end=start + len(text), span_text=text,
                level=max(1, min(3, int(row.get("level", 1)))),
                confidence=float(row.get("confidence", 0.5)),
            ))

        known = {s["id"] for s in SKILLS}
        spans = [s for s in spans if s.skill_id in known]
        return enforce_span_guard(spans, raw_text)
