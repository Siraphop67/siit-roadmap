"""MATCH_TARGET — จับคู่ผู้ใช้กับอาชีพเป้าหมาย (❌ ไม่ใช้ LLM · กำหนดผลได้)

ใช้กับฝั่ง "ยังไม่รู้ว่าอยากเป็นอะไร" · รวมสัญญาณ 4 ทาง

  ① กิจกรรมที่อยากทำ   จากแบบทดสอบ 41 มิติ (O*NET Work Activities)  ← แกนหลัก
  ② ทักษะที่มีหลักฐาน   จาก CV ที่ผู้ใช้ยืนยันแล้ว                    ← แรงที่สุด เป็นข้อมูลของเราเอง
  ③ ทักษะที่กรอกเอง     ผู้ใช้บอกว่าตัวเองมี                          ← กลาง ไม่มีหลักฐาน
  ④ ค่านิยม/บุคลิก      Work Values + Work Styles                    ← เบา ใช้ตัดสินตอนคะแนนเสมอ

🔴 ทำไมต้อง "หักค่ากลาง" ก่อนเทียบ
   อาชีพบางอาชีพให้คะแนนความสำคัญสูงเกือบทุกกิจกรรม (ระดับงานสูง) บางอาชีพต่ำเกือบทุกอัน
   ถ้าเทียบดิบ ๆ ผลจะสะท้อน "ระดับความเข้มข้นของงาน" ไม่ใช่ "ลักษณะงาน"
   → หัก mean ของแต่ละอาชีพออกก่อน เหลือแต่ "รูปทรง" ซึ่งเป็นสิ่งที่แยกอาชีพออกจากกันจริง

🔒 กติกาเหล็ก
   · ทุกอาชีพที่คืนออกไปต้องมี traced_to ไม่ว่างเสมอ
   · ถ้าอันดับ 1 ห่างจากอันดับ 2 ไม่พอ ต้องคืน separated=False แล้วให้ถามต่อ
     ห้ามยัดอันดับให้ดูมั่นใจ — นี่คือสิ่งที่ทำให้แบบทดสอบทั่วไป "แนะนำให้เป็นพยาบาลทุกคน"
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# น้ำหนักของแต่ละสัญญาณ
# ⚠️ ตั้งจากเหตุผลเชิงออกแบบ ยังไม่ได้จูนกับผู้ใช้จริง — ต้องบอกตามตรงเมื่อรายงานผล
W_ACTIVITY = 1.0
W_EXTRACTED = 1.4      # มีหลักฐานรองรับ จึงหนักกว่าที่ผู้ใช้บอกเอง
W_SELF_REPORTED = 0.6
W_VALUES = 0.3

# อันดับ 1 ต้องนำอันดับ 2 อย่างน้อยเท่านี้ (สัดส่วนของช่วงคะแนนทั้งหมด) ถึงจะถือว่า "แยกออกแล้ว"
SEPARATION_MARGIN = 0.12


@dataclass(frozen=True)
class ActivityAnswer:
    activity_id: str
    # -2 ไม่อยากทำเลย · -1 ไม่ค่อยอยากทำ · 0 เฉย ๆ · +1 ค่อนข้างอยากทำ · +2 อยากทำมาก
    #
    # 🔴 ความแรงมีความหมายจริง ไม่ได้ใส่ไว้ให้สวย — `_activity_score` ใช้สหสัมพันธ์
    #    ซึ่งไม่สนสเกลรวม แต่สนว่าข้อไหนแรงกว่าข้อไหน · ตอบ ±1 ล้วนทำให้ทุกข้อ
    #    น้ำหนักเท่ากันหมด แล้วอาชีพที่มีลายเซ็นใกล้กันจะแยกไม่ออก (DECISIONS D15)
    value: int


@dataclass(frozen=True)
class TraceEntry:
    kind: str            # activity | extracted_skill | self_reported_skill | values
    ref_id: str
    label: str
    contribution: float
    # ทำไมข้อนี้ถึงดันคะแนนขึ้นหรือลง — ใช้เขียนคำอธิบายบนหน้าจอให้อ่านแล้วเข้าใจ
    # wants_and_does    คุณอยากทำ และงานนี้ได้ทำเยอะ
    # avoids_and_spared คุณไม่อยากทำ และงานนี้แทบไม่ต้องทำ
    # wants_but_absent  คุณอยากทำ แต่งานนี้แทบไม่ได้ทำ
    # unwanted_but_core คุณไม่อยากทำ แต่งานนี้ต้องทำเยอะ
    direction: str = ""

    @property
    def reads_as_reason(self) -> bool:
        """ข้อที่เอาไปเขียนเป็นเหตุผลบนหน้าจอได้โดยไม่ทำให้คนงง"""
        return self.direction in {"wants_and_does", "unwanted_but_core"}


@dataclass
class TargetScore:
    target_id: str
    score: float = 0.0
    score_activity: float = 0.0
    score_extracted: float = 0.0
    score_self_reported: float = 0.0
    score_values: float = 0.0
    rank_no: int = 0
    is_unconsidered: bool = False
    traced_to: list[TraceEntry] = field(default_factory=list)

    @property
    def supporting(self) -> list[TraceEntry]:
        return sorted([t for t in self.traced_to if t.contribution > 0],
                      key=lambda t: -t.contribution)

    @property
    def opposing(self) -> list[TraceEntry]:
        return sorted([t for t in self.traced_to if t.contribution < 0],
                      key=lambda t: t.contribution)

    @property
    def headline_reasons(self) -> list[TraceEntry]:
        """เหตุผลที่เอาขึ้นหน้าจอได้ — ตัดข้อที่จริงทางคณิตศาสตร์แต่อ่านแล้วงงออก

        "เสนองานนี้เพราะคุณไม่อยากซ่อมเครื่องจักร" เป็นข้อที่ดันคะแนนขึ้นจริง
        แต่ไม่ใช่ประโยคที่ใช้อธิบายให้คนฟังแล้วเชื่อ
        """
        return [t for t in self.supporting if t.reads_as_reason][:4]


@dataclass
class MatchOutcome:
    ranked: list[TargetScore]
    separated: bool
    separation_reason: str
    answered_count: int
    unconsidered_id: str | None = None


def _centroid(profiles: dict[str, dict[str, float]]) -> dict[str, float]:
    """ค่าเฉลี่ยของทุกอาชีพในรายการ — ใช้หักออกเพื่อให้เหลือแต่ลายเซ็นของแต่ละอาชีพ"""
    if not profiles:
        return {}
    keys: set[str] = set()
    for p in profiles.values():
        keys |= set(p)
    return {
        k: sum(p.get(k, 0.0) for p in profiles.values()) / len(profiles)
        for k in keys
    }


def centered_profile(profile: dict[str, float]) -> dict[str, float]:
    """หักค่ากลางของอาชีพนั้นออก เหลือแต่รูปทรงของงาน"""
    if not profile:
        return {}
    mean = sum(profile.values()) / len(profile)
    return {k: v - mean for k, v in profile.items()}


def signature(profile: dict[str, float], centroid: dict[str, float]) -> dict[str, float]:
    """สิ่งที่ทำให้อาชีพนี้ *ต่าง* จากอาชีพอื่นในรายการ

    🔴 ทำไมต้องหักค่าเฉลี่ยของทุกอาชีพออก
       งานวิศวกรรมทุกสายมีรูปทรงร่วมกันเยอะมาก (ตัดสินใจ · แก้ปัญหา · ใช้คอมพิวเตอร์)
       ถ้าเทียบกับโปรไฟล์ดิบ ทุกอาชีพจะได้คะแนนกอง ๆ กันที่ 0.9+ จนแยกไม่ออก
       หักค่าเฉลี่ยออกแล้วเหลือเฉพาะ "ลายเซ็น" ของแต่ละอาชีพ คะแนนถึงจะกระจาย
    """
    return {k: v - centroid.get(k, 0.0) for k, v in profile.items()}


def _activity_score(
    answers: list[ActivityAnswer],
    profile: dict[str, float],
    centroid: dict[str, float],
    labels: dict[str, str],
) -> tuple[float, list[TraceEntry]]:
    """สหสัมพันธ์ระหว่างคำตอบของผู้ใช้กับลักษณะงานของอาชีพ (เฉพาะข้อที่ตอบแล้ว)

    🔴 ให้คะแนนด้วย "โปรไฟล์ดิบ" ไม่ใช่ลายเซ็นที่หักค่าเฉลี่ยแล้ว — วัดมาแล้ว

       น้ำหนักลายเซ็น    เทสต์กู้คืน   ช่องว่างอันดับ 1-2
              0.0          8/8            0.035
              0.2          5/8            0.049
              1.0          5/8            0.092

       หักค่าเฉลี่ยของทุกอาชีพออกทำให้ช่องว่างกว้างขึ้นก็จริง แต่ทิ้งข้อมูลที่
       อาชีพกลาง ๆ (หุ่นยนต์ · กระบวนการผลิต · การผลิต) ใช้แยกตัวเอง จนกู้คืนไม่ได้
       → ให้คะแนนด้วยโปรไฟล์ดิบ แล้วใช้ลายเซ็นเฉพาะตอนเลือกคำอธิบายว่าอะไรเด่นของอาชีพนี้

    🔴 หักค่ากลาง "บนเฉพาะข้อที่ตอบ" ไม่ใช่บนทั้ง 41 มิติ
       ไม่งั้นจะเหลือค่าคงที่ติดมา ซึ่งเอนเข้าหาอาชีพที่ให้ความสำคัญสูงแทบทุกกิจกรรม
    """
    sig = signature(profile, centroid)
    answered = [a for a in answers if a.activity_id in profile and a.value != 0]
    if len(answered) < 2:
        return 0.0, []

    xs = [float(a.value) for a in answered]
    ys = [profile[a.activity_id] for a in answered]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]

    sx = math.sqrt(sum(d * d for d in dx))
    sy = math.sqrt(sum(d * d for d in dy))
    if sx == 0 or sy == 0:          # ตอบเหมือนกันหมด หรืออาชีพนี้ไม่มีลายเซ็น
        return 0.0, []

    score = sum(a * b for a, b in zip(dx, dy)) / (sx * sy)

    traces = []
    for a, dxi, dyi in zip(answered, dx, dy):
        # "เด่น" วัดจากลายเซ็น — งานนี้ทำกิจกรรมนี้มากกว่าอาชีพอื่นในรายการ
        # ใช้เฉพาะตอนเขียนคำอธิบาย ไม่ได้เอาไปคิดคะแนน
        core = sig.get(a.activity_id, 0.0) > 0
        wants = a.value > 0
        traces.append(TraceEntry(
            kind="activity",
            ref_id=a.activity_id,
            label=labels.get(a.activity_id, a.activity_id),
            contribution=round(dxi * dyi / (sx * sy), 4),
            direction=("wants_and_does" if wants and core
                       else "avoids_and_spared" if not wants and not core
                       else "wants_but_absent" if wants and not core
                       else "unwanted_but_core"),
        ))
    traces.sort(key=lambda t: -abs(t.contribution))
    return score, traces[:8]


def _skill_score(
    have: dict[str, int],
    requirements: list[tuple[str, int, float]],
    labels: dict[str, str],
    kind: str,
) -> tuple[float, list[TraceEntry]]:
    """สัดส่วนความต้องการที่ทักษะชุดนี้ครอบคลุม ถ่วงด้วยความสำคัญ"""
    if not requirements:
        return 0.0, []
    total_w = sum(w for _, _, w in requirements) or 1.0
    got, traces = 0.0, []
    for skill_id, min_level, weight in requirements:
        level = have.get(skill_id, 0)
        if level <= 0:
            continue
        ratio = min(1.0, level / min_level)
        got += weight * ratio
        traces.append(TraceEntry(
            kind=kind, ref_id=skill_id,
            label=labels.get(skill_id, skill_id),
            contribution=round(weight * ratio / total_w, 4),
        ))
    traces.sort(key=lambda t: -t.contribution)
    return got / total_w, traces[:5]


def match_targets(
    *,
    answers: list[ActivityAnswer],
    target_profiles: dict[str, dict[str, float]],
    requirements: dict[str, list[tuple[str, int, float]]],
    extracted_skills: dict[str, int] | None = None,
    self_reported_skills: dict[str, int] | None = None,
    activity_labels: dict[str, str] | None = None,
    skill_labels: dict[str, str] | None = None,
    eligible_ids: set[str] | None = None,
    user_field: str | None = None,
    target_fields: dict[str, list[str]] | None = None,
) -> MatchOutcome:
    extracted_skills = extracted_skills or {}
    self_reported_skills = self_reported_skills or {}
    activity_labels = activity_labels or {}
    skill_labels = skill_labels or {}
    target_fields = target_fields or {}

    pool = {
        tid: prof for tid, prof in target_profiles.items()
        if prof and (eligible_ids is None or tid in eligible_ids)
    }
    centroid = _centroid(pool)

    scores: list[TargetScore] = []
    for target_id, profile in pool.items():
        ts = TargetScore(target_id=target_id)
        reqs = requirements.get(target_id, [])

        ts.score_activity, act_tr = _activity_score(answers, profile, centroid, activity_labels)
        ts.score_extracted, ext_tr = _skill_score(
            extracted_skills, reqs, skill_labels, "extracted_skill")
        ts.score_self_reported, self_tr = _skill_score(
            self_reported_skills, reqs, skill_labels, "self_reported_skill")

        ts.score = (
            W_ACTIVITY * ts.score_activity
            + W_EXTRACTED * ts.score_extracted
            + W_SELF_REPORTED * ts.score_self_reported
            + W_VALUES * ts.score_values
        )
        ts.traced_to = act_tr + ext_tr + self_tr
        scores.append(ts)

    # 🔒 ย้อนที่มาไม่ได้ = ไม่แสดง
    scores = [s for s in scores if s.traced_to]
    scores.sort(key=lambda s: (-s.score, s.target_id))
    for i, s in enumerate(scores, start=1):
        s.rank_no = i

    separated, reason = _check_separation(scores)

    unconsidered = _pick_unconsidered(scores, user_field, target_fields)
    if unconsidered:
        unconsidered.is_unconsidered = True

    return MatchOutcome(
        ranked=scores,
        separated=separated,
        separation_reason=reason,
        answered_count=sum(1 for a in answers if a.value != 0),
        unconsidered_id=unconsidered.target_id if unconsidered else None,
    )


def _check_separation(scores: list[TargetScore]) -> tuple[bool, str]:
    """อันดับ 1 นำอันดับ 2 พอจะสรุปได้หรือยัง"""
    if len(scores) < 2:
        return False, "ยังมีอาชีพให้เทียบไม่พอ"
    span = scores[0].score - scores[-1].score
    if span <= 0:
        return False, "คะแนนทุกอาชีพเท่ากันหมด — ยังแยกไม่ออก"
    gap = scores[0].score - scores[1].score
    if gap / span >= SEPARATION_MARGIN:
        return True, ""
    return False, (
        f"ตอนนี้ “{scores[0].target_id}” กับ “{scores[1].target_id}” ยังแยกกันไม่ชัด"
    )


def _pick_unconsidered(
    scores: list[TargetScore],
    user_field: str | None,
    target_fields: dict[str, list[str]],
) -> TargetScore | None:
    """อาชีพที่คะแนนดีแต่ผู้ใช้ไม่น่าเคยพิจารณา

    เกณฑ์: อยู่ใน 5 อันดับแรก แต่ไม่ได้อยู่ในสาขาที่ผู้ใช้เรียน
    (ถ้ายังไม่ได้เลือกสาขา ใช้อันดับ 3 ขึ้นไปแทน เพราะอันดับ 1–2 เขาเห็นอยู่แล้ว)
    """
    top = scores[:5]
    if user_field:
        for s in top:
            if user_field not in target_fields.get(s.target_id, []):
                return s
        return None
    return top[2] if len(top) >= 3 else None


def next_best_item(
    answered_ids: set[str],
    target_profiles: dict[str, dict[str, float]],
    top_two: tuple[str, str],
) -> str | None:
    """NEXT_ITEM — เลือกข้อถัดไปที่แยกอันดับ 1 กับ 2 ได้ดีที่สุด

    ทำให้แบบทดสอบสั้นลงและทุกข้อรู้สึกมีเหตุผล แทนที่จะไล่ถามเรียงไปเรื่อย
    """
    a, b = top_two
    ca, cb = centered_profile(target_profiles.get(a, {})), centered_profile(target_profiles.get(b, {}))
    candidates = [
        (abs(ca.get(k, 0.0) - cb.get(k, 0.0)), k)
        for k in set(ca) | set(cb)
        if k not in answered_ids
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][1]
