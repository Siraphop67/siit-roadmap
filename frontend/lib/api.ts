/**
 * สัญญาระหว่างหน้าเว็บกับ API — `backend/app/api.py` · `api_discover.py`
 * `api_employer.py` · `api_skills.py`
 *
 * ทุกหน้าเรียกผ่านไฟล์นี้ไฟล์เดียว ห้ามยิง fetch ตรงจากหน้าจอ
 * เพราะถ้ารูปร่าง response เปลี่ยน เราอยากให้ TypeScript แดงที่เดียว ไม่ใช่ค่อย ๆ พังตอนรัน
 *
 * เจ้าของไฟล์: 🅲 (docs/TEAM.md §3) · อยากได้ฟิลด์เพิ่มให้บอก 🅳 อย่าไปแก้ api.py เอง
 *
 * 🔒 กติกาที่ไฟล์นี้ช่วยบังคับ (docs/TEAM.md §1)
 *    ข้อ 1 — ทักษะจาก CV กับที่กรอกเอง เป็นคนละ type และคนละฟิลด์ ไม่มีตัวช่วยไหนรวมให้
 *    ข้อ 3 — `ExtractedSpan.user_status` เริ่มที่ "pending" เสมอ ยังไม่ยืนยัน = ยังไม่นับ
 *    ข้อ 5 — `health()` กับ `meta()` บอกตามจริงว่าอะไรยัง mock เอาขึ้นจอได้เลย
 */

const BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:8000/api";

/** ระดับทักษะตรงกับ `settings.max_level` ฝั่ง backend — แก้ที่นั่นแล้วต้องมาแก้ที่นี่ด้วย */
export const MAX_LEVEL = 3;
export const LEVEL_LABELS: Record<number, string> = {
  1: "รู้จัก",
  2: "ทำได้เมื่อมีคนแนะ",
  3: "ทำเองได้",
};

// ══════════════════════ META ══════════════════════

export type Field = { id: string; name_th: string };
export type Obligation = { id: string; label: string; allowed_sectors: string[] | null };

export type Meta = {
  fields: Field[];
  education_levels: string[];
  obligations: Obligation[];
  sectors: Record<string, string>;
  resource_kinds: Record<ResourceKind, string>;
  extractor: string;
  /** ประกาศงานจริงที่เก็บมาแล้ว — 0 = requirement ยังเป็นชุดที่ทีมเขียนเอง */
  job_postings: number;
  /**
   * 🔴 ข้อความบอกข้อจำกัดตามจริง — เอาขึ้นจอ อย่าเก็บไว้เฉย ๆ
   * `notes.data` เปลี่ยนเองตามจำนวนประกาศงานที่มีจริง อย่า hardcode ฝั่งหน้าเว็บ
   */
  notes: { data: string; extractor: string };
};

export type Health = {
  ok: boolean;
  database: "postgres" | "sqlite";
  extractor: string;
  /** false = ตัวสกัดยังเป็นการจับคำสำคัญ ไม่ใช่ LLM — ห้ามให้หน้าจอพูดว่าเป็น AI */
  extractor_is_real_llm: boolean;
  skills: number;
  skill_edges: number;
  career_targets: number;
  learning_resources: number;
  /** 🔒 เป็น 0 จนกว่า 🅴 จะเก็บประกาศงานจริง — อย่าให้หน้าจอพูดเกินตัวเลขนี้ */
  job_postings: number;
};

// ══════════════════════ คลังอาชีพ ══════════════════════

/** เหตุผลที่อาชีพถูกกรอง — `field`/`obligation` ตัดถาวร · `education`/`gpa` แค่รอเวลา */
export type BlockKind = "field" | "obligation" | "education" | "gpa";
export type Block = { kind: BlockKind; message: string };

export type TargetCard = {
  id: string;
  title_th: string;
  title_en: string;
  summary: string;
  sector: string;
  sector_label: string;
  field_whitelist: string[];
  requirement_count: number;
  /**
   * ทักษะเด่นไม่เกิน 3 ตัว เรียงตาม `importance` มาแล้ว — ใช้ทำป้ายบนการ์ด
   * อยากได้ครบทุกข้อต้องเรียก `api.target(id)` · อย่าเรียงใหม่เอง ลำดับนี้มาจากเครื่องยนต์
   */
  top_skills: TopSkill[];
  /** 🔴 เป็น 0 ทุกอาชีพจนกว่าจะเก็บประกาศงานจริง (DECISIONS D11) */
  posting_count: number;
  data_status: string;
  /** ยังสมัครไม่ได้ตอนนี้ แต่ไม่ถูกตัดออก — แสดงเป็น "สมัครได้เมื่อถึงปี 3" */
  conditions_at_application: Block[];
};

