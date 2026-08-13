# -*- coding: utf-8 -*-
"""ดึงข้อความจริงทุกหน้าจอจาก API เขียนเป็น docs/DESIGN-CONTENT.md ให้คนออกแบบ

    make backend        # ต้องเปิดค้างไว้ก่อน
    make design-content

🔴 ทำไมต้องมีสคริปต์นี้ ไม่พิมพ์เอาเอง
   จุดที่แบบพังคือ **ความยาวจริงของข้อความไทย** ไม่ใช่ความสวย
   เหตุผลการกรองยาว 93 ตัวอักษร · ชื่ออาชีพยาว 33 · คำอธิบาย 75
   ออกแบบด้วย placeholder สั้น ๆ แล้วมาใส่ของจริงทีหลัง = จัดหน้าใหม่ทั้งหมด

   และสคริปต์นี้ทำให้ไฟล์ **สร้างใหม่ได้ทุกครั้งที่ข้อมูลเปลี่ยน**
   ถ้าพิมพ์มือ พอ 🅴 เพิ่มอาชีพหรือแก้ข้อความ ไฟล์จะล้าสมัยเงียบ ๆ

⚠️ สคริปต์สร้างผู้ใช้ทดสอบ 3 คนในฐานข้อมูล และไม่ได้ลบให้
   รันบนฐานข้อมูลที่มีข้อมูลผู้ใช้จริงแล้วจะมีขยะปน — ใช้กับเครื่องพัฒนาเท่านั้น
"""
import json
import sys
import urllib.request
from pathlib import Path

B = "http://localhost:8000/api"


def call(path, body=None, headers=None):
    h = {"Content-Type": "application/json", **(headers or {})}
    r = urllib.request.Request(B + path, json.dumps(body).encode() if body else None, h)
    try:
        return json.load(urllib.request.urlopen(r))
    except urllib.error.HTTPError as e:
        return {"_status": e.code, **json.loads(e.read())}


CV = """สมชาย ใจดี — นักศึกษาวิศวกรรมคอมพิวเตอร์ ปี 3

- ทำระบบวิเคราะห์ข้อมูลการใช้ห้องเรียนด้วย Python และ pandas
- สร้าง REST API ด้วย FastAPI ต่อกับ PostgreSQL ใช้ SQL ดึงข้อมูล
- ดูแลโค้ดด้วย Git เขียน unit test ด้วย pytest ทุกฟีเจอร์
- ใช้ Docker และ Linux ในการ deploy
TOEIC 780
"""

out = []
w = out.append

# ── ผู้ใช้ที่ไม่มีเงื่อนไขกรอง ── เห็นอาชีพครบ
plain = call("/session", {"entry": "known"})["user_id"]
all_targets = call(f"/targets?user_id={plain}")

# ── ผู้ใช้ทุนรัฐบาล เกรดต่ำ ── เห็นกล่อง "ไปไม่ถึง"
gated = call("/session", {"entry": "known"})["user_id"]
call("/profile", {"user_id": gated, "field": "CPE", "education_level": "ปี 2",
                  "year": 2, "gpa": 2.40, "obligation_id": "gov"})
gated_targets = call(f"/targets?user_id={gated}")

w("# ข้อความจริงจากระบบ — สำหรับใส่ใน Stitch\n")
w("> สร้างด้วย `make design-content` — ดึงจาก API จริง ไม่ได้พิมพ์เอง ไม่ได้ย่อ  ")
w("> ข้อมูลเปลี่ยนเมื่อไหร่ รันใหม่ได้ทันที\n")
w("> 🔴 **ออกแบบด้วยข้อความชุดนี้ อย่าใช้ placeholder สั้น ๆ** — "
  "จุดที่แบบพังคือความยาวจริงของภาษาไทย\n")

w("\n## 🔴 ความยาวที่ต้องรองรับ\n")
titles = [t["title_th"] for t in all_targets["targets"]]
reasons = sorted({r["message"] for f in gated_targets["filtered_out"] for r in f["reasons"]}
                 | {c["message"] for t in gated_targets["targets"]
                    for c in t["conditions_at_application"]})
