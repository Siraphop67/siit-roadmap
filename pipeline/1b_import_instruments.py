"""ท่อขั้นที่ 1b — นำเข้าเครื่องมือวัดจาก O*NET  (❌ ไม่ใช้ LLM · ไม่ต้องมี API key)

    python pipeline/1b_import_instruments.py

ออก:
  out/work_activities.json          41 กิจกรรม + คำอธิบาย + หมวดใหญ่ 4 หมวด
  out/target_activity_profiles.json โปรไฟล์กิจกรรมของ 8 อาชีพเป้าหมาย (ใช้จับคู่)
  out/work_values.json              ค่านิยม 6 ด้าน + โปรไฟล์ของ 8 อาชีพ
  out/work_styles.json              บุคลิกการทำงาน 16 ด้าน + โปรไฟล์ของ 8 อาชีพ
  out/illustrative_activities.json  ตัวอย่างกิจกรรมรูปธรรมจาก O*NET (ใช้เป็นวัตถุดิบเขียนข้อคำถาม)
  out/discrimination.json           🔴 รายงานว่าเครื่องมือแต่ละตัวแยก 8 อาชีพออกจากกันได้แค่ไหน

🔴 ทำไมต้องมี discrimination.json
   เธรด r/findapath บ่นว่าแบบทดสอบอาชีพ "แนะนำให้เป็นพยาบาลทุกคน" — คือผลลัพธ์ที่ไม่แยกคน
   ไฟล์นี้วัดปัญหานั้นเป็นตัวเลขก่อนที่เราจะเขียนแบบทดสอบ ถ้าเครื่องมือไหนแยกอาชีพไม่ได้
   ต่อให้เขียนข้อคำถามสวยแค่ไหนก็จะได้ผลลัพธ์กลาง ๆ เหมือนกัน
"""

from __future__ import annotations

import csv
import itertools
import json
import math
import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parent
SRC = PIPELINE / "cache" / "onet" / "db_29_1_text"
OUT = PIPELINE / "out"

# 8 อาชีพเป้าหมาย ครอบคลุมทั้ง 7 สาขาวิศวะของ SIIT
# 🔴 สองรหัสแรกเป็น "อาชีพตัวแทน" — O*NET ยังไม่มีข้อมูลกิจกรรมของ
#    Software Developers (15-1252) และ Data Scientists (15-2051)
#    จึงใช้อาชีพในตระกูลเดียวกันที่มีข้อมูลครบแทน และบันทึกไว้ใน careers.py ว่าใช้ตัวแทน
TARGETS: dict[str, str] = {
    "15-1251.00": "วิศวกรซอฟต์แวร์ (ตัวแทน: Computer Programmers)",
    "15-2051.01": "วิศวกรข้อมูล (ตัวแทน: Business Intelligence Analysts)",
    "17-2199.08": "วิศวกรหุ่นยนต์",
    "17-2051.00": "วิศวกรโครงสร้าง",
    "17-2041.00": "วิศวกรกระบวนการผลิต",
    "17-2112.00": "วิศวกรการผลิต",
    "17-2071.00": "วิศวกรไฟฟ้ากำลัง",
    "17-2141.00": "วิศวกรออกแบบเครื่องกล",
}


def read_tsv(name: str) -> list[dict]:
    path = SRC / name
    if not path.exists():
        sys.exit(f"ไม่พบ {path} — รัน pipeline/1_import_onet.py ก่อน")
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def content_model() -> dict[str, dict]:
    return {
        r["Element ID"]: {"name_en": r["Element Name"], "description": r["Description"]}
        for r in read_tsv("Content Model Reference.txt")
    }


def spread(profiles: dict[str, dict[str, float]]) -> dict:
    """วัดว่าเครื่องมือนี้แยก 8 อาชีพออกจากกันได้แค่ไหน

    คืนระยะทางแบบยุคลิดของทุกคู่ · ยิ่งคู่ที่แย่ที่สุดสูง แปลว่าเครื่องมือยิ่งใช้ได้
    """
    socs = [s for s in profiles if profiles[s]]
    if len(socs) < 2:
        return {"usable": False}
    keys = sorted(set.intersection(*[set(profiles[s]) for s in socs]))
    pairs = []
    for a, b in itertools.combinations(socs, 2):
        d = math.dist([profiles[a][k] for k in keys], [profiles[b][k] for k in keys])
        pairs.append({"a": TARGETS[a], "b": TARGETS[b], "distance": round(d, 3)})
    pairs.sort(key=lambda p: p["distance"])
    return {
        "dimensions": len(keys),
        "worst_pair": pairs[0],
        "best_pair": pairs[-1],
        "ratio_worst_over_best": round(pairs[0]["distance"] / pairs[-1]["distance"], 3),
        "all_pairs": pairs,
    }


