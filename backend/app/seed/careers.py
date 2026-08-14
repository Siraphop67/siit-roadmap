"""คลังอาชีพเป้าหมาย 8 อาชีพ — ครอบคลุมทั้ง 7 สาขาวิศวะของ SIIT

⚠️ สถานะข้อมูล — อ่านก่อนอ้างอิงบนเวที
   `requirement` ในไฟล์นี้ **ยังไม่ได้มาจากประกาศงานจริง** — เป็นชุดที่เราเขียนขึ้นเอง
   โดยอิงโครงสร้างอาชีพของ O*NET (`onet_soc_code` ชี้ไปที่อาชีพจริงในฐานข้อมูล)
   ทุกแถวจึงมี `data_status = "placeholder"` และ `posting_count = 0`

   ท่อขั้นที่ 2 (`pipeline/2_extract_postings.py`) **ไม่ได้เขียนทับไฟล์นี้** — มันออกเป็น
   `pipeline/out/posting_requirements.json` แล้ว loader เอาไป *ผสม* กับชุดในไฟล์นี้
   ของที่เขียนไว้ตรงนี้ไม่ถูกลบเมื่อประกาศงานไม่ได้พูดถึง เพราะตัวสกัดจับได้เฉพาะคำที่เขียนตรงตัว
   ทุกแถวติดป้าย `source` ว่า curated · postings · both และ `data_status` ของอาชีพ
   เปลี่ยนเป็น "from_postings" เองเมื่อมีประกาศงานยืนยัน

   🔴 ห้ามพูดบนเวทีว่า requirement มาจากตลาดจริง จนกว่าจะรันท่อขั้นที่ 2 แล้ว
"""

from __future__ import annotations

PLACEHOLDER = "placeholder"