w(f"| | ยาวสุด | ตัวอย่างที่ยาวที่สุด |")
w("|---|--:|---|")
w(f"| ชื่ออาชีพ (ไทย) | {max(len(x) for x in titles)} ตัวอักษร | {max(titles, key=len)} |")
w(f"| เหตุผลการกรอง | {max(len(x) for x in reasons)} ตัวอักษร | {max(reasons, key=len)} |")
w(f"| คำอธิบายอาชีพ | {max(len(t['summary']) for t in all_targets['targets'])} ตัวอักษร | "
  f"{max((t['summary'] for t in all_targets['targets']), key=len)} |")

w("\n---\n\n## หน้า `/targets` — คลังอาชีพ\n")
w("### การ์ดอาชีพ ทั้ง 8 อัน (ข้อความจริง)\n")
for t in all_targets["targets"]:
    w(f"**{t['title_th']}** · {t['title_en']} · `{t['sector_label']}`  ")
    w(f"{t['summary']}  ")
    w(f"*ต้องแสดงความสามารถ {t['requirement_count']} เรื่อง · "
      f"{'อ้างอิงประกาศงานจริง ' + str(t['posting_count']) + ' ประกาศ' if t['posting_count'] else 'ยังไม่ได้อ้างอิงประกาศงานจริง'}*\n")

w("\n### สถานะที่ต้องออกแบบเผื่อ\n")
w(f"| สถานะ | เกิดเมื่อ | ตอนนี้ |")
w("|---|---|---|")
w(f"| ปกติ | ไม่มีโปรไฟล์ | **{len(all_targets['targets'])} การ์ด** ไม่มีกล่องล่าง |")
w(f"| ถูกกรองหนัก | ทุนรัฐบาล + เกรด 2.40 | **{len(gated_targets['targets'])} การ์ด** "
  f"+ กล่องล่าง **{len(gated_targets['filtered_out'])} อัน** |")
w("| กำลังโหลด | เปิดหน้าครั้งแรก | สปินเนอร์ + “กำลังโหลดคลังอาชีพ” |")
w("| ต่อ API ไม่ได้ | ลืมเปิด backend | “ต่อกับ API ไม่ได้ที่ … — เปิด backend แล้วหรือยัง” |")

w("\n### 🔴 กล่อง “อาชีพที่เงื่อนไขของคุณไปไม่ถึง” — จุดที่ต่างจากเว็บหางาน\n")
w("มีได้ถึง 7 การ์ด และ**บางอันมี 2 เหตุผลซ้อนกัน** · ข้อความจริงทั้งหมด:\n")
for f in gated_targets["filtered_out"]:
    w(f"- **{f['title_th']}**")
    for r in f["reasons"]:
        w(f"    - `✕ ถาวร` {r['message']}")
w("")
w("### `◷ ตามเวลา` — ยังอยู่ในรายการหลัก ไม่ใช่ในกล่องล่าง\n")
for t in gated_targets["targets"]:
    for c in t["conditions_at_application"]:
        w(f"- **{t['title_th']}** → `◷` {c['message']}")

w("\n> **สองแบบนี้ต้องดูต่างกันทันที** — `✕` คือไปไม่ได้จริง · `◷` คือแค่ยังไม่ถึงเวลา  ")
w("> ใช้สีเดียวกันเมื่อไหร่ ผู้ใช้จะอ่านว่าปิดประตูทั้งคู่\n")

# ── รายละเอียดอาชีพ ──
d = call("/targets/ROBOT-ENG")
w("\n---\n\n## หน้า `/targets/[id]` — รายละเอียดอาชีพ\n")
w(f"**{d['title_th']}**  \n{d['summary']}\n")
w(f"**วันหนึ่งของคนทำงานนี้** — {len(d['day_in_the_life'])} ตัวอักษร  ")
w(f"{d['day_in_the_life']}\n")
w(f"สาขาที่รับ `{' · '.join(d['field_whitelist'])}` · วุฒิขั้นต่ำ `{d['min_education']}` "
  f"· เกรดขั้นต่ำ `{d['min_gpa']}`\n")
