"""4.2 ELIGIBILITY — ตัวกรองคุณสมบัติ (❌ ไม่ใช้ AI)

🔴 จุดที่ตั้งใจต่างจาก แผน draft 2 §5 — อ่านก่อนแก้

สเปกเดิมกรองทุกเงื่อนไขแบบเดียวกัน คือ "ไม่ผ่าน = ตัดออก" ทั้งหมด
แต่กลุ่มเป้าหมายของ prototype นี้คือคนที่ยัง "ปี 1 / ยังไม่ได้เลือกสาขา"
ถ้ากรอง min_education แบบแข็ง อาชีพเป้าหมายทุกแห่งจะหายหมดตั้งแต่หน้าแรก
— และผลิตภัณฑ์ที่ทั้งอันคือ "แสดงเส้นทางไปยังอาชีพเป้าหมายในอนาคต"
   จะกลายเป็นผลิตภัณฑ์ที่ซ่อนอาชีพเป้าหมายที่กำลังเดินไปหา

จึงแยกเงื่อนไขเป็น 2 ชนิด:

  permanent — เรียนเพิ่มยังไงก็ไม่เปลี่ยน → ตัดออกจากรายการจริง
              · สาขาที่เรียน (field)
              · เงื่อนไขชดใช้ทุน (obligation)

  time      — ยังไม่ถึง แต่ถึงได้ → คงไว้ในรายการ แสดงเป็น "เงื่อนไขตอนสมัคร"
              · ระดับการศึกษาขั้นต่ำ
              · เกรดขั้นต่ำ

🔴 เงื่อนไขชดใช้ทุนยังเป็น hard filter เหมือนเดิม — นี่คือฟิลด์ที่เว็บหางาน
   ทั่วไปไม่มี และเป็นจุดสาธิตที่ ⭐ ในสคริปต์ (Demo-Script ข้อ 5)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.seed.careers import SECTORS, education_rank


@dataclass(frozen=True)
class Block:
    kind: str          # field | obligation | education | gpa
    permanence: str    # permanent | time
    message: str


@dataclass
class EligibilityVerdict:
    target_id: str
    blocks: list[Block] = field(default_factory=list)

    @property
    def permanent_blocks(self) -> list[Block]:
        return [b for b in self.blocks if b.permanence == "permanent"]

    @property
    def time_blocks(self) -> list[Block]:
        return [b for b in self.blocks if b.permanence == "time"]

    @property
    def eligible(self) -> bool:
        """ผ่านตัวกรองถาวร — ยังอยู่ในรายการได้"""
        return not self.permanent_blocks


@dataclass(frozen=True)
class ProfileInput:
    field_code: str | None = None          # สาขาที่เรียนอยู่ · None = ยังไม่ได้เลือก
    education_level: str | None = None
    gpa: float | None = None
    obligation_allowed_sectors: list[str] | None = None
    obligation_label: str | None = None
    hours_per_week: int | None = None
    resources: list[str] | None = None


@dataclass(frozen=True)
class TargetInput:
    id: str
    org: str
    role_title: str
    sector: str
    field_whitelist: list[str]
    min_education: str | None
    min_gpa: float | None


def evaluate(profile: ProfileInput, dest: TargetInput) -> EligibilityVerdict:
    v = EligibilityVerdict(target_id=dest.id)

    # ── ถาวร: สาขาที่เรียน ──
    # ยังไม่ได้เลือกสาขา = ไม่กรอง (ทั้งระบบมีไว้สำหรับคนกลุ่มนี้)
    if profile.field_code and profile.field_code not in dest.field_whitelist:
        v.blocks.append(
            Block(
                kind="field",
                permanence="permanent",
                message=f"ที่นี่รับเฉพาะสาขา {' · '.join(dest.field_whitelist)}",
            )
        )

    # ── ถาวร: เงื่อนไขชดใช้ทุน ──
    allowed = profile.obligation_allowed_sectors
    if allowed is not None and dest.sector not in allowed:
        label = profile.obligation_label or "เงื่อนไขทุนที่คุณมี"
        v.blocks.append(
            Block(
                kind="obligation",
                permanence="permanent",
                message=(
                    f"{label} — ที่นี่เป็น{SECTORS.get(dest.sector, dest.sector)} "
                    f"จึงไม่นับเป็นการชดใช้ทุน"
                ),
            )
        )

    # ── เวลา: ระดับการศึกษา ──
    if dest.min_education is not None:
        have = education_rank(profile.education_level)
        need = education_rank(dest.min_education)
        if have >= 0 and have < need:
            v.blocks.append(
                Block(
                    kind="education",
                    permanence="time",
                    message=f"สมัครได้เมื่อถึง{dest.min_education}",
                )
            )

    # ── เวลา: เกรดขั้นต่ำ ──
    if dest.min_gpa is not None and profile.gpa is not None and profile.gpa < dest.min_gpa:
        v.blocks.append(
            Block(
                kind="gpa",
                permanence="time",
                message=f"เกรดขั้นต่ำตอนสมัครคือ {dest.min_gpa:.2f}",
            )
        )

    return v


def filter_targets(
    profile: ProfileInput, targets: list[TargetInput]
) -> tuple[list[EligibilityVerdict], list[EligibilityVerdict]]:
    """คืน (ที่ยังอยู่ในรายการ, ที่ถูกตัดออกถาวร)

    รายการที่สองไม่ได้ทิ้งเงียบ ๆ — เอาไปแสดงพร้อมเหตุผลบนหน้าจอ
    เพราะ "การตัดออกพร้อมเหตุผล" คือข้อมูล ไม่ใช่ความล้มเหลว
    """
    kept, removed = [], []
    for d in targets:
        v = evaluate(profile, d)
        (kept if v.eligible else removed).append(v)
    return kept, removed
