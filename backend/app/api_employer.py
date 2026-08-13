"""HTTP API — ฝั่งบริษัทที่อยากลงประกาศรับสมัคร

  บริษัทส่งประกาศ    POST /employer/posting
  เช็คสถานะของตัวเอง  GET  /employer/posting/{id}
  คิวรออนุมัติ        GET  /employer/review        (ต้องมี token)
  อนุมัติ / ไม่อนุมัติ  POST /employer/review/{id}   (ต้องมี token)

🔒 ทางเดียว — ไม่มี endpoint ไหนในไฟล์นี้คืนข้อมูลนักศึกษาให้ฝั่งบริษัท
   ไม่มีรายชื่อ ไม่มีโปรไฟล์ ไม่มี CV ไม่มีแม้แต่จำนวนคนที่ดูประกาศ
   บริษัทลงประกาศได้ นักศึกษาเห็นประกาศแล้วไปสมัครที่ url หรือ contact_email ของบริษัทเอง
   ถ้าวันหนึ่งจะให้บริษัทเห็นผู้สมัคร ต้องรื้อเรื่องความยินยอมทั้งหมดก่อน ไม่ใช่เพิ่ม endpoint

🔴 ทำไมต้องมีคิวรออนุมัติ ไม่ปล่อยขึ้นทันที
   ระบบนี้ไม่มีการยืนยันตัวตนองค์กรเลย ใครก็พิมพ์ว่าตัวเองเป็นบริษัทไหนก็ได้
   ฟอร์มเปิดโล่งที่ขึ้นจอทันที = ประกาศงานปลอมที่เล็งนักศึกษา ซึ่งเป็นช่องทางหลอกลวงที่มีจริง
   คนที่กดอนุมัติคือด่านเดียวที่มี — และมันคือด่านเดียวกับที่ D11 บอกว่าต้องมีคนอยู่ในวงจร

⚠️ token ของหน้ารีวิวเป็นของชั่วคราว
   เทียบกับค่าใน env ตัวเดียว ไม่ใช่ระบบบัญชี · พอเพียงสำหรับต้นแบบที่มีคนอนุมัติคนเดียว
   ถ้าจะมีผู้ดูแลหลายคนหรือใช้จริงนอกทีม ต้องเปลี่ยนเป็นบัญชีจริงก่อน
"""

from __future__ import annotations

import os
import re
import secrets
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CareerTarget, JobPosting
from app.seed.careers import SECTORS
from app.seed.postings import EMPLOYMENT_TYPES, Posting, validate

router = APIRouter(prefix="/api/employer")

# ผู้ดูแลที่กดอนุมัติใช้ค่านี้ · ไม่ตั้ง = ปิดหน้ารีวิวทั้งหมด (ปลอดภัยกว่าเปิดทิ้งไว้)
ADMIN_TOKEN_ENV = "EMPLOYER_REVIEW_TOKEN"

EMAIL_RE = re.compile(r"\A[\w.+-]+@[\w-]+\.[\w.]+\Z")


def _slug(text: str, limit: int = 24) -> str:
    """ชิ้นส่วนของ id ที่อ่านออก — ASCII ล้วนโดยตั้งใจ

    🔴 id ตัวนี้ไปอยู่ใน URL path (`/employer/posting/{id}`) ถ้าปล่อยอักษรไทยติดไป
       จะต้อง percent-encode ทุกที่ที่ใช้ · curl ธรรมดา urllib และ log จะพังหรืออ่านไม่ออก
       ชื่อบริษัทเก็บไว้ในฟิลด์ org อยู่แล้ว id ไม่ต้องอ่านออกเป็นภาษาไทย

    ชื่อที่เป็นภาษาไทยล้วนจะเหลือสตริงว่าง — กรณีนั้นใช้ "org" แล้วให้ส่วนสุ่มท้าย id แยกความต่าง
    """
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:limit] or "org"


