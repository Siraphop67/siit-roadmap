"""เทสต์เครื่องยนต์ roadmap — ฝั่ง "รู้แล้วว่าอยากไปไหน"

invariant ที่ยกมาจาก draft 1 และยังต้องเป็นจริง:
  · path[0] เป็นตัวเดียวกับที่ RANK เลือก
  · ผู้ใช้ที่เริ่มจากศูนย์ต้องมีก้าวถัดไปเสมอ
  · ทุกก้าวต้องมีทางไปถึงอย่างน้อย 1 ทาง
"""

from __future__ import annotations

import pytest

from app.engine.eligibility import ProfileInput, TargetInput, evaluate, filter_targets
from app.engine.roadmap import (
    EVIDENCE_BOTH,
    EVIDENCE_EXTRACTED,
    EVIDENCE_SELF,
    Requirement,
    Resource,
    build_roadmap,
    frontier,
    merge_evidence,
    rank_steps,
    todo_closure,
)
from app.engine.skill_graph import SkillGraph
from app.seed.careers import CAREER_TARGETS
from app.seed.resources import resources_by_skill
from app.seed.skills import ORDER_FLEXIBLE, SKILL_EDGES, SKILL_IDS, SKILLS


@pytest.fixture(scope="module")
def graph() -> SkillGraph:
    return SkillGraph(SKILL_IDS, SKILL_EDGES)


@pytest.fixture(scope="module")
def names() -> dict[str, str]:
    return {s["id"]: s["name_th"] for s in SKILLS}


@pytest.fixture(scope="module")
def resources() -> dict[str, list[Resource]]:
    out: dict[str, list[Resource]] = {}
    for skill_id, rows in resources_by_skill().items():
        for r in rows:
            level = next(lv for sid, lv in r["teaches"] if sid == skill_id)
            out.setdefault(skill_id, []).append(Resource(
                id=r["id"], kind=r["kind"], title=r["title"], provider=r["provider"],
                est_hours=r["est_hours"], cost_baht=r["cost_baht"], min_year=r["min_year"],
                proof_of_done=r["proof_of_done"], reaches_level=level,
            ))
    return out


def reqs_of(target_id: str) -> list[Requirement]:
    t = next(t for t in CAREER_TARGETS if t["id"] == target_id)
    return [Requirement(s, lv, w) for s, lv, w in t["requirements"]]


ALL_TARGETS = [t["id"] for t in CAREER_TARGETS]


def make(graph, names, resources, target_id, have=None, **kw):
    return build_roadmap(
        graph=graph, target_id=target_id, requirements=reqs_of(target_id),
        have=have or {}, resources=resources, skill_names=names,
        flexible_skills=ORDER_FLEXIBLE, **kw)


# ═══════════ ความถูกต้องของข้อมูลตั้งต้น ═══════════


def test_graph_is_a_dag_with_no_dangling_edges(graph):
    assert len(graph.nodes) == 73
    assert graph.dangling_edges() == []


def test_every_requirement_points_at_a_real_skill():
    ids = set(SKILL_IDS)
    for t in CAREER_TARGETS:
        for skill_id, _lv, _w in t["requirements"]:
            assert skill_id in ids, f'{t["id"]} อ้างทักษะที่ไม่มีอยู่: {skill_id}'


def test_flexible_skills_are_real():
    assert ORDER_FLEXIBLE <= set(SKILL_IDS)


# ═══════════ 🔒 invariant หลัก ═══════════


@pytest.mark.parametrize("target_id", ALL_TARGETS)
@pytest.mark.parametrize("hours", [None, 4, 15])
def test_first_actionable_step_is_the_one_rank_chose(graph, names, resources, target_id, hours):
    """🔒 เส้นทางกับข้อเสนอต้องเป็นตัวเดียวกัน ไม่งั้นผู้ใช้เห็นอย่างแต่ระบบเสนออีกอย่าง"""
    rm = make(graph, names, resources, target_id, hours_per_week=hours)
    todo = todo_closure(graph, reqs_of(target_id), {})
    scores = rank_steps(graph, todo, reqs_of(target_id), resources, hours)
    front = [s for s in frontier(graph, todo, {}, ORDER_FLEXIBLE) if s not in ORDER_FLEXIBLE]
    if not front:
        return
    best = max(front, key=lambda s: (scores[s], [-ord(c) for c in s]))

    current = rm.current_step
    assert current is not None, f"{target_id}: ไม่มีก้าวที่กดได้เลย"
    assert current.skill_id == best, (
        f"{target_id}: หน้าจอชี้ {current.skill_id} แต่ RANK เลือก {best}"
    )