export type TargetsResponse = {
  targets: TargetCard[];
  /** 🔒 ต้องขึ้นจอพร้อมเหตุผลทุกอัน — อาชีพหายเงียบ ๆ คือบั๊ก ไม่ใช่ฟีเจอร์ */
  filtered_out: { id: string; title_th: string; reasons: Block[] }[];
  data_note: string;
};

export type TargetRequirementView = {
  skill_id: string;
  name_th: string;
  min_level: number;
  importance: number;
  /** พบในประกาศงานจริงกี่ประกาศ · 0 = ยังไม่มีประกาศยืนยัน */
  appears_in_n_postings: number;
  /**
   * 🔒 requirement ข้อนี้มาจากไหน — หน้าจอต้องแสดงต่างกัน (กติกาข้อ 5)
   * `curated` ทีมเขียนเอง · `postings` พบในประกาศจริง · `both` ทั้งคู่ (แข็งแรงที่สุด)
   */
  source: "curated" | "postings" | "both";
};

/**
 * requirement หนึ่งข้อ + ชื่ออังกฤษ — ใช้บนป้ายที่มีที่ว่างน้อย
 *
 * 🔴 `name_th` ของทักษะเป็นประโยคเต็ม ("เขียน SQL ดึงและรวมข้อมูลจากฐานข้อมูล")
 *    ไม่ใช่ชื่อสั้น · ป้ายเล็ก ๆ ควรใช้ `name_en` แต่ต้องเช็ค `name_en_is_placeholder` ก่อน
 */
export type TopSkill = TargetRequirementView & {
  name_en: string;
  /** true = ทักษะนี้ไม่มีตัวตรงใน O*NET ค่า `name_en` จึงเท่ากับ skill_id ห้ามเอาขึ้นจอ */
  name_en_is_placeholder: boolean;
};

export type TargetDetail = {
  id: string;
  title_th: string;
  title_en: string;
  summary: string;
  day_in_the_life: string;
  sector_label: string;
  field_whitelist: string[];
  min_education: string | null;
  min_gpa: number | null;
  salary_note: string;
  data_status: string;
  onet_soc_code: string | null;
  requirements: TargetRequirementView[];
};

// ══════════════════════ โปรไฟล์ ══════════════════════

export type ProfileBody = {
  user_id: string;
  field?: string | null;
  education_level?: string | null;
  year?: number | null;
  gpa?: number | null;
  hours_per_week?: number | null;
  budget_baht?: number | null;
  obligation_id?: string | null;
  /** skill_id → level · ส่ง object เปล่าเพื่อล้างทั้งชุด · ไม่ส่ง = ไม่แตะของเดิม */
  self_reported_skills?: Record<string, number> | null;
};

export type ProfileView = {
  exists: boolean;
  field?: string | null;
  education_level?: string | null;
  year?: number | null;
  gpa?: number | null;
  hours_per_week?: number | null;
  budget_baht?: number | null;
  obligation_id?: string | null;
  /** 🔒 ที่ผู้ใช้กรอกเอง — ไม่มีหลักฐาน ห้ามแสดงปนกับ skills_from_cv */
  self_reported_skills: Record<string, number>;
};

// ══════════════════════ ส่งผลงาน + สกัด ══════════════════════

export type DocumentKind = "pdf" | "text" | "github" | "linkedin";

export type IngestResult = {
  document_id: string;
  kind: DocumentKind;
  char_count: number;
  extracted_count: number;
  extractor: string;
  /** เช่น เหตุผลที่ LinkedIn ต้องให้วางเอง — ถ้าไม่ว่างให้แสดง */
  note: string;
};

export type ExtractionStatus = "pending" | "confirmed" | "rejected" | "edited";

/** ⭐ span ชี้กลับไปที่ raw_text ตรง ๆ — `raw_text.slice(span_start, span_end)` ต้องได้ span_text */
export type ExtractedSpan = {
  id: string;
  skill_id: string;
  name_th: string;
  span_start: number;
  span_end: number;
  span_text: string;
  level: number;
  confidence: number;
  user_status: ExtractionStatus;
};

export type DocumentReview = {
  document_id: string;
  kind: DocumentKind;
  source_ref: string;
  raw_text: string;
  extractor: string;
  extracted: ExtractedSpan[];
  note: string;
};

export type ConfirmResult = {
  updated: number;
  /** skill_id → level ที่นับเป็นหลักฐานแล้ว */
  confirmed_skills: Record<string, number>;
};

// ══════════════════════ ROADMAP ══════════════════════

export type ResourceKind =
  | "siit_course"
  | "online_course"
  | "certificate"
  | "project"
  | "activity"
  | "internship"
  | "competition";

export type StepStatus = "current" | "in_progress" | "flexible" | "locked";
export type EvidenceKind = "extracted" | "self_reported" | "both";

