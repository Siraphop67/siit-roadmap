"""ท่อขั้นที่ 1 — สร้างโครงทักษะสากลจาก O*NET  (❌ ไม่ใช้ LLM · ไม่ต้องมี API key)

O*NET เป็นฐานข้อมูลอาชีพของกระทรวงแรงงานสหรัฐ เปิดให้ดาวน์โหลดเป็นชุดฟรี
(เฉพาะ web service API เท่านั้นที่ต้องสมัคร — เราไม่ได้ใช้ตัวนั้น)

    python pipeline/1_import_onet.py

เข้า : pipeline/cache/onet/db_29_1_text/*.txt
ออก : pipeline/out/onet_skills.json · pipeline/out/onet_occupations.json

⚠️ สิ่งที่ออกมาคือ **รายการตั้งต้นให้คนคัด** ไม่ใช่ของที่เอาไปใช้ตรง ๆ
   ชื่อทั้งหมดเป็นภาษาอังกฤษและอิงตลาดสหรัฐ — การแปลไทยและการตัดให้เหลือ
   เฉพาะที่ตรงกับบริบท SIIT เป็นงานมือที่หลบไม่ได้ (แผน §2 D2)
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

PIPELINE = Path(__file__).resolve().parent
SRC = PIPELINE / "cache" / "onet" / "db_29_1_text"
OUT = PIPELINE / "out"

# สายอาชีพที่เกี่ยวกับ SIIT — 15-1 คอมพิวเตอร์ · 15-2 คณิตศาสตร์/ข้อมูล · 17-2 วิศวกรรม
SOC_PREFIXES = ("15-1", "15-2", "17-2")

# ความสำคัญขั้นต่ำ (สเกล IM ของ O*NET คือ 1–5) — ต่ำกว่านี้คือทักษะที่แทบไม่เกี่ยว
MIN_IMPORTANCE = 3.0

# เครื่องมือต้องปรากฏในอาชีพอย่างน้อยกี่อาชีพถึงจะเก็บ (กันของเฉพาะทางเกินไป)
MIN_TOOL_OCCURRENCES = 3


def read_tsv(name: str) -> list[dict]:
    path = SRC / name
    if not path.exists():
        sys.exit(
            f"ไม่พบ {path}\n"
            "รันคำสั่งนี้ก่อน:\n"
            "  curl -sL -o pipeline/cache/onet.zip "
            "https://www.onetcenter.org/dl_files/database/db_29_1_text.zip\n"
            "  unzip -q pipeline/cache/onet.zip -d pipeline/cache/onet"
        )
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def slug(text: str, prefix: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]
    return f"{prefix}-{s}"


def in_scope(soc: str) -> bool:
    return soc.startswith(SOC_PREFIXES)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # ── อาชีพในขอบเขต ──
    occupations = {
        r["O*NET-SOC Code"]: {"soc": r["O*NET-SOC Code"], "title": r["Title"],
                              "description": r["Description"]}
        for r in read_tsv("Occupation Data.txt")
        if in_scope(r["O*NET-SOC Code"])
    }
    print(f"อาชีพในขอบเขต (15-1 · 15-2 · 17-2)   : {len(occupations)}")

    skills: dict[str, dict] = {}
    requirements: dict[str, list[dict]] = defaultdict(list)

    # ── ความสามารถเชิงกว้าง: Skills.txt + Knowledge.txt ──
    for fname, category in (("Skills.txt", "skill"), ("Knowledge.txt", "knowledge")):
        for r in read_tsv(fname):
            soc = r["O*NET-SOC Code"]
            if soc not in occupations or r["Scale ID"] != "IM":
                continue
            try:
                importance = float(r["Data Value"])
            except ValueError:
                continue
            if importance < MIN_IMPORTANCE:
                continue

            sid = slug(r["Element Name"], "onet")
            skills.setdefault(sid, {
                "id": sid,
                "name_en": r["Element Name"],
                "name_th": None,          # 🔴 งานแปลมือ
                "category": category,
                "onet_element_id": r["Element ID"],
                "source": "onet",
                "used_by_n_occupations": 0,
            })
            skills[sid]["used_by_n_occupations"] += 1
            requirements[soc].append({
                "skill_id": sid,
                "importance": round(importance / 5.0, 3),
                "kind": category,
            })

    # ── เครื่องมือจริงที่ใช้ในงาน: Technology Skills.txt ──
    tool_rows = [r for r in read_tsv("Technology Skills.txt") if r["O*NET-SOC Code"] in occupations]
    tool_counts = Counter(r["Example"] for r in tool_rows)

    for r in tool_rows:
        example = r["Example"]
        hot = r.get("Hot Technology") == "Y" or r.get("In Demand") == "Y"
        if not hot and tool_counts[example] < MIN_TOOL_OCCURRENCES:
            continue

        sid = slug(example, "tool")
        skills.setdefault(sid, {
            "id": sid,
            "name_en": example,
            "name_th": None,
            "category": "tool",
            "onet_element_id": None,
            "source": "onet",
            "commodity": r["Commodity Title"],
            "hot_technology": r.get("Hot Technology") == "Y",
            "used_by_n_occupations": 0,
        })
        skills[sid]["used_by_n_occupations"] += 1
        requirements[r["O*NET-SOC Code"]].append({
            "skill_id": sid,
            "importance": 0.9 if hot else 0.6,
            "kind": "tool",
        })

    # ── เขียนออก ──
    skill_list = sorted(skills.values(), key=lambda s: (-s["used_by_n_occupations"], s["id"]))
    (OUT / "onet_skills.json").write_text(
        json.dumps(skill_list, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    occ_list = []
    for soc, occ in sorted(occupations.items()):
        reqs = sorted(requirements[soc], key=lambda x: -x["importance"])
        occ_list.append({**occ, "requirements": reqs})
    (OUT / "onet_occupations.json").write_text(
        json.dumps(occ_list, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    by_cat = Counter(s["category"] for s in skill_list)
    print(f"ทักษะที่สกัดได้                      : {len(skill_list)}")
    for cat, n in by_cat.most_common():
        print(f"    {cat:12} {n}")
    print(f"คู่ (อาชีพ ↔ ทักษะ)                   : {sum(len(v) for v in requirements.values())}")
    print(f"\nเขียนแล้ว → {OUT}/onet_skills.json · {OUT}/onet_occupations.json")
    print("🔴 ขั้นถัดไปเป็นงานมือ: แปลไทย + คัดให้เหลือเฉพาะที่ตรงกับ SIIT")


if __name__ == "__main__":
    main()