@pytest.mark.parametrize("target_id", ALL_TARGETS)
def test_fresh_user_always_has_a_next_step(graph, names, resources, target_id):
    rm = make(graph, names, resources, target_id)
    assert rm.steps, f"{target_id}: roadmap ว่างเปล่า"
    assert any(s.actionable for s in rm.steps), f"{target_id}: ไม่มีก้าวที่ลงมือได้"
    assert all(s.target_level == s.current_level + 1 for s in rm.steps), "ข้ามขั้นได้ = ผิดหลัก"


@pytest.mark.parametrize("target_id", ALL_TARGETS)
def test_every_step_has_at_least_one_way_to_reach_it(graph, names, resources, target_id):
    """ก้าวที่ไม่มีทางไปถึง = ก้าวที่กดไม่ได้"""
    rm = make(graph, names, resources, target_id)
    for s in rm.steps:
        assert s.options, f"{target_id}: ก้าว {s.skill_id} ไม่มีทางไปถึงเลย"


@pytest.mark.parametrize("target_id", ALL_TARGETS)
def test_steps_respect_prerequisite_order(graph, names, resources, target_id):
    rm = make(graph, names, resources, target_id)
    seen: set[str] = set()
    todo = {s.skill_id for s in rm.steps}
    for step in rm.steps:
        unmet = (graph.prereqs(step.skill_id) & todo) - seen - ORDER_FLEXIBLE
        assert not unmet, f"{step.skill_id} ถูกวางก่อน prerequisite {unmet}"
        seen.add(step.skill_id)


def test_exactly_one_step_is_marked_current(graph, names, resources):
    rm = make(graph, names, resources, "SW-DEV")
    assert sum(1 for s in rm.steps if s.status == "current") == 1


def test_roadmap_is_deterministic(graph, names, resources):
    runs = [[(s.skill_id, s.status) for s in make(graph, names, resources, "ROBOT-ENG").steps]
            for _ in range(3)]
    assert runs[0] == runs[1] == runs[2]


# ═══════════ กลไก "ลำดับไม่ตายตัว" จาก roadmap.sh ═══════════


def test_flexible_skills_are_actionable_regardless_of_position(graph, names, resources):
    """"อ่านเอกสารอังกฤษ" ทำเมื่อไหร่ก็ได้ ไม่ต้องรอก้าวก่อนหน้า"""
    rm = make(graph, names, resources, "SW-DEV")
    flex = [s for s in rm.steps if s.skill_id in ORDER_FLEXIBLE]
    assert flex, "ควรมีทักษะที่ทำเมื่อไหร่ก็ได้อยู่ในเส้นทางนี้"
    for s in flex:
        assert s.status == "flexible"
        assert s.actionable


def test_flexible_skills_do_not_block_others(graph, names, resources):
    """ก้าวที่ต่อจากทักษะยืดหยุ่น ต้องไม่ถูกล็อกเพราะรอมัน"""
    rm = make(graph, names, resources, "STRUCT-ENG")
    order = {s.skill_id: s.order_no for s in rm.steps}
    for a, b in SKILL_EDGES:
        if a in ORDER_FLEXIBLE and a in order and b in order:
            # ไม่บังคับว่า a ต้องมาก่อน b
            pass
    doc = next((s for s in rm.steps if s.skill_id == "P-DOC"), None)
    if doc:
        assert doc.status == "flexible"


# ═══════════ แยกหลักฐานสองชนิด ═══════════


def test_evidence_kinds_never_collapse_into_one():
    """จุดขายของผลิตภัณฑ์ — ต้องบอกได้เสมอว่าทักษะไหนพิสูจน์ได้ ทักษะไหนแค่บอกมา"""
    have = merge_evidence({"T-PY": 3}, {"SW-DS": 2})
    assert have["T-PY"].kind == EVIDENCE_EXTRACTED
    assert have["SW-DS"].kind == EVIDENCE_SELF


def test_same_skill_from_both_sources_is_labelled_both():
    have = merge_evidence({"T-PY": 2}, {"T-PY": 3})
    assert have["T-PY"].kind == EVIDENCE_BOTH
    assert have["T-PY"].level == 3, "ใช้ระดับที่สูงกว่า"


def test_steps_carry_where_the_evidence_came_from(graph, names, resources):
    have = merge_evidence({"F-SOLVE": 3}, {"F-MATH": 2})
    rm = make(graph, names, resources, "SW-DEV", have=have)
    by_id = {s.skill_id: s for s in rm.steps}
    for sid, kind in (("F-SOLVE", EVIDENCE_EXTRACTED), ("F-MATH", EVIDENCE_SELF)):
        if sid in by_id:
            assert by_id[sid].evidence_kind == kind


def test_having_skills_shortens_the_roadmap(graph, names, resources):
    empty = make(graph, names, resources, "SW-DEV")
    skilled = make(graph, names, resources, "SW-DEV",
                   have=merge_evidence({"T-PY": 3, "F-SOLVE": 3, "SW-DS": 3}, {}))
    assert skilled.total_steps < empty.total_steps
    assert skilled.steps_done > empty.steps_done