export type StepOption = {
  resource_id: string;
  kind: ResourceKind;
  kind_label: string;
  title: string;
  provider: string | null;
  est_hours: number | null;
  cost_baht: number | null;
  min_year: number | null;
  proof_of_done: string | null;
  /** true = ระบบสร้างโปรเจกต์ให้เอง ไม่ได้มาจากคลัง — ควรติดป้ายให้ต่างจากของจริง */
  generated: boolean;
  fits: boolean;
  /** ไม่ null = ตัวเลือกนี้ติดเงื่อนไข 🔒 ต้องแสดงพร้อมเหตุผล ห้ามซ่อน */
  blocked_reason: string | null;
};

export type RoadmapStep = {
  skill_id: string;
  name_th: string;
  order_no: number;
  status: StepStatus;
  /** 🔒 กติกาข้อ 4 — ก้าวที่กดได้ต้องเป็นก้าวที่ระบบจัดอันดับให้ ใช้ค่านี้ อย่าคำนวณเอง */
  actionable: boolean;
  current_level: number;
  target_level: number;
  /** 🔒 มาจาก CV หรือกรอกเอง — ป้ายต้องต่างกัน (กติกาข้อ 1) */
  evidence_kind: EvidenceKind | null;
  unlock_count: number;
  options: StepOption[];
};

export type RoadmapResponse = {
  target: {
    id: string;
    title_th: string;
    title_en: string;
    summary: string;
    data_status: string;
  };
  total_steps: number;
  steps_done: number;
  coverage: number;
  evidence_summary: { from_cv: number; self_reported: number; note: string };
  steps: RoadmapStep[];
  /** วาดเป็นกราฟก็ได้ · ถ้าวาดเป็นรายการให้ใช้ `order_no` แทน */
  edges: { from: string; to: string }[];
  legend: Record<StepStatus, string>;
};

/**
 * เส้นทางที่ผู้ใช้เคยเปิดดู — เมนู "เส้นทางของฉัน" กับ "ประวัติ" ใช้รายการเดียวกัน
 *
 * 🔴 ไม่มีปุ่ม "บันทึก" ในระบบ · ทุกครั้งที่เรียก `api.roadmap()` ระบบเก็บผลไว้เองอยู่แล้ว
 *    รายการนี้จึงคือ *ทุกอาชีพที่เคยเปิดดู* ไม่ใช่สิ่งที่ผู้ใช้เลือกเก็บ
 *    หน้าจอห้ามเขียนว่า "บันทึกแล้ว" — ถ้าอยากได้ปุ่มบันทึกจริงต้องให้ 🅳 เพิ่มคอลัมน์ก่อน
 */
export type RoadmapListItem = {
  target_id: string;
  title_th: string;
  title_en: string;
  data_status: string | null;
  total_steps: number;
  steps_done: number;
  coverage: number;
  /** 🔴 เวลา UTC ไม่มี offset ต่อท้าย (เหมือน `uploaded_at` ใน MeResponse) — ต้อง +7 เอง */
  computed_at: string;
  /** เป้าหมายหลักที่ตั้งไว้ตอนนี้ · เปิดดูอาชีพอื่นไม่ได้เปลี่ยนค่านี้ ต้องเรียก `api.setGoal` */
  is_primary_goal: boolean;
  /** 🔒 กติกาข้อ 4 — ก้าวเดียวกับที่ระบบจัดอันดับให้ในหน้า roadmap ใช้ค่านี้ อย่าคำนวณเอง */
  next_step: { skill_id: string; name_th: string } | null;
};

export type RoadmapListResponse = {
  roadmaps: RoadmapListItem[];
  /** ไม่ว่าง = `roadmaps` ว่าง และนี่คือข้อความที่ต้องขึ้นจอ ห้ามโชว์รายการเปล่าเงียบ ๆ */
  empty_message: string;
  note: string;
};

// ══════════════════════ กราฟทักษะ ══════════════════════
//
// กราฟทั้งใบ 73 ทักษะ · ต่างจาก `edges` ใน RoadmapResponse ที่เป็น subgraph ของอาชีพเดียว
// 🔴 API ส่งกราฟเต็มเสมอ ไม่มีตัวกรองฝั่ง server — กรองบนหน้าจอเอา (73 node เล็กพอ)

/** หมวดของทักษะ เช่น `foundation` `tool` `software` — ชื่อไทยมาใน `SkillGraph.categories` */
export type SkillCategory = string;

export type SkillRef = {
  id: string;
  name_en: string;
  name_th: string | null;
  category: SkillCategory;
  category_th: string;
  /** true = `name_en` เท่ากับ id เพราะทักษะนี้ไม่มีตัวตรงใน O*NET — ใช้ `name_th` แทน */
  name_en_is_placeholder: boolean;
};

