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

from dataclasses import dataclass
from typing import Protocol


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