def _require_admin(x_review_token: str | None = Header(default=None)) -> None:
    """🔒 ไม่ตั้ง token ใน env = ไม่มีใครเข้าหน้ารีวิวได้ รวมถึงคนที่เดา token ว่าง"""
    expected = os.getenv(ADMIN_TOKEN_ENV, "")
    if not expected:
        raise HTTPException(
            503,
            f"หน้ารีวิวยังไม่เปิดใช้ — ตั้ง {ADMIN_TOKEN_ENV} ใน .env ของ backend ก่อน",
        )
    # เทียบเป็น bytes — ถ้ามีคนตั้ง token เป็นภาษาไทยใน .env การเทียบแบบ str จะโยน TypeError
    # แล้วกลายเป็น 500 แทนที่จะเป็น 401 · (header ส่งอักษรนอก ASCII ไม่ได้อยู่แล้ว
    #  token ภาษาไทยจึงใช้ไม่ได้จริง แต่ต้องตอบว่า "ไม่ถูกต้อง" ไม่ใช่ระบบพัง)
    given = (x_review_token or "").encode("utf-8")
    if not given or not secrets.compare_digest(given, expected.encode("utf-8")):
        raise HTTPException(401, "token ไม่ถูกต้อง")


# ═════════════════════ บริษัทส่งประกาศ ═════════════════════


class PostingSubmission(BaseModel):
    """ช่องเดียวกับ data/postings/_TEMPLATE.md — ประกาศจากสองทางจึงเทียบกันได้ตรง ๆ"""

    org: str = Field(min_length=2, max_length=200)
    title: str = Field(min_length=2, max_length=200)
    url: str
    sector: str
    employment_type: str
    raw_text: str = Field(min_length=1)

    target_id: str | None = None
    location: str | None = None
    salary_text: str | None = None
    posted_at: str | None = None
    closes_at: str | None = None
    requires_field: list[str] | None = None
    requires_gpa: float | None = Field(default=None, ge=0, le=4)
    requires_education: str | None = None
    note: str | None = None

    # ผู้กรอกยินยอมโดยการกรอกเอง — ต่างจากอีเมลที่ไปดึงมาจากที่อื่น
    contact_email: str | None = None
    submitted_by: str = Field(min_length=2, max_length=64)


@router.post("/posting")
def submit_posting(body: PostingSubmission, db: Session = Depends(get_db)) -> dict:
    """บริษัทส่งประกาศเข้าคิว — ยังไม่ขึ้นจอจนกว่าจะมีคนอนุมัติ

    ผ่านด่านตรวจชุดเดียวกับไฟล์ที่ทีมเก็บเอง ถ้าฝั่งนี้หลวมกว่า มันจะกลายเป็นประตูหลัง
    """
    target_ids = {t.id for t in db.scalars(select(CareerTarget)).all()}

    meta = body.model_dump(exclude={"raw_text", "contact_email", "submitted_by"})
    meta["collected_at"] = date.today().isoformat()
    meta["collected_by"] = body.submitted_by
    meta = {k: v for k, v in meta.items() if v is not None}

    p = Posting(id="", path=None, meta=meta, body=body.raw_text.strip())  # type: ignore[arg-type]
    validate(p, target_ids)

    if body.contact_email and not EMAIL_RE.match(body.contact_email):
        p.errors.append("`contact_email` ไม่ใช่รูปแบบอีเมล")

    if not p.ok:
        # ส่งกลับทุกข้อพร้อมกัน คนกรอกจะได้แก้รอบเดียว ไม่ใช่แก้ทีละข้อ
        raise HTTPException(422, {"errors": p.errors, "warnings": p.warnings})

    posting_id = f"emp-{date.today().isoformat()}-{_slug(body.org)}-{secrets.token_hex(3)}"
    db.add(JobPosting(
        id=posting_id,
        target_id=body.target_id,
        org=body.org.strip(),
        title=body.title.strip(),
        url=body.url,
        collected_at=meta["collected_at"],
        collected_by=body.submitted_by.strip(),
        raw_text=p.body,          # 🔒 ตามที่ส่งมา — span จะชี้กลับมาที่ค่านี้
        source="employer",
        status="pending",         # 🔒 ไม่มีทางลัดให้ขึ้นจอทันที
        contact_email=body.contact_email,
    ))
    db.commit()

    return {
        "posting_id": posting_id,
        "status": "pending",
        "warnings": p.warnings,
        "message": (
            "ได้รับประกาศแล้ว — จะยังไม่ขึ้นให้นักศึกษาเห็นจนกว่าทีมจะตรวจ "
            "เพราะเรายังไม่มีระบบยืนยันตัวตนองค์กร และไม่อยากให้ประกาศปลอมหลุดถึงนักศึกษา"
        ),
        "check_status_at": f"/api/employer/posting/{posting_id}",
    }