export type SkillNode = SkillRef & {
  source: "onet" | "market" | "manual";
  source_th: string;
  /** false = ทำเมื่อไหร่ก็ได้ ไม่ต้องรอ prerequisite */
  order_strict: boolean;
  prereq_count: number;
  unlock_count: number;
  career_count: number;
  resource_count: number;
  /**
   * 🔒 กติกาข้อ 1 — สองค่านี้แยกกันเสมอ ห้ามรวมเป็นตัวเลขเดียวบนหน้าจอ
   * null = ยังไม่มีหลักฐานทางนั้น · ที่ยืนยันจาก CV กับที่กรอกเองต้องดูออกว่าต่างกัน
   */
  level_from_cv: number | null;
  level_self_reported: number | null;
};

export type SkillGraph = {
  nodes: SkillNode[];
  edges: { from: string; to: string; reviewed_by_human: boolean }[];
  /** ใช้ทำ legend — `count` บวกกันได้เท่าจำนวน node พอดี */
  categories: { id: SkillCategory; label_th: string; count: number }[];
  counts: { skills: number; edges: number; roots: number };
  /** null = เรียกแบบไม่ส่ง userId */
  you: { from_cv: number; self_reported: number } | null;
  /** 🔒 ข้อจำกัดตามจริง — `labels` ไม่ว่างเมื่อมีทักษะที่ยังไม่มีชื่ออังกฤษ เอาขึ้นจอได้ */
  notes: { labels: string; edges: string };
};

export type SkillCareerLink = {
  target_id: string;
  title_th: string;
  title_en: string;
  sector_label: string;
  min_level: number;
  importance: number;
  appears_in_n_postings: number;
  source: "curated" | "postings" | "both";
};

export type SkillResource = {
  id: string;
  kind: ResourceKind;
  kind_label: string;
  title: string;
  provider: string | null;
  url: string | null;
  est_hours: number | null;
  cost_baht: number | null;
  min_year: number | null;
  proof_of_done: string | null;
  /** เรียนอันนี้จบแล้วไปถึงระดับไหน (1–3) */
  reaches_level: number;
  /** 🔴 "placeholder" = ชื่อทั่วไป ยังไม่ใช่วิชาหรือคอร์สจริงที่เปิดสอนอยู่ */
  data_status: string;
};

export type SkillDetail = SkillRef & {
  description: string | null;
  source: "onet" | "market" | "manual";
  source_th: string;
  onet_element_id: string | null;
  order_strict: boolean;
  prereqs: SkillRef[];
  unlocks: SkillRef[];
  /** ⭐ ได้ทักษะนี้แล้วเปิดทางไปอีกกี่ตัว (นับต่อเนื่องทั้งสาย) — ใช้บอกว่าคุ้มลงแรงแค่ไหน */
  unlocks_total: number;
  supported_careers: SkillCareerLink[];
  resources: SkillResource[];
  /** null = เรียกแบบไม่ส่ง userId · `evidence` คือ span จริงใน CV (กติกาข้อ 2) */
  you: {
    level_from_cv: number | null;
    level_self_reported: number | null;
    evidence: {
      document_id: string;
      span_start: number;
      span_end: number;
      span_text: string;
      level: number;
      confidence: number;
    }[];
  } | null;
  notes: { careers: string; resources: string };
};

// ══════════════ ฝั่ง "ยังไม่รู้ว่าอยากเป็นอะไร" ══════════════

/** 🔒 ไม่มีชื่ออาชีพในข้อคำถามโดยตั้งใจ — ผู้ใช้ตอบต่อกิจกรรม ไม่ใช่ต่อชื่ออาชีพ */
export type DiscoverItem = {
  item_id: string;
  no: number;
  prompt_th: string;
  context_th: string | null;
  group_th: string | null;
};

/** -1 ไม่อยากทำ · 0 เฉย ๆ · +1 อยากทำ */
export type ActivityAnswer = -1 | 0 | 1;

export type MatchReason = {
  kind: "activity" | "extracted_skill" | "self_reported_skill" | "values";
  ref_id: string;
  label: string;
  direction: "wants_and_does" | "unwanted_but_core";
  /** ประโยคพร้อมขึ้นจอ — ใช้ตัวนี้ อย่าแปล direction เอง */
  reads_as: string;
};

export type WantsReason = MatchReason & { direction: "wants_and_does" };
export type HeadsUp = MatchReason & { direction: "unwanted_but_core" };