w(f"**ความสามารถที่ต้องแสดง {len(d['requirements'])} เรื่อง** — แต่ละข้อมีป้ายบอกที่มา\n")
for r in d["requirements"]:
    label = {"curated": "ทีมเขียนเอง", "postings": "จากประกาศงานจริง",
             "both": "ประกาศงานจริงยืนยัน"}[r["source"]]
    w(f"- {r['name_th']} · ระดับ {r['min_level']} · `{label}`")
w(f"\n> ⚠️ {d['salary_note']}\n")

# ── แบบทดสอบ ──
u = call("/session", {"entry": "unsure"})["user_id"]
w("\n---\n\n## หน้า `/discover` — แบบทดสอบ (ยังไม่ได้สร้าง)\n")
w("**ทีละ 1 ข้อ ไม่ใช่ลิสต์ยาว** · ระบบเลือกข้อถัดไปเอง จบใน 12–24 ข้อ\n")
HANDS = ["เครื่อง", "ซ่อม", "ประกอบ", "ติดตั้ง", "วัสดุ", "โครงสร้าง", "หน้างาน", "มือ"]
nxt = call(f"/discover/next?user_id={u}")
w("### ข้อคำถามจริง 3 ข้อแรก\n")
seen = 0
while not nxt["done"] and seen < 14:
    it = nxt["item"]
    if seen < 3:
        w(f"**ข้อ {it['no']}** · หมวด *{it['group_th']}*  ")
        w(f"{it['prompt_th']}  ")
        w(f"*{it['context_th']}*\n")
        w(f"ปุ่มตอบ 3 ปุ่ม: `ไม่อยากทำ` · `เฉย ๆ` · `อยากทำ`\n")
    txt = f"{it['prompt_th']} {it.get('context_th') or ''}"
    call("/discover/answer", {"user_id": u, "item_id": it["item_id"],
                              "answer": 1 if any(k in txt for k in HANDS) else -1})
    seen += 1
    nxt = call(f"/discover/next?user_id={u}")
    if nxt.get("interim") and seen == 6:
        w("### ⭐ ผลระหว่างทาง — โผล่ทุก 6 ข้อ\n")
        for c in nxt["interim"]["top"]:
            why = c["reasons"][0]["label"] if c["reasons"] else "—"
            w(f"- **{c['title_th']}** · เทียบในกลุ่ม {c['relative_score']}/100 · ← {why}")
        w(f"\n> {nxt['interim']['scale_note']}\n")
    if not nxt["done"] and seen == 4:
        w(f"### ⭐ ข้อความ “ทำไมยังถามต่อ” (ขึ้นระหว่างทำ)\n\n> {nxt['reason']}\n")

res = call(f"/discover/result?user_id={u}")
w("### หน้าผลลัพธ์\n")
for c in res["targets"]:
    w(f"**{c['rank_no']}. {c['title_th']}** · เทียบในกลุ่ม {c['relative_score']}/100"
      + ("  ⭐ อาชีพที่คุณอาจไม่เคยคิดถึง" if c["is_unconsidered"] else ""))
    for r in c["reasons"]:
        w(f"    - ทำไมถึงเสนอ: **{r['label']}** — *{r['reads_as']}*")
    for h in c["heads_up"]:
        w(f"    - ควรรู้ก่อนเลือก: **{h['label']}** — *{h['reads_as']}*")
w(f"\n> 🔴 {res['scale_note']}")
w(f">\n> {res['weights_note']}\n")
w("> **“ทำไมถึงเสนอ” กับ “ควรรู้ก่อนเลือก” ต้องอยู่คนละที่บนจอ** — "
  "รวมกันเมื่อไหร่ หน้าจอจะอ่านได้ว่า “เสนองานนี้เพราะคุณไม่อยากทำสิ่งนี้”\n")

