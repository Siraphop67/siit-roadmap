"""สร้าง roadmap — GAP · FRONTIER · RANK · PATH · RESOURCE_MATCH  (❌ ไม่ใช้ LLM)

ใช้กับทั้งสองฝั่ง หลังจากผู้ใช้ล็อกอาชีพเป้าหมายแล้ว

🔒 invariant ที่ยกมาจาก draft 1 และต้องเป็นจริงเสมอ
   `path[0]` ต้องเป็นตัวเดียวกับที่ RANK เลือก — เป็นจริงโดยโครงสร้าง
   เพราะ topo sort รับคะแนน RANK เป็น priority (ดู SkillGraph.topo_sort)

🔴 กลไก "ลำดับไม่ตายตัว" (จาก roadmap.sh)
   ทักษะที่ `order_strict = False` ไม่บล็อกก้าวอื่น — เช่น "อ่านเอกสารอังกฤษ"
   ทำเมื่อไหร่ก็ได้ ไม่ต้องรอให้เสร็จก่อนถึงจะไปก้าวถัดไป
   → ตอนคิดลำดับ ให้ตัดเส้นที่ออกจากทักษะกลุ่มนี้ทิ้ง

🔴 แยกหลักฐานสองชนิดตลอดทาง
   ทักษะที่มาจาก CV (`extracted`) กับที่ผู้ใช้กรอกเอง (`self_reported`)
   ถูกนับรวมในการคำนวณ แต่ **ติดป้ายแยกกันเสมอ** เพื่อให้หน้าจอบอกได้ว่าข้อไหนพิสูจน์ได้
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import settings
from app.engine.skill_graph import SkillGraph

EVIDENCE_EXTRACTED = "extracted"
EVIDENCE_SELF = "self_reported"
EVIDENCE_BOTH = "both"


@dataclass(frozen=True)
class Requirement:
    skill_id: str
    min_level: int
    importance: float = 1.0
    appears_in_n_postings: int = 0


@dataclass(frozen=True)
class Resource:
    id: str
    kind: str
    title: str
    provider: str
    est_hours: int
    cost_baht: int
    min_year: int
    proof_of_done: str
    reaches_level: int
    generated: bool = False


@dataclass
class Have:
    level: int
    kind: str  # extracted | self_reported | both


@dataclass
class StepOption:
    resource: Resource
    fits_time: bool = True
    fits_budget: bool = True
    fits_year: bool = True

    @property
    def fits_all(self) -> bool:
        return self.fits_time and self.fits_budget and self.fits_year

    @property
    def blocked_reason(self) -> str | None:
        if self.fits_all:
            return None
        parts = []
        if not self.fits_year:
            parts.append(f"ลงได้เมื่อถึงปี {self.resource.min_year}")
        if not self.fits_budget:
            parts.append(f"ค่าใช้จ่าย {self.resource.cost_baht:,} บาท เกินงบที่ระบุไว้")
        if not self.fits_time:
            parts.append(f"ใช้เวลาราว {self.resource.est_hours} ชั่วโมง มากกว่าที่มี")
        return " · ".join(parts)


@dataclass
class Step:
    skill_id: str
    order_no: int
    current_level: int
    target_level: int
    status: str    # current | in_progress | flexible | locked
    evidence_kind: str | None = None  # extracted | self_reported | both | None
    rank_score: float = 0.0
    unlock_count: int = 0
    importance: float = 0.0
    options: list[StepOption] = field(default_factory=list)

    @property
    def actionable(self) -> bool:
        return self.status in {"current", "flexible"}


@dataclass
class RoadmapResult:
    target_id: str
    steps: list[Step] = field(default_factory=list)
    total_steps: int = 0
    steps_done: int = 0
    coverage: float = 0.0
    edges: list[tuple[str, str]] = field(default_factory=list)  # ให้หน้าเว็บวาดกราฟได้

    @property
    def current_step(self) -> Step | None:
        return next((s for s in self.steps if s.status == "current"), None)


# ═══════════════════════ GAP ═══════════════════════


def merge_evidence(
    extracted: dict[str, int] | None,
    self_reported: dict[str, int] | None,
) -> dict[str, Have]:
    """รวมทักษะสองแหล่ง แต่ยังบอกได้ว่าแต่ละตัวมาจากไหน

    ถ้ามีทั้งสองแหล่ง ใช้ระดับที่สูงกว่า และติดป้ายว่า both
    """
    extracted, self_reported = extracted or {}, self_reported or {}
    out: dict[str, Have] = {}
    for sid, lv in extracted.items():
        out[sid] = Have(level=lv, kind=EVIDENCE_EXTRACTED)
    for sid, lv in self_reported.items():
        if sid in out:
            out[sid] = Have(level=max(out[sid].level, lv), kind=EVIDENCE_BOTH)
        else:
            out[sid] = Have(level=lv, kind=EVIDENCE_SELF)
    return out


def _is_met(skill_id: str, requirements: list[Requirement], have: dict[str, Have]) -> bool:
    got = have.get(skill_id)
    if not got or got.level <= 0:
        return False
    need = max((r.min_level for r in requirements if r.skill_id == skill_id), default=1)
    return got.level >= need


def todo_closure(
    graph: SkillGraph,
    requirements: list[Requirement],
    have: dict[str, Have],
) -> set[str]:
    """ทุกอย่างที่ยังต้องทำเพื่อไปถึงอาชีพนี้ รวม prerequisite ที่ปลายทางไม่ได้ขอตรง ๆ"""
    needed = {r.skill_id for r in requirements}
    closure = graph.transitive_prereqs(needed)
    return {s for s in closure if not _is_met(s, requirements, have)}


# ═══════════════════ FRONTIER + RANK ═══════════════════


def _blocking_prereqs(graph: SkillGraph, skill_id: str, flexible: set[str]) -> set[str]:
    """prerequisite ที่บล็อกจริง — ทักษะ "ทำเมื่อไหร่ก็ได้" ไม่บล็อกใคร"""
    return graph.prereqs(skill_id) - flexible


def frontier(
    graph: SkillGraph,
    todo: set[str],
    have: dict[str, Have],
    flexible: set[str],
) -> list[str]:
    """ทักษะที่ลงมือได้ตอนนี้ — prerequisite ที่บล็อกครบแล้ว"""
    return sorted(s for s in todo if not (_blocking_prereqs(graph, s, flexible) & todo))


def rank_steps(
    graph: SkillGraph,
    todo: set[str],
    requirements: list[Requirement],
    resources: dict[str, list[Resource]],
    hours_per_week: int | None,
) -> dict[str, float]:
    """ให้คะแนนทุกทักษะใน todo — ใช้เป็น priority ของการเรียงลำดับ

    score = w1·ปลดล็อกกี่ก้าว + w2·ความสำคัญต่ออาชีพ + w3·ปรากฏในประกาศงานบ่อยแค่ไหน
          − w4·|ชั่วโมงที่ต้องใช้ − ที่มี| − w5·(ไม่มีทางไปถึงเลย)
    """
    req_by_skill = {r.skill_id: r for r in requirements}
    scores: dict[str, float] = {}

    for sid in todo:
        req = req_by_skill.get(sid)
        unlock = len(graph.transitive_unlocks(sid, within=todo))
        opts = resources.get(sid, [])
        est = min((o.est_hours for o in opts), default=12)
        hours_gap = abs(est - hours_per_week * 4) if hours_per_week else 0.0

        scores[sid] = round(
            settings.rank_w_unlock * unlock
            + settings.rank_w_importance * (req.importance if req else 0.0)
            + settings.rank_w_frequency * (req.appears_in_n_postings if req else 0)
            - settings.rank_w_hours_fit * hours_gap
            - settings.rank_w_no_resource * (0 if opts else 1),
            4,
        )
    return scores


# ═══════════════════ RESOURCE MATCH ═══════════════════


def generated_project(skill_id: str, skill_name: str) -> Resource:
    """ทางเลือกสำรองเมื่อทักษะนี้ยังไม่มีทรัพยากรในคลัง

    🔴 ก้าวที่ไม่มีทางไปถึงเลย คือก้าวที่กดไม่ได้ — ระบบจึงต้องมีอย่างน้อยหนึ่งทางเสมอ
       แต่ต้องติดป้ายว่าเป็นของที่ระบบสร้างเอง ไม่ใช่วิชาหรือคอร์สที่มีอยู่จริง
    """
    return Resource(
        id=f"GEN-{skill_id}",
        kind="project",
        title=f"ทำโปรเจกต์เล็กที่แสดงว่า “{skill_name}” เกิดขึ้นจริง",
        provider="ทำเอง",
        est_hours=12,
        cost_baht=0,
        min_year=1,
        proof_of_done="บันทึกสิ่งที่ทำ ผลที่วัดได้ และสิ่งที่ลองแล้วไม่ได้ผล",
        reaches_level=2,
        generated=True,
    )


def match_resources(
    skill_id: str,
    skill_name: str,
    resources: dict[str, list[Resource]],
    hours_per_week: int | None,
    budget_baht: int | None,
    year: int | None,
) -> list[StepOption]:
    """ทางไปถึงทักษะนี้ทั้งหมด พร้อมบอกว่าอันไหนติดเงื่อนไขอะไร

    ไม่ตัดตัวเลือกที่ติดเงื่อนไขทิ้ง — แสดงพร้อมเหตุผล เหมือนที่ทำกับอาชีพที่ถูกกรองออก
    """
    opts = list(resources.get(skill_id, []))
    if not opts:
        opts = [generated_project(skill_id, skill_name)]

    weeks_budget = hours_per_week * 12 if hours_per_week else None  # หนึ่งเทอมราว 12 สัปดาห์
    out = [
        StepOption(
            resource=r,
            fits_time=(weeks_budget is None or r.est_hours <= weeks_budget),
            fits_budget=(budget_baht is None or r.cost_baht <= budget_baht),
            fits_year=(year is None or r.min_year <= year),
        )
        for r in opts
    ]
    out.sort(key=lambda o: (not o.fits_all, o.resource.cost_baht, o.resource.est_hours))
    return out


# ═══════════════════════ PATH ═══════════════════════


def build_roadmap(
    *,
    graph: SkillGraph,
    target_id: str,
    requirements: list[Requirement],
    have: dict[str, Have],
    resources: dict[str, list[Resource]],
    skill_names: dict[str, str],
    flexible_skills: set[str],
    hours_per_week: int | None = None,
    budget_baht: int | None = None,
    year: int | None = None,
) -> RoadmapResult:
    todo = todo_closure(graph, requirements, have)
    scores = rank_steps(graph, todo, requirements, resources, hours_per_week)

    # เรียงลำดับโดยตัดเส้นที่ออกจากทักษะ "ทำเมื่อไหร่ก็ได้" ทิ้ง
    blocking = SkillGraph(
        list(graph.nodes),
        [(a, b) for a, b in graph.edges if a not in flexible_skills],
    )
    ordered = blocking.topo_sort(todo, priority=scores)

    front = set(frontier(graph, todo, have, flexible_skills))
    req_by_skill = {r.skill_id: r for r in requirements}

    steps: list[Step] = []
    current_assigned = False
    for i, sid in enumerate(ordered, start=1):
        got = have.get(sid)
        current_level = got.level if got else 0
        req = req_by_skill.get(sid)

        # 🔴 ก้าวที่มีหลักฐานอยู่แล้วบางส่วน ต้องไม่ขึ้นเป็น "ล็อก"
        #    ไม่งั้นหน้าจอจะบอกว่า "มีหลักฐานจาก CV" พร้อมกับแม่กุญแจ ซึ่งอ่านแล้วขัดกันเอง
        if sid in flexible_skills:
            status = "flexible"
        elif sid in front and not current_assigned:
            status = "current"
            current_assigned = True
        elif current_level > 0:
            status = "in_progress"      # มีอยู่แล้วบางส่วน แต่ยังไม่ถึงระดับที่ต้องการ
        else:
            status = "locked"

        steps.append(Step(
            skill_id=sid,
            order_no=i,
            current_level=current_level,
            target_level=current_level + 1,
            status=status,
            evidence_kind=got.kind if got else None,
            rank_score=scores.get(sid, 0.0),
            unlock_count=len(graph.transitive_unlocks(sid, within=todo)),
            importance=req.importance if req else 0.0,
            options=match_resources(
                sid, skill_names.get(sid, sid), resources,
                hours_per_week, budget_baht, year),
        ))

    needed = {r.skill_id for r in requirements}
    full_closure = graph.transitive_prereqs(needed)
    met_reqs = sum(1 for r in requirements if _is_met(r.skill_id, requirements, have))

    return RoadmapResult(
        target_id=target_id,
        steps=steps,
        total_steps=len(steps),
        steps_done=len(full_closure) - len(todo),
        coverage=round(met_reqs / len(requirements), 3) if requirements else 0.0,
        edges=[(a, b) for a, b in graph.edges if a in todo and b in todo],
    )
