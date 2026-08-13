"""โหลดข้อมูลตั้งต้นลงฐานข้อมูล

รันซ้ำได้เสมอ และ **อัปเดตของเดิมให้ตรงกับไฟล์ทุกครั้ง**
เพราะคลังทักษะ อาชีพ และทรัพยากรจะถูกแก้อยู่ตลอดจนถึงวันสาธิต
ถ้า loader ข้ามแถวที่มีอยู่แล้ว ทีมจะต้องลบฐานข้อมูลทุกครั้งที่แก้ข้อความ
แล้วจะเผลอสาธิตด้วยข้อมูลเก่าโดยไม่รู้ตัว

ข้อมูลของผู้ใช้ (เอกสาร · ทักษะที่ยืนยัน · เป้าหมาย · roadmap) ไม่ถูกแตะต้อง
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    ActivityItem,
    Base,
    CareerTarget,
    JobPosting,
    LearningResource,
    ResourceSkill,
    Skill,
    SkillEdge,
    TargetActivityProfile,
    TargetRequirement,
    WorkActivity,
)
from app.seed.activities import ACTIVITY_GROUPS_TH, ACTIVITY_ITEMS, WORK_ACTIVITIES_TH
from app.seed.careers import CAREER_TARGETS
from app.seed.postings import load_all as load_postings
from app.seed.postings import to_row as posting_row
from app.seed.resources import LEARNING_RESOURCES
from app.seed.skills import ORDER_FLEXIBLE, SKILL_EDGES, SKILLS


def create_all(engine) -> None:
    Base.metadata.create_all(engine)


def _upsert(db: Session, model, pk, fields: dict) -> None:
    row = db.get(model, pk)
    if row is None:
        db.add(model(**fields))
        return
    for key, value in fields.items():
        if getattr(row, key) != value:
            setattr(row, key, value)


def _onet_index() -> dict[str, dict]:
    """ชื่ออังกฤษของทักษะ ดึงมาจากผลของท่อ ไม่ต้องพิมพ์ซ้ำ"""
    path = settings.pipeline_out / "onet_skills.json"
    if not path.exists():
        return {}
    return {s["id"]: s for s in json.loads(path.read_text(encoding="utf-8"))}


def _posting_requirements() -> dict[str, dict[str, dict]]:
    """ผลของท่อขั้นที่ 2 — target_id → skill_id → แถวที่ยืนยันได้จากประกาศงานจริง

    ไม่มีไฟล์ = ยังไม่ได้รัน `python pipeline/2_extract_postings.py` หรือยังไม่มีประกาศงาน
    ทั้งสองกรณีระบบต้องเดินต่อได้ด้วยชุดที่ทีมเขียนไว้ และรายงานว่ายังเป็น 0
    """
    path = settings.pipeline_out / "posting_requirements.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        target_id: {r["skill_id"]: r for r in t.get("requirements", [])}
        for target_id, t in data.get("targets", {}).items()
    }


def _activity_profiles() -> dict[str, dict[str, float]]:
    path = settings.pipeline_out / "target_activity_profiles.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("profiles", {})


def seed(db: Session) -> dict[str, int]:
    onet = _onet_index()

    # ── ทักษะ ──
    for s in SKILLS:
        ref = onet.get(s["onet_element_id"] or "", {})
        _upsert(db, Skill, s["id"], {
            "id": s["id"],
            "name_en": ref.get("name_en", s["id"]),
            "name_th": s["name_th"],
            "description": None,
            "category": s["category"],
            "onet_element_id": s["onet_element_id"],
            "source": s["source"],
            "order_strict": s["id"] not in ORDER_FLEXIBLE,
        })
    db.flush()

    # ── เส้น prerequisite — ให้ตรงกับไฟล์เป๊ะ เส้นที่ลบออกต้องหายไปจริง ──
    wanted = set(SKILL_EDGES)
    existing = {(e.from_id, e.to_id): e for e in db.scalars(select(SkillEdge)).all()}
    for a, b in wanted - set(existing):
        db.add(SkillEdge(from_id=a, to_id=b, reviewed_by_human=True))
    for edge in set(existing) - wanted:
        db.delete(existing[edge])

    # ── กิจกรรมในงาน + ข้อคำถาม ──
    for a in WORK_ACTIVITIES_TH:
        group = ".".join(a["id"].split(".")[:3])
        _upsert(db, WorkActivity, a["id"], {
            "id": a["id"], "name_en": a["id"], "name_th": a["name_th"],
            "description_th": a["context_th"], "group_id": group,
            "group_th": ACTIVITY_GROUPS_TH.get(group),
        })
    db.flush()
    for item in ACTIVITY_ITEMS:
        _upsert(db, ActivityItem, item["id"], {
            "id": item["id"], "activity_id": item["activity_id"],
            "prompt_th": item["prompt_th"], "context_th": item["context_th"],
            "reverse": item["reverse"],
        })

    # ── อาชีพเป้าหมาย + requirement + โปรไฟล์กิจกรรม ──
    profiles = _activity_profiles()
    posting_reqs = _posting_requirements()
    for t in CAREER_TARGETS:
        _upsert(db, CareerTarget, t["id"], {
            "id": t["id"], "title_th": t["title_th"], "title_en": t["title_en"],
            "summary": t["summary"], "day_in_the_life": t["day_in_the_life"],
            "sector": t["sector"], "field_whitelist": t["field_whitelist"],
            "min_education": t["min_education"], "min_gpa": t["min_gpa"],
            "onet_soc_code": t["onet_soc_code"], "posting_count": 0,
            "salary_note": t["salary_note"], "data_status": "placeholder",
        })
        db.flush()

        # requirement = ชุดที่ทีมเขียนไว้ **ผสม** กับที่ยืนยันได้จากประกาศงานจริง
        # ของที่ทีมเขียนไม่ถูกลบเมื่อประกาศไม่ได้พูดถึง เพราะตัวสกัดจับได้เฉพาะคำที่เขียนตรงตัว
        # (ดูเหตุผลเต็มใน pipeline/2_extract_postings.py)
        from_postings = posting_reqs.get(t["id"], {})
        db.query(TargetRequirement).filter(TargetRequirement.target_id == t["id"]).delete()
        for skill_id, min_level, importance in t["requirements"]:
            found = from_postings.get(skill_id)
            db.add(TargetRequirement(
                target_id=t["id"], skill_id=skill_id, min_level=min_level,
                importance=importance,
                appears_in_n_postings=found["appears_in_n_postings"] if found else 0,
                source="both" if found else "curated"))
        for skill_id, row in from_postings.items():
            if any(skill_id == s for s, _, _ in t["requirements"]):
                continue
            db.add(TargetRequirement(
                target_id=t["id"], skill_id=skill_id, min_level=row["min_level"],
                # ความสำคัญ = สัดส่วนประกาศที่พูดถึงทักษะนี้ · อ่านออกทันทีว่า "7 ใน 9 ประกาศ"
                importance=row["share"],
                appears_in_n_postings=row["appears_in_n_postings"],
                source="postings"))

        db.query(TargetActivityProfile).filter(
            TargetActivityProfile.target_id == t["id"]).delete()
        for activity_id, importance in profiles.get(t["onet_activity_soc"], {}).items():
            db.add(TargetActivityProfile(
                target_id=t["id"], activity_id=activity_id, importance=importance))

    # ── ทรัพยากรการเรียนรู้ ──
    for r in LEARNING_RESOURCES:
        _upsert(db, LearningResource, r["id"], {
            "id": r["id"], "kind": r["kind"], "title": r["title"], "provider": r["provider"],
            "url": r["url"], "description": r["description"], "est_hours": r["est_hours"],
            "cost_baht": r["cost_baht"], "min_year": r["min_year"],
            "proof_of_done": r["proof_of_done"], "data_status": r["data_status"],
        })
        db.flush()
        db.query(ResourceSkill).filter(ResourceSkill.resource_id == r["id"]).delete()
        for skill_id, level in r["teaches"]:
            db.add(ResourceSkill(resource_id=r["id"], skill_id=skill_id, reaches_level=level))

    # ── ประกาศงานจริงที่ 🅴 เก็บมา (data/postings/*.md) ──
    # ยังว่างอยู่จนกว่าจะมีคนเก็บ · ไฟล์ที่ยังผิดรูปแบบจะถูกข้าม ไม่ทำให้ระบบบูตไม่ขึ้น
    # 🔒 posting_count ของอาชีพนับจากของจริงเท่านั้น ไม่มีไฟล์ = 0 และต้องเป็น 0
    postings = load_postings(target_ids={t["id"] for t in CAREER_TARGETS})
    good = [p for p in postings if p.ok]
    if bad := [p for p in postings if not p.ok]:
        print(f"[seed] ⚠️  ประกาศงาน {len(bad)} ไฟล์ยังผิดรูปแบบ จึงข้ามไป — ดูด้วย make check-postings")
    for p in good:
        _upsert(db, JobPosting, p.id, posting_row(p))
    db.flush()

    counted: dict[str, int] = {}
    for p in good:
        if tid := p.meta.get("target_id"):
            counted[tid] = counted.get(tid, 0) + 1
    # 🔒 นับประกาศจากฟอร์มบริษัทเฉพาะที่อนุมัติแล้ว — ที่รอคิวยังไม่นับ
    for row in db.scalars(select(JobPosting).where(
            JobPosting.source == "employer", JobPosting.status == "approved")).all():
        if row.target_id:
            counted[row.target_id] = counted.get(row.target_id, 0) + 1
    for t in CAREER_TARGETS:
        row = db.get(CareerTarget, t["id"])
        if not row:
            continue
        n = counted.get(t["id"], 0)
        row.posting_count = n
        # 🔒 กติกาข้อ 5 — สถานะข้อมูลต้องเปลี่ยนตามความจริง ไม่ใช่ค้างที่ placeholder ตลอดกาล
        row.data_status = "from_postings" if posting_reqs.get(t["id"]) else "placeholder"

    db.commit()
    return {
        "skill": len(SKILLS),
        "skill_edge": len(SKILL_EDGES),
        "work_activity": len(WORK_ACTIVITIES_TH),
        "activity_item": len(ACTIVITY_ITEMS),
        "career_target": len(CAREER_TARGETS),
        "target_requirement": sum(len(t["requirements"]) for t in CAREER_TARGETS),
        "learning_resource": len(LEARNING_RESOURCES),
        "job_posting": len(good),
    }


def seed_path_exists() -> bool:
    return (settings.pipeline_out / "target_activity_profiles.json").exists()


PIPELINE_HINT = (
    "ยังไม่มีผลของท่อข้อมูล — รัน\n"
    "  python pipeline/1_import_onet.py\n"
    "  python pipeline/1b_import_instruments.py"
)


def check_pipeline() -> str | None:
    return None if seed_path_exists() else PIPELINE_HINT


def pipeline_dir() -> Path:
    return settings.pipeline_out
