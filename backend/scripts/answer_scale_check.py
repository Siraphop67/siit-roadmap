"""วัดว่าสเกลคำตอบกี่ระดับแยกอาชีพได้ดีกว่ากัน — หลักฐานของ DECISIONS D15

    make answer-scale

จำลองผู้ใช้ที่ "ควรได้อาชีพ X" แล้วให้เดินแบบทดสอบตามลำดับจริงที่ `/discover/next` ใช้
(`next_best_item` เลือกข้อถัดไปจากอันดับ 1 กับ 2 ปัจจุบัน) แล้ววัดสามอย่าง:

  · กู้คืนได้ไหม   อันดับ 1 ตรงกับอาชีพที่จำลองไว้
  · กี่ข้อถึงจบ    ยิ่งน้อยยิ่งดี คนเลิกกลางคันน้อยลง
  · ช่องว่าง 1-2   ยิ่งกว้าง `separated` ยิ่งเชื่อได้

⚠️ นี่คือการวัด *การสูญเสียข้อมูลจากการหยาบของสเกล* ไม่ใช่พฤติกรรมมนุษย์จริง
   ความชอบของผู้ใช้จำลองถูกตั้งให้เท่ากับลายเซ็นของอาชีพนั้นพอดี ซึ่งคนจริงไม่เป็นแบบนั้น
   ตัวเลขที่ได้จึงเป็นขอบบน ไม่ใช่ค่าที่จะเจอกับผู้ใช้จริง — แต่เทียบสองสเกลกันได้
   เพราะทั้งคู่เจอสมมติฐานเดียวกัน
"""

from __future__ import annotations

import os
import random
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select              # noqa: E402
from sqlalchemy.orm import sessionmaker                    # noqa: E402

from app.engine.match_target import (                      # noqa: E402
    ActivityAnswer,
    match_targets,
    next_best_item,
)
from app.models import (                                   # noqa: E402
    CareerTarget,
    TargetActivityProfile,
    TargetRequirement,
    WorkActivity,
)
from app.seed.loader import create_all, seed               # noqa: E402

MIN_ITEMS, MAX_ITEMS = 12, 24
SEEDS = 20
# เกินเท่านี้ (หน่วยเป็นส่วนเบี่ยงเบนมาตรฐาน) ถือว่า "รู้สึกเฉย ๆ" — เท่ากันทั้งสองสเกล
# เพื่อให้ต่างกันแค่เรื่องความละเอียด ไม่ใช่เรื่องว่าใครทิ้งข้อมากกว่ากัน
DEADBAND = 0.35
STRONG = 1.0


def load():
    engine = create_engine(f"sqlite:///{os.path.join(tempfile.mkdtemp(), 'scale.db')}")
    create_all(engine)
    with sessionmaker(bind=engine)() as db:
        seed(db)
        profiles: dict[str, dict[str, float]] = {}
        for row in db.scalars(select(TargetActivityProfile)).all():
            profiles.setdefault(row.target_id, {})[row.activity_id] = row.importance
        labels = {a.id: a.display_name for a in db.scalars(select(WorkActivity)).all()}
        reqs: dict[str, list[tuple[str, int, float]]] = {}
        for r in db.scalars(select(TargetRequirement)).all():
            reqs.setdefault(r.target_id, []).append((r.skill_id, r.min_level, r.importance))
        targets = db.scalars(select(CareerTarget)).all()
        fields = {t.id: t.field_whitelist for t in targets}
        names = {t.id: t.title_th for t in targets}
    return profiles, labels, reqs, fields, names


def true_preference(profile: dict[str, float]) -> dict[str, float]:
    """ความชอบจริงของผู้ใช้จำลอง = กิจกรรมนั้นสำคัญกว่าค่าเฉลี่ยของอาชีพนั้นแค่ไหน"""
    values = list(profile.values())
    mean = statistics.fmean(values)
    sd = statistics.pstdev(values) or 1.0
    return {k: (v - mean) / sd for k, v in profile.items()}