# ── ส่งผลงาน ──
doc = call("/portfolio/text", {"user_id": plain, "text": CV, "consent": True})
rev = call(f"/portfolio/{doc['document_id']}")
w("\n---\n\n## หน้า `/portfolio` — ส่งผลงาน + ไฮไลต์ (ยังไม่ได้สร้าง)\n")
w("รับ 4 ทาง: **PDF · วางข้อความ · ลิงก์ GitHub · LinkedIn** (LinkedIn ให้วางเอง)\n")
w("⭐ **หน้าไฮไลต์คือจุดที่พิสูจน์ว่าระบบอ่านจริง** — API ส่ง `raw_text` + ตำแหน่งตัวอักษรมาให้ "
  "ต้องระบายสีตรงตำแหน่งนั้นจริง ๆ\n")
w(f"ผลสกัดจาก CV ตัวอย่าง — **{len(rev['extracted'])} รายการ** ทุกอันเริ่มที่ `pending`:\n")
for e in rev["extracted"][:8]:
    w(f'- **{e["name_th"]}** · ระดับ {e["level"]} · มั่นใจ {e["confidence"]} '
      f'· ไฮไลต์คำว่า “{e["span_text"]}”')
w(f"\n> {rev['note']}")
w("\n> ผู้ใช้ต้องกด ✓ / ✗ / แก้ระดับ รายข้อ — **ยังไม่ยืนยัน = ยังไม่นับ**\n")

# ── roadmap ──
call("/portfolio/%s/confirm" % doc["document_id"],
     {"user_id": plain, "decisions": {e["id"]: "confirmed" for e in rev["extracted"]}})
call("/goal", {"user_id": plain, "target_id": "SW-DEV"})
rm = call(f"/roadmap?user_id={plain}")
w("\n---\n\n## หน้า `/roadmap` — ★ หน้าหลัก (ยังไม่ได้สร้าง)\n")
w(f"**{rm['target']['title_th']}** · {rm['total_steps']} ก้าว · เดินแล้ว {rm['steps_done']} "
  f"· ครอบคลุม {int(rm['coverage'] * 100)}%\n")
w(f"หลักฐาน: จาก CV {rm['evidence_summary']['from_cv']} · กรอกเอง "
  f"{rm['evidence_summary']['self_reported']}  ")
w(f"> 🔒 {rm['evidence_summary']['note']} — **ห้ามแสดงรวมกัน**\n")
w("### 4 สถานะของก้าว — ต้องดูต่างกันชัด\n")
w("| สถานะ | ความหมาย |\n|---|---|")
for k, v in rm["legend"].items():
    w(f"| `{k}` | {v} |")
w("\n### ก้าวจริงในเส้นทางนี้\n")
for s in rm["steps"][:8]:
    ev = {"extracted": " · หลักฐานจาก CV", "self_reported": " · กรอกเอง",
          "both": " · ทั้งสองอย่าง", None: ""}[s["evidence_kind"]]
    w(f"**{s['order_no']}. {s['name_th']}** · `{s['status']}` "
      f"· ระดับ {s['current_level']}→{s['target_level']}{ev} · {len(s['options'])} ทางไปถึง")
    for o in s["options"][:3]:
        cost = f"{o['cost_baht']:,} บาท" if o["cost_baht"] else "ไม่มีค่าใช้จ่าย"
        hrs = f"{o['est_hours']} ชม." if o["est_hours"] else "ไม่ระบุเวลา"
        blocked = f" · 🔴 {o['blocked_reason']}" if o["blocked_reason"] else ""
        w(f'    - `{o["kind_label"]}` {o["title"]} · {hrs} · {cost}{blocked}')
w("\n> **ตัวเลือกที่ติดเงื่อนไขต้องยังแสดงอยู่พร้อมเหตุผล ไม่ซ่อน**\n")
w(f"> API ส่งทั้ง `order_no` (วาดเป็นรายการ) และ `edges` {len(rm['edges'])} เส้น "
  "(วาดเป็นกราฟ) — **เลือกได้ว่าจะวาดแบบไหน**\n")

target = Path(__file__).resolve().parents[2] / "docs" / "DESIGN-CONTENT.md"
target.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"เขียนแล้ว {target} — {len(out)} บรรทัด")
