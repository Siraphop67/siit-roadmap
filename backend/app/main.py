"""เว็บ Roadmap สำหรับนักศึกษา SIIT

รัน:  uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.api_discover import router as discover_router
from app.api_employer import router as employer_router
from app.config import settings
from app.db import SessionLocal, engine
from app.seed.loader import check_pipeline, create_all, seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    warning = check_pipeline()
    if warning:
        print(f"[seed] ⚠️  {warning}")
    create_all(engine)
    with SessionLocal() as db:
        counts = seed(db)
    print(f"[seed] {counts}")
    print(f"[db]   {'postgres' if settings.is_postgres else 'sqlite'}")
    print(f"[llm]  {settings.llm_provider}"
          + ("" if settings.llm_is_real else "  (สกัดด้วยคำสำคัญ ไม่ใช่ LLM)"))
    yield


app = FastAPI(
    title="SIIT Roadmap",
    description=(
        "เว็บหางานบอกว่ามีงานอะไร — ของเราบอกว่าจะไปถึงงานนั้นได้ยังไง "
        "โดยอ่านจาก CV ของผู้ใช้เอง ไม่ใช่เชื่อสิ่งที่กรอกมาอย่างเดียว"
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(discover_router)
app.include_router(employer_router)


@app.get("/")
def root() -> dict:
    return {"name": "SIIT Roadmap", "docs": "/docs", "version": "0.2.0"}