export type MatchCard = {
  target_id: string;
  title_th: string;
  title_en: string;
  summary: string;
  sector_label: string;
  field_whitelist: string[];
  rank_no: number;
  /**
   * 🔴 ตำแหน่งเทียบกันในกลุ่ม 0–100 — **ไม่ใช่เปอร์เซ็นต์ความเหมาะสม**
   * อันดับ 1 ได้ 100 เสมอเพราะเป็นอันดับ 1 · ต้องแสดงคู่กับ `scale_note` เสมอ
   * คะแนนดิบไม่ถูกส่งออกมาเลย เพราะมันกองกันที่ 0.88–0.96 จนอ่านผิดได้ง่าย
   */
  relative_score: number;
  /** "อาชีพที่คุณอาจไม่เคยคิดถึง" — คะแนนดี แต่อยู่นอกสาขาที่เรียน */
  is_unconsidered: boolean;
  /**
   * "ทำไมถึงเสนออาชีพนี้" — มีแต่ข้อที่ผู้ใช้อยากทำ **และ** งานนี้ได้ทำเยอะ
   * 🔴 เอาไปพิมพ์ได้ตรง ๆ ทั้งลิสต์ · ข้อที่ผู้ใช้ไม่อยากทำถูกแยกไปที่ `heads_up` แล้ว
   *    ถ้ารวมกัน หน้าจอจะขึ้นว่า "เสนองานนี้เพราะคุณไม่อยากขายของ" ซึ่งคือปัญหาที่ D3 แก้ไปแล้ว
   */
  reasons: WantsReason[];
  /** "สิ่งที่ควรรู้ก่อนเลือก" — งานนี้ต้องทำเยอะ ทั้งที่ผู้ใช้บอกว่าไม่อยากทำ · วางคนละที่กับ reasons */
  heads_up: HeadsUp[];
  reasons_against: { label: string; ref_id: string }[];
  /** ติดเงื่อนไขทุน/สาขา — ติดป้ายไว้ ไม่ได้หายไปจากผล */
  blocked_reasons: Block[];
};

export type DiscoverNext = {
  done: boolean;
  /** ทำไมยังถามต่อ หรือทำไมถึงจบ — อ้างชื่ออาชีพจริง เอาขึ้นจอได้ตรง ๆ */
  reason: string;
  answered: number;
  min_items: number;
  max_items: number;
  item: DiscoverItem | null;
  /** ⭐ โผล่ทุก 6 ข้อ — ให้ผู้ใช้เห็นว่ากำลังไปทางไหนระหว่างทำ ไม่ต้องรอจบ */
  interim: { separated: boolean; top: MatchCard[]; scale_note: string } | null;
};

export type AnswerResult = {
  recorded: boolean;
  answered: number;
  separated: boolean;
  feedback_due: boolean;
  can_finish: boolean;
};

export type DiscoverResult = {
  answered: number;
  separated: boolean;
  /** ไม่ว่าง = อันดับ 1 กับ 2 ยังไม่ห่างพอ ต้องขึ้นจอ ห้ามโชว์อันดับเฉย ๆ */
  separation_message: string;
  /** ไม่ว่าง = `targets` ว่าง และนี่คือเหตุผลว่าทำไม พร้อมทางออก */
  empty_message: string;
  targets: MatchCard[];
  unconsidered: MatchCard | null;
  unconsidered_note: string;
  scale_note: string;
  weights_note: string;
  next_step: string;
};

// ══════════════ ฝั่งบริษัทลงประกาศรับสมัคร ══════════════
//
// 🔒 ทางเดียว — ไม่มีอะไรในส่วนนี้คืนข้อมูลนักศึกษาให้บริษัท และจะไม่มี
//    บริษัทลงประกาศได้ · นักศึกษาเห็นประกาศแล้วไปสมัครที่ url หรืออีเมลของบริษัทเอง

export type EmploymentType = "new_grad" | "internship" | "coop" | "experienced";
export type PostingStatus = "pending" | "approved" | "rejected";

export type EmployerMeta = {
  sectors: Record<string, string>;
  employment_types: Record<EmploymentType, string>;
  targets: { id: string; title_th: string }[];
  /** 🔴 เอาขึ้นหน้าฟอร์ม — บริษัทต้องรู้ก่อนกรอกว่าต้องผ่านการตรวจ และจะไม่เห็นข้อมูลนักศึกษา */
  notes: { review: string; privacy: string; raw_text: string };
};

export type PostingSubmission = {
  org: string;
  title: string;
  url: string;
  sector: string;
  employment_type: EmploymentType;
  /** ข้อความประกาศตามต้นฉบับ · 🔴 ห้ามมีอีเมลหรือเบอร์โทรในนี้ ใส่ที่ contact_email แทน */
  raw_text: string;
  submitted_by: string;
  target_id?: string | null;
  location?: string | null;
  salary_text?: string | null;
  posted_at?: string | null;
  closes_at?: string | null;
  requires_field?: string[] | null;
  requires_gpa?: number | null;
  requires_education?: string | null;
  note?: string | null;
  contact_email?: string | null;
};

export type SubmissionResult = {
  posting_id: string;
  /** 🔒 เป็น "pending" เสมอ — ไม่มีทางลัดให้ขึ้นจอทันที */
  status: "pending";
  warnings: string[];
  message: string;
  check_status_at: string;
};

