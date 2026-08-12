"""สร้างผู้ใช้ตัวอย่าง 1 คนที่เดินครบเส้นแล้ว — สำหรับคนทำหน้าเว็บ

ปัญหาที่แก้: จะดูหน้า /roadmap สักครั้ง ต้องเดินตั้งแต่ตอบแบบทดสอบ ส่ง CV ยืนยันผลสกัด
เลือกเป้าหมาย ทุกครั้งที่รีเฟรช · สคริปต์นี้ทำให้จบใน 3 วินาที

    make backend            # ต้องเปิดค้างไว้ก่อน
    make demo-user          # หรือ  python scripts/demo_user.py --persona hands-on

ได้ user_id มาแล้วเอาไปวางใน DevTools Console ของ localhost:3000 ตามที่สคริปต์บอก
แล้วเปิดหน้าไหนก็ได้ ข้อมูลจะครบทันที

🔴 ยิงผ่าน HTTP API จริง ไม่ได้เขียนลงฐานข้อมูลตรง ๆ
   เพื่อให้ข้อมูลตัวอย่างเดินผ่านด่านเดียวกับผู้ใช้จริงทุกด่าน
   (ยินยอมก่อนส่ง CV · ทักษะต้องยืนยันก่อนนับ · span ต้องชี้กลับไปได้)
   ถ้าสคริปต์นี้พัง แปลว่า API พัง ไม่ใช่สคริปต์ล้าสมัย

⚠️ CV ในไฟล์นี้เป็นข้อมูลสมมติทั้งหมด — ห้ามเอา CV ของคนจริงมาใส่ (docs/CONTRIBUTING.md)
"""

from __future__ import annotations

import argparse
import sys

import httpx

BASE = "http://localhost:8000/api"

CV = """สมชาย ใจดี — นักศึกษาวิศวกรรมคอมพิวเตอร์ ปี 2

โครงงานและประสบการณ์
- ทำระบบวิเคราะห์ข้อมูลการใช้ห้องเรียนด้วย Python และ pandas
- สร้าง REST API ด้วย FastAPI ต่อกับ PostgreSQL ใช้ SQL ดึงข้อมูล
- ดูแลโค้ดด้วย Git เขียน unit test ด้วย pytest ทุกฟีเจอร์
- ทำ dashboard ด้วย Power BI ให้หัวหน้าไลน์ดูของเสียรายวัน
- ใช้ Docker และ Linux ในการ deploy
- เป็นหัวหน้ากลุ่มโครงงาน 4 คน นำเสนอหน้าชั้นทุกสัปดาห์
TOEIC 780
"""

