"""ท่อขั้นที่ 2 — แปลงประกาศงานจริงเป็น requirement  (ใช้ตัวสกัดเดียวกับที่อ่าน CV)

    python pipeline/2_extract_postings.py
    python pipeline/2_extract_postings.py --min-postings 1   # ตอนยังเก็บได้น้อย

เข้า:  data/postings/*.md   ประกาศงานที่ 🅴 เก็บด้วยมือ (ดู data/postings/README.md)
ออก:  out/posting_requirements.json

นี่คือตัวเชื่อมที่หายไประหว่าง "เก็บประกาศงานเสร็จ" กับ "ข้อมูลนั้นมีผลกับหน้าจอ"
ถ้าไม่รันขั้นนี้ ประกาศงานจะนอนอยู่ในตาราง job_posting โดยไม่มีอะไรอ่าน
และ `appears_in_n_postings` จะเป็น 0 ตลอด ซึ่งทำให้น้ำหนัก rank_w_frequency = 1.5
ในสูตรจัดลำดับก้าว (engine/roadmap.py) คูณศูนย์อยู่ทั้งหมด

🔴 ไม่เขียนทับ seed/careers.py
   docstring เดิมใน careers.py บอกว่าขั้นนี้จะเขียนทับไฟล์นั้น — เราไม่ทำ เพราะ
   ① เขียนทับซอร์สที่คนเขียนด้วยมือแล้วพังทีเดียวคือกู้คืนยาก
   ② ตัวสกัดจับได้เฉพาะคำที่เขียนตรงตัว requirement ที่จริงแต่ประกาศไม่ได้เขียนตรง ๆ
      จะหายไปหมดถ้าแทนที่ทั้งชุด
   → ขั้นนี้ออกเป็น JSON แล้ว loader เอาไป **ผสม** กับชุดที่ทีมเขียนไว้
     ของเดิมไม่ถูกลบ · ของใหม่ถูกเพิ่ม · ทุกแถวติดป้ายว่ามาจากไหน (`source`)

🛡 span guard ทำงานเหมือนตอนอ่าน CV
   ทักษะที่อ้างต้องชี้กลับไปที่ข้อความจริงในประกาศได้ ชี้ไม่ได้ = ทิ้ง
   ทำให้พูดบนเวทีได้ว่า "requirement ข้อนี้มาจากประโยคนี้ ในประกาศนี้" แล้วเปิดให้ดูได้จริง

⚠️ ตัวสกัดตอนนี้เป็นการจับคำสำคัญ ไม่ใช่ LLM
   ประกาศที่เขียนว่า "ทำให้สองระบบคุยกัน" จะไม่ถูกนับเป็น API
   ตัวเลขที่ออกมาจึงเป็น *ขอบล่าง* ของความจริงเสมอ — ไฟล์ผลลัพธ์บันทึกไว้ด้วย
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PIPELINE = Path(__file__).resolve().parent
REPO = PIPELINE.parent
OUT = PIPELINE / "out"
sys.path.insert(0, str(REPO / "backend"))

from app.config import settings                       # noqa: E402
from app.llm import get_extractor                     # noqa: E402
from app.seed.careers import CAREER_TARGETS           # noqa: E402
from app.seed.postings import load_all                # noqa: E402
from app.seed.skills import SKILLS                    # noqa: E402

# ทักษะที่ปรากฏในประกาศเดียวคือเสียงรบกวน ไม่ใช่ requirement ของอาชีพ
DEFAULT_MIN_POSTINGS = 2

TARGET_TH = {t["id"]: t["title_th"] for t in CAREER_TARGETS}
SKILL_TH = {s["id"]: s["name_th"] for s in SKILLS}
CURATED = {
    t["id"]: {skill_id for skill_id, _, _ in t["requirements"]}
    for t in CAREER_TARGETS
}


def aggregate(usable, extractor, min_postings: int, broken: int = 0) -> dict:
    """รวมผลสกัดจากทุกประกาศให้เป็น requirement รายอาชีพ

    แยกออกมาจาก main() เพื่อให้เทสต์เรียกได้โดยไม่ต้องมีไฟล์จริงในโฟลเดอร์
    """
    known_skills = {s["id"] for s in SKILLS}

    # target_id → skill_id → รายการหลักฐานจากแต่ละประกาศ
    hits: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    per_target_postings: dict[str, int] = defaultdict(int)
    dropped_by_guard = 0
    unknown_skill_spans = 0
    no_target: list[str] = []

    for p in usable:
        target_id = p.meta.get("target_id")
        if not target_id:
            no_target.append(p.id)
            continue
        per_target_postings[target_id] += 1

        spans = extractor.extract(p.body)
        seen_here: set[str] = set()
        for s in spans:
            if not s.verify(p.body):        # 🛡 ชี้กลับไม่ได้ = ทิ้ง เหมือนกติกาตอนอ่าน CV
                dropped_by_guard += 1
                continue
            if s.skill_id not in known_skills:
                unknown_skill_spans += 1
                continue
            if s.skill_id in seen_here:
                continue                     # 1 ประกาศนับให้ 1 ทักษะได้ครั้งเดียว
            seen_here.add(s.skill_id)
            hits[target_id][s.skill_id].append({
                "posting_id": p.id,
                "level": s.level,
                "confidence": round(s.confidence, 3),
                "span_text": s.span_text,
                "span_start": s.span_start,
                "span_end": s.span_end,
            })

    targets_out: dict[str, dict] = {}
    for target_id, n_postings in sorted(per_target_postings.items()):
        kept, dropped = [], []
        for skill_id, evidence in hits[target_id].items():
            n = len(evidence)
            levels = [e["level"] for e in evidence]
            row = {
                "skill_id": skill_id,
                "name_th": SKILL_TH.get(skill_id, skill_id),
                "appears_in_n_postings": n,
                # สัดส่วนของประกาศที่พูดถึงทักษะนี้ — อ่านออกทันทีว่า "7 ใน 9 ประกาศ"
                "share": round(n / n_postings, 3),
                # ใช้ค่ากลาง ไม่ใช่ค่าสูงสุด — ประกาศเดียวที่ขอระดับ 3 ไม่ควรลากทั้งอาชีพขึ้น
                "min_level": int(statistics.median_low(levels)),
                "levels": sorted(levels),
                "in_curated_set": skill_id in CURATED.get(target_id, set()),
                # 🔎 หลักฐานที่เปิดให้ดูได้บนเวที — ประโยคจริงจากประกาศจริง
                "example": max(evidence, key=lambda e: e["confidence"]),
            }
            (kept if n >= min_postings else dropped).append(row)

        kept.sort(key=lambda r: (-r["appears_in_n_postings"], r["skill_id"]))
        dropped.sort(key=lambda r: r["skill_id"])
        targets_out[target_id] = {
            "title_th": TARGET_TH.get(target_id, target_id),
            "posting_count": n_postings,
            "requirements": kept,
            "below_threshold": dropped,
            "curated_not_found_in_postings": sorted(
                CURATED.get(target_id, set()) - set(hits[target_id])
            ),
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "extractor": extractor.name,
        # 🔒 กติกาข้อ 5 — ไฟล์ผลลัพธ์ต้องบอกเองว่ามันถูกสร้างด้วยอะไร
        "extractor_is_real_llm": settings.llm_is_real,
        "caveat": (
            "ตัวสกัดจับได้เฉพาะคำที่เขียนตรงตัว ทักษะที่ประกาศเขียนอ้อม ๆ จะไม่ถูกนับ "
            "ตัวเลขในไฟล์นี้จึงเป็นขอบล่างของความจริง"
        ) if not settings.llm_is_real else "",
        "min_postings": min_postings,
        "postings_total": len(usable) + broken,
        "postings_usable": len(usable),
        "postings_broken": broken,
        "postings_without_target": no_target,
        "spans_dropped_by_guard": dropped_by_guard,
        "spans_unknown_skill": unknown_skill_spans,
        "targets": targets_out,
    }


def _approved_employer_postings() -> list:
    """ประกาศจากฟอร์มบริษัทที่ผ่านการอนุมัติแล้ว — อยู่ในฐานข้อมูล ไม่ใช่ในไฟล์

    ฐานข้อมูลอาจยังไม่มี (เครื่องที่ยังไม่เคยรัน backend) — กรณีนั้นถือว่าไม่มีประกาศจากบริษัท
    ไม่ใช่ข้อผิดพลาด ท่อยังต้องเดินต่อได้ด้วยไฟล์อย่างเดียว
    """
    try:
        from sqlalchemy import select

        from app.db import SessionLocal
        from app.models import JobPosting
        from app.seed.postings import from_db_rows

        with SessionLocal() as db:
            rows = db.scalars(
                select(JobPosting).where(
                    JobPosting.source == "employer",
                    JobPosting.status == "approved",
                )
            ).all()
            return from_db_rows(rows)
    except Exception as exc:                       # noqa: BLE001
        print(f"[ท่อ] อ่านประกาศจากบริษัทไม่ได้ ({exc}) — ใช้เฉพาะไฟล์")
        return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-postings", type=int, default=DEFAULT_MIN_POSTINGS)
    args = ap.parse_args()

    from_files = load_all(target_ids=set(TARGET_TH))
    usable = [p for p in from_files if p.ok]
    broken = len(from_files) - len(usable)      # นับจากไฟล์เท่านั้น ต้องคิดก่อนรวมของบริษัท

    # 🔒 ประกาศที่บริษัทส่งเข้ามาเอง นับเฉพาะที่ผ่านการอนุมัติแล้วเท่านั้น
    #    ถ้านับ pending ด้วย ใครก็ดัน requirement ของอาชีพได้โดยไม่ต้องผ่านใคร
    from_employers = _approved_employer_postings()
    if from_employers:
        print(f"[ท่อ] รวมประกาศจากบริษัทที่อนุมัติแล้ว {len(from_employers)} อัน")
        usable += from_employers

    if not usable:
        print(f"""
