"""HTTP API — ฝั่ง "รู้แล้วว่าอยากไปไหน"

ลำดับที่ผู้ใช้เดิน:
  หน้าแรก          POST /session
  คลังอาชีพ        GET  /targets · GET /targets/{id}
  โปรไฟล์          POST /profile
  ส่งผลงาน         POST /portfolio/{text|github|linkedin|upload}
  ตรวจผลสกัด       GET  /portfolio/{id} · POST /portfolio/{id}/confirm
  เลือกเป้าหมาย     POST /goal
  ★ ROADMAP ★     GET  /roadmap
  ข้อมูลของฉัน      GET  /me · DELETE /me
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.engine.eligibility import ProfileInput, TargetInput, filter_targets
from app.engine.roadmap import (
    Requirement,
    Resource,
    build_roadmap,
    merge_evidence,
)
from app.engine.skill_graph import SkillGraph
from app.ingest import IngestError, from_github, from_linkedin, from_pdf, from_text
from app.llm import get_extractor
from app.models import (
    ActivityResponse,
    CareerTarget,
    Consent,
    ExtractedSkill,
    InterestResponse,
    LearnerProfile,
    LearningResource,
    PersonalityResult,
    ResourceSkill,
    Roadmap,
    RoadmapStep,
    SelfReportedSkill,
    Skill,
    SkillEdge,
    StepOption,
    TargetMatch,
    TargetRequirement,
    User,
    UserDocument,
    UserGoal,
)
from app.seed.careers import EDUCATION_LEVELS, FIELDS, OBLIGATIONS, SECTORS, obligation_by_id
from app.seed.skills import ORDER_FLEXIBLE

router = APIRouter(prefix="/api")

RESOURCE_KIND_TH = {
    "siit_course": "วิชาในหลักสูตร",
    "online_course": "คอร์สออนไลน์",
    "certificate": "ใบรับรอง",
    "project": "โปรเจกต์",
    "activity": "กิจกรรม",
    "internship": "ฝึกงาน",
    "competition": "การแข่งขัน",
}


# ═════════════════════ ตัวช่วย ═════════════════════


def _user(db: Session, user_id: str) -> User:
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "ไม่พบผู้ใช้ — เริ่มใหม่ที่หน้าแรก")
    return u


def _graph(db: Session) -> SkillGraph:
    ids = [s.id for s in db.scalars(select(Skill)).all()]
    edges = [(e.from_id, e.to_id) for e in db.scalars(select(SkillEdge)).all()]
    return SkillGraph(ids, edges)


def _skill_names(db: Session) -> dict[str, str]:
    return {s.id: s.display_name for s in db.scalars(select(Skill)).all()}


def _resources(db: Session) -> dict[str, list[Resource]]:
    out: dict[str, list[Resource]] = {}
    rows = db.execute(
        select(ResourceSkill, LearningResource)
        .join(LearningResource, LearningResource.id == ResourceSkill.resource_id)
    ).all()
    for link, res in rows:
        out.setdefault(link.skill_id, []).append(Resource(
            id=res.id, kind=res.kind, title=res.title, provider=res.provider,
            est_hours=res.est_hours, cost_baht=res.cost_baht, min_year=res.min_year,
            proof_of_done=res.proof_of_done, reaches_level=link.reaches_level,
        ))
    return out


def _requirements(db: Session, target_id: str) -> list[Requirement]:
    rows = db.scalars(
        select(TargetRequirement).where(TargetRequirement.target_id == target_id)).all()
    return [Requirement(r.skill_id, r.min_level, r.importance, r.appears_in_n_postings)
            for r in rows]


def _confirmed_skills(db: Session, user_id: str) -> dict[str, int]:
    """เฉพาะที่ผู้ใช้ยืนยันแล้วเท่านั้นถึงนับเป็นหลักฐาน"""
    out: dict[str, int] = {}
    for e in db.scalars(select(ExtractedSkill).where(
            ExtractedSkill.user_id == user_id,
            ExtractedSkill.user_status.in_(("confirmed", "edited")))).all():
        out[e.skill_id] = max(out.get(e.skill_id, 0), e.level)
    return out


def _self_reported(db: Session, user_id: str) -> dict[str, int]:
    return {s.skill_id: s.level for s in db.scalars(
        select(SelfReportedSkill).where(SelfReportedSkill.user_id == user_id)).all()}


def _profile_input(db: Session, user_id: str) -> tuple[ProfileInput, LearnerProfile | None]:
    p = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    if not p:
        return ProfileInput(), None
    ob = p.obligation_json or {}
    return ProfileInput(
        field_code=p.field, education_level=p.education_level, gpa=p.gpa,
        obligation_allowed_sectors=ob.get("allowed_sectors"),
        obligation_label=ob.get("label"), hours_per_week=p.hours_per_week,
    ), p


def _target_input(t: CareerTarget) -> TargetInput:
    return TargetInput(
        id=t.id, org=t.title_th, role_title=t.title_en, sector=t.sector,
        field_whitelist=t.field_whitelist, min_education=t.min_education, min_gpa=t.min_gpa)


# ═════════════════════ META ═════════════════════


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    return {
        "ok": True,
        "database": "postgres" if settings.is_postgres else "sqlite",
        "extractor": settings.llm_provider,
        "extractor_is_real_llm": settings.llm_is_real,
        "skills": db.query(Skill).count(),
        "skill_edges": db.query(SkillEdge).count(),
        "career_targets": db.query(CareerTarget).count(),
        "learning_resources": db.query(LearningResource).count(),
    }


@router.get("/meta")
def meta() -> dict:
    return {
        "fields": FIELDS,
        "education_levels": EDUCATION_LEVELS,
        "obligations": OBLIGATIONS,
        "sectors": SECTORS,
        "resource_kinds": RESOURCE_KIND_TH,
        "extractor": settings.llm_provider,
        "notes": {
            "data": "อาชีพและ requirement ยังไม่ได้มาจากประกาศงานจริง · วิชาในหลักสูตรยังเป็นชื่อทั่วไป",
            "extractor": (
                "ตัวสกัด CV ตอนนี้ใช้การจับคำสำคัญ ไม่ใช่ LLM — "
                "จับได้เฉพาะคำที่เขียนตรงตัว"
            ),
        },
    }


# ═════════════════════ หน้าแรก ═════════════════════


class SessionRequest(BaseModel):
    entry: Literal["known", "unsure"] = "known"


@router.post("/session")
def create_session(body: SessionRequest, db: Session = Depends(get_db)) -> dict:
    u = User(entry=body.entry)
    db.add(u)
    db.commit()
    return {"user_id": u.id, "entry": u.entry}


# ═════════════════════ คลังอาชีพ ═════════════════════


@router.get("/targets")
def list_targets(user_id: str | None = None, db: Session = Depends(get_db)) -> dict:
    """อาชีพทั้งหมด — ที่กรองออกถาวรแยกไว้พร้อมเหตุผล ไม่หายไปเงียบ ๆ"""
    targets = db.scalars(select(CareerTarget)).all()
    by_id = {t.id: t for t in targets}
    profile = _profile_input(db, user_id)[0] if user_id else ProfileInput()
    kept, removed = filter_targets(profile, [_target_input(t) for t in targets])

    def card(t: CareerTarget, verdict) -> dict:
        return {
            "id": t.id, "title_th": t.title_th, "title_en": t.title_en,
            "summary": t.summary, "sector": t.sector,
            "sector_label": SECTORS.get(t.sector, t.sector),
            "field_whitelist": t.field_whitelist,
            "requirement_count": db.query(TargetRequirement).filter(
                TargetRequirement.target_id == t.id).count(),
            "posting_count": t.posting_count,
            "data_status": t.data_status,
            "conditions_at_application": [
                {"kind": b.kind, "message": b.message} for b in verdict.time_blocks],
        }

    return {
        "targets": [card(by_id[v.target_id], v) for v in kept],
        "filtered_out": [
            {
                "id": v.target_id,
                "title_th": by_id[v.target_id].title_th,
                "reasons": [{"kind": b.kind, "message": b.message} for b in v.permanent_blocks],
            }
            for v in removed
        ],
        "data_note": "requirement ยังไม่ได้มาจากประกาศงานจริง — จำนวนประกาศจึงเป็น 0 ทุกอาชีพ",
    }


@router.get("/targets/{target_id}")
def target_detail(target_id: str, db: Session = Depends(get_db)) -> dict:
    t = db.get(CareerTarget, target_id)
    if not t:
        raise HTTPException(404, "ไม่พบอาชีพนี้")
    names = _skill_names(db)
    reqs = db.scalars(
        select(TargetRequirement).where(TargetRequirement.target_id == target_id)
        .order_by(TargetRequirement.importance.desc())).all()
    return {
        "id": t.id, "title_th": t.title_th, "title_en": t.title_en,
        "summary": t.summary, "day_in_the_life": t.day_in_the_life,
        "sector_label": SECTORS.get(t.sector, t.sector),
        "field_whitelist": t.field_whitelist,
        "min_education": t.min_education, "min_gpa": t.min_gpa,
        "salary_note": t.salary_note, "data_status": t.data_status,
        "onet_soc_code": t.onet_soc_code,
        "requirements": [
            {
                "skill_id": r.skill_id, "name_th": names.get(r.skill_id, r.skill_id),
                "min_level": r.min_level, "importance": r.importance,
                "appears_in_n_postings": r.appears_in_n_postings,
            }
            for r in reqs
        ],
    }


# ═════════════════════ โปรไฟล์ ═════════════════════


class ProfileRequest(BaseModel):
    user_id: str
    field: str | None = None
    education_level: str | None = None
    year: int | None = Field(default=None, ge=1, le=8)
    gpa: float | None = Field(default=None, ge=0, le=4)
    hours_per_week: int | None = Field(default=None, ge=1, le=80)
    budget_baht: int | None = Field(default=None, ge=0)
    obligation_id: str | None = None
    self_reported_skills: dict[str, int] | None = None


@router.post("/profile")
def save_profile(body: ProfileRequest, db: Session = Depends(get_db)) -> dict:
    _user(db, body.user_id)
    ob = obligation_by_id(body.obligation_id)
    p = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == body.user_id))
    if not p:
        p = LearnerProfile(user_id=body.user_id)
        db.add(p)

    p.field = body.field
    p.education_level = body.education_level
    p.year = body.year
    p.gpa = body.gpa
    p.hours_per_week = body.hours_per_week
    p.budget_baht = body.budget_baht
    p.obligation_json = (
        {"id": ob["id"], "label": ob["label"], "allowed_sectors": ob["allowed_sectors"]}
        if ob and ob["allowed_sectors"] is not None else None
    )

    if body.self_reported_skills is not None:
        known = {s.id for s in db.scalars(select(Skill)).all()}
        db.query(SelfReportedSkill).filter(
            SelfReportedSkill.user_id == body.user_id).delete()
        for skill_id, level in body.self_reported_skills.items():
            if skill_id in known and 1 <= level <= settings.max_level:
                db.add(SelfReportedSkill(
                    user_id=body.user_id, skill_id=skill_id, level=level))

    db.commit()
    return {"saved": True}


@router.get("/profile")
def get_profile(user_id: str, db: Session = Depends(get_db)) -> dict:
    p = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    if not p:
        return {"exists": False, "self_reported_skills": {}}
    return {
        "exists": True, "field": p.field, "education_level": p.education_level,
        "year": p.year, "gpa": p.gpa, "hours_per_week": p.hours_per_week,
        "budget_baht": p.budget_baht,
        "obligation_id": (p.obligation_json or {}).get("id"),
        "self_reported_skills": _self_reported(db, user_id),
    }


# ═════════════════════ ส่งผลงาน + สกัด ═════════════════════


def _store_document(db: Session, user_id: str, result, consented: bool) -> dict:
    if not consented:
        raise HTTPException(
            400,
            "ต้องยินยอมให้เก็บและวิเคราะห์เอกสารก่อน — เอกสารนี้เป็นข้อมูลส่วนบุคคล")

    db.merge(Consent(
        id=f"{user_id}:store_document", user_id=user_id, purpose="store_document",
        granted=True, granted_at=datetime.now(timezone.utc)))

    doc = UserDocument(
        user_id=user_id, kind=result.kind, source_ref=result.source_ref,
        raw_text=result.raw_text, char_count=result.char_count)
    db.add(doc)
    db.flush()

    extractor = get_extractor()
    spans = extractor.extract(result.raw_text)
    known = {s.id for s in db.scalars(select(Skill)).all()}
    kept = 0
    for s in spans:
        if s.skill_id not in known:
            continue
        db.add(ExtractedSkill(
            document_id=doc.id, user_id=user_id, skill_id=s.skill_id,
            span_start=s.span_start, span_end=s.span_end, span_text=s.span_text,
            level=s.level, confidence=s.confidence, user_status="pending"))
        kept += 1

    doc.extracted_at = datetime.now(timezone.utc)
    doc.extractor = extractor.name
    db.commit()
    return {
        "document_id": doc.id, "kind": doc.kind, "char_count": doc.char_count,
        "extracted_count": kept, "extractor": extractor.name,
        "note": getattr(result, "note", ""),
    }


class TextPortfolio(BaseModel):
    user_id: str
    text: str
    consent: bool = False


class LinkPortfolio(BaseModel):
    user_id: str
    url: str
    text: str | None = None
    consent: bool = False


@router.post("/portfolio/text")
def portfolio_text(body: TextPortfolio, db: Session = Depends(get_db)) -> dict:
    _user(db, body.user_id)
    try:
        return _store_document(db, body.user_id, from_text(body.text), body.consent)
    except IngestError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/portfolio/github")
def portfolio_github(body: LinkPortfolio, db: Session = Depends(get_db)) -> dict:
    _user(db, body.user_id)
    try:
        return _store_document(db, body.user_id, from_github(body.url), body.consent)
    except IngestError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/portfolio/linkedin")
def portfolio_linkedin(body: LinkPortfolio, db: Session = Depends(get_db)) -> dict:
    _user(db, body.user_id)
    try:
        return _store_document(
            db, body.user_id, from_linkedin(body.text or "", body.url), body.consent)
    except IngestError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/portfolio/upload")
async def portfolio_upload(
    user_id: str, consent: bool = False, file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    _user(db, user_id)
    data = await file.read()
    try:
        return _store_document(
            db, user_id, from_pdf(data, file.filename or "cv.pdf"), consent)
    except IngestError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/portfolio/{document_id}")
def review_document(document_id: str, db: Session = Depends(get_db)) -> dict:
    """ผลสกัดพร้อมตำแหน่งใน CV — หน้าจอเอาไปไฮไลต์ได้ตรง ๆ"""
    doc = db.get(UserDocument, document_id)
    if not doc:
        raise HTTPException(404, "ไม่พบเอกสารนี้")
    names = _skill_names(db)
    rows = db.scalars(
        select(ExtractedSkill).where(ExtractedSkill.document_id == document_id)
        .order_by(ExtractedSkill.confidence.desc())).all()
    return {
        "document_id": doc.id, "kind": doc.kind, "source_ref": doc.source_ref,
        "raw_text": doc.raw_text, "extractor": doc.extractor,
        "extracted": [
            {
                "id": e.id, "skill_id": e.skill_id,
                "name_th": names.get(e.skill_id, e.skill_id),
                "span_start": e.span_start, "span_end": e.span_end,
                "span_text": e.span_text, "level": e.level,
                "confidence": e.confidence, "user_status": e.user_status,
            }
            for e in rows
        ],
        "note": "ทุกข้อชี้กลับไปที่ข้อความจริงใน CV — ยืนยันหรือแก้ได้ก่อนถึงจะถูกนับ",
    }


class ConfirmRequest(BaseModel):
    user_id: str
    decisions: dict[str, str]           # extracted_skill_id → confirmed | rejected | edited
    levels: dict[str, int] | None = None


@router.post("/portfolio/{document_id}/confirm")
def confirm_extraction(
    document_id: str, body: ConfirmRequest, db: Session = Depends(get_db)) -> dict:
    _user(db, body.user_id)
    rows = {e.id: e for e in db.scalars(
        select(ExtractedSkill).where(ExtractedSkill.document_id == document_id)).all()}
    changed = 0
    for eid, decision in body.decisions.items():
        e = rows.get(eid)
        if not e or decision not in {"confirmed", "rejected", "edited"}:
            continue
        e.user_status = decision
        if body.levels and eid in body.levels:
            e.level = max(1, min(settings.max_level, body.levels[eid]))
        changed += 1
    db.commit()
    return {"updated": changed, "confirmed_skills": _confirmed_skills(db, body.user_id)}


# ═════════════════════ เป้าหมาย + ROADMAP ═════════════════════


class GoalRequest(BaseModel):
    user_id: str
    target_id: str


@router.post("/goal")
def set_goal(body: GoalRequest, db: Session = Depends(get_db)) -> dict:
    _user(db, body.user_id)
    if not db.get(CareerTarget, body.target_id):
        raise HTTPException(404, "ไม่พบอาชีพนี้")
    db.query(UserGoal).filter(UserGoal.user_id == body.user_id).update({"is_primary": False})
    existing = db.scalar(select(UserGoal).where(
        UserGoal.user_id == body.user_id, UserGoal.target_id == body.target_id))
    if existing:
        existing.is_primary = True
    else:
        db.add(UserGoal(user_id=body.user_id, target_id=body.target_id,
                        is_primary=True, source="self", traced_to_json=[]))
    db.commit()
    return {"target_id": body.target_id}


@router.get("/roadmap")
def get_roadmap(user_id: str, target_id: str | None = None,
                db: Session = Depends(get_db)) -> dict:
    """★ หน้าหลักของเว็บ

    ส่งทั้ง "ลำดับก้าว" และ "เส้นเชื่อม" ไปให้ เพื่อให้หน้าเว็บเลือกวาดเป็น
    รายการหรือกราฟก็ได้ — UI ยังไม่ตัดสินใจ
    """
    _user(db, user_id)
    if not target_id:
        goal = db.scalar(select(UserGoal).where(
            UserGoal.user_id == user_id, UserGoal.is_primary.is_(True)))
        if not goal:
            raise HTTPException(409, "ยังไม่ได้เลือกอาชีพเป้าหมาย")
        target_id = goal.target_id

    target = db.get(CareerTarget, target_id)
    if not target:
        raise HTTPException(404, "ไม่พบอาชีพนี้")

    profile_in, profile = _profile_input(db, user_id)
    extracted = _confirmed_skills(db, user_id)
    self_reported = _self_reported(db, user_id)
    have = merge_evidence(extracted, self_reported)
    names = _skill_names(db)

    rm = build_roadmap(
        graph=_graph(db), target_id=target_id, requirements=_requirements(db, target_id),
        have=have, resources=_resources(db), skill_names=names,
        flexible_skills=ORDER_FLEXIBLE,
        hours_per_week=profile.hours_per_week if profile else None,
        budget_baht=profile.budget_baht if profile else None,
        year=profile.year if profile else None,
    )

    _persist_roadmap(db, user_id, rm)

    return {
        "target": {
            "id": target.id, "title_th": target.title_th, "title_en": target.title_en,
            "summary": target.summary, "data_status": target.data_status,
        },
        "total_steps": rm.total_steps,
        "steps_done": rm.steps_done,
        "coverage": rm.coverage,
        "evidence_summary": {
            "from_cv": len(extracted),
            "self_reported": len(self_reported),
            "note": "ทักษะจาก CV มีหลักฐานชี้กลับไปได้ · ที่กรอกเองยังไม่มี",
        },
        "steps": [
            {
                "skill_id": s.skill_id, "name_th": names.get(s.skill_id, s.skill_id),
                "order_no": s.order_no, "status": s.status, "actionable": s.actionable,
                "current_level": s.current_level, "target_level": s.target_level,
                "evidence_kind": s.evidence_kind, "unlock_count": s.unlock_count,
                "options": [
                    {
                        "resource_id": o.resource.id, "kind": o.resource.kind,
                        "kind_label": RESOURCE_KIND_TH.get(o.resource.kind, o.resource.kind),
                        "title": o.resource.title, "provider": o.resource.provider,
                        "est_hours": o.resource.est_hours, "cost_baht": o.resource.cost_baht,
                        "min_year": o.resource.min_year,
                        "proof_of_done": o.resource.proof_of_done,
                        "generated": o.resource.generated,
                        "fits": o.fits_all, "blocked_reason": o.blocked_reason,
                    }
                    for o in s.options
                ],
            }
            for s in rm.steps
        ],
        "edges": [{"from": a, "to": b} for a, b in rm.edges],
        "legend": {
            "current": "ก้าวที่ลงมือได้ตอนนี้",
            "in_progress": "มีอยู่แล้วบางส่วน แต่ยังไม่ถึงระดับที่อาชีพนี้ต้องการ",
            "flexible": "ทำเมื่อไหร่ก็ได้ ไม่ต้องรอก้าวอื่น",
            "locked": "ยังกดไม่ได้ ต้องผ่านก้าวก่อนหน้า",
        },
    }


def _persist_roadmap(db: Session, user_id: str, rm) -> None:
    db.execute(delete(Roadmap).where(
        Roadmap.user_id == user_id, Roadmap.target_id == rm.target_id))
    row = Roadmap(user_id=user_id, target_id=rm.target_id, total_steps=rm.total_steps,
                  steps_done=rm.steps_done, coverage=rm.coverage)
    db.add(row)
    db.flush()
    for s in rm.steps:
        step = RoadmapStep(
            roadmap_id=row.id, skill_id=s.skill_id, order_no=s.order_no,
            current_level=s.current_level, target_level=s.target_level,
            status=s.status, evidence_kind=s.evidence_kind, rank_score=s.rank_score)
        db.add(step)
        db.flush()
        for o in s.options:
            if o.resource.generated:
                continue     # โปรเจกต์ที่ระบบสร้างเองไม่มีแถวในคลัง จึงไม่บันทึกอ้างอิง
            db.add(StepOption(
                step_id=step.id, resource_id=o.resource.id,
                fits_time=o.fits_time, fits_budget=o.fits_budget, fits_year=o.fits_year,
                blocked_reason=o.blocked_reason))
    db.commit()


# ═════════════════════ ข้อมูลของฉัน + PDPA ═════════════════════


@router.get("/me")
def me(user_id: str, db: Session = Depends(get_db)) -> dict:
    _user(db, user_id)
    names = _skill_names(db)
    docs = db.scalars(select(UserDocument).where(UserDocument.user_id == user_id)).all()
    goals = db.scalars(select(UserGoal).where(UserGoal.user_id == user_id)).all()
    extracted = _confirmed_skills(db, user_id)
    return {
        "documents": [
            {"id": d.id, "kind": d.kind, "source_ref": d.source_ref,
             "char_count": d.char_count, "uploaded_at": d.uploaded_at.isoformat()}
            for d in docs
        ],
        "skills_from_cv": [
            {"skill_id": k, "name_th": names.get(k, k), "level": v} for k, v in extracted.items()],
        "skills_self_reported": [
            {"skill_id": k, "name_th": names.get(k, k), "level": v}
            for k, v in _self_reported(db, user_id).items()],
        "goals": [{"target_id": g.target_id, "is_primary": g.is_primary} for g in goals],
    }


@router.delete("/me")
def delete_everything(user_id: str, db: Session = Depends(get_db)) -> dict:
    """ลบข้อมูลของผู้ใช้ทั้งหมดจริง ๆ — สิทธิ์ตาม PDPA

    ลบทุกตารางที่ผูกกับผู้ใช้ รวม CV ที่อัปโหลดและข้อความที่สกัดออกมาแล้ว
    """
    _user(db, user_id)
    counts: dict[str, int] = {}
    for model in (ExtractedSkill, UserDocument, SelfReportedSkill, ActivityResponse,
                  InterestResponse, PersonalityResult, TargetMatch, UserGoal,
                  LearnerProfile, Consent):
        result = db.execute(delete(model).where(model.user_id == user_id))
        counts[model.__tablename__] = result.rowcount or 0

    for rm in db.scalars(select(Roadmap).where(Roadmap.user_id == user_id)).all():
        for step in db.scalars(select(RoadmapStep).where(
                RoadmapStep.roadmap_id == rm.id)).all():
            db.execute(delete(StepOption).where(StepOption.step_id == step.id))
        db.execute(delete(RoadmapStep).where(RoadmapStep.roadmap_id == rm.id))
    counts["roadmap"] = db.execute(
        delete(Roadmap).where(Roadmap.user_id == user_id)).rowcount or 0

    db.execute(delete(User).where(User.id == user_id))
    db.commit()
    return {"deleted": True, "rows": counts}
