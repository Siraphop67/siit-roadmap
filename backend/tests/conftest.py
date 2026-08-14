"""ค่าตั้งกลางของเทสต์ทั้งชุด

🔴 ทำไมต้องบังคับตัวสกัดเป็น keyword
   `settings` อ่านจาก `backend/.env` ตอน import · ใครที่ตั้ง `LLM_PROVIDER=local`
   ไว้ทดสอบบนเครื่องตัวเอง จะทำให้เทสต์ที่แตะเส้นทางส่งผลงานวิ่งไปเรียก LLM จริง
   ผลคือ ~78 วินาทีต่อเทสต์หนึ่งข้อ และผลลัพธ์เปลี่ยนไปตามรุ่นของโมเดล
   — เทสต์ต้องกำหนดผลได้และเร็ว ไม่ใช่ขึ้นกับว่าเครื่องใครตั้งอะไรไว้

   เทสต์ที่ *ตั้งใจ* ทดสอบ provider อื่น ให้ monkeypatch ในไฟล์ของตัวเอง
   (ดู `test_llm_anthropic.py` และ `test_meta_reports_the_real_extractor`)
"""

from __future__ import annotations

import pytest

from app.config import settings


@pytest.fixture(autouse=True, scope="session")
def _pin_extractor_to_keyword() -> None:
    settings.llm_provider = "keyword"
