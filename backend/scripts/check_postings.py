"""ตรวจว่าประกาศงานใน data/postings/ กรอกถูกรูปแบบหรือยัง

    make check-postings

สั่งได้บ่อยเท่าที่ต้องการ · ไม่ต้องเปิด backend · ไม่แตะฐานข้อมูล

ทำไมต้องมี: คนเก็บประกาศงานไม่ใช่โปรแกรมเมอร์ และไม่ควรต้องรอให้ใครมารันให้
เพื่อจะรู้ว่าไฟล์ที่กรอกไว้ 30 อันใช้ได้หรือเปล่า
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

# ให้รันได้จากที่ไหนก็ได้ — คนเก็บประกาศงานไม่ควรต้องรู้เรื่อง PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.seed.careers import CAREER_TARGETS, SECTORS  # noqa: E402
from app.seed.postings import EMPLOYMENT_TYPES, POSTINGS_DIR, load_all  # noqa: E402

TARGET_TH = {t["id"]: t["title_th"] for t in CAREER_TARGETS}
GOAL = 30           # เป้าขั้นต่ำตาม docs/TEAM.md §3 🅴
PER_TARGET = 4      # เป้าคร่าว ๆ ต่ออาชีพ


def main() -> int:
    postings = load_all(target_ids=set(TARGET_TH))

    if not postings:
        print(f"""
ยังไม่มีประกาศงานสักอันใน {POSTINGS_DIR}

เริ่มเก็บอันแรก:
    cp data/postings/_TEMPLATE.md data/postings/2026-08-20-ชื่อองค์กร-ตำแหน่ง.md

อ่านวิธีเก็บที่ data/postings/README.md
""")
        return 0

    ok = [p for p in postings if p.ok]
    bad = [p for p in postings if not p.ok]

    for p in postings:
        if p.errors:
            print(f"\n❌ {p.path.name}")
            for e in p.errors:
                print(f"     {e}")
        elif p.warnings:
            print(f"\n⚠️  {p.path.name}")
        for w in p.warnings:
            print(f"     · {w}")

    print(f"\n{'─' * 62}")
    print(f"ใช้ได้ {len(ok)} · ต้องแก้ {len(bad)} · รวม {len(postings)} ไฟล์")

    if len(ok) < GOAL:
        print(f"เป้าคือ {GOAL}–50 ประกาศ — ยังขาดอีก {GOAL - len(ok)} อัน")

    # ── กระจายครบไหม ──
    by_sector = Counter(p.meta.get("sector") for p in ok)
    by_type = Counter(p.meta.get("employment_type") for p in ok)
    by_target = Counter(p.meta.get("target_id") for p in ok if p.meta.get("target_id"))

    print("\nกระจายตามภาคส่วน")
    for code, label in SECTORS.items():
        n = by_sector.get(code, 0)
        print(f"  {'✓' if n else '·'} {label:36} {n}")
    if not any(by_sector.get(c) for c in ("government", "state_enterprise", "academic")):
        print("  🔴 ยังไม่มีงานฝั่งรัฐ/รัฐวิสาหกิจ/มหาวิทยาลัยเลย")
        print("     จุดสาธิตเรื่องเงื่อนไขทุนต้องมีงานฝั่งนั้นให้ชี้จริง ๆ")

    print("\nกระจายตามประเภทการจ้าง")
    for code, label in EMPLOYMENT_TYPES.items():
        print(f"  {'✓' if by_type.get(code) else '·'} {label:36} {by_type.get(code, 0)}")

    print(f"\nกระจายตามอาชีพ (เป้าอาชีพละ {PER_TARGET}–6)")
    for tid, title in TARGET_TH.items():
        n = by_target.get(tid, 0)
        mark = "✓" if n >= PER_TARGET else ("·" if n else "🔴")
        print(f"  {mark} {title:36} {n}")

    unassigned = sum(1 for p in ok if not p.meta.get("target_id"))
    if unassigned:
        print(f"\n  ยังไม่ได้ระบุ target_id อีก {unassigned} อัน — ประกาศพวกนี้ยังไม่ถูกนับให้อาชีพไหน")

    print()
    if bad:
        print("แก้ไฟล์ที่ ❌ แล้วสั่งใหม่ได้เลย · วิธีกรอกอยู่ที่ data/postings/README.md")
        return 1
    print("✅ ทุกไฟล์ใช้ได้ — รัน make backend แล้วข้อมูลจะเข้าระบบเอง")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