@router.get("/posting/{posting_id}")
def check_status(posting_id: str, db: Session = Depends(get_db)) -> dict:
    """บริษัทเช็คว่าประกาศของตัวเองผ่านหรือยัง — ใช้ id ที่ได้ตอนส่งเป็นกุญแจ"""
    p = db.get(JobPosting, posting_id)
    if not p or p.source != "employer":
        raise HTTPException(404, "ไม่พบประกาศนี้")
    return {
        "posting_id": p.id,
        "org": p.org,
        "title": p.title,
        "status": p.status,
        "submitted_at": p.submitted_at.isoformat(),
        "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
        "review_note": p.review_note,
        "status_th": {
            "pending": "รอทีมตรวจ",
            "approved": "ผ่านแล้ว — นักศึกษาเห็นประกาศนี้ได้",
            "rejected": "ไม่ผ่าน",
        }.get(p.status, p.status),
    }


# ═════════════════════ คิวรออนุมัติ ═════════════════════


@router.get("/review", dependencies=[Depends(_require_admin)])
def review_queue(
    status: Literal["pending", "approved", "rejected"] = "pending",
    db: Session = Depends(get_db),
) -> dict:
    rows = db.scalars(
        select(JobPosting)
        .where(JobPosting.source == "employer", JobPosting.status == status)
        .order_by(JobPosting.submitted_at)
    ).all()
    return {
        "status": status,
        "count": len(rows),
        "postings": [
            {
                "posting_id": p.id,
                "org": p.org,
                "title": p.title,
                "url": p.url,
                "target_id": p.target_id,
                "submitted_by": p.collected_by,
                "submitted_at": p.submitted_at.isoformat(),
                "contact_email": p.contact_email,
                "raw_text": p.raw_text,      # คนตรวจต้องอ่านของจริง ไม่ใช่อ่านสรุป
                "char_count": len(p.raw_text),
            }
            for p in rows
        ],
        "checklist": [
            "องค์กรนี้มีอยู่จริงไหม — ค้นชื่อดู",
            "url เปิดแล้วเจอประกาศเดียวกันไหม",
            "มีการขอเงิน ขอบัตรประชาชน หรือขอโอนค่ามัดจำไหม — เจอแล้วปฏิเสธทันที",
            "ข้อความอ่านแล้วเป็นประกาศงานจริง ไม่ใช่โฆษณาหรือสแปม",
        ],
    }


class ReviewDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str | None = None


@router.post("/review/{posting_id}", dependencies=[Depends(_require_admin)])
def review(posting_id: str, body: ReviewDecision, db: Session = Depends(get_db)) -> dict:
    p = db.get(JobPosting, posting_id)
    if not p or p.source != "employer":
        raise HTTPException(404, "ไม่พบประกาศนี้")

    p.status = body.decision
    p.review_note = body.note
    p.reviewed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "posting_id": p.id,
        "status": p.status,
        "next_step": (
            "รัน make postings แล้ว make backend อีกครั้ง ประกาศนี้ถึงจะมีผลกับ requirement"
            if p.status == "approved" else ""
        ),
    }


# ═════════════════════ META สำหรับหน้าฟอร์ม ═════════════════════


@router.get("/meta")
def employer_meta(db: Session = Depends(get_db)) -> dict:
    """ตัวเลือกที่หน้าฟอร์มต้องใช้ — ดึงจากที่เดียวกับที่ระบบตรวจ จะได้ไม่หลุดจากกัน"""
    return {
        "sectors": SECTORS,
        "employment_types": EMPLOYMENT_TYPES,
        "targets": [
            {"id": t.id, "title_th": t.title_th}
            for t in db.scalars(select(CareerTarget).order_by(CareerTarget.id)).all()
        ],
        "notes": {
            "review": "ประกาศทุกอันต้องผ่านการตรวจจากทีมก่อนขึ้นให้นักศึกษาเห็น",
            "privacy": (
                "ระบบนี้เป็นทางเดียว — บริษัทลงประกาศได้ แต่ไม่เห็นข้อมูลนักศึกษา "
                "นักศึกษาที่สนใจจะติดต่อไปตามลิงก์หรืออีเมลที่ให้ไว้เอง"
            ),
            "raw_text": (
                "วางข้อความประกาศตามต้นฉบับ ห้ามใส่อีเมลหรือเบอร์โทรในตัวข้อความ "
                "— ใส่ในช่องติดต่อแยกแทน"
            ),
        },
    }