def collect(fname: str, prefix: str, scale: str, cmr: dict) -> tuple[list[dict], dict]:
    """ดึง element ที่ขึ้นต้นด้วย prefix + โปรไฟล์ของอาชีพเป้าหมาย"""
    rows = read_tsv(fname)
    elements: dict[str, dict] = {}
    profiles: dict[str, dict[str, float]] = {s: {} for s in TARGETS}

    for r in rows:
        eid, soc = r["Element ID"], r["O*NET-SOC Code"]
        if not eid.startswith(prefix) or r["Scale ID"] != scale:
            continue
        meta = cmr.get(eid, {})
        elements.setdefault(eid, {
            "id": eid,
            "name_en": r["Element Name"],
            "name_th": None,  # 🔴 งานแปลมือ
            "description_en": meta.get("description", ""),
        })
        if soc in profiles:
            profiles[soc][eid] = float(r["Data Value"])

    return sorted(elements.values(), key=lambda e: e["id"]), profiles


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cmr = content_model()
    report: dict[str, dict] = {}

    # ── กิจกรรมในงาน 41 มิติ (แกนของแบบทดสอบ) ──
    acts, act_profiles = collect("Work Activities.txt", "4.A.", "IM", cmr)
    # เอาเฉพาะชั้นล่างสุด 41 ตัว — รหัสหน้าตา 4.A.1.b.2 (จุด 4 ตัว)
    # ชั้นบนคือหมวด (4.A.1 = Information Input) กับหมวดย่อย (4.A.1.a) ไม่ใช่กิจกรรมจริง
    acts = [a for a in acts if a["id"].count(".") == 4]
    keep = {a["id"] for a in acts}
    act_profiles = {s: {k: v for k, v in p.items() if k in keep} for s, p in act_profiles.items()}

    # หมวดใหญ่ 4 หมวด — ใช้จัดกลุ่มข้อคำถามและอธิบายผล
    for a in acts:
        # 4.A.1.b.2 → หมวด 4.A.1 (Information Input) · หมวดย่อย 4.A.1.b
        top = ".".join(a["id"].split(".")[:3])
        mid = ".".join(a["id"].split(".")[:4])
        a["group_id"] = top
        a["group_en"] = cmr.get(top, {}).get("name_en", "")
        a["subgroup_id"] = mid
        a["subgroup_en"] = cmr.get(mid, {}).get("name_en", "")

    (OUT / "work_activities.json").write_text(
        json.dumps(acts, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "target_activity_profiles.json").write_text(
        json.dumps({"targets": TARGETS, "profiles": act_profiles}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    report["work_activities"] = spread(act_profiles)

    # ── ค่านิยมในการทำงาน 6 ด้าน ──
    values, val_profiles = collect("Work Values.txt", "1.B.2.", "EX", cmr)
    (OUT / "work_values.json").write_text(
        json.dumps({"elements": values, "profiles": val_profiles}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    report["work_values"] = spread(val_profiles)

    # ── บุคลิกในการทำงาน 16 ด้าน ──
    styles, sty_profiles = collect("Work Styles.txt", "1.C.", "IM", cmr)
    (OUT / "work_styles.json").write_text(
        json.dumps({"elements": styles, "profiles": sty_profiles}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    report["work_styles"] = spread(sty_profiles)

    # ── ความสนใจ RIASEC 6 ด้าน (เก็บไว้เทียบให้เห็นว่าทำไมไม่ใช้เป็นแกน) ──
    riasec, ria_profiles = collect("Interests.txt", "1.B.1.", "OI", cmr)
    riasec = [r for r in riasec if r["id"] <= "1.B.1.f"]
    keep_r = {r["id"] for r in riasec}
    ria_profiles = {s: {k: v for k, v in p.items() if k in keep_r} for s, p in ria_profiles.items()}
    (OUT / "riasec.json").write_text(
        json.dumps({"elements": riasec, "profiles": ria_profiles}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    report["riasec"] = spread(ria_profiles)

    # ── ตัวอย่างกิจกรรมรูปธรรม — วัตถุดิบสำหรับเขียนข้อคำถามภาษาไทย ──
    illus: dict[str, list[str]] = {}
    for r in read_tsv("Interests Illustrative Activities.txt"):
        illus.setdefault(f"{r['Element Name']} / {r['Interest Type']}", []).append(r["Activity"])
    (OUT / "illustrative_activities.json").write_text(
        json.dumps(illus, ensure_ascii=False, indent=2), encoding="utf-8")

    (OUT / "discrimination.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── สรุปให้อ่านบนจอ ──
    print(f"กิจกรรมในงาน   {len(acts):3} มิติ   (4 หมวดใหญ่)")
    print(f"ค่านิยม        {len(values):3} มิติ")
    print(f"บุคลิกการทำงาน {len(styles):3} มิติ")
    print(f"RIASEC        {len(riasec):3} มิติ")
    print(f"ตัวอย่างกิจกรรม {sum(len(v) for v in illus.values()):3} ข้อ จาก {len(illus)} พื้นที่ความสนใจ")
    print()
    print("🔴 เครื่องมือไหนแยก 8 อาชีพออกจากกันได้ (ยิ่งคู่แย่สุดสูง ยิ่งดี)")
    print(f"   {'เครื่องมือ':16} {'มิติ':>4} {'คู่แย่สุด':>9} {'คู่ดีสุด':>9}  คู่ที่แยกยากที่สุด")
    for name in ("work_activities", "riasec", "work_values", "work_styles"):
        r = report[name]
        if "worst_pair" not in r:
            print(f" 🔴 {name:16} — ไม่มีข้อมูลโปรไฟล์ ตรวจตัวกรอง element")
            continue
        w, b = r["worst_pair"], r["best_pair"]
        flag = "🟢" if w["distance"] >= 1.5 else "🔴"
        print(f" {flag} {name:16} {r['dimensions']:>4} {w['distance']:>9.2f} {b['distance']:>9.2f}"
              f"  {w['a']} ↔ {w['b']}")
    print()
    print(f"เขียนแล้ว → {OUT}")


if __name__ == "__main__":
    main()
