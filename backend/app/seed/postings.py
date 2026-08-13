"""อ่านประกาศงานที่ 🅴 เก็บมาด้วยมือจาก `data/postings/*.md`

รูปแบบไฟล์: YAML frontmatter + ตัวข้อความประกาศตามต้นฉบับ
คำอธิบายสำหรับคนเก็บอยู่ที่ `data/postings/README.md` — ไฟล์นี้คือด่านตรวจของมัน

🔴 ทำไมเป็น markdown ไม่ใช่ JSON หรือ CSV
   คนกรอกไม่ใช่โปรแกรมเมอร์ และของที่ต้องวางคือข้อความยาวหลายย่อหน้าที่มีทั้ง
   เครื่องหมายคำพูด บรรทัดใหม่ และ bullet · ใน JSON ต้อง escape ทุกอย่าง พลาดแล้วพังทั้งไฟล์
   ส่วน markdown วางทับได้ตรง ๆ ไม่ต้องแตะอะไรเลย

🔴 ทำไม id มาจากชื่อไฟล์
   ช่อง id ในหัวไฟล์คือช่องที่คนคัดลอกไฟล์แม่แบบแล้วลืมแก้บ่อยที่สุด
   ใช้ชื่อไฟล์แทนทำให้ id ซ้ำกันไม่ได้โดยธรรมชาติ

🔒 ตัวข้อความถูกเก็บตามที่วางมา ไม่มีการตัดแต่ง
   เพราะ PostingExtraction จะชี้กลับไปที่ตำแหน่งตัวอักษรในข้อความนี้
   (กติกาข้อ 2 ใน docs/TEAM.md — เหมือนกับ span ที่ชี้กลับไปที่ CV)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from app.seed.careers import FIELDS, SECTORS

POSTINGS_DIR = Path(__file__).resolve().parents[3] / "data" / "postings"

EMPLOYMENT_TYPES = {
    "new_grad": "รับนักศึกษาจบใหม่",
    "internship": "ฝึกงาน",
    "coop": "สหกิจศึกษา",
    "experienced": "ต้องมีประสบการณ์",
}

REQUIRED = ("org", "title", "url", "collected_at", "collected_by", "sector", "employment_type")
OPTIONAL = (
    "target_id", "location", "salary_text", "posted_at", "closes_at",
    "requires_field", "requires_gpa", "requires_education", "note",
)

# ประกาศงานที่สั้นกว่านี้แปลว่ายังคัดลอกมาไม่ครบ — ประกาศจริงที่สั้นที่สุดก็เกินนี้
MIN_BODY_CHARS = 300

# 🔴 repo เป็น public — ข้อมูลติดต่อของคนที่ไม่ได้ยินยอมต้องไม่หลุดเข้าไป
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
# ต้องจับได้ทั้งบ้าน 02-123-4567 (2-3-4) และมือถือ 081-234-5678 (3-3-4) และ +66 81 234 5678
# ตัวเลขอื่นในประกาศ (เงินเดือน 25,000 · เกรด 2.75 · ปี 2569) ต้องไม่โดนจับผิด
PHONE = re.compile(
    r"(?<![\d.,])(?:0\d{1,2}|\+66[\s-]?\d{1,2})[\s-]?\d{3}[\s-]?\d{4}(?![\d.,])"
)

FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.S)


@dataclass
class Posting:
    id: str
    # None = ไม่ได้มาจากไฟล์ แต่มาจากฟอร์มที่บริษัทกรอก (app/api_employer.py)
    path: Path | None
    meta: dict
    body: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _parse_date(value, label: str, errors: list[str]) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        errors.append(f"{label} ต้องเป็นวันที่แบบ YYYY-MM-DD (เจอ “{value}”)")
        return None


def parse(path: Path, target_ids: set[str] | None = None) -> Posting:
    """อ่าน 1 ไฟล์ แล้วบอกว่าอะไรผิด (errors) และอะไรน่าห่วง (warnings)

    errors  = โหลดเข้าระบบไม่ได้ ต้องแก้
    warnings = โหลดได้ แต่คนเก็บน่าจะอยากรู้
    """
    raw = path.read_text(encoding="utf-8")
    p = Posting(id=path.stem, path=path, meta={}, body="")

    m = FRONTMATTER.match(raw)
    if not m:
        p.errors.append("หาหัวไฟล์ไม่เจอ — ไฟล์ต้องขึ้นต้นด้วย --- และปิดหัวไฟล์ด้วย --- อีกบรรทัด")
        return p

    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        p.errors.append(f"หัวไฟล์อ่านไม่ออก: {exc}")
        return p
    if not isinstance(meta, dict):
        p.errors.append("หัวไฟล์ต้องเป็นรายการ ช่อง: ค่า")
        return p

    p.meta = meta
    p.body = m.group(2).strip()
    validate(p, target_ids)
    return p


def validate(
    p: Posting,
    target_ids: set[str] | None = None,
    audience: str = "file",
) -> Posting:
    """กติกาเดียวกันทั้งไฟล์ที่ 🅴 เก็บ และฟอร์มที่บริษัทกรอกเอง

    แยกออกมาเพราะประกาศงานเข้าระบบได้สองทาง แต่ต้องผ่านด่านเดียวกัน
    ถ้าฝั่งฟอร์มหลวมกว่า มันจะกลายเป็นประตูหลังทันที

    `audience` เปลี่ยนแค่ *ถ้อยคำ* ไม่ได้เปลี่ยนกติกา — คนอ่านคนละกลุ่มกัน
      "file" ทีมเก็บเอง รู้ว่า repo เป็น public
      "form" บริษัทกรอกเอง ไม่รู้จัก repo และประกาศของเขาไม่ได้เข้า repo ด้วยซ้ำ
    """
    meta, errors = p.meta, p.errors

    # ── ช่องที่ต้องกรอก ──
    for key in REQUIRED:
        if meta.get(key) in (None, "", []):
            errors.append(f"ยังไม่ได้กรอก `{key}`")

    unknown = set(meta) - set(REQUIRED) - set(OPTIONAL)
    if unknown:
        p.warnings.append(f"มีช่องที่ระบบไม่รู้จัก จะถูกข้ามไป: {', '.join(sorted(unknown))}")

    # ── ค่าที่ต้องอยู่ในชุดที่กำหนด ──
    if (s := meta.get("sector")) and s not in SECTORS:
        errors.append(f"`sector` ต้องเป็นหนึ่งใน {' · '.join(SECTORS)} (เจอ “{s}”)")
    if (e := meta.get("employment_type")) and e not in EMPLOYMENT_TYPES:
        errors.append(
            f"`employment_type` ต้องเป็นหนึ่งใน {' · '.join(EMPLOYMENT_TYPES)} (เจอ “{e}”)")

    if (t := meta.get("target_id")) and target_ids is not None and t not in target_ids:
        errors.append(f"`target_id` “{t}” ไม่มีอยู่ในคลังอาชีพ — ใส่ null ถ้าไม่แน่ใจ")

    known_fields = {f["id"] for f in FIELDS}
    for code in meta.get("requires_field") or []:
        if code not in known_fields:
            errors.append(f"`requires_field` มี “{code}” ที่ไม่ใช่สาขาของ SIIT")

    if (g := meta.get("requires_gpa")) is not None:
        if not isinstance(g, (int, float)) or not 0 <= g <= 4:
            errors.append(f"`requires_gpa` ต้องเป็นตัวเลข 0–4 (เจอ “{g}”)")

    # ── วันที่ ──
    collected = _parse_date(meta.get("collected_at"), "`collected_at`", errors)
    if collected and collected > date.today():
        errors.append("`collected_at` เป็นวันในอนาคต — น่าจะพิมพ์ผิด")
    posted = _parse_date(meta.get("posted_at"), "`posted_at`", errors)
    closes = _parse_date(meta.get("closes_at"), "`closes_at`", errors)
    if posted and closes and closes < posted:
        errors.append("`closes_at` มาก่อน `posted_at`")

    if (u := meta.get("url")) and not str(u).startswith(("http://", "https://")):
        errors.append(f"`url` ต้องขึ้นต้นด้วย http:// หรือ https:// (เจอ “{u}”)")

    # ── ตัวข้อความ ──
    if not p.body:
        errors.append("ไม่มีข้อความประกาศใต้หัวไฟล์")
    elif len(p.body) < MIN_BODY_CHARS:
        errors.append(
            f"ข้อความประกาศสั้นเกินไป ({len(p.body)} ตัวอักษร ต้องอย่างน้อย {MIN_BODY_CHARS}) "
            "— คัดลอกมาครบหรือยัง ต้องมีทั้งคุณสมบัติผู้สมัครและหน้าที่ความรับผิดชอบ"
        )
    if "วางข้อความประกาศงานทั้งหมดตรงนี้" in p.body:
        errors.append("ยังไม่ได้ลบข้อความของแม่แบบออก")

    # ── 🔴 ข้อมูลส่วนบุคคล ──
    why = (
        "ข้อมูลติดต่อต้องไม่อยู่ในตัวประกาศ — ใส่ในช่องอีเมลติดต่อแทน"
        if audience == "form"
        else "repo เป็น public ต้องลบออกก่อน"
    )
    if hits := EMAIL.findall(p.body):
        errors.append(f"เจออีเมลในข้อความ {len(hits)} จุด (เช่น {hits[0]}) — {why}")
    if hits := PHONE.findall(p.body):
        errors.append(f"เจอเบอร์โทรในข้อความ {len(hits)} จุด (เช่น {hits[0]}) — {why}")

    # ── เตือน ไม่ใช่ error ──
    # ชื่อช่องต้องเป็นภาษาที่คนอ่านใช้จริง — บริษัทที่กรอกฟอร์มไม่รู้จัก `target_id`
    # เขาเห็นแค่ป้ายบนหน้าจอ ส่วนทีมที่แก้ไฟล์เห็นชื่อช่องใน YAML
    labels = {
        "target_id": "อาชีพที่ตรงที่สุด" if audience == "form" else "`target_id`",
        "salary_text": "เงินเดือน" if audience == "form" else "`salary_text`",
        "closes_at": "ปิดรับสมัคร" if audience == "form" else "`closes_at`",
    }
    for key, why in (
        ("target_id", "ระบบจะยังไม่รู้ว่าประกาศนี้นับให้อาชีพไหน"),
        ("salary_text", "อ่านย้อนจากข้อความได้ แต่ตอนนี้เร็วกว่า"),
        ("closes_at", "ไม่มีวันปิดรับ จะซ่อนงานที่หมดอายุไม่ได้"),
    ):
        if meta.get(key) in (None, "", []):
            p.warnings.append(f"ไม่ได้ใส่ {labels[key]} — {why}")

    return p


def load_all(directory: Path | None = None, target_ids: set[str] | None = None) -> list[Posting]:
    """อ่านทุกไฟล์ในโฟลเดอร์ · ไฟล์ที่ขึ้นต้นด้วย `_` ถูกข้าม (แม่แบบ/ตัวอย่าง)"""
    directory = directory or POSTINGS_DIR
    if not directory.exists():
        return []
    return [
        parse(path, target_ids)
        for path in sorted(directory.glob("*.md"))
        if not path.name.startswith("_") and path.name != "README.md"
    ]


def from_db_rows(rows) -> list[Posting]:
    """แปลงแถว JobPosting ที่บริษัทส่งมา ให้หน้าตาเหมือนกับที่อ่านจากไฟล์

    ท่อขั้นที่ 2 จะได้ประมวลผลประกาศจากสองทางด้วยโค้ดชุดเดียวกัน
    ถ้าไม่มีตัวนี้ ประกาศที่บริษัทส่งเข้ามาจะนอนอยู่ในตารางโดยไม่ถูกนับเลย
    """
    return [
        Posting(
            id=r.id, path=None, body=r.raw_text,
            meta={
                "org": r.org, "title": r.title, "url": r.url,
                "collected_at": r.collected_at, "collected_by": r.collected_by,
                "target_id": r.target_id,
            },
        )
        for r in rows
    ]


def to_row(p: Posting) -> dict:
    """แปลงเป็นฟิลด์ของตาราง job_posting"""
    return {
        "id": p.id,
        "target_id": p.meta.get("target_id") or None,
        "org": str(p.meta.get("org", "")),
        "title": str(p.meta.get("title", "")),
        "url": p.meta.get("url") or None,
        "collected_at": str(p.meta.get("collected_at", "")),
        "collected_by": p.meta.get("collected_by") or None,
        "raw_text": p.body,          # 🔒 ตามที่วางมา — span จะชี้กลับมาที่ค่านี้
        # ไฟล์ = ทีมเห็นประกาศต้นฉบับกับตาตัวเองแล้ว จึงไม่ต้องเข้าคิวรออนุมัติ
        # ต่างจากฟอร์มที่บริษัทกรอกเอง ซึ่งไม่มีใครยืนยันตัวตนได้ (ดู app/api_employer.py)
        "source": "manual",
        "status": "approved",
    }