# คำที่ใช้ตัดสินว่า persona นี้จะตอบ "อยากทำ" กับข้อไหน
PERSONAS: dict[str, tuple[str, tuple[str, ...]]] = {
    "hands-on": (
        "ชอบงานลงมือกับของจริง",
        ("เครื่อง", "ซ่อม", "ประกอบ", "ติดตั้ง", "วัสดุ", "โครงสร้าง", "หน้างาน", "มือ"),
    ),
    "data": (
        "ชอบงานกับข้อมูลและระบบ",
        ("ข้อมูล", "คำนวณ", "วิเคราะห์", "เขียนโปรแกรม", "ระบบ", "ตัวเลข", "เอกสาร"),
    ),
    "people": (
        "ชอบงานที่ได้ทำกับคน",
        ("คน", "ทีม", "สอน", "ประสาน", "นำเสนอ", "โน้มน้าว", "ลูกค้า", "ปรึกษา"),
    ),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--persona", choices=sorted(PERSONAS), default="data")
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--field", default="CPE", help="สาขาที่เรียน (CE CPE ChE EE IE ME DE)")
    ap.add_argument("--obligation", default="none", help="none | gov | univ")
    ap.add_argument(
        "--skip-discover", action="store_true",
        help="ไม่ต้องตอบแบบทดสอบ (ใช้เมื่อจะทดสอบเฉพาะฝั่ง 'รู้แล้ว')",
    )
    args = ap.parse_args()
    label, words = PERSONAS[args.persona]

    c = httpx.Client(base_url=args.base, timeout=30)
    try:
        c.get("/health").raise_for_status()
    except httpx.HTTPError:
        print(f"❌ ต่อ {args.base} ไม่ได้ — เปิด backend ก่อนด้วย  make backend", file=sys.stderr)
        return 1

    print(f"กำลังสร้างผู้ใช้ตัวอย่าง — {label}\n")

    uid = c.post("/session", json={"entry": "unsure"}).json()["user_id"]
    print(f"  ① เปิด session                {uid}")

    c.post("/profile", json={
        "user_id": uid, "field": args.field, "education_level": "ปี 2", "year": 2,
        "gpa": 3.10, "hours_per_week": 8, "budget_baht": 1500,
        "obligation_id": args.obligation,
    }).raise_for_status()
    print(f"  ② โปรไฟล์                      {args.field} · ปี 2 · 8 ชม./สัปดาห์ · ทุน {args.obligation}")

    # ── CV → สกัด → ยืนยัน ──
    doc = c.post("/portfolio/text", json={
        "user_id": uid, "text": CV, "consent": True,
    }).json()
    review = c.get(f"/portfolio/{doc['document_id']}").json()
    # ยืนยันทุกข้อที่มั่นใจ ≥ 0.5 · ที่เหลือปฏิเสธ เพื่อให้หน้าจอมีทั้งสองสถานะให้ดู
    decisions = {
        e["id"]: ("confirmed" if e["confidence"] >= 0.5 else "rejected")
        for e in review["extracted"]
    }
    confirmed = c.post(f"/portfolio/{doc['document_id']}/confirm", json={
        "user_id": uid, "decisions": decisions,
    }).json()
    print(f"  ③ ส่ง CV + ยืนยันผลสกัด        สกัดได้ {doc['extracted_count']} "
          f"· ยืนยัน {len(confirmed['confirmed_skills'])} ทักษะ")

    # ── แบบทดสอบฝั่ง "ยังไม่รู้" ──
    target_id = None
    if not args.skip_discover:
        answered = 0
        nxt = c.get("/discover/next", params={"user_id": uid}).json()
        while not nxt["done"] and answered < 40:
            item = nxt["item"]
            text = f"{item['prompt_th']} {item.get('context_th') or ''}"
            c.post("/discover/answer", json={
                "user_id": uid, "item_id": item["item_id"],
                "answer": 1 if any(w in text for w in words) else -1,
            })
            answered += 1
            nxt = c.get("/discover/next", params={"user_id": uid}).json()

        result = c.get("/discover/result", params={"user_id": uid}).json()
        if result["targets"]:
            top = result["targets"][0]
            target_id = top["target_id"]
            why = top["reasons"][0]["label"] if top["reasons"] else "—"
            print(f"  ④ ตอบแบบทดสอบ {answered} ข้อ          อันดับ 1: {top['title_th']} ← {why}")
            if result["separation_message"]:
                print(f"      ⚠ {result['separation_message']}")
        else:
            print(f"  ④ ตอบแบบทดสอบ {answered} ข้อ          {result['empty_message']}")

    # ── เลือกเป้าหมาย → roadmap ──
    if target_id is None:
        target_id = c.get("/targets", params={"user_id": uid}).json()["targets"][0]["id"]
    c.post("/goal", json={"user_id": uid, "target_id": target_id}).raise_for_status()

    rm = c.get("/roadmap", params={"user_id": uid}).json()
    current = next((s for s in rm["steps"] if s["status"] == "current"), None)
    print(f"  ⑤ เลือกเป้าหมาย → roadmap      {rm['target']['title_th']} · "
          f"{rm['total_steps']} ก้าว · เดินแล้ว {rm['steps_done']}")
    if current:
        print(f"      ก้าวที่ลงมือได้ตอนนี้: {current['name_th']} "
              f"({len(current['options'])} ทางไปถึง)")

    print(f"""
✅ พร้อมแล้ว

   เอาบรรทัดนี้ไปวางใน DevTools Console ที่ http://localhost:3000

   localStorage.setItem("siit-roadmap-user", "{uid}"); location.reload()

   แล้วเปิดหน้าไหนก็ได้ — /roadmap · /portfolio · /targets · /discover
   ลบผู้ใช้ตัวอย่างทิ้ง:  curl -X DELETE "{args.base}/me?user_id={uid}"
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