def quantize(z: float, levels: int) -> int:
    if abs(z) < DEADBAND:
        return 0
    if levels == 3:
        return 1 if z > 0 else -1
    if z >= STRONG:
        return 2
    if z > 0:
        return 1
    return -1 if z > -STRONG else -2


def _widest_spread(profiles, answered: set[str]) -> str | None:
    values: dict[str, list[float]] = {}
    for profile in profiles.values():
        for activity_id, v in profile.items():
            if activity_id not in answered:
                values.setdefault(activity_id, []).append(v)
    if not values:
        return None
    return sorted(values.items(), key=lambda kv: (-(max(kv[1]) - min(kv[1])), kv[0]))[0][0]


def run_one(truth: str, levels: int, noise: float, rng: random.Random, data) -> dict:
    profiles, labels, reqs, fields, _ = data
    prefs = true_preference(profiles[truth])
    answers: list[ActivityAnswer] = []
    answered: set[str] = set()

    def match() -> object:
        return match_targets(
            answers=answers, target_profiles=profiles, requirements=reqs,
            extracted_skills={}, self_reported_skills={},
            activity_labels=labels, skill_labels={},
            user_field=None, target_fields=fields,
        )

    for _ in range(MAX_ITEMS):
        outcome = match()
        if outcome.separated and len(answers) >= MIN_ITEMS:
            break
        activity_id = None
        if len(outcome.ranked) >= 2:
            activity_id = next_best_item(
                answered, profiles,
                (outcome.ranked[0].target_id, outcome.ranked[1].target_id))
        if activity_id is None or activity_id in answered:
            activity_id = _widest_spread(profiles, answered)
        if activity_id is None:
            break
        z = prefs.get(activity_id, 0.0) + rng.gauss(0, noise)
        answers.append(ActivityAnswer(activity_id=activity_id, value=quantize(z, levels)))
        answered.add(activity_id)

    outcome = match()
    return {
        "recovered": bool(outcome.ranked) and outcome.ranked[0].target_id == truth,
        "items": len(answers),
        "separated": outcome.separated,
        "gap": (outcome.ranked[0].score - outcome.ranked[1].score
                if len(outcome.ranked) >= 2 else 0.0),
    }


def main() -> None:
    data = load()
    profiles, _, _, _, names = data
    print(f"อาชีพที่นำมาเทียบ {len(profiles)} · กิจกรรม "
          f"{len(next(iter(profiles.values())))} มิติ · {SEEDS} seed ต่อช่อง\n")

    for noise in (0.0, 0.4, 0.8):
        print(f"── สัญญาณรบกวน sd={noise} " + "─" * 42)
        for levels in (3, 5):
            rows = [
                run_one(truth, levels, noise, random.Random(s), data)
                for s in range(SEEDS) for truth in profiles
            ]
            n = len(rows)
            print(f"  {levels} ระดับ: กู้คืน {sum(r['recovered'] for r in rows)}/{n}"
                  f" ({sum(r['recovered'] for r in rows) / n:.0%})"
                  f" · แยกออก {sum(r['separated'] for r in rows) / n:.0%}"
                  f" · ข้อเฉลี่ย {statistics.fmean(r['items'] for r in rows):.1f}"
                  f" · ช่องว่าง {statistics.fmean(r['gap'] for r in rows):.3f}")
        print()

    print("── ราย 8 อาชีพ ที่ noise=0.4 " + "─" * 34)
    for truth in profiles:
        cells = []
        for levels in (3, 5):
            rows = [run_one(truth, levels, 0.4, random.Random(s), data) for s in range(SEEDS)]
            cells.append(f"{levels} ระดับ {sum(r['recovered'] for r in rows):2d}/{SEEDS}"
                         f" ({statistics.fmean(r['items'] for r in rows):4.1f} ข้อ)")
        print(f"  {names[truth][:26]:<26} · " + " · ".join(cells))


if __name__ == "__main__":
    main()
