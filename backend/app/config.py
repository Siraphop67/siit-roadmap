"""ค่าตั้งของระบบ

DATABASE_URL — ไม่ตั้ง = SQLite ในไฟล์ (รันได้ทันที) · ตั้ง postgresql+psycopg://... = Postgres
LLM_PROVIDER — keyword (ค่าเริ่มต้น) | local | anthropic
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

    # ── Gemini / Google AI Studio (LLM_PROVIDER=gemini) ──
    # ชั้นฟรีใช้ได้จริง ขอ key ที่ https://aistudio.google.com/apikey
    # 🔴 ชั้นฟรีระบุว่านำข้อมูลไปพัฒนาผลิตภัณฑ์ของ Google — อ่านหมายเหตุใน llm/google.py
    #    ก่อนเอาไปใช้กับ CV ของผู้ใช้จริง
    # SDK อ่านได้ทั้งสองชื่อ เรารับทั้งคู่จะได้ไม่ต้องมานั่งงงว่าตั้งตัวไหน
    google_api_key: str | None = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    # 🔴 เลือกจาก "ให้ผลเดิมทุกครั้ง" ไม่ใช่ "เจอเยอะที่สุด" — เหตุผลเต็มใน DECISIONS D17
    #    3.6-flash กับ 3.5-flash-lite ให้ผลไม่ซ้ำเดิมในการรัน 3 ครั้ง ทั้งที่ temperature=0
    #    (ส่วนคิดของรุ่นใหม่ไม่นิ่ง) · วัดก่อน-หลังไม่ได้ถ้าตัวสกัดตอบไม่เหมือนเดิม
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    # งบส่วนคิด · ติดลบ = ไม่ส่งไปเลย ให้โมเดลตัดสินใจเอง ← ค่าเริ่มต้น
    # 🔴 ห้ามตั้งเป็น 0 เป็นค่าเริ่มต้น — วัดแล้วว่า gemini-3.6-flash กับ 3.5-flash-lite
    #    ตอบ 400 INVALID_ARGUMENT ทันทีที่ส่ง thinking_budget=0 ไป (รุ่นใหม่ไม่ให้ปิด)
    #    ตั้งเป็นตัวเลข >= 0 ได้ถ้ารุ่นที่ใช้รองรับ
    gemini_thinking_budget: int = int(os.getenv("GEMINI_THINKING_BUDGET", "-1"))

    # ── LLM ที่รันบนเครื่องตัวเอง (LLM_PROVIDER=local) ──
    # คุยผ่าน OpenAI-compatible chat completions — Ollama · LM Studio · llama.cpp · vLLM
    local_llm_base_url: str = os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1")
    # 🔴 gemma4:26b เพราะวัดแล้วว่าไม่ตีความเกินหลักฐาน — 12 ทักษะจาก 12 ประโยคคนละประโยค
    #    qwen2.5:14b ได้ 19 ทักษะจาก 10 ประโยค (1.9 ต่อประโยค) = เอาประโยคเดียวไปอ้างซ้ำ
    #    เวลาเท่ากันทั้งคู่ (~78 วินาที) · ผลวัดเต็มอยู่ใน docs/DECISIONS.md D13
    local_llm_model: str = os.getenv("LOCAL_LLM_MODEL", "gemma4:26b")
    # เซิร์ฟเวอร์บางตัวไม่รองรับ JSON mode แล้วจะปฏิเสธทั้งคำขอ — ปิดได้ด้วย =0
    local_llm_json_mode: bool = os.getenv("LOCAL_LLM_JSON_MODE", "1") not in {"0", "false", ""}

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
    def llm_model_in_use(self) -> str:
        """ชื่อรุ่นที่ใช้อยู่จริงตาม provider — /meta เอาไปบอกผู้ใช้ว่ากำลังอ่านด้วยอะไร"""
        if self.llm_provider.lower() == "local":
            return self.local_llm_model
        if self.llm_provider.lower() == "anthropic":
            return self.llm_model
        if self.llm_provider.lower() in {"gemini", "google"}:
            return self.gemini_model
        return self.llm_provider

    @property
    def llm_is_real(self) -> bool:
        """มี LLM จริงอยู่เบื้องหลังไหม — ใช้รายงานตามตรงบนหน้าจอและใน /health

        keyword กับ mock ไม่ใช่ LLM ทั้งคู่ · ห้ามรายงานว่าเป็น
        """
        return self.llm_provider.lower() not in {"mock", "keyword"}


settings = Settings()