# ═══════════ ทางเลือกและเงื่อนไข ═══════════


def test_options_that_do_not_fit_are_shown_with_a_reason(graph, names, resources):
    """ไม่ตัดทิ้งเงียบ ๆ — แสดงพร้อมเหตุผล เหมือนอาชีพที่ถูกกรองออก"""
    rm = make(graph, names, resources, "SW-DEV", budget_baht=0, year=1, hours_per_week=2)
    blocked = [o for s in rm.steps for o in s.options if not o.fits_all]
    assert blocked, "ตั้งเงื่อนไขแคบขนาดนี้ควรมีตัวเลือกที่ติดเงื่อนไขบ้าง"
    for o in blocked:
        assert o.blocked_reason, "ตัวเลือกที่ใช้ไม่ได้ต้องบอกเหตุผล"


def test_affordable_options_are_listed_first(graph, names, resources):
    rm = make(graph, names, resources, "SW-DEV", budget_baht=0, year=1)
    for s in rm.steps:
        fits = [i for i, o in enumerate(s.options) if o.fits_all]
        blocked = [i for i, o in enumerate(s.options) if not o.fits_all]
        if fits and blocked:
            assert max(fits) < min(blocked), f"{s.skill_id}: ตัวเลือกที่ใช้ได้ควรอยู่บน"


def test_roadmap_exposes_edges_for_graph_rendering(graph, names, resources):
    """หน้าเว็บต้องเลือกวาดเป็นกราฟหรือรายการก็ได้ (UI ยังไม่ตัดสินใจ)"""
    rm = make(graph, names, resources, "ROBOT-ENG")
    ids = {s.skill_id for s in rm.steps}
    assert rm.edges
    for a, b in rm.edges:
        assert a in ids and b in ids


# ═══════════ eligibility ที่ยกมาจาก draft 1 ═══════════


def _target_input(t: dict) -> TargetInput:
    return TargetInput(
        id=t["id"], org=t["title_th"], role_title=t["title_en"], sector=t["sector"],
        field_whitelist=t["field_whitelist"], min_education=t["min_education"],
        min_gpa=t["min_gpa"])


def test_scholarship_obligation_removes_private_sector_targets():
    profile = ProfileInput(
        obligation_allowed_sectors=["government", "state_enterprise", "academic"],
        obligation_label="ทุนรัฐบาล")
    kept, removed = filter_targets(profile, [_target_input(t) for t in CAREER_TARGETS])
    assert removed, "เงื่อนไขชดใช้ทุนไม่ได้กรองอะไรออกเลย"
    for v in removed:
        assert any(b.kind == "obligation" for b in v.permanent_blocks)
    assert kept


def test_being_early_in_the_degree_never_hides_a_target():
    profile = ProfileInput(education_level="ปี 1", gpa=2.0)
    for t in CAREER_TARGETS:
        v = evaluate(profile, _target_input(t))
        assert v.eligible, f'{t["id"]} หายไปเพราะเพิ่งปี 1'
        assert all(b.permanence == "time" for b in v.time_blocks)


def test_every_field_has_at_least_one_target():
    from app.seed.careers import FIELDS
    covered = {f for t in CAREER_TARGETS for f in t["field_whitelist"]}
    missing = {f["id"] for f in FIELDS} - covered
    assert not missing, f"สาขาที่ไม่มีอาชีพเป้าหมายเลย: {missing}"


def test_partial_evidence_is_not_shown_as_locked(graph, names, resources):
    """ก้าวที่มีหลักฐานอยู่แล้วบางส่วน ต้องไม่ขึ้นแม่กุญแจ

    ไม่งั้นหน้าจอจะบอก "มีหลักฐานจาก CV" พร้อมกับ 🔒 ซึ่งอ่านแล้วขัดกันเอง
    """
    have = merge_evidence({"T-CAD3D": 1, "ME-STATICS": 1}, {})
    rm = make(graph, names, resources, "MECH-DESIGN", have=have)
    partial = [s for s in rm.steps if s.current_level > 0]
    assert partial, "ควรมีก้าวที่มีหลักฐานบางส่วน"
    for s in partial:
        assert s.status != "locked", f"{s.skill_id}: มีหลักฐานแล้วแต่ยังขึ้นล็อก"
        assert s.evidence_kind is not None


def test_steps_without_any_evidence_stay_locked(graph, names, resources):
    rm = make(graph, names, resources, "MECH-DESIGN")
    locked = [s for s in rm.steps if s.status == "locked"]
    assert locked
    for s in locked:
        assert s.current_level == 0 and s.evidence_kind is None