# (id, title_th, title_en, soc, sector, fields, min_edu, min_gpa, summary, day_in_the_life)
CAREER_TARGETS: list[dict] = [
    {
        "id": "SW-DEV",
        "title_th": "วิศวกรซอฟต์แวร์",
        "title_en": "Software Developer",
        "onet_soc_code": "15-1252.00",
        "onet_activity_soc": "15-1251.00",
        "activity_proxy_note": "O*NET ยังไม่มีข้อมูลกิจกรรมของ Software Developers (15-1252) — ใช้โปรไฟล์ของ Computer Programmers (15-1251) แทน",
        "sector": "private",
        "field_whitelist": ["CPE", "DE"],
        "min_education": "ปี 3",
        "min_gpa": 2.50,
        "summary": "ผู้อยู่เบื้องหลังการสร้างสรรค์ระบบที่ขับเคลื่อนชีวิตผู้คนในทุกวัน พร้อมดูแลเสถียรภาพให้ระบบทำงานได้อย่างราบรื่นแม้ในวันที่ผู้ใช้งานมหาศาล",
        "day_in_the_life": (
            "เช้าดูว่าเมื่อคืนระบบมีอะไรพังไหม · สายเขียนฟีเจอร์ใหม่พร้อมเทสต์ · "
            "บ่ายอ่านโค้ดของเพื่อนแล้วให้ความเห็น · เย็นปล่อยของขึ้นระบบจริงแล้วดูตัวเลข"
        ),
        "salary_note": "ยังไม่ได้เก็บข้อมูลเงินเดือนจริง",
        "requirements": [
            ("T-PY", 3, 1.0), ("SW-DS", 3, 1.0), ("SW-OOP", 2, 0.9),
            ("T-GIT", 2, 0.9), ("SW-TEST", 2, 0.8), ("SW-DB", 2, 0.7),
            ("SW-API", 2, 0.8), ("F-ENG", 2, 0.7), ("P-TEAM", 2, 0.6),
        ],
    },
    {
        "id": "DATA-ENG",
        "title_th": "วิศวกรข้อมูล",
        "title_en": "Data Engineer / Data Scientist",
        "onet_soc_code": "15-2051.00",
        "onet_activity_soc": "15-2051.01",
        "activity_proxy_note": "O*NET ยังไม่มีข้อมูลกิจกรรมของ Data Scientists (15-2051) — ใช้โปรไฟล์ของ Business Intelligence Analysts (15-2051.01) ซึ่งเป็นอาชีพย่อยของกันแทน",
        "sector": "private",
        "field_whitelist": ["DE", "CPE", "IE"],
        "min_education": "ปี 3",
        "min_gpa": 2.50,
        "summary": "ผู้เนรมิตข้อมูลที่กระจัดกระจายให้เป็นระบบระเบียบ ช่วยให้องค์กรวิเคราะห์และตัดสินใจทางธุรกิจได้อย่างเฉียบขาดและรวดเร็ว",
        "day_in_the_life": (
            "เช้าดูว่าท่อข้อมูลเมื่อคืนวิ่งครบไหม · สายไล่หาว่าตัวเลขที่เพี้ยนมาจากไหน · "
            "บ่ายคุยกับฝ่ายผลิตว่าเขาอยากรู้อะไร · เย็นทำแดชบอร์ดให้เขาดูเอง"
        ),
        "salary_note": "ยังไม่ได้เก็บข้อมูลเงินเดือนจริง",
        "requirements": [
            ("T-PY", 3, 1.0), ("T-SQL", 3, 1.0), ("DA-CLEAN", 3, 1.0),
            ("DA-PIPE", 2, 0.9), ("T-STAT", 2, 0.8), ("T-VIZ", 2, 0.8),
            ("DA-ML", 2, 0.6), ("F-ENG", 2, 0.7),
        ],
    },
    {
        "id": "ROBOT-ENG",
        "title_th": "วิศวกรหุ่นยนต์และระบบอัตโนมัติ",
        "title_en": "Robotics / Automation Engineer",
        "onet_soc_code": "17-2199.08",
        "onet_activity_soc": "17-2199.08",
        "activity_proxy_note": None,
        "sector": "academic",
        "field_whitelist": ["ME", "EE", "CPE"],
        "min_education": "ปี 2",
        "min_gpa": 2.75,
        "summary": "ผู้สร้างชีวิตให้เครื่องจักรกล สามารถเคลื่อนไหวและทำงานอัตโนมัติได้อย่างแม่นยำ ปลอดภัย และตอบสนองได้ตรงตามความต้องการ",
        "day_in_the_life": (
            "เช้าปรับพารามิเตอร์ตัวควบคุมแล้ววัดผล · สายแก้วงจรที่ทำให้มอเตอร์สั่น · "
            "บ่ายเขียนโปรแกรมบนบอร์ดควบคุม · เย็นทดสอบซ้ำ 100 รอบแล้วจดว่าพลาดกี่ครั้ง"
        ),
        "salary_note": "ยังไม่ได้เก็บข้อมูลเงินเดือนจริง",
        "requirements": [
            ("EMB-MCU", 3, 1.0), ("EE-CIRCUIT", 2, 0.9), ("EMB-C", 2, 0.9),
            ("EE-CTRL", 2, 0.8), ("ME-MECHATRONIC", 2, 0.8), ("T-CAD3D", 2, 0.6),
            ("F-ENG", 2, 0.7),
        ],
    },
    {
        "id": "STRUCT-ENG",
        "title_th": "วิศวกรออกแบบโครงสร้าง",
        "title_en": "Structural Design Engineer",
        "onet_soc_code": "17-2051.00",
        "onet_activity_soc": "17-2051.00",
        "activity_proxy_note": None,
        "sector": "private",
        "field_whitelist": ["CE"],
        "min_education": "ปี 3",
        "min_gpa": 2.50,
        "summary": "ผู้ออกแบบความมั่นคงให้ทุกสิ่งก่อสร้าง มั่นใจได้ในทุกการใช้งานด้วยการคำนวณทางวิศวกรรมที่แม่นยำและเชื่อถือได้",
        "day_in_the_life": (
            "เช้าตรวจแบบที่ผู้รับเหมาส่งกลับมา · สายคำนวณคานช่วงยาวที่สถาปนิกเพิ่งเปลี่ยน · "
            "บ่ายลงหน้างานดูของจริง · เย็นแก้แบบแล้วออกเอกสารให้เซ็น"
        ),
        "salary_note": "ยังไม่ได้เก็บข้อมูลเงินเดือนจริง",
        "requirements": [
            ("CE-STATIC", 3, 1.0), ("CE-RC", 3, 1.0), ("T-CAD2D", 3, 0.9),
            ("CE-FEM", 2, 0.8), ("CE-BIM", 2, 0.7), ("CE-COST", 2, 0.6),
            ("P-DOC", 2, 0.7), ("F-ENG", 2, 0.6),
        ],
    },
    {
        "id": "PROCESS-ENG",
        "title_th": "วิศวกรกระบวนการผลิต",
        "title_en": "Process Engineer",
        "onet_soc_code": "17-2041.00",
        "onet_activity_soc": "17-2041.00",
        "activity_proxy_note": None,
        "sector": "private",
        "field_whitelist": ["ChE", "IE"],
        "min_education": "ปี 3",
        "min_gpa": None,
        "summary": "ผู้เปลี่ยนวัตถุดิบให้กลายเป็นผลิตภัณฑ์ที่มีมูลค่า ในสเกลอุตสาหกรรมที่สามารถผลิตได้จริง คุ้มค่า และปลอดภัยสูงสุด",
        "day_in_the_life": (
            "เช้าดูว่าล็อตเมื่อวานได้คุณภาพไหม · สายไล่หาสาเหตุที่ผลผลิตตกลง 3% · "
            "บ่ายทดลองปรับอุณหภูมิในระดับห้องแล็บ · เย็นเขียนรายงานเสนอการเปลี่ยนแปลง"
        ),
        "salary_note": "ยังไม่ได้เก็บข้อมูลเงินเดือนจริง",
        "requirements": [
            ("CH-MASS", 3, 1.0), ("CH-PFD", 3, 0.9), ("CH-ENERGY", 2, 0.9),
            ("CH-SAFE", 2, 0.9), ("CH-LAB", 2, 0.8), ("CH-SIM", 2, 0.7),
            ("F-ENG", 2, 0.6),
        ],
    },
    {
        "id": "MFG-ENG",
        "title_th": "วิศวกรการผลิตและปรับปรุงกระบวนการ",
        "title_en": "Manufacturing / Industrial Engineer",
        "onet_soc_code": "17-2112.00",
        "onet_activity_soc": "17-2112.00",
        "activity_proxy_note": None,
        "sector": "private",
        "field_whitelist": ["IE", "ME"],
        "min_education": "ปี 3",
        "min_gpa": None,
        "summary": "ผู้ไขความลับในการลดต้นทุนและเวลา ค้นหาจุดบกพร่องในระบบเพื่อยกระดับประสิทธิภาพการผลิตโดยไม่ต้องลงทุนเพิ่ม",
        "day_in_the_life": (
            "เช้ายืนดูไลน์ผลิตแล้วจับเวลา · สายคุยกับพนักงานหน้างานว่าติดตรงไหน · "
            "บ่ายทำตัวเลขให้เห็นว่าคอขวดอยู่ไหน · เย็นเสนอการเปลี่ยนลำดับงานพร้อมตัวเลขก่อน-หลัง"
        ),
        "salary_note": "ยังไม่ได้เก็บข้อมูลเงินเดือนจริง",
        "requirements": [
            ("IE-FLOW", 3, 1.0), ("IE-TIME", 3, 1.0), ("IE-SPC", 2, 0.9),
            ("IE-LEAN", 2, 0.8), ("T-STAT", 2, 0.8), ("IE-LAYOUT", 2, 0.7),
            ("F-EXCEL", 2, 0.7), ("P-PRESENT", 2, 0.6),
        ],
    },
    {
        "id": "POWER-ENG",
        "title_th": "วิศวกรระบบไฟฟ้ากำลัง",
        "title_en": "Power Systems Engineer",
        "onet_soc_code": "17-2071.00",
        "onet_activity_soc": "17-2071.00",
        "activity_proxy_note": None,
        "sector": "state_enterprise",
        "field_whitelist": ["EE", "ME"],
        "min_education": "ปี 3",
        "min_gpa": 3.00,
        "summary": "ผู้วางรากฐานความมั่นคงทางพลังงาน วางแผนระบบไฟฟ้าแห่งอนาคตและผสานพลังงานสะอาดเข้ากับโครงข่ายอย่างยั่งยืน",
        "day_in_the_life": (
            "เช้าดูโหลดของสถานีเมื่อวาน · สายคำนวณว่าถ้าเสียบโซลาร์เพิ่มแรงดันจะกระเพื่อมไหม · "
            "บ่ายประชุมกับฝ่ายวางแผน · เย็นเขียนรายงานเสนอผู้บริหาร"
        ),
        "salary_note": "ยังไม่ได้เก็บข้อมูลเงินเดือนจริง",
        "requirements": [
            ("EE-CIRCUIT", 3, 1.0), ("EE-POWER", 3, 1.0), ("EE-MEASURE", 2, 0.8),
            ("T-MATLAB", 2, 0.8), ("F-EXCEL", 2, 0.7), ("P-DOC", 2, 0.8),
            ("F-ENG", 2, 0.7),
        ],
    },
    {
        "id": "MECH-DESIGN",
        "title_th": "วิศวกรออกแบบเครื่องกล",
        "title_en": "Mechanical Design Engineer",
        "onet_soc_code": "17-2141.00",
        "onet_activity_soc": "17-2141.00",
        "activity_proxy_note": None,
        "sector": "private",
        "field_whitelist": ["ME"],
        "min_education": "ปี 3",
        "min_gpa": 2.50,
        "summary": "ผู้รังสรรค์กลไกที่เคลื่อนไหวได้จริง ออกแบบชิ้นส่วนให้ทนทานต่อการใช้งาน และสามารถนำไปผลิตได้จริงภายใต้งบประมาณที่กำหนด",
        "day_in_the_life": (
            "เช้าแก้แบบตามที่ฝ่ายผลิตบอกว่าทำไม่ได้ · สายรันวิเคราะห์ความแข็งแรง · "
            "บ่ายเลือกวัสดุกับผู้ขาย · เย็นสั่งทำต้นแบบแล้วนัดวันทดสอบ"
        ),
        "salary_note": "ยังไม่ได้เก็บข้อมูลเงินเดือนจริง",
        "requirements": [
            ("T-CAD3D", 3, 1.0), ("ME-STATICS", 3, 1.0), ("ME-MATERIAL", 2, 0.9),
            ("ME-FEA", 2, 0.8), ("ME-MACHINE", 2, 0.8), ("ME-FAB", 2, 0.7),
            ("F-ENG", 2, 0.6),
        ],
    },
]

