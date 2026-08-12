"""Data model — draft 2

🔴 ข้อบังคับที่ฝังอยู่ในสคีมานี้ (อ่านแผน §2 D3 ก่อนแก้):

  1. **`extracted_skill` กับ `self_reported_skill` เป็นคนละตาราง และจะเป็นคนละตารางตลอดไป**
     ตัวแรกมาจาก CV และมี span อ้างอิงกลับไปที่บรรทัดในเอกสารได้
     ตัวหลังคือสิ่งที่ผู้ใช้บอกเอง ไม่มีหลักฐาน
     roadmap ใช้ทั้งสอง แต่หน้าจอต้องแยกให้เห็นเสมอว่าอันไหนพิสูจน์ได้
     — นี่คือสิ่งเดียวที่ทำให้ "เหนือกว่าเว็บหางาน" เป็นจริง ไม่ใช่คำโฆษณา

  2. `extracted_skill` ต้องมี span (span_start/end/text ไม่เป็น null)
     และ span_text ต้องเป็น substring ของ user_document.raw_text ตรงตัว
     ไม่ผ่าน = ทิ้ง ไม่ว่าจะมาจาก LLM จริงหรือ mock

  3. `skill_edge` เป็น DAG — เส้นผิดหนึ่งเส้น roadmap ผิดทั้งเส้น
     เส้นที่ LLM เสนอต้องผ่านคนตรวจก่อน commit เสมอ

  4. CV เป็นข้อมูลส่วนบุคคล — `consent` แยกตามวัตถุประสงค์
     และต้องลบได้จริงทั้งหมดจากหน้า /me (PDPA)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JSONType = JSON().with_variant(JSONB, "postgresql")


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ═══════════════════════ คลังกลาง — สร้างโดยท่อ ═══════════════════════


class Skill(Base):
    """ทักษะ — โครงมาจากมาตรฐานสากล เนื้อเติมจากตลาดงานจริง (แผน §2 D2)"""

    __tablename__ = "skill"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name_en: Mapped[str] = mapped_column(Text)
    name_th: Mapped[str | None] = mapped_column(Text)  # null = ยังไม่ได้แปล → หน้าจอ fallback เป็น en
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(48))  # ใช้จัดกลุ่มเป็น topic บนหน้า roadmap
    onet_element_id: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(16), default="onet")  # onet | market | manual

    # กลไกจาก roadmap.sh — "ลำดับไม่ตายตัว · ทำเมื่อไหร่ก็ได้"
    # false = ไม่บังคับให้อยู่ในลำดับ topo ของ roadmap (เช่น "อ่านเอกสารอังกฤษ")
    order_strict: Mapped[bool] = mapped_column(Boolean, default=True)

    @property
    def display_name(self) -> str:
        return self.name_th or self.name_en


class SkillEdge(Base):
    """prereq DAG — from ต้องมาก่อน to

    🔴 ตารางเดียวที่แบกทั้งการเลือกก้าวถัดไปและลำดับของ roadmap ทั้งเส้น
    """

    __tablename__ = "skill_edge"
    __table_args__ = (UniqueConstraint("from_id", "to_id", name="uq_skill_edge"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_id: Mapped[str] = mapped_column(ForeignKey("skill.id"))
    to_id: Mapped[str] = mapped_column(ForeignKey("skill.id"))
    reviewed_by_human: Mapped[bool] = mapped_column(Boolean, default=False)


class CareerTarget(Base):
    """อาชีพเป้าหมาย — requirement มาจากประกาศงานจริง"""

    __tablename__ = "career_target"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title_th: Mapped[str] = mapped_column(Text)
    title_en: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    day_in_the_life: Mapped[str | None] = mapped_column(Text)  # "วันหนึ่งของคนทำงานนี้"
    sector: Mapped[str] = mapped_column(String(32))
    field_whitelist: Mapped[list] = mapped_column(JSONType)  # สาขาที่รับ
    min_education: Mapped[str | None] = mapped_column(String(32))
    min_gpa: Mapped[float | None] = mapped_column(Float)
    onet_soc_code: Mapped[str | None] = mapped_column(String(16))
    posting_count: Mapped[int] = mapped_column(Integer, default=0)  # สกัดจากกี่ประกาศ
    salary_note: Mapped[str | None] = mapped_column(Text)
    data_status: Mapped[str] = mapped_column(String(24), default="placeholder")

    requirements: Mapped[list["TargetRequirement"]] = relationship(
        back_populates="target", cascade="all, delete-orphan"
    )
    activity_profile: Mapped[list["TargetActivityProfile"]] = relationship(
        back_populates="target", cascade="all, delete-orphan"
    )


class TargetRequirement(Base):
    __tablename__ = "target_requirement"
    __table_args__ = (UniqueConstraint("target_id", "skill_id", name="uq_target_req"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_id: Mapped[str] = mapped_column(ForeignKey("career_target.id"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skill.id"))
    min_level: Mapped[int] = mapped_column(Integer)  # 1 รู้จัก · 2 ทำได้เมื่อมีคนแนะ · 3 ทำเองได้
    importance: Mapped[float] = mapped_column(Float, default=1.0)  # 0–1
    appears_in_n_postings: Mapped[int] = mapped_column(Integer, default=0)

    target: Mapped[CareerTarget] = relationship(back_populates="requirements")


class WorkActivity(Base):
    """กิจกรรมในงาน 41 มิติจาก O*NET — แกนของแบบทดสอบฝั่ง "ยังไม่รู้"

    🔴 ทำไมใช้ตัวนี้ ไม่ใช่ RIASEC (วัดกับ 8 อาชีพเป้าหมายแล้ว ดู pipeline/out/discrimination.json)

        เครื่องมือ         มิติ   คู่ที่แยกยากที่สุด
        Work Activities   41     2.29   🟢 แยกได้ทุกคู่
        RIASEC             6     0.43   🔴 หุ่นยนต์กับกระบวนการผลิตแทบแยกไม่ออก
        Work Values        6     0.69   🔴
        Work Styles       16     0.91   🔴

    RIASEC ทำให้วิศวะทุกสายกองรวมกันที่ "Realistic + Investigative" ซึ่งคือปัญหา
    "แบบทดสอบแนะนำให้เป็นพยาบาลทุกคน" ในเวอร์ชันของเรา
    """

    __tablename__ = "work_activity"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)  # เช่น 4.A.1.b.2
    name_en: Mapped[str] = mapped_column(Text)
    name_th: Mapped[str | None] = mapped_column(Text)
    description_th: Mapped[str | None] = mapped_column(Text)
    group_id: Mapped[str] = mapped_column(String(16))   # 4 หมวดใหญ่ — ใช้จัดกลุ่มข้อคำถาม
    group_th: Mapped[str | None] = mapped_column(Text)

    @property
    def display_name(self) -> str:
        return self.name_th or self.name_en


class TargetActivityProfile(Base):
    """อาชีพ × กิจกรรม × ความสำคัญ (สเกล 1–5 ของ O*NET) — ใช้จับคู่กับคำตอบผู้ใช้"""

    __tablename__ = "target_activity_profile"
    __table_args__ = (UniqueConstraint("target_id", "activity_id", name="uq_target_activity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_id: Mapped[str] = mapped_column(ForeignKey("career_target.id"))
    activity_id: Mapped[str] = mapped_column(ForeignKey("work_activity.id"))
    importance: Mapped[float] = mapped_column(Float)

    target: Mapped[CareerTarget] = relationship(back_populates="activity_profile")


class ActivityItem(Base):
    """ข้อคำถามหนึ่งข้อ — ถามถึง "กิจกรรม" ที่จับต้องได้ ไม่ใช่ถามถึงตัวผู้ใช้

    ✅ "ตรวจเครื่องจักรว่าชิ้นไหนกำลังจะพัง แล้วบอกได้ว่าต้องซ่อมตรงไหน"
    ❌ "คุณเป็นคนละเอียดรอบคอบไหม"
    """

    __tablename__ = "activity_item"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    activity_id: Mapped[str] = mapped_column(ForeignKey("work_activity.id"))
    prompt_th: Mapped[str] = mapped_column(Text)
    context_th: Mapped[str | None] = mapped_column(Text)  # ตัวอย่างเสริมให้เห็นภาพ
    reverse: Mapped[bool] = mapped_column(Boolean, default=False)


class JobPosting(Base):
    """ประกาศงานจริงที่เก็บมาด้วยมือ — ห้ามเขียน scraper (แผน §2 D5)"""

    __tablename__ = "job_posting"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    target_id: Mapped[str | None] = mapped_column(ForeignKey("career_target.id"))
    org: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    collected_at: Mapped[str] = mapped_column(String(32))
    collected_by: Mapped[str | None] = mapped_column(String(64))
    raw_text: Mapped[str] = mapped_column(Text)


class PostingExtraction(Base):
    """ผลที่ LLM สกัดจากประกาศงาน — span ต้อง verify กับ raw_text ได้"""

    __tablename__ = "posting_extraction"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    posting_id: Mapped[str] = mapped_column(ForeignKey("job_posting.id"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skill.id"))
    span_text: Mapped[str] = mapped_column(Text)
    min_level: Mapped[int] = mapped_column(Integer, default=2)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)


class LearningResource(Base):
    """ทางไปถึงทักษะหนึ่งตัว — วิชา SIIT · คอร์ส · เซอร์ · โปรเจกต์ · กิจกรรม

    ก้าวหนึ่งใน roadmap มีทางไปถึงได้หลายทาง ผู้ใช้เลือกเองตามเวลา งบ และชั้นปี
    """

    __tablename__ = "learning_resource"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(24))
    # siit_course | online_course | certificate | project | activity | internship | competition
    title: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    est_hours: Mapped[int] = mapped_column(Integer)
    cost_baht: Mapped[int] = mapped_column(Integer, default=0)
    min_year: Mapped[int] = mapped_column(Integer, default=1)  # ชั้นปีต่ำสุดที่ลงได้
    proof_of_done: Mapped[str] = mapped_column(Text)  # เสร็จแล้วมีอะไรยืนยัน
    data_status: Mapped[str] = mapped_column(String(24), default="placeholder")

    teaches: Mapped[list["ResourceSkill"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )


class ResourceSkill(Base):
    __tablename__ = "resource_skill"
    __table_args__ = (UniqueConstraint("resource_id", "skill_id", name="uq_resource_skill"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("learning_resource.id"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skill.id"))
    reaches_level: Mapped[int] = mapped_column(Integer, default=2)

    resource: Mapped[LearningResource] = relationship(back_populates="teaches")


# ═══════════════════════ ฝั่งผู้ใช้ ═══════════════════════


class User(Base):
    __tablename__ = "app_user"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    entry: Mapped[str] = mapped_column(String(16), default="known")  # known | unsure
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Consent(Base):
    """ความยินยอมแยกตามวัตถุประสงค์ (PDPA)

    "ใช้เพื่อสร้าง roadmap" ≠ "ส่งข้อความใน CV ไปให้ผู้ให้บริการ LLM"
    ผู้ใช้ต้องกดยินยอมข้อหลังแยกต่างหากก่อนระบบจะส่งอะไรออกไปข้างนอก
    """

    __tablename__ = "consent"
    __table_args__ = (UniqueConstraint("user_id", "purpose", name="uq_consent"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"))
    purpose: Mapped[str] = mapped_column(String(32))  # store_document | send_to_llm | share
    granted: Mapped[bool] = mapped_column(Boolean, default=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LearnerProfile(Base):
    """เงื่อนไขจริงที่ทำให้ roadmap ทำได้จริง — ไม่ใช่ที่มาของความสามารถ"""

    __tablename__ = "learner_profile"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"), unique=True)

    field: Mapped[str | None] = mapped_column(String(16))       # สาขาที่เรียน · None = ยังไม่ได้เลือก
    education_level: Mapped[str | None] = mapped_column(String(32))
    year: Mapped[int | None] = mapped_column(Integer)
    gpa: Mapped[float | None] = mapped_column(Float)            # ไม่บังคับเสมอ
    hours_per_week: Mapped[int | None] = mapped_column(Integer)
    budget_baht: Mapped[int | None] = mapped_column(Integer)
    obligation_json: Mapped[dict | None] = mapped_column(JSONType)  # เงื่อนไขชดใช้ทุน
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class SelfReportedSkill(Base):
    """ทักษะที่ผู้ใช้บอกว่าตัวเองมี — 🔴 ไม่มีหลักฐาน ห้ามปนกับ ExtractedSkill"""

    __tablename__ = "self_reported_skill"
    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_self_skill"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skill.id"))
    level: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UserDocument(Base):
    """CV / พอร์ต / repo ที่ผู้ใช้ส่งเข้ามา — ข้อมูลส่วนบุคคล ต้องลบได้"""

    __tablename__ = "user_document"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"))
    kind: Mapped[str] = mapped_column(String(16))  # pdf | text | github | linkedin | portfolio
    source_ref: Mapped[str | None] = mapped_column(Text)  # ชื่อไฟล์ หรือ URL
    raw_text: Mapped[str] = mapped_column(Text)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    extracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extractor: Mapped[str | None] = mapped_column(String(24))  # mock | anthropic
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ExtractedSkill(Base):
    """ทักษะที่สกัดจากเอกสารของผู้ใช้ — 🔴 มีหลักฐานชี้กลับไปได้เสมอ

    span_start/end/text ห้ามเป็น null และ span_text ต้องเป็น substring
    ของ user_document.raw_text ตรงตัว (มี test บังคับ)
    """

    __tablename__ = "extracted_skill"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("user_document.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skill.id"))
    span_start: Mapped[int] = mapped_column(Integer)
    span_end: Mapped[int] = mapped_column(Integer)
    span_text: Mapped[str] = mapped_column(Text)
    level: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    user_status: Mapped[str] = mapped_column(String(16), default="pending")
    # pending | confirmed | rejected | edited


# ── ฝั่ง "ยังไม่รู้" ──


class InterestResponse(Base):
    __tablename__ = "interest_response"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"))
    question_id: Mapped[str] = mapped_column(String(32))
    answer: Mapped[str] = mapped_column(Text)


class PersonalityResult(Base):
    """ผล RIASEC — 🔴 ป้อนเข้าการ *เสนอเป้าหมาย* เท่านั้น ไม่แตะการคำนวณ roadmap (แผน §2 D4)"""

    __tablename__ = "personality_result"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"), unique=True)
    instrument: Mapped[str] = mapped_column(String(16), default="riasec")
    scores_json: Mapped[dict] = mapped_column(JSONType)
    top_codes: Mapped[list] = mapped_column(JSONType)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ActivityResponse(Base):
    """คำตอบต่อข้อคำถามหนึ่งข้อ — 🔒 ห้ามไหลเข้า ExtractedSkill

    ความอยากทำกิจกรรมไม่ใช่หลักฐานว่าทำเป็น · ทักษะมาจาก CV เท่านั้น
    """

    __tablename__ = "activity_response"
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uq_activity_response"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"))
    item_id: Mapped[str] = mapped_column(ForeignKey("activity_item.id"))
    answer: Mapped[int] = mapped_column(Integer)  # -1 ไม่อยากทำ · 0 เฉย ๆ · +1 อยากทำ
    asked_at_round: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TargetMatch(Base):
    """ผลจับคู่อาชีพของผู้ใช้หนึ่งคน — เก็บคะแนนแยกตามสัญญาณ เพื่อให้ย้อนที่มาได้

    🔒 `traced_to_json` ว่าง = ห้ามแสดง — เหมือนกติกาใน draft 1
       ทุกอาชีพที่เสนอต้องบอกได้ว่ากิจกรรมข้อไหนดันมันขึ้นมา และข้อไหนดันลง
    """

    __tablename__ = "target_match"
    __table_args__ = (UniqueConstraint("user_id", "target_id", name="uq_target_match"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"))
    target_id: Mapped[str] = mapped_column(ForeignKey("career_target.id"))
    score: Mapped[float] = mapped_column(Float)
    score_activity: Mapped[float] = mapped_column(Float, default=0.0)      # ① แบบทดสอบกิจกรรม
    score_extracted: Mapped[float] = mapped_column(Float, default=0.0)     # ② ทักษะจาก CV
    score_self_reported: Mapped[float] = mapped_column(Float, default=0.0) # ③ ทักษะที่กรอกเอง
    score_values: Mapped[float] = mapped_column(Float, default=0.0)        # ④ ค่านิยม/บุคลิก
    rank_no: Mapped[int] = mapped_column(Integer, default=0)
    is_unconsidered: Mapped[bool] = mapped_column(Boolean, default=False)  # "อาจไม่เคยคิดถึง"
    traced_to_json: Mapped[list] = mapped_column(JSONType)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ── เป้าหมายและ roadmap ──


class UserGoal(Base):
    __tablename__ = "user_goal"
    __table_args__ = (UniqueConstraint("user_id", "target_id", name="uq_user_goal"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"))
    target_id: Mapped[str] = mapped_column(ForeignKey("career_target.id"))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(16), default="self")  # self | suggested
    traced_to_json: Mapped[list | None] = mapped_column(JSONType)  # ถ้า suggested ต้องบอกที่มาได้
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Roadmap(Base):
    __tablename__ = "roadmap"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.id"))
    target_id: Mapped[str] = mapped_column(ForeignKey("career_target.id"))
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    steps_done: Mapped[int] = mapped_column(Integer, default=0)
    coverage: Mapped[float] = mapped_column(Float, default=0.0)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    steps: Mapped[list["RoadmapStep"]] = relationship(
        back_populates="roadmap", cascade="all, delete-orphan"
    )


class RoadmapStep(Base):
    __tablename__ = "roadmap_step"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    roadmap_id: Mapped[str] = mapped_column(ForeignKey("roadmap.id"))
    skill_id: Mapped[str] = mapped_column(ForeignKey("skill.id"))
    order_no: Mapped[int] = mapped_column(Integer)
    current_level: Mapped[int] = mapped_column(Integer, default=0)
    target_level: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="locked")
    # done | current | locked
    evidence_kind: Mapped[str | None] = mapped_column(String(16))  # extracted | self_reported | None
    rank_score: Mapped[float] = mapped_column(Float, default=0.0)

    roadmap: Mapped[Roadmap] = relationship(back_populates="steps")
    options: Mapped[list["StepOption"]] = relationship(
        back_populates="step", cascade="all, delete-orphan"
    )


class StepOption(Base):
    """ทางไปถึงก้าวนี้หนึ่งทาง"""

    __tablename__ = "step_option"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    step_id: Mapped[str] = mapped_column(ForeignKey("roadmap_step.id"))
    resource_id: Mapped[str] = mapped_column(ForeignKey("learning_resource.id"))
    fits_time: Mapped[bool] = mapped_column(Boolean, default=True)
    fits_budget: Mapped[bool] = mapped_column(Boolean, default=True)
    fits_year: Mapped[bool] = mapped_column(Boolean, default=True)
    blocked_reason: Mapped[str | None] = mapped_column(Text)

    step: Mapped[RoadmapStep] = relationship(back_populates="options")