export type PostingStatusView = {
  posting_id: string;
  org: string;
  title: string;
  status: PostingStatus;
  status_th: string;
  submitted_at: string;
  reviewed_at: string | null;
  review_note: string | null;
};

export type ReviewRow = {
  posting_id: string;
  org: string;
  title: string;
  url: string | null;
  target_id: string | null;
  submitted_by: string | null;
  submitted_at: string;
  contact_email: string | null;
  raw_text: string;
  char_count: number;
};

export type ReviewQueue = {
  status: PostingStatus;
  count: number;
  postings: ReviewRow[];
  /** รายการที่คนตรวจต้องไล่ดู — แสดงคู่กับประกาศ อย่าให้กดอนุมัติรัว ๆ ได้ */
  checklist: string[];
};

/** ข้อผิดพลาดจากฟอร์มบริษัท — API ส่งกลับมาทุกข้อพร้อมกัน คนกรอกจะได้แก้รอบเดียว */
export type SubmissionErrors = { errors: string[]; warnings: string[] };

/** แกะรายการข้อผิดพลาดออกจาก ApiError ของฟอร์มบริษัท · ไม่ใช่รูปแบบนี้จะได้ null */
export function submissionErrors(e: unknown): SubmissionErrors | null {
  if (!(e instanceof ApiError)) return null;
  const d = e.detail as SubmissionErrors | undefined;
  return d && Array.isArray(d.errors)
    ? { errors: d.errors, warnings: d.warnings ?? [] }
    : null;
}

// ══════════════════════ ข้อมูลของฉัน ══════════════════════

export type SkillLine = { skill_id: string; name_th: string; level: number };

export type MeResponse = {
  documents: {
    id: string;
    kind: DocumentKind;
    source_ref: string;
    char_count: number;
    uploaded_at: string;
  }[];
  /** 🔒 สองรายการนี้แยกกันตั้งแต่ API — หน้าจอห้ามรวม (กติกาข้อ 1) */
  skills_from_cv: SkillLine[];
  skills_self_reported: SkillLine[];
  goals: { target_id: string; is_primary: boolean }[];
};

// ══════════════════════ ตัวเรียก ══════════════════════