TARGET_IDS = [t["id"] for t in CAREER_TARGETS]

# เงื่อนไขชดใช้ทุน — 🔴 ฟิลด์ที่เว็บหางานทั่วไปไม่มี
OBLIGATIONS: list[dict] = [
    {"id": "none", "label": "ไม่มีทุนที่มีเงื่อนไขผูกพัน", "allowed_sectors": None},
    {"id": "gov", "label": "ทุนรัฐบาล / ทุนหน่วยงานรัฐ (ต้องกลับไปทำงานใช้ทุน)",
     "allowed_sectors": ["government", "state_enterprise", "academic"]},
    {"id": "univ", "label": "ทุนของสถาบัน (ผูกกับงานวิจัยหรือการเรียนต่อ)",
     "allowed_sectors": ["academic", "government"]},
]

EDUCATION_LEVELS: list[str] = ["ปี 1", "ปี 2", "ปี 3", "ปี 4", "จบปริญญาตรี"]

SECTORS: dict[str, str] = {
    "academic": "มหาวิทยาลัย / ห้องปฏิบัติการวิจัย",
    "government": "หน่วยงานราชการ",
    "state_enterprise": "รัฐวิสาหกิจ",
    "private": "เอกชน",
}

FIELDS: list[dict] = [
    {"id": "CE", "name_th": "วิศวกรรมโยธา"},
    {"id": "CPE", "name_th": "วิศวกรรมคอมพิวเตอร์"},
    {"id": "ChE", "name_th": "วิศวกรรมเคมี"},
    {"id": "EE", "name_th": "วิศวกรรมไฟฟ้า"},
    {"id": "IE", "name_th": "วิศวกรรมอุตสาหการ"},
    {"id": "ME", "name_th": "วิศวกรรมเครื่องกล"},
    {"id": "DE", "name_th": "วิศวกรรมดิจิทัล"},
]


def education_rank(level: str | None) -> int:
    if level is None:
        return -1
    try:
        return EDUCATION_LEVELS.index(level)
    except ValueError:
        return -1


def obligation_by_id(obligation_id: str | None) -> dict | None:
    if not obligation_id:
        return None
    return next((o for o in OBLIGATIONS if o["id"] == obligation_id), None)
