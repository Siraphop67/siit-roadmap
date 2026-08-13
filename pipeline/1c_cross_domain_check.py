"""ท่อ 1c — ถ้าขยายข้ามสายงาน แบบทดสอบยังแยกอาชีพออกไหม  (❌ ไม่ใช้ LLM)

    python pipeline/1c_cross_domain_check.py
    python pipeline/1c_cross_domain_check.py --per-group 3

ออก: out/cross_domain_discrimination.json

🔴 คำถามที่ท่อนี้ตอบ
   ตัวเลข 2.29 ที่เราอ้างว่า "กิจกรรมในงานแยกอาชีพได้ดีกว่า RIASEC" วัดจาก
   **8 อาชีพวิศวกรรมที่คล้ายกันมาก** — เป็นกรณีที่แยกยาก

   พอจะขยายไปทุกสายงาน มีสองแรงสวนกัน:
     · อาชีพข้ามสายแยกง่ายขึ้น (พยาบาลกับวิศวกรโยธาไม่มีทางสับสน)
     · แต่คู่ใกล้ ๆ ในแต่ละสายจะเยอะขึ้นมาก (นักบัญชี ↔ ผู้ตรวจสอบบัญชี)

   เราเดาไม่ได้ว่าผลรวมจะออกทางไหน จึงวัด แทนที่จะเถียง

🔒 ใช้ตัววัดตัวเดียวกับ 1b เป๊ะ (`spread()` — ระยะยุคลิดของทุกคู่ ดูคู่ที่ใกล้ที่สุด)
   ถ้าเขียนตัววัดใหม่ ตัวเลขสองชุดจะเทียบกันไม่ได้

🔴 การเลือกอาชีพต้องไม่ใช่การเลือกที่ทำให้ตัวเองดูดี
   จึงสุ่มไม่ได้ และเลือกมือก็ไม่ได้ — ใช้กติกาที่ตรวจสอบได้แทน:
   หยิบอาชีพจาก **ทุกหมวดใหญ่ของ O*NET** (2 หลักแรกของรหัส SOC) หมวดละเท่า ๆ กัน
   โดย**กระจายให้ทั่วหมวด** ไม่ใช่เอาตัวแรก ๆ — ใครรันซ้ำก็ได้ชุดเดิม

   ⚠️ เคยพลาดมาแล้ว: รอบแรกใช้ "เอาตัวแรกของแต่ละหมวด" ผลคือได้ First-Line Supervisors
      มา 9 ตัว เพราะรหัส xx-1011 อยู่ต้นหมวดทุกหมวด ชุดที่ได้จึงคล้ายกันผิดปกติ
      และทำให้คู่ที่ใกล้ที่สุดต่ำกว่าความจริง

🔴 ห้ามเทียบ "ระยะดิบ" ข้ามเครื่องมือ
   ระยะยุคลิดโตตามจำนวนมิติ — 41 มิติย่อมได้ตัวเลขสูงกว่า 6 มิติโดยธรรมชาติ
   ไม่ว่าจะแยกอาชีพได้จริงหรือไม่ · ตัวที่เทียบได้คือ **คู่ใกล้สุด ÷ คู่ไกลสุด**
   ซึ่งไม่มีหน่วย และบอกว่า "คู่ที่แย่ที่สุดอยู่ห่างแค่ไหนเมื่อเทียบกับช่วงทั้งหมด"
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

PIPELINE = Path(__file__).resolve().parent
OUT = PIPELINE / "out"

# ชื่อหมวดใหญ่ตามระบบ SOC — ไว้อ่านรายงานให้รู้ว่าครอบคลุมอะไรบ้าง
MAJOR_GROUPS = {
    "11": "ผู้บริหาร", "13": "ธุรกิจและการเงิน", "15": "คอมพิวเตอร์และคณิตศาสตร์",
    "17": "สถาปัตย์และวิศวกรรม", "19": "วิทยาศาสตร์", "21": "สังคมสงเคราะห์",
    "23": "กฎหมาย", "25": "การศึกษา", "27": "ศิลปะและการออกแบบ",
    "29": "บุคลากรทางการแพทย์", "31": "ผู้ช่วยทางการแพทย์", "33": "ความปลอดภัย",
    "35": "อาหาร", "37": "ดูแลอาคารสถานที่", "39": "บริการส่วนบุคคล",
    "41": "การขาย", "43": "ธุรการ", "45": "เกษตรและประมง",
    "47": "ก่อสร้าง", "49": "ติดตั้งและซ่อมบำรุง", "51": "การผลิต", "53": "ขนส่ง",
}


def load_1b():
    """ยืมตัววัดจากท่อ 1b — ชื่อไฟล์ขึ้นต้นด้วยตัวเลข จึง import ปกติไม่ได้"""
    spec = importlib.util.spec_from_file_location(
        "onet_instruments", PIPELINE / "1b_import_instruments.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pick_targets(m, per_group: int) -> dict[str, str]:
    """อาชีพหมวดละ N ตัว — เอาเฉพาะที่มีข้อมูลครบทั้งกิจกรรมในงานและ RIASEC

    ไม่มีข้อมูลครบทั้งสองตัว = เทียบกันไม่ได้ ต้องคัดออกก่อน ไม่ใช่ปล่อยให้ค่าหาย
    """
    titles = {r["O*NET-SOC Code"]: r["Title"] for r in m.read_tsv("Occupation Data.txt")}

    def socs_with(fname: str, prefix: str, scale: str) -> set[str]:
        return {
            r["O*NET-SOC Code"] for r in m.read_tsv(fname)
            if r["Element ID"].startswith(prefix) and r["Scale ID"] == scale
        }

    usable = socs_with("Work Activities.txt", "4.A", "IM") & socs_with(
        "Interests.txt", "1.B.1", "OI")

    chosen: dict[str, str] = {}
    for group in sorted(MAJOR_GROUPS):
        in_group = sorted(s for s in usable if s.startswith(group))
        if not in_group:
            continue
        # กระจายให้ทั่วหมวด — เอาตัวแรก ๆ จะได้ First-Line Supervisors ทุกหมวด
        step = len(in_group) / (per_group + 1)
        for i in range(1, per_group + 1):
            soc = in_group[min(len(in_group) - 1, int(step * i))]
            chosen[soc] = titles.get(soc, soc)
    return chosen


def measure(m, targets: dict[str, str]) -> dict:
    """🔒 ใช้ collect() + spread() ของ 1b ตรง ๆ ตัวเลขจึงเทียบกับ 8 อาชีพวิศวะได้"""
    m.TARGETS = targets                      # spread() อ่านชื่อจากตัวแปรนี้
    cmr = m.content_model()
    out = {}
    for name, (fname, prefix, scale) in {
        "work_activities": ("Work Activities.txt", "4.A", "IM"),
        "riasec": ("Interests.txt", "1.B.1", "OI"),
    }.items():
        _, profiles = m.collect(fname, prefix, scale, cmr)
        out[name] = m.spread(profiles)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-group", type=int, default=2)
    args = ap.parse_args()

    m = load_1b()
    targets = pick_targets(m, args.per_group)
    if len(targets) < 3:
        print("อาชีพที่ข้อมูลครบมีน้อยเกินจะเทียบ — รัน make onet ก่อน")
        return 1

    result = measure(m, targets)
    baseline = json.loads((OUT / "discrimination.json").read_text(encoding="utf-8"))

    report = {
        "occupations": len(targets),
        "major_groups": sorted({s[:2] for s in targets}),
        "per_group": args.per_group,
        "targets": targets,
        "cross_domain": {
            k: {kk: vv for kk, vv in v.items() if kk != "all_pairs"}
            for k, v in result.items()
        },
        "engineering_baseline": {
            k: {kk: vv for kk, vv in baseline[k].items() if kk != "all_pairs"}
            for k in ("work_activities", "riasec")
        },
        "hardest_pairs": result["work_activities"]["all_pairs"][:10],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cross_domain_discrimination.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    _print(report, result)
    print(f"\nเขียนแล้ว → {OUT / 'cross_domain_discrimination.json'}")
    return 0


def _print(report: dict, result: dict) -> None:
    n = report["occupations"]
    print(f"\nอาชีพที่นำมาเทียบ {n} ตัว จาก {len(report['major_groups'])} หมวดใหญ่ "
          f"(หมวดละ {report['per_group']} ตัว)")
    print(f"จำนวนคู่ที่เทียบ {n * (n - 1) // 2} คู่\n")

    # 🔴 เทียบด้วยสัดส่วน ไม่ใช่ระยะดิบ — ระยะดิบเทียบข้ามจำนวนมิติไม่ได้
    print("สัดส่วน = คู่ที่ใกล้ที่สุด ÷ คู่ที่ไกลที่สุด · ยิ่งสูง ยิ่งแยกได้ทั่วถึง")
    print(f"\n{'':20} {'มิติ':>4} {'ใกล้สุด':>9} {'ไกลสุด':>9} {'สัดส่วน':>9}")
    for name, label in (("work_activities", "กิจกรรมในงาน"), ("riasec", "RIASEC")):
        for scope, src in (("ข้ามสาย", report["cross_domain"][name]),
                           ("วิศวะ 8 อาชีพ", report["engineering_baseline"][name])):
            ratio = src["worst_pair"]["distance"] / src["best_pair"]["distance"]
            head = f"{label} · {scope}"
            print(f"  {head:18} {src['dimensions']:>4} {src['worst_pair']['distance']:>9.2f} "
                  f"{src['best_pair']['distance']:>9.2f} {ratio:>9.3f}")

    cd_wa = report["cross_domain"]["work_activities"]
    cd_ri = report["cross_domain"]["riasec"]
    r_wa = cd_wa["worst_pair"]["distance"] / cd_wa["best_pair"]["distance"]
    r_ri = cd_ri["worst_pair"]["distance"] / cd_ri["best_pair"]["distance"]
    print(f"\nข้ามสายงาน: กิจกรรมในงานแยกได้ทั่วถึงกว่า RIASEC {r_wa / r_ri:.1f} เท่า")

    wa = result["work_activities"]["all_pairs"]

    print("\n🔴 10 คู่ที่แยกยากที่สุดเมื่อใช้กิจกรรมในงาน — จุดที่ระบบจะสับสน")
    for p in wa[:10]:
        print(f"   {p['distance']:>5.2f}  {p['a']}  ↔  {p['b']}")

    # เทียบกับคู่ที่แย่ที่สุดของชุดวิศวะ ซึ่งเป็นชุดที่เรารู้ว่าระบบใช้งานได้จริง
    bar = report["engineering_baseline"]["work_activities"]["worst_pair"]["distance"]
    worse = sum(1 for p in wa if p["distance"] < bar)
    print(f"\nคู่ที่แยกยากกว่าคู่ที่แย่ที่สุดของชุดวิศวะ ({bar:.2f}): "
          f"{worse} จาก {len(wa)} คู่ = {worse / len(wa) * 100:.1f}%")
    print("   ยิ่งน้อย แปลว่าชุดข้ามสายไม่ได้ยากกว่าชุดที่ระบบทำงานได้อยู่แล้วมากนัก")


if __name__ == "__main__":
    raise SystemExit(main())