/** error ที่รู้ทั้งข้อความไทยจาก API และรหัสสถานะ — หน้าจอเลือกใช้ได้ตามต้องการ */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    /**
     * body ที่ API ส่งมาดิบ ๆ — บาง endpoint ส่งรายการข้อผิดพลาดมาเป็นก้อน
     * (ฟอร์มบริษัทส่งกลับทุกข้อพร้อมกัน) ซึ่งถ้าย่อเป็นข้อความเดียวแล้วข้อมูลหาย
     * ใช้ `submissionErrors(e)` แกะออกมา อย่าไปแกะ message เอง
     */
    readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function readError(res: Response): Promise<{ message: string; detail?: unknown }> {
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === "string") return { message: detail, detail };
    // FastAPI ส่ง array เมื่อ validation ของ pydantic ไม่ผ่าน — ผู้ใช้ไม่ได้อยากอ่าน JSON
    if (Array.isArray(detail)) {
      return { message: "ข้อมูลที่ส่งไปยังไม่ครบหรือผิดรูปแบบ", detail };
    }
    // ก้อนที่เราส่งเอง เช่น {errors: [...], warnings: [...]} จากฟอร์มบริษัท
    if (detail && typeof detail === "object") {
      const errors = (detail as { errors?: unknown }).errors;
      return {
        message:
          Array.isArray(errors) && errors.length
            ? String(errors[0])
            : "ข้อมูลที่กรอกยังไม่ผ่านการตรวจ",
        detail,
      };
    }
  } catch {
    /* body ไม่ใช่ JSON — ตกไปใช้ข้อความตามรหัสสถานะ */
  }
  if (res.status === 404) return { message: "ไม่พบข้อมูลที่ขอ" };
  if (res.status >= 500) return { message: "ระบบฝั่งเซิร์ฟเวอร์มีปัญหา ลองใหม่อีกครั้ง" };
  return { message: `เรียก API ไม่สำเร็จ (${res.status})` };
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, cache: "no-store" });
  } catch {
    // แยกกรณี "ยิงไม่ถึง" ออกจาก "ยิงถึงแล้วตอบ error" — เจอบ่อยตอนลืมเปิด backend
    throw new ApiError(`ต่อกับ API ไม่ได้ที่ ${BASE} — เปิด backend แล้วหรือยัง (make backend)`, 0);
  }
  if (!res.ok) {
    const { message, detail } = await readError(res);
    throw new ApiError(message, res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function json<T>(path: string, method: "POST" | "DELETE", body?: unknown): Promise<T> {
  return call<T>(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

const q = (params: Record<string, string | number | boolean | null | undefined>) => {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined) sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
};

export const api = {
  // ── meta ──
  health: () => call<Health>("/health"),
  meta: () => call<Meta>("/meta"),

  // ── หน้าแรก ──
  /** "known" = รู้แล้วว่าอยากไปไหน · "unsure" = เข้าทางแบบทดสอบ */
  createSession: (entry: "known" | "unsure" = "known") =>
    json<{ user_id: string; entry: string }>("/session", "POST", { entry }),

  // ── คลังอาชีพ ──
  /** ส่ง userId ไปด้วยถ้ามีโปรไฟล์แล้ว — API จะได้แยกอาชีพที่โดนเงื่อนไขทุนกรองออกให้ */
  targets: (userId?: string | null) => call<TargetsResponse>(`/targets${q({ user_id: userId })}`),
  target: (targetId: string) => call<TargetDetail>(`/targets/${encodeURIComponent(targetId)}`),

  // ── โปรไฟล์ ──
  getProfile: (userId: string) => call<ProfileView>(`/profile${q({ user_id: userId })}`),
  saveProfile: (body: ProfileBody) => json<{ saved: boolean }>("/profile", "POST", body),

  // ── ส่งผลงาน 4 ทาง ──
  // consent ต้องเป็น true ทุกครั้ง — API ปฏิเสธถ้าไม่ยินยอม เพราะ CV เป็นข้อมูลส่วนบุคคล
  portfolioText: (body: { user_id: string; text: string; consent: boolean }) =>
    json<IngestResult>("/portfolio/text", "POST", body),

  portfolioGithub: (body: { user_id: string; url: string; consent: boolean }) =>
    json<IngestResult>("/portfolio/github", "POST", body),

  /** LinkedIn ดึงอัตโนมัติไม่ได้ (ผิด ToS) — ผู้ใช้ต้องวาง `text` มาเอง */
  portfolioLinkedin: (body: {
    user_id: string;
    url: string;
    text: string;
    consent: boolean;
  }) => json<IngestResult>("/portfolio/linkedin", "POST", body),

  /** อัปโหลด PDF — user_id/consent ไปทาง query, ไฟล์ไปทาง multipart */
  portfolioUpload: (userId: string, file: File, consent: boolean) => {
    const form = new FormData();
    form.append("file", file);
    // ไม่ตั้ง Content-Type เอง ปล่อยให้เบราว์เซอร์ใส่ boundary ให้
    return call<IngestResult>(`/portfolio/upload${q({ user_id: userId, consent })}`, {
      method: "POST",
      body: form,
    });
  },

  // ── ตรวจผลสกัด ──
  document: (documentId: string) =>
    call<DocumentReview>(`/portfolio/${encodeURIComponent(documentId)}`),

  /** decisions: extracted_skill_id → confirmed|rejected|edited · levels ส่งเฉพาะอันที่แก้ระดับ */
  confirmExtraction: (
    documentId: string,
    body: {
      user_id: string;
      decisions: Record<string, "confirmed" | "rejected" | "edited">;
      levels?: Record<string, number>;
    },
  ) => json<ConfirmResult>(`/portfolio/${encodeURIComponent(documentId)}/confirm`, "POST", body),

  // ── ฝั่ง "ยังไม่รู้ว่าอยากเป็นอะไร" ──
  /** ข้อถัดไป 1 ข้อ — เลือกให้อัตโนมัติว่าถามข้อไหนถึงจะแยกอันดับ 1 กับ 2 ได้เร็วที่สุด */
  discoverNext: (userId: string) => call<DiscoverNext>(`/discover/next${q({ user_id: userId })}`),

  discoverAnswer: (body: { user_id: string; item_id: string; answer: ActivityAnswer }) =>
    json<AnswerResult>("/discover/answer", "POST", body),

  /** ตอบข้อเดิมซ้ำ = แก้คำตอบ ไม่ใช่เพิ่มแถวใหม่ */
  discoverResult: (userId: string) =>
    call<DiscoverResult>(`/discover/result${q({ user_id: userId })}`),

  /** ล้างคำตอบแบบทดสอบ — ไม่แตะ CV ทักษะที่ยืนยันแล้ว หรือโปรไฟล์ */
  discoverReset: (userId: string) =>
    json<{ cleared: number }>("/discover/reset", "POST", { user_id: userId }),

  // ── ฝั่งบริษัทลงประกาศ ──
  /** ตัวเลือกสำหรับหน้าฟอร์ม — ดึงจากที่เดียวกับที่ระบบตรวจ จะได้ไม่หลุดจากกัน */
  employerMeta: () => call<EmployerMeta>("/employer/meta"),

  /**
   * ส่งประกาศเข้าคิว — 🔒 ได้ `status: "pending"` เสมอ ไม่มีทางลัดให้ขึ้นจอทันที
   * กรอกไม่ผ่านจะโยน ApiError 422 · ใช้ `submissionErrors(e)` แกะรายการข้อผิดพลาดออกมา
   * API ส่งกลับมาทุกข้อพร้อมกัน หน้าจอควรแสดงทั้งหมด ไม่ใช่ทีละข้อ
   */
  submitPosting: (body: PostingSubmission) =>
    json<SubmissionResult>("/employer/posting", "POST", body),

  /** บริษัทเช็คสถานะประกาศของตัวเอง — posting_id ที่ได้ตอนส่งคือกุญแจ */
  postingStatus: (postingId: string) =>
    call<PostingStatusView>(`/employer/posting/${encodeURIComponent(postingId)}`),

  /** คิวรออนุมัติ — ต้องมี token · ไม่ได้ตั้ง EMPLOYER_REVIEW_TOKEN ใน .env จะได้ 503 */
  reviewQueue: (token: string, status: PostingStatus = "pending") =>
    call<ReviewQueue>(`/employer/review${q({ status })}`, {
      headers: { "X-Review-Token": token },
    }),

  reviewPosting: (
    token: string,
    postingId: string,
    body: { decision: "approved" | "rejected"; note?: string },
  ) =>
    call<{ posting_id: string; status: PostingStatus; next_step: string }>(
      `/employer/review/${encodeURIComponent(postingId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Review-Token": token },
        body: JSON.stringify(body),
      },
    ),

  // ── เป้าหมาย + roadmap ──
  setGoal: (body: { user_id: string; target_id: string }) =>
    json<{ target_id: string }>("/goal", "POST", body),

  /** ไม่ส่ง targetId = ใช้เป้าหมายหลักที่ตั้งไว้ · ยังไม่เคยตั้ง → ApiError status 409 */
  roadmap: (userId: string, targetId?: string | null) =>
    call<RoadmapResponse>(`/roadmap${q({ user_id: userId, target_id: targetId })}`),

  /** อาชีพที่เคยเปิด roadmap แล้ว เรียงจากล่าสุด — ไม่ใช่รายการที่กดบันทึกไว้ */
  roadmaps: (userId: string) =>
    call<RoadmapListResponse>(`/roadmaps${q({ user_id: userId })}`),

  // ── กราฟทักษะ ──
  /** ส่ง userId ถ้ามี — จะได้รู้ว่า node ไหนผู้ใช้มีแล้ว · ไม่ส่งก็ดูกราฟได้ */
  skills: (userId?: string | null) => call<SkillGraph>(`/skills${q({ user_id: userId })}`),

  skill: (skillId: string, userId?: string | null) =>
    call<SkillDetail>(`/skills/${encodeURIComponent(skillId)}${q({ user_id: userId })}`),

  // ── ข้อมูลของฉัน + PDPA ──
  me: (userId: string) => call<MeResponse>(`/me${q({ user_id: userId })}`),

  /** ลบจริงทุกตาราง กู้คืนไม่ได้ — ต้องให้ผู้ใช้ยืนยันก่อนเรียก */
  deleteMe: (userId: string) =>
    json<{ deleted: boolean; rows: Record<string, number> }>(
      `/me${q({ user_id: userId })}`,
      "DELETE",
    ),
};

// ══════════════════════ session ══════════════════════
// เข้าใช้ได้โดยไม่ต้องสมัคร — เก็บแค่ user_id ไว้ในเครื่อง ไม่มีชื่อ อีเมล เบอร์โทร

const KEY_USER = "siit-roadmap-user";
const KEY_TARGET = "siit-roadmap-target";
const KEY_DOCUMENT = "siit-roadmap-document";

const store = {
  get: (k: string) => (typeof window === "undefined" ? null : window.localStorage.getItem(k)),
  set: (k: string, v: string) => window.localStorage.setItem(k, v),
  del: (k: string) => window.localStorage.removeItem(k),
};

export const session = {
  read: () => store.get(KEY_USER),
  write: (userId: string) => store.set(KEY_USER, userId),

  readTarget: () => store.get(KEY_TARGET),
  writeTarget: (targetId: string) => store.set(KEY_TARGET, targetId),

  readDocument: () => store.get(KEY_DOCUMENT),
  writeDocument: (documentId: string) => store.set(KEY_DOCUMENT, documentId),

  /** ล้างร่องรอยในเครื่องนี้ — ไม่ได้ลบข้อมูลฝั่งเซิร์ฟเวอร์ ใช้ `api.deleteMe` สำหรับอันนั้น */
  clear: () => [KEY_USER, KEY_TARGET, KEY_DOCUMENT].forEach(store.del),
};

/** ได้ user_id ที่มีอยู่ หรือสร้างใหม่ให้ — หน้าไหนก็เรียกได้โดยไม่ต้องเช็คเอง */
export async function ensureSession(entry: "known" | "unsure" = "known"): Promise<string> {
  const existing = session.read();
  if (existing) return existing;
  const { user_id } = await api.createSession(entry);
  session.write(user_id);
  return user_id;
}
