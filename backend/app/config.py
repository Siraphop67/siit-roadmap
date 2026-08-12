"""ค่าตั้งของระบบ

DATABASE_URL — ไม่ตั้ง = SQLite ในไฟล์ (รันได้ทันที) · ตั้ง postgresql+psycopg://... = Postgres
LLM_PROVIDER — mock (ค่าเริ่มต้น) | anthropic
               🔴 ยังไม่มี API key จึงใช้ mock · สลับได้โดยไม่แตะ logic ที่ไหน
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'siit_roadmap.db'}")
    cors_origins: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")

    # ── ตัวสกัดทักษะจาก CV ──
    # keyword   = สกัดด้วยคำสำคัญ กำหนดผลได้ ไม่ต้องมี key (ค่าเริ่มต้น)
    # anthropic = เรียก LLM จริง ต้องมี ANTHROPIC_API_KEY
    llm_provider: str = os.getenv("LLM_PROVIDER", "keyword")
    anthropic_api_key: str | None = os.getenv("ANTHROPIC_API_KEY")
    llm_model: str = os.getenv("LLM_MODEL", "claude-sonnet-5")

    # ── ที่อยู่ของข้อมูลที่ท่อสร้างไว้ ──
    pipeline_out: Path = REPO_DIR / "pipeline" / "out"

    # ── น้ำหนักการจัดลำดับก้าวใน roadmap (4.4 RANK) ──
    rank_w_unlock: float = 3.0        # ก้าวนี้ปลดล็อกก้าวอื่นกี่ก้าว
    rank_w_importance: float = 2.5    # ปลายทางให้ความสำคัญแค่ไหน
    rank_w_frequency: float = 1.5     # ปรากฏในประกาศงานบ่อยแค่ไหน
    rank_w_hours_fit: float = 0.05    # พอดีกับเวลาที่มีไหม
    rank_w_no_resource: float = 4.0   # ไม่มีทางไปถึงเลย → ดันลงล่าง

    # ── ระดับทักษะ ──
    max_level: int = 3  # 1 รู้จัก · 2 ทำได้เมื่อมีคนแนะ · 3 ทำเองได้

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgres")

    @property
    def llm_is_real(self) -> bool:
        """มี LLM จริงอยู่เบื้องหลังไหม — ใช้รายงานตามตรงบนหน้าจอและใน /health

        keyword กับ mock ไม่ใช่ LLM ทั้งคู่ · ห้ามรายงานว่าเป็น
        """
        return self.llm_provider.lower() not in {"mock", "keyword"}


settings = Settings()
