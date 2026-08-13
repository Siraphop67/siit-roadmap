"""HTTP API — กราฟทักษะทั้งใบ (หน้า Skill Graph)

  กราฟทั้งใบ      GET  /api/skills          ← 73 ทักษะ · 105 เส้น prerequisite
  ทักษะรายตัว     GET  /api/skills/{id}     ← ใครใช้ทักษะนี้ · เรียนจากไหนได้ · ปลดล็อกอะไรต่อ

ต่างจาก `GET /api/roadmap` ตรงที่ roadmap ส่ง *subgraph ของอาชีพเดียว* พร้อมลำดับก้าว
ส่วนที่นี่ส่งกราฟทั้งใบให้เดินดูก่อนเลือกอาชีพ — คนที่ยังไม่รู้ว่าอยากเป็นอะไร
ควรเห็นได้ว่า "ทักษะนี้พาไปงานอะไรได้บ้าง" โดยไม่ต้องตั้งเป้าหมายก่อน

🔒 กติกาข้อ 1 — ทักษะจาก CV กับที่กรอกเองอยู่คนละฟิลด์ (`level_from_cv` · `level_self_reported`)
   ไม่มีบรรทัดไหนในไฟล์นี้รวมสองค่านี้เป็นตัวเลขเดียว หน้าจอจึงรวมโดยบังเอิญไม่ได้
   (`/api/roadmap` รวมด้วย `merge_evidence` ได้เพราะมันตอบว่า "คุณอยู่ตรงไหนของเส้น"
    หน้ากราฟไม่มีเส้นให้อยู่ จึงไม่มีเหตุผลให้รวม)

🔒 กติกาข้อ 5 — ทักษะ 26 ตัวจาก 73 ไม่มีตัวตรงใน O*NET ตัวโหลดจึงใส่ `name_en` เท่ากับ id
   (เช่น "SW-TEST") ทุก node ติดป้าย `name_en_is_placeholder` มาด้วย และสรุปจำนวนไว้ที่
   `notes.labels` — ห้ามให้หน้าจอเอา id ขึ้นเป็นชื่อ node เงียบ ๆ

🔴 ไม่มีตัวกรองฝั่ง server โดยตั้งใจ
   73 node เล็กพอจะกรองบนหน้าจอ · ถ้ากรองที่นี่ เส้นที่ปลายข้างหนึ่งถูกกรองออกจะหายไปด้วย
   แล้วกราฟที่ผู้ใช้เห็นจะไม่ใช่กราฟจริง — คืนทั้งใบแล้วให้หน้าจอซ่อนเอาชัดเจนกว่า
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import RESOURCE_KIND_TH
from app.db import get_db
from app.engine.skill_graph import SkillGraph
from app.models import (
    CareerTarget,
    ExtractedSkill,
    LearningResource,
    ResourceSkill,
    SelfReportedSkill,
    Skill,
    SkillEdge,
    TargetRequirement,
    User,
)
from app.seed.careers import SECTORS

router = APIRouter(prefix="/api/skills")

# หมวดของทักษะ — ชื่อหมวดตรงกับหัวข้อที่ `seed/skills.py` แบ่งไว้ ไม่ได้ตั้งใหม่
CATEGORY_TH = {
    "foundation": "พื้นฐานร่วม",
    "tool": "เครื่องมือกลาง",
    "analysis": "วิเคราะห์ข้อมูล",
    "software": "ซอฟต์แวร์",
    "data": "ข้อมูลและโมเดล",
    "embedded": "ระบบฝังตัว",
    "civil": "โยธา",
    "chemical": "เคมี",
    "electrical": "ไฟฟ้า",
    "industrial": "อุตสาหการ",
    "mechanical": "เครื่องกล",
    "professional": "ทักษะวิชาชีพ",
}

SOURCE_TH = {
    "onet": "มีตัวตรงใน O*NET",
    "market": "ตลาดใช้จริง แต่ O*NET ไม่มีเป็นรายการแยก",
    "manual": "ทีมเพิ่มเองจากบริบทการเรียน",
}


# ═════════════════════ ตัวช่วย ═════════════════════


def _user(db: Session, user_id: str) -> User:
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "ไม่พบผู้ใช้ — เริ่มใหม่ที่หน้าแรก")
    return u


def _skills(db: Session) -> list[Skill]:
    return list(db.scalars(select(Skill).order_by(Skill.id)).all())


def _graph(db: Session, skills: list[Skill]) -> SkillGraph:
    edges = [(e.from_id, e.to_id) for e in db.scalars(select(SkillEdge)).all()]
    return SkillGraph([s.id for s in skills], edges)


def _cv_levels(db: Session, user_id: str) -> dict[str, int]:
    """🔒 กติกาข้อ 3 — เฉพาะที่ผู้ใช้ยืนยันแล้วเท่านั้นถึงนับ · pending ไม่ขึ้นกราฟ"""
    out: dict[str, int] = {}
    for e in db.scalars(select(ExtractedSkill).where(
            ExtractedSkill.user_id == user_id,
            ExtractedSkill.user_status.in_(("confirmed", "edited")))).all():
        out[e.skill_id] = max(out.get(e.skill_id, 0), e.level)
    return out


def _self_levels(db: Session, user_id: str) -> dict[str, int]:
    return {s.skill_id: s.level for s in db.scalars(
        select(SelfReportedSkill).where(SelfReportedSkill.user_id == user_id)).all()}


def _career_counts(db: Session) -> dict[str, int]:
    """ทักษะนี้ถูกอาชีพกี่อาชีพต้องการ — ใช้ตัดสินขนาด node บนกราฟได้"""
    out: dict[str, int] = {}
    for r in db.scalars(select(TargetRequirement)).all():
        out[r.skill_id] = out.get(r.skill_id, 0) + 1
    return out


def _resource_counts(db: Session) -> dict[str, int]:
    out: dict[str, int] = {}
    for link in db.scalars(select(ResourceSkill)).all():
        out[link.skill_id] = out.get(link.skill_id, 0) + 1
    return out


def _brief(s: Skill) -> dict:
    """ทักษะแบบย่อ — ใช้ตอนอ้างถึงทักษะอื่น (prereq / unlock) ไม่ใช่ตัวที่กำลังดู"""
    return {
        "id": s.id,
        "name_en": s.name_en,
        "name_th": s.name_th,
        "category": s.category,
        "category_th": CATEGORY_TH.get(s.category, s.category),
        "name_en_is_placeholder": s.name_en == s.id,
    }


# ═════════════════════ กราฟทั้งใบ ═════════════════════


@router.get("")
def list_skills(user_id: str | None = None, db: Session = Depends(get_db)) -> dict:
    """★ หน้า Skill Graph

    ส่ง node + edge ดิบ ๆ ไม่มีพิกัด — การวางตำแหน่งเป็นเรื่องของหน้าจอ
    ที่นี่บอกได้แค่ว่าอะไรต่อกับอะไร และอะไรเป็นรากของกราฟ (`prereq_count == 0`)
    """
    skills = _skills(db)
    graph = _graph(db, skills)
    careers = _career_counts(db)
    resources = _resource_counts(db)

    cv: dict[str, int] = {}
    self_reported: dict[str, int] = {}
    if user_id:
        _user(db, user_id)
        cv = _cv_levels(db, user_id)
        self_reported = _self_levels(db, user_id)

    nodes = []
    for s in skills:
        nodes.append({
            **_brief(s),
            "source": s.source,
            "source_th": SOURCE_TH.get(s.source, s.source),
            # false = ทำเมื่อไหร่ก็ได้ ไม่ต้องรอ prerequisite (roadmap.sh เรียก "ลำดับไม่ตายตัว")
            "order_strict": s.order_strict,
            "prereq_count": len(graph.prereqs(s.id)),
            "unlock_count": len(graph.unlocks(s.id)),
            "career_count": careers.get(s.id, 0),
            "resource_count": resources.get(s.id, 0),
            # 🔒 กติกาข้อ 1 — สองฟิลด์ ไม่ใช่ฟิลด์เดียว · null = ยังไม่มีหลักฐานทางนั้น
            "level_from_cv": cv.get(s.id),
            "level_self_reported": self_reported.get(s.id),
        })

    counts: dict[str, int] = {}
    for s in skills:
        counts[s.category] = counts.get(s.category, 0) + 1

    placeholder = sum(1 for n in nodes if n["name_en_is_placeholder"])
    return {
        "nodes": nodes,
        "edges": [
            {"from": a, "to": b, "reviewed_by_human": True} for a, b in graph.edges
        ],
        "categories": [
            {"id": cid, "label_th": CATEGORY_TH.get(cid, cid), "count": n}
            for cid, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "counts": {
            "skills": len(nodes),
            "edges": len(graph.edges),
            "roots": sum(1 for n in nodes if n["prereq_count"] == 0),
        },
        "you": (
            {"from_cv": len(cv), "self_reported": len(self_reported)}
            if user_id else None
        ),
        "notes": {
            # 🔒 กติกาข้อ 5 — ข้อจำกัดสองข้อนี้ขึ้นจอได้เลย อย่าเก็บไว้เฉย ๆ
            "labels": (
                f"ทักษะ {placeholder} จาก {len(nodes)} ตัวยังไม่มีชื่ออังกฤษจาก O*NET "
                "— node พวกนี้ `name_en` เท่ากับรหัส ให้ใช้ `name_th` แทน"
                if placeholder else ""
            ),
            "edges": (
                "เส้น prerequisite ทุกเส้นเขียนและอ่านทวนด้วยคนแล้ว "
                "ยังไม่ได้ยืนยันจากประกาศงานจริง"
            ),
        },
    }


# ═════════════════════ ทักษะรายตัว ═════════════════════


@router.get("/{skill_id}")
def skill_detail(skill_id: str, user_id: str | None = None,
                 db: Session = Depends(get_db)) -> dict:
    """แผงข้างของหน้ากราฟ — ทักษะนี้พาไปอาชีพไหนได้ และเรียนจากไหน"""
    s = db.get(Skill, skill_id)
    if not s:
        raise HTTPException(404, "ไม่พบทักษะนี้")

    skills = _skills(db)
    by_id = {x.id: x for x in skills}
    graph = _graph(db, skills)

    reqs = db.execute(
        select(TargetRequirement, CareerTarget)
        .join(CareerTarget, CareerTarget.id == TargetRequirement.target_id)
        .where(TargetRequirement.skill_id == skill_id)
        .order_by(TargetRequirement.importance.desc())
    ).all()

    rows = db.execute(
        select(ResourceSkill, LearningResource)
        .join(LearningResource, LearningResource.id == ResourceSkill.resource_id)
        .where(ResourceSkill.skill_id == skill_id)
        .order_by(ResourceSkill.reaches_level.desc())
    ).all()

    you = None
    if user_id:
        _user(db, user_id)
        spans = db.scalars(
            select(ExtractedSkill).where(
                ExtractedSkill.user_id == user_id,
                ExtractedSkill.skill_id == skill_id,
                ExtractedSkill.user_status.in_(("confirmed", "edited")))
            .order_by(ExtractedSkill.confidence.desc())).all()
        you = {
            # 🔒 กติกาข้อ 1 — คนละฟิลด์ · กติกาข้อ 2 — ที่มาจาก CV ต้องชี้กลับไปที่ข้อความจริงได้
            "level_from_cv": max((e.level for e in spans), default=None),
            "level_self_reported": _self_levels(db, user_id).get(skill_id),
            "evidence": [
                {"document_id": e.document_id, "span_start": e.span_start,
                 "span_end": e.span_end, "span_text": e.span_text,
                 "level": e.level, "confidence": e.confidence}
                for e in spans
            ],
        }

    return {
        **_brief(s),
        "description": s.description,
        "source": s.source,
        "source_th": SOURCE_TH.get(s.source, s.source),
        "onet_element_id": s.onet_element_id,
        "order_strict": s.order_strict,
        "prereqs": [_brief(by_id[i]) for i in sorted(graph.prereqs(skill_id)) if i in by_id],
        "unlocks": [_brief(by_id[i]) for i in sorted(graph.unlocks(skill_id)) if i in by_id],
        # ⭐ "ได้ทักษะนี้แล้วเปิดทางไปอีกกี่ตัว" — ตัวเลขที่ทำให้เลือกได้ว่าจะลงแรงตรงไหน
        "unlocks_total": len(graph.transitive_unlocks(skill_id)),
        "supported_careers": [
            {
                "target_id": t.id, "title_th": t.title_th, "title_en": t.title_en,
                "sector_label": SECTORS.get(t.sector, t.sector),
                "min_level": r.min_level, "importance": r.importance,
                # 🔒 กติกาข้อ 5 — แยกข้อที่ยืนยันได้จากประกาศจริง ออกจากข้อที่ทีมเขียนเอง
                "appears_in_n_postings": r.appears_in_n_postings,
                "source": r.source,
            }
            for r, t in reqs
        ],
        "resources": [
            {
                "id": res.id, "kind": res.kind,
                "kind_label": RESOURCE_KIND_TH.get(res.kind, res.kind),
                "title": res.title, "provider": res.provider, "url": res.url,
                "est_hours": res.est_hours, "cost_baht": res.cost_baht,
                "min_year": res.min_year, "proof_of_done": res.proof_of_done,
                "reaches_level": link.reaches_level, "data_status": res.data_status,
            }
            for link, res in rows
        ],
        "you": you,
        "notes": {
            "careers": (
                "อาชีพที่ขึ้นตรงนี้มาจาก requirement ที่ทีมเขียนไว้ ยังไม่ได้ยืนยันจากประกาศงานจริง"
                if all(r.appears_in_n_postings == 0 for r, _ in reqs) else
                "ข้อที่ `appears_in_n_postings` มากกว่า 0 ยืนยันได้จากประกาศงานที่เก็บมาแล้ว"
            ),
            "resources": (
                "แหล่งเรียนที่ `data_status` เป็น placeholder คือชื่อทั่วไป "
                "ยังไม่ใช่วิชาหรือคอร์สจริงที่เปิดสอนอยู่"
            ),
        },
    }
