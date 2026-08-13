"""HTTP API — ฝั่ง "ยังไม่รู้ว่าอยากเป็นอะไร"

ห่อ `engine/match_target.py` ที่ผ่านเทสต์กู้คืน 8/8 แล้ว ให้เป็นแบบทดสอบที่เดินได้จริง

  ขอข้อถัดไป      GET  /discover/next     ← เลือกข้อที่แยกอันดับ 1 กับ 2 ได้ดีที่สุด
  ตอบ 1 ข้อ        POST /discover/answer
  ดูผลจับคู่       GET  /discover/result
  เริ่มใหม่         POST /discover/reset

🔒 กติกาที่ไฟล์นี้บังคับ
   · คำตอบแบบทดสอบไม่ไหลเข้า ExtractedSkill เด็ดขาด — ความอยากทำไม่ใช่หลักฐานว่าทำเป็น
     (ตรงกับ docstring ของ ActivityResponse ใน models.py)
   · อาชีพที่ traced_to ว่าง จะไม่ถูกคืนออกไป — เครื่องยนต์คัดให้แล้ว ที่นี่ไม่ปลดกติกา
   · อันดับ 1 ยังไม่ห่างพอ → `separated=False` และบอกตรง ๆ ว่ายังแยกไม่ออก
     ห้ามยัดอันดับให้ดูมั่นใจ นี่คือสิ่งที่ทำให้แบบทดสอบทั่วไป "แนะนำให้เป็นพยาบาลทุกคน"

🔴 คะแนนดิบห้ามขึ้นจอ
   คะแนนดิบของทุกอาชีพกองกันอยู่ที่ 0.88–0.96 เอาไปโชว์ตรง ๆ จะอ่านเหมือน
   "เหมาะกับคุณ 94%" ทั้งที่ต่างกัน 0.02 · ทุก response จึงส่ง `relative_score`
   ซึ่งเป็น *ตำแหน่งเทียบกันในกลุ่ม* 0–100 พร้อม `scale_note` กำกับเสมอ
   และไม่มี endpoint ไหนส่งคะแนนดิบออกไปเลย

🔴 อาชีพที่ติดเงื่อนไขถาวรยังถูกจับคู่ ไม่ถูกตัดทิ้ง
   ถ้ากรองก่อนจับคู่ ผู้ใช้ทุนรัฐบาลจะเหลืออาชีพให้เทียบอาชีพเดียว แล้วแบบทดสอบก็ไร้ความหมาย
   จึงจับคู่กับทั้ง 8 อาชีพ แล้วติดป้าย `blocked_reasons` บอกว่าอันไหนติดอะไร
   ผู้ใช้ได้เห็นว่า "งานนี้เข้ากับคุณมาก แต่ทุนของคุณไม่ให้ไปเอกชน" ซึ่งเป็นข้อมูล ไม่ใช่ทางตัน
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.engine.eligibility import ProfileInput, TargetInput, filter_targets
from app.engine.match_target import (
    ActivityAnswer,
    MatchOutcome,
    TargetScore,
    match_targets,
    next_best_item,
)
from app.models import (
    ActivityItem,
    ActivityResponse,
    CareerTarget,
    ExtractedSkill,
    LearnerProfile,
    SelfReportedSkill,
    Skill,
    TargetActivityProfile,
    TargetMatch,
    TargetRequirement,
    User,
    WorkActivity,
)
from app.seed.activities import ANSWER_CHOICES
from app.seed.careers import SECTORS

router = APIRouter(prefix="/api/discover")

# ── จำนวนข้อ ──
# ตอบน้อยกว่านี้ห้ามสรุป แม้คะแนนจะแยกกันแล้ว — กันกรณีตอบ 3 ข้อแรกแล้วบังเอิญห่าง
MIN_ITEMS = 12
# ถามเกินนี้ไม่ได้ ต่อให้ยังแยกไม่ออก — ยาวกว่านี้คนเลิกกลางคัน แล้วบอกตรง ๆ ว่ายังไม่ชัด
MAX_ITEMS = 24
# ⭐ แสดงผลระหว่างทางทุกกี่ข้อ — สิ่งเดียวที่คนในเธรด r/findapath ชมว่าดี
FEEDBACK_EVERY = 6
# จำนวนอาชีพที่คืนในผลลัพธ์
TOP_N = 5

SCALE_NOTE = (
    "ตัวเลขนี้คือตำแหน่งเทียบกันในกลุ่มอาชีพที่นำมาเทียบ ไม่ใช่เปอร์เซ็นต์ความเหมาะสม "
    "อันดับ 1 ได้ 100 เสมอเพราะเป็นอันดับ 1 ไม่ได้แปลว่าเข้ากันสมบูรณ์"
)

WEIGHTS_NOTE = (
    "น้ำหนักของสัญญาณทั้ง 4 ตั้งจากเหตุผลเชิงออกแบบ ยังไม่ได้จูนกับผู้ใช้จริง"
)


# ═════════════════════ ตัวช่วย ═════════════════════


def _user(db: Session, user_id: str) -> User:
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "ไม่พบผู้ใช้ — เริ่มใหม่ที่หน้าแรก")
    return u


def _profiles(db: Session) -> dict[str, dict[str, float]]:
    """อาชีพ → {กิจกรรม: ความสำคัญ} · มาจาก O*NET ตรง ๆ เราไม่ได้ตั้งเอง"""
    out: dict[str, dict[str, float]] = {}
    for row in db.scalars(select(TargetActivityProfile)).all():
        out.setdefault(row.target_id, {})[row.activity_id] = row.importance
    return out


def _items(db: Session) -> dict[str, ActivityItem]:
    return {i.id: i for i in db.scalars(select(ActivityItem)).all()}


def _activity_labels(db: Session) -> dict[str, str]:
    return {a.id: a.display_name for a in db.scalars(select(WorkActivity)).all()}


def _skill_labels(db: Session) -> dict[str, str]:
    return {s.id: s.display_name for s in db.scalars(select(Skill)).all()}


def _requirements(db: Session) -> dict[str, list[tuple[str, int, float]]]:
    out: dict[str, list[tuple[str, int, float]]] = {}
    for r in db.scalars(select(TargetRequirement)).all():
        out.setdefault(r.target_id, []).append((r.skill_id, r.min_level, r.importance))
    return out


def _confirmed_skills(db: Session, user_id: str) -> dict[str, int]:
    """🔒 เฉพาะที่ผู้ใช้ยืนยันแล้ว — ตรงกับกติกาข้อ 3 ใน docs/TEAM.md"""
    out: dict[str, int] = {}
    for e in db.scalars(select(ExtractedSkill).where(
            ExtractedSkill.user_id == user_id,
            ExtractedSkill.user_status.in_(("confirmed", "edited")))).all():
        out[e.skill_id] = max(out.get(e.skill_id, 0), e.level)
    return out


def _self_reported(db: Session, user_id: str) -> dict[str, int]:
    return {s.skill_id: s.level for s in db.scalars(
        select(SelfReportedSkill).where(SelfReportedSkill.user_id == user_id)).all()}


def _responses(db: Session, user_id: str) -> list[ActivityResponse]:
    return list(db.scalars(
        select(ActivityResponse).where(ActivityResponse.user_id == user_id)
        .order_by(ActivityResponse.created_at)).all())


def _answers(db: Session, user_id: str, items: dict[str, ActivityItem]) -> list[ActivityAnswer]:
    return [
        ActivityAnswer(activity_id=items[r.item_id].activity_id, value=r.answer)
        for r in _responses(db, user_id)
        if r.item_id in items
    ]


def _blocked(db: Session, user_id: str) -> dict[str, list[dict]]:
    """อาชีพไหนติดเงื่อนไขถาวรบ้าง — ติดป้าย ไม่ตัดออกจากการจับคู่"""
    p = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    if not p:
        return {}
    ob = p.obligation_json or {}
    profile = ProfileInput(
        field_code=p.field, education_level=p.education_level, gpa=p.gpa,
        obligation_allowed_sectors=ob.get("allowed_sectors"),
        obligation_label=ob.get("label"), hours_per_week=p.hours_per_week,
    )
    targets = db.scalars(select(CareerTarget)).all()
    _, removed = filter_targets(profile, [
        TargetInput(
            id=t.id, org=t.title_th, role_title=t.title_en, sector=t.sector,
            field_whitelist=t.field_whitelist, min_education=t.min_education,
            min_gpa=t.min_gpa)
        for t in targets
    ])
    return {
        v.target_id: [{"kind": b.kind, "message": b.message} for b in v.permanent_blocks]
        for v in removed
    }


def _run_match(db: Session, user_id: str) -> tuple[MatchOutcome, dict[str, CareerTarget]]:
    items = _items(db)
    p = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == user_id))
    targets = {t.id: t for t in db.scalars(select(CareerTarget)).all()}
    outcome = match_targets(
        answers=_answers(db, user_id, items),
        target_profiles=_profiles(db),
        requirements=_requirements(db),
        extracted_skills=_confirmed_skills(db, user_id),
        self_reported_skills=_self_reported(db, user_id),
        activity_labels=_activity_labels(db),
        skill_labels=_skill_labels(db),
        user_field=p.field if p else None,
        target_fields={t.id: t.field_whitelist for t in targets.values()},
    )
    return outcome, targets


def _relative(ranked: list[TargetScore]) -> dict[str, int]:
    """คะแนนดิบ → ตำแหน่งเทียบกันในกลุ่ม 0–100

    🔴 นี่คือจุดที่แก้ปัญหา "คะแนนกองกันที่ 0.88–0.96" ที่ docs/TEAM.md สั่งให้แก้
       ค่าที่ออกไปบอกได้แค่ว่า *เรียงกันยังไง* ไม่ได้บอกว่าเข้ากันกี่เปอร์เซ็นต์
    """
    if not ranked:
        return {}
    hi, lo = ranked[0].score, ranked[-1].score
    if hi - lo <= 1e-9:
        return {s.target_id: 50 for s in ranked}   # เท่ากันหมด — ไม่มีใครนำใคร
    return {s.target_id: round((s.score - lo) / (hi - lo) * 100) for s in ranked}


def _line(t, reads_as: str) -> dict:
    return {"kind": t.kind, "ref_id": t.ref_id, "label": t.label,
            "direction": t.direction, "reads_as": reads_as}


def _reason_lines(s: TargetScore) -> list[dict]:
    """เหตุผลที่ใช้ตอบว่า “ทำไมถึงเสนออาชีพนี้” — เฉพาะ wants_and_does

    🔴 ทำไมไม่รวม unwanted_but_core ไว้ในลิสต์เดียวกัน
       D3 เก็บทั้งสอง direction ไว้ถูกแล้ว ทั้งคู่เป็นข้อมูลที่มีค่า
       แต่ headline_reasons เรียงตามน้ำหนัก ทำให้ unwanted_but_core ขึ้นเป็นข้อแรกได้
       (วัดจริงแล้ว: อันดับ 1 ของผู้ใช้ทดสอบขึ้นว่า “คุณไม่อยากขายของ แต่งานนี้ต้องขายเยอะ”)
       หน้าจอที่พิมพ์ reasons[0] จะกลายเป็น “เสนองานนี้เพราะคุณไม่อยากขายของ”
       ซึ่งคือปัญหาเดียวกับที่ D3 แก้ไปแล้ว แค่เปลี่ยนคำ
       → แยกเป็นคนละฟิลด์ ให้หน้าจอเอาไปวางคนละที่ ไม่ต้องมาคัดเอง
    """
    return [
        _line(t, "คุณอยากทำ และงานนี้ได้ทำเยอะ")
        for t in s.headline_reasons if t.direction == "wants_and_does"
    ]


def _heads_up_lines(s: TargetScore) -> list[dict]:
    """สิ่งที่ควรรู้ก่อนเลือก — งานนี้ต้องทำเยอะ ทั้งที่ผู้ใช้บอกว่าไม่อยากทำ

    ไม่ใช่เหตุผลที่เสนอ แต่เป็นข้อมูลที่คนกำลังตัดสินใจควรได้เห็น
    """
    return [
        _line(t, "งานนี้ต้องทำเรื่องนี้เยอะ ทั้งที่คุณบอกว่าไม่อยากทำ")
        for t in s.headline_reasons if t.direction == "unwanted_but_core"
    ]


def _card(
    s: TargetScore,
    targets: dict[str, CareerTarget],
    relative: dict[str, int],
    blocked: dict[str, list[dict]],
) -> dict:
    t = targets[s.target_id]
    return {
        "target_id": s.target_id,
        "title_th": t.title_th,
        "title_en": t.title_en,
        "summary": t.summary,
        "sector_label": SECTORS.get(t.sector, t.sector),
        "field_whitelist": t.field_whitelist,
        "rank_no": s.rank_no,
        "relative_score": relative.get(s.target_id, 0),
        "is_unconsidered": s.is_unconsidered,
        # 🔒 traced_to ว่างไม่ได้ — เครื่องยนต์คัดออกไปแล้วก่อนถึงตรงนี้
        # ทำไมถึงเสนอ · สิ่งที่ควรรู้ก่อนเลือก · สิ่งที่ดันคะแนนลง — คนละฟิลด์ คนละที่บนจอ
        "reasons": _reason_lines(s),
        "heads_up": _heads_up_lines(s),
        "reasons_against": [
            {"label": t2.label, "ref_id": t2.ref_id} for t2 in s.opposing[:2]
        ],
        # ติดเงื่อนไขทุน/สาขา — บอกไว้ ไม่ได้ตัดออกจากผล
        "blocked_reasons": blocked.get(s.target_id, []),
    }


def _persist(db: Session, user_id: str, outcome: MatchOutcome) -> None:
    db.execute(delete(TargetMatch).where(TargetMatch.user_id == user_id))
    for s in outcome.ranked:
        db.add(TargetMatch(
            user_id=user_id, target_id=s.target_id, score=s.score,
            score_activity=s.score_activity, score_extracted=s.score_extracted,
            score_self_reported=s.score_self_reported, score_values=s.score_values,
            rank_no=s.rank_no, is_unconsidered=s.is_unconsidered,
            traced_to_json=[
                {"kind": t.kind, "ref_id": t.ref_id, "label": t.label,
                 "contribution": t.contribution, "direction": t.direction}
                for t in s.traced_to
            ],
        ))
    db.commit()


def _empty_message(responses: list[ActivityResponse]) -> str:
    """ทำไมไม่มีอาชีพให้ดูเลย — ต้องตอบให้ตรงสาเหตุจริง

    🔴 เคสที่เจอตอนเทสต์: ตอบ "เฉย ๆ" ครบ 24 ข้อ แล้วได้อาชีพ 0 อัน
       เพราะ `_activity_score` ต้องมีข้อที่ไม่เป็นกลางอย่างน้อย 2 ข้อถึงจะคำนวณสหสัมพันธ์ได้
       เมื่อไม่มีคะแนน ก็ไม่มี traced_to และกติกา "ย้อนที่มาไม่ได้ = ไม่แสดง" ตัดออกหมด
       กติกานั้นถูกและห้ามแก้ · ที่ต้องแก้คือข้อความ ห้ามบอกว่า "ยังตอบไม่พอ"
       ให้คนที่ตอบครบเพดานแล้ว
    """
    decided = sum(1 for r in responses if r.answer != 0)
    if not responses:
        return "ยังไม่ได้ตอบแบบทดสอบ"
    if decided < 2:
        return (
            f"คุณตอบ “เฉย ๆ” เกือบทุกข้อ (ตอบไปแล้ว {len(responses)} ข้อ "
            f"มีแค่ {decided} ข้อที่บอกว่าอยากหรือไม่อยากทำ) ระบบจึงยังไม่มีอะไรใช้เทียบ "
            "— ลองย้อนกลับไปเลือก “อยากทำ” หรือ “ไม่อยากทำ” สักสองสามข้อ"
        )
    return (
        "ยังไม่มีอาชีพไหนที่ย้อนกลับไปอธิบายได้จากคำตอบของคุณ "
        "— เราไม่แสดงอาชีพที่บอกไม่ได้ว่าทำไมถึงเสนอ"
    )


def _still_asking(outcome: MatchOutcome, targets: dict[str, CareerTarget], left: int) -> str:
    """⭐ บอกว่าทำไมยังถามต่อ — อ้างชื่ออาชีพจริง ไม่ใช่รหัส"""
    if len(outcome.ranked) < 2:
        return "ยังตอบไม่พอจะเทียบอาชีพได้ ขอถามอีกสักหน่อย"
    a, b = outcome.ranked[0].target_id, outcome.ranked[1].target_id
    more = min(4, left)
    return (
        f"ตอนนี้ “{targets[a].title_th}” กับ “{targets[b].title_th}” ยังแยกกันไม่ชัด "
        f"ขอถามอีก {more} ข้อ"
    )


def _item_payload(item: ActivityItem, activity: WorkActivity | None, no: int) -> dict:
    """🔒 ไม่มีชื่ออาชีพในนี้โดยตั้งใจ — ผู้ใช้ต้องตอบต่อ *กิจกรรม* ไม่ใช่ต่อชื่ออาชีพ"""
    return {
        "item_id": item.id,
        "no": no,
        "prompt_th": item.prompt_th,
        "context_th": item.context_th,
        "group_th": activity.group_th if activity else None,
    }


# ═════════════════════ ขอข้อถัดไป ═════════════════════


@router.get("/next")
def next_item(user_id: str, db: Session = Depends(get_db)) -> dict:
    """ข้อถัดไป 1 ข้อ — เลือกข้อที่แยกอันดับ 1 กับ 2 ได้ดีที่สุด

    ไม่ได้ไล่ถามเรียง 41 ข้อ · ตอบ 12–24 ข้อก็พอ และทุกข้อมีเหตุผลว่าทำไมถึงถาม
    """
    _user(db, user_id)
    items = _items(db)
    profiles = _profiles(db)
    responses = _responses(db, user_id)
    answered_item_ids = {r.item_id for r in responses}
    answered_activity_ids = {
        items[r.item_id].activity_id for r in responses if r.item_id in items
    }
    answered = len(responses)

    by_activity = {i.activity_id: i for i in items.values()}
    left = len(items) - answered

    outcome, targets = _run_match(db, user_id)
    interim = None
    if answered and answered % FEEDBACK_EVERY == 0:
        # ⭐ แสดงผลระหว่างทาง — ไม่ต้องรอจบถึงจะเห็นว่ากำลังไปทางไหน
        relative = _relative(outcome.ranked)
        blocked = _blocked(db, user_id)
        interim = {
            "separated": outcome.separated,
            "top": [
                _card(s, targets, relative, blocked) for s in outcome.ranked[:3]
            ],
            "scale_note": SCALE_NOTE,
            "compared_count": len(outcome.ranked),
        }

    enough = answered >= MIN_ITEMS
    if (outcome.separated and enough) or answered >= MAX_ITEMS or left <= 0:
        return {
            "done": True,
            "reason": (
                "แยกออกแล้วว่าคุณเอนไปทางไหน" if outcome.separated
                else _empty_message(responses) if not outcome.ranked
                else "ถามครบจำนวนสูงสุดแล้ว แต่ยังแยกไม่ชัด — ผลจะบอกตามตรง"
            ),
            "answered": answered,
            "min_items": MIN_ITEMS,
            "max_items": MAX_ITEMS,
            "can_finish": enough,
            "answer_choices": ANSWER_CHOICES,
            "item": None,
            "interim": interim,
        }

    # เลือกข้อถัดไป
    activity_id: str | None = None
    if len(outcome.ranked) >= 2:
        activity_id = next_best_item(
            answered_activity_ids, profiles,
            (outcome.ranked[0].target_id, outcome.ranked[1].target_id),
        )
    if activity_id is None or activity_id not in by_activity:
        # ยังไม่มีอันดับให้แยก (ข้อแรก ๆ) — หยิบข้อที่อาชีพต่างกันมากที่สุดก่อน
        activity_id = _widest_spread(profiles, answered_activity_ids)
    if activity_id is None or activity_id not in by_activity:
        remaining = [i for i in items.values() if i.id not in answered_item_ids]
        if not remaining:
            return {
                "done": True, "reason": "ตอบครบทุกข้อแล้ว", "answered": answered,
                "min_items": MIN_ITEMS, "max_items": MAX_ITEMS,
                "can_finish": enough, "answer_choices": ANSWER_CHOICES,
                "item": None, "interim": interim,
            }
        activity_id = remaining[0].activity_id

    item = by_activity[activity_id]
    activity = db.get(WorkActivity, activity_id)
    return {
        "done": False,
        "reason": _still_asking(outcome, targets, left),
        "answered": answered,
        "min_items": MIN_ITEMS,
        "max_items": MAX_ITEMS,
        # ⭐ ตอบครบขั้นต่ำแล้วต้องออกได้ ไม่ต้องรอให้ระบบบอกว่าจบ
        "can_finish": enough,
        # 🔒 ป้ายปุ่มมาจากที่เดียว — หน้าจอห้าม hardcode 5 ระดับเอง
        "answer_choices": ANSWER_CHOICES,
        "item": _item_payload(item, activity, answered + 1),
        "interim": interim,
    }


def _widest_spread(
    profiles: dict[str, dict[str, float]], answered: set[str]
) -> str | None:
    """ข้อที่อาชีพทั้ง 8 ให้ค่าต่างกันมากที่สุด — ใช้ตอนยังไม่มีอันดับให้แยก

    ถามข้อที่ทุกอาชีพตอบเหมือนกันคือเสียข้อฟรี
    """
    values: dict[str, list[float]] = {}
    for prof in profiles.values():
        for aid, v in prof.items():
            if aid not in answered:
                values.setdefault(aid, []).append(v)
    if not values:
        return None
    ranked = sorted(values.items(), key=lambda kv: (-(max(kv[1]) - min(kv[1])), kv[0]))
    return ranked[0][0]


# ═════════════════════ ตอบ 1 ข้อ ═════════════════════


class AnswerRequest(BaseModel):
    user_id: str
    item_id: str
    # สเกล 5 ระดับ — ค่าและถ้อยคำอยู่ที่ `ANSWER_CHOICES` และส่งไปกับ /next ทุกครั้ง
    # หน้าจอห้าม hardcode ป้าย ให้ใช้ที่ API ส่งมา จะได้ไม่หลุดจากกันเวลาแก้คำ
    answer: Literal[-2, -1, 0, 1, 2]
    round_no: int = Field(default=1, ge=1)


@router.post("/answer")
def answer_item(body: AnswerRequest, db: Session = Depends(get_db)) -> dict:
    """บันทึกคำตอบ 1 ข้อ แล้วคำนวณอันดับใหม่ทันที

    🔒 คำตอบลงตาราง activity_response เท่านั้น — ไม่มีบรรทัดไหนในไฟล์นี้ที่เขียน
       ExtractedSkill จากคำตอบแบบทดสอบ · ความอยากทำไม่ใช่หลักฐานว่าทำเป็น
    """
    _user(db, body.user_id)
    item = db.get(ActivityItem, body.item_id)
    if not item:
        raise HTTPException(404, "ไม่พบข้อคำถามนี้")

    existing = db.scalar(select(ActivityResponse).where(
        ActivityResponse.user_id == body.user_id,
        ActivityResponse.item_id == body.item_id))
    if existing:
        existing.answer = body.answer      # ตอบซ้ำข้อเดิม = แก้คำตอบ ไม่ใช่เพิ่มแถว
    else:
        db.add(ActivityResponse(
            user_id=body.user_id, item_id=body.item_id,
            answer=body.answer, asked_at_round=body.round_no))
    db.commit()

    outcome, _ = _run_match(db, body.user_id)
    _persist(db, body.user_id, outcome)
    answered = len(_responses(db, body.user_id))

    return {
        "recorded": True,
        "answered": answered,
        "separated": outcome.separated,
        "feedback_due": answered % FEEDBACK_EVERY == 0,
        "can_finish": answered >= MIN_ITEMS,
    }


# ═════════════════════ ผลจับคู่ ═════════════════════


@router.get("/result")
def result(user_id: str, db: Session = Depends(get_db)) -> dict:
    """อาชีพที่เป็นไปได้ 3–5 อัน + "อาชีพที่คุณอาจไม่เคยคิดถึง"

    🔒 ถ้ายังแยกไม่ออก จะบอกตรง ๆ ว่ายังแยกไม่ออก — ห้ามยัดอันดับให้ดูมั่นใจ
    """
    _user(db, user_id)
    responses = _responses(db, user_id)
    if not responses:
        raise HTTPException(409, "ยังไม่ได้ตอบแบบทดสอบเลย")

    outcome, targets = _run_match(db, user_id)
    _persist(db, user_id, outcome)

    relative = _relative(outcome.ranked)
    blocked = _blocked(db, user_id)
    top = [_card(s, targets, relative, blocked) for s in outcome.ranked[:TOP_N]]

    unconsidered = next(
        (c for c in top if c["is_unconsidered"]),
        None,
    )
    if unconsidered is None and outcome.unconsidered_id:
        s = next((x for x in outcome.ranked if x.target_id == outcome.unconsidered_id), None)
        if s:
            unconsidered = _card(s, targets, relative, blocked)

    if not top:
        # ไม่มีอาชีพให้ดูเลย — บอกสาเหตุจริงและทางออก ห้ามคืนรายการว่างเปล่าเงียบ ๆ
        return {
            "answered": len(responses),
            "separated": False,
            "separation_message": "",
            "empty_message": _empty_message(responses),
            "targets": [],
            "unconsidered": None,
            "unconsidered_note": "",
            "compared_count": len(outcome.ranked),
            "scale_note": SCALE_NOTE,
            "weights_note": WEIGHTS_NOTE,
            "next_step": "กลับไปตอบแบบทดสอบอีกครั้งที่ /discover/next",
        }

    return {
        "answered": len(responses),
        "separated": outcome.separated,
        # ⭐ ยังแยกไม่ออกก็พูดตรง ๆ — ตัวเลขที่ดูมั่นใจเกินจริงคือสิ่งที่เราตั้งใจไม่ทำ
        "separation_message": (
            "" if outcome.separated
            else (
                _still_asking(outcome, targets, 0).split(" ขอถามอีก")[0]
                + " — ผลข้างล่างจึงอ่านเป็น “ทางที่เป็นไปได้” ไม่ใช่คำตอบสุดท้าย"
            )
        ),
        "empty_message": "",
        "targets": top,
        "unconsidered": unconsidered,
        "unconsidered_note": (
            "อาชีพนี้คะแนนดี แต่ไม่ได้อยู่ในสาขาที่คุณเรียน จึงมักไม่ถูกนึกถึง"
            if unconsidered else ""
        ),
        # 🔴 จำนวนอาชีพที่เอามาเทียบกันจริง — หน้าจอต้องเขียนได้ว่า "อันดับ 1 จาก 8 อาชีพ"
        #    ไม่ใช่ "เหมาะกับคุณ 100%" · relative_score ไม่มีความหมายถ้าไม่บอกว่าเทียบกับกี่อัน
        "compared_count": len(outcome.ranked),
        "scale_note": SCALE_NOTE,
        "weights_note": WEIGHTS_NOTE,
        "next_step": "เลือกอาชีพที่สนใจแล้วไปต่อที่ /goal เพื่อดู roadmap ของอาชีพนั้น",
    }


# ═════════════════════ เริ่มใหม่ ═════════════════════


class ResetRequest(BaseModel):
    user_id: str


@router.post("/reset")
def reset(body: ResetRequest, db: Session = Depends(get_db)) -> dict:
    """ล้างคำตอบแบบทดสอบทั้งหมด — ไม่แตะ CV ทักษะที่ยืนยันแล้ว หรือโปรไฟล์"""
    _user(db, body.user_id)
    n = db.execute(delete(ActivityResponse).where(
        ActivityResponse.user_id == body.user_id)).rowcount or 0
    db.execute(delete(TargetMatch).where(TargetMatch.user_id == body.user_id))
    db.commit()
    return {"cleared": n}