ยังไม่มีประกาศงานที่ใช้ได้ใน {REPO / 'data' / 'postings'}

  เก็บยังไง → data/postings/README.md
  ตรวจไฟล์ → make check-postings

ยังไม่เขียนไฟล์ผลลัพธ์ เพราะไฟล์ผลลัพธ์เปล่าจะกลบของเดิมโดยไม่ได้อะไรกลับมา
""")
        return 0

    result = aggregate(usable, get_extractor(), args.min_postings, broken=broken)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "posting_requirements.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    _report(result, args.min_postings)
    print(f"\nเขียนแล้ว → {path}")
    print("รัน make backend อีกครั้ง แล้ว requirement จะอัปเดตตามไฟล์นี้")
    return 0


def _report(result: dict, min_postings: int) -> None:
    print(f"\nตัวสกัด: {result['extractor']}"
          + ("" if result["extractor_is_real_llm"] else "  (จับคำสำคัญ ไม่ใช่ LLM)"))
    print(f"ประกาศงาน: ใช้ได้ {result['postings_usable']} · ผิดรูปแบบ {result['postings_broken']}"
          f" · ไม่ได้ระบุอาชีพ {len(result['postings_without_target'])}")
    if result["spans_dropped_by_guard"]:
        print(f"🛡 span ที่ชี้กลับไม่ได้ ถูกทิ้ง {result['spans_dropped_by_guard']} อัน")

    if result["postings_without_target"]:
        print("\n⚠️  ประกาศที่ยังไม่ได้ระบุ target_id จะไม่ถูกนับให้อาชีพไหนเลย:")
        for pid in result["postings_without_target"][:5]:
            print(f"     {pid}")

    print(f"\n{'อาชีพ':34} {'ประกาศ':>6} {'req ที่ยืนยันได้':>16} {'ของใหม่':>8}")
    for tid, t in result["targets"].items():
        new = sum(1 for r in t["requirements"] if not r["in_curated_set"])
        print(f"  {t['title_th']:32} {t['posting_count']:>6} {len(t['requirements']):>16} {new:>8}")

    missing = {
        tid: t["curated_not_found_in_postings"]
        for tid, t in result["targets"].items()
        if t["curated_not_found_in_postings"]
    }
    if missing:
        print("\n🔴 requirement ที่ทีมเขียนไว้ แต่ไม่พบในประกาศจริงเลย")
        print("   (ไม่ได้ถูกลบ — แต่ควรถามตัวเองว่ายังควรอยู่ไหม หรือตัวสกัดแค่จับไม่ได้)")
        for tid, skills in list(missing.items())[:4]:
            names = ", ".join(SKILL_TH.get(s, s) for s in skills[:6])
            print(f"     {TARGET_TH.get(tid, tid)}: {names}")

    thin = [t for t in result["targets"].values() if t["posting_count"] < min_postings + 2]
    if thin:
        print(f"\n⚠️  อาชีพที่ยังมีประกาศน้อยเกินจะสรุปได้ ({len(thin)} อาชีพ) — เก็บเพิ่มอีก")


if __name__ == "__main__":
    raise SystemExit(main())
