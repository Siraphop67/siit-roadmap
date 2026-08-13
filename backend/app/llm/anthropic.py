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

from app.config import settings
from app.llm.base import (
    MAX_TOKENS,
    SYSTEM_PROMPT,
    ExtractedSpan,
    ExtractorError,
    parse_payload,
)
from app.seed.skills import SKILLS

def _first_text_block(message) -> str:
    """ดึงข้อความจากคำตอบ — content เป็นลิสต์ของ block ที่อาจไม่ใช่ text ทั้งหมด"""
    for block in getattr(message, "content", []) or []:
        text = getattr(block, "text", None)
        if isinstance(text, str) and text.strip():
            return text
    raise ExtractorError("LLM ตอบกลับมาโดยไม่มีข้อความ")


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
