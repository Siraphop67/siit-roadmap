"""ชั้นคัดกรอง — 73 ทักษะที่ใช้จริงในเว็บ + DAG ของ prerequisite

O*NET ให้มา 664 ทักษะ ซึ่งเยอะเกินจะทำเป็น roadmap ที่คนอ่านรู้เรื่อง และเป็นภาษาอังกฤษล้วน
ไฟล์นี้คือชั้นที่คนคัดแล้ว: เลือกมา 73 ตัว ตั้งชื่อไทย และจัดลำดับก่อนหลัง

🔒 `onet_ref` ทุกตัวต้องมีอยู่จริงใน `pipeline/out/onet_skills.json`
   (มี test บังคับ) — เพื่อให้ข้ออ้างว่า "อิงมาตรฐานสากล" ตรวจสอบได้ ไม่ใช่แค่พูด

`source`:
  onet   — มีตัวตรงใน O*NET
  market — ตลาดใช้จริงแต่ O*NET ไม่มีเป็นรายการแยก (รอท่อขั้นที่ 2 ยืนยันจากประกาศงาน)
  manual — เราเพิ่มเองเพราะบริบทการเรียน

ระดับ 3 ขั้น: 1 รู้จัก · 2 ทำได้เมื่อมีคนแนะ · 3 ทำเองได้
"""

from __future__ import annotations

# (id, name_th, category, onet_ref, source)
_S = [
    # ══════════ พื้นฐานร่วม — ไม่มี prerequisite เป็นรากของ DAG ══════════
    ("F-MATH", "คณิตศาสตร์วิศวกรรม — แคลคูลัสและพีชคณิตเชิงเส้นที่ใช้กับงานจริง", "foundation", "onet-mathematics", "onet"),
    ("F-DATA", "อ่านชุดข้อมูลแล้วบอกได้ว่ามันกำลังบอกอะไร และบอกอะไรไม่ได้", "foundation", "onet-reading-comprehension", "onet"),
    ("F-WRITE", "เขียนเอกสารทางเทคนิคที่คนอื่นอ่านแล้วทำตามได้", "foundation", "onet-writing", "onet"),
    ("F-SOLVE", "แยกปัญหาใหญ่ให้เป็นปัญหาย่อยที่แก้ได้ทีละอัน", "foundation", "onet-complex-problem-solving", "onet"),
    ("F-EXCEL", "ใช้สเปรดชีตคำนวณและทำกราฟจากข้อมูลของตัวเอง", "tool", "tool-microsoft-excel", "onet"),
    ("F-MEASURE", "วัดของจริงและจดผลอย่างเป็นระบบจนทำซ้ำได้", "foundation", "onet-operations-monitoring", "onet"),
    ("F-DRAW", "อ่านแบบและไดอะแกรมทางวิศวกรรมแล้วบอกได้ว่าของจริงหน้าตายังไง", "foundation", "onet-design", "onet"),
    ("F-ENG", "อ่านเอกสารเทคนิคภาษาอังกฤษได้ด้วยตัวเอง", "foundation", "onet-english-language", "onet"),
    ("F-PHYS", "ใช้ฟิสิกส์อธิบายพฤติกรรมของระบบจริง", "foundation", "onet-physics", "onet"),

    # ══════════ เครื่องมือกลาง ══════════
    ("T-PY", "เขียนโปรแกรม Python แก้โจทย์ที่มีเงื่อนไขหลายชั้น", "tool", "tool-python", "onet"),
    ("T-GIT", "ใช้ Git จัดการเวอร์ชันและทำงานร่วมกับคนอื่น", "tool", "tool-git", "onet"),
    ("T-SQL", "เขียน SQL ดึงและรวมข้อมูลจากฐานข้อมูล", "tool", "tool-structured-query-language-sql", "onet"),
    ("T-LINUX", "ใช้ Linux สั่งงานผ่านบรรทัดคำสั่ง", "tool", "tool-linux", "onet"),
    ("T-MATLAB", "ใช้ MATLAB คำนวณเชิงตัวเลขและจำลองระบบ", "tool", "tool-the-mathworks-matlab", "onet"),
    ("T-CAD2D", "เขียนแบบ 2 มิติด้วย CAD ให้ช่างอ่านแล้วสร้างได้", "tool", "tool-autodesk-autocad", "onet"),
    ("T-CAD3D", "เขียนแบบและโมเดลชิ้นส่วน 3 มิติจนนำไปผลิตได้", "tool", "tool-dassault-systemes-solidworks", "onet"),
    ("T-STAT", "ใช้สถิติบอกได้ว่าตัวเลขที่เห็นผิดปกติจริงหรือแค่บังเอิญ", "analysis", "tool-statistical-software", "onet"),
    ("T-VIZ", "ทำภาพข้อมูลที่คนดูแล้วตัดสินใจได้ทันที", "analysis", "tool-microsoft-power-bi", "onet"),

    # ══════════ ซอฟต์แวร์ · ข้อมูล · ระบบฝังตัว ══════════
    ("SW-DS", "เลือกและใช้โครงสร้างข้อมูลกับอัลกอริทึมให้เหมาะกับงาน", "software", "onet-programming", "onet"),
    ("SW-OOP", "ออกแบบโปรแกรมให้แก้ต่อได้โดยไม่พัง", "software", "onet-systems-analysis", "onet"),
    ("SW-TEST", "เขียนเทสต์อัตโนมัติจนคนอื่น clone ไปรันแล้วได้ผลเดิม", "software", None, "market"),
    ("SW-DB", "ออกแบบฐานข้อมูลเชิงสัมพันธ์ที่ไม่เก็บข้อมูลซ้ำซ้อน", "software", None, "market"),
    ("SW-API", "ออกแบบและเรียกใช้ API เชื่อมสองระบบเข้าด้วยกัน", "software", None, "market"),
    ("SW-WEB", "สร้างเว็บที่ดึงข้อมูลจาก API มาแสดงและใช้งานได้จริง", "software", "tool-javascript", "onet"),
    ("SW-CLOUD", "นำระบบขึ้นคลาวด์และดูแลให้ทำงานต่อเนื่อง", "software", "tool-amazon-web-services-aws-software", "onet"),
    ("SW-CONTAINER", "ห่อระบบด้วยคอนเทนเนอร์ให้รันที่ไหนก็ได้ผลเหมือนกัน", "software", "tool-docker", "onet"),
    ("DA-CLEAN", "รวบรวมและทำความสะอาดข้อมูล (Data Cleaning) ให้พร้อมใช้งานจริง", "data", None, "market"),
    ("DA-ML", "ฝึกโมเดล machine learning กับข้อมูลจริงและวัดว่าดีแค่ไหน", "data", "tool-tensorflow", "onet"),
    ("DA-DEPLOY", "นำโมเดลขึ้นใช้งานจริงแล้ววัดผลหลังใช้", "data", "tool-pytorch", "onet"),
    ("DA-PIPE", "ทำท่อข้อมูลที่เดินเองทุกวันโดยไม่มีคนมากด", "data", None, "market"),
    ("EMB-C", "เขียนโปรแกรมภาษา C ที่จัดการหน่วยความจำเองได้", "embedded", "tool-c", "onet"),
    ("EMB-MCU", "เขียนโปรแกรมไมโครคอนโทรลเลอร์ให้ควบคุมของจริง", "embedded", "onet-technology-design", "onet"),
    ("EMB-IOT", "ต่ออุปกรณ์วัดให้ส่งข้อมูลขึ้นระบบได้ต่อเนื่อง", "embedded", None, "market"),

    # ══════════ โยธา ══════════
    ("CE-STATIC", "วิเคราะห์แรงตกกระทบในโครงสร้างด้วยหลักสมดุลสถิต", "civil", None, "manual"),
    ("CE-MATERIAL", "ทดสอบสมบัติวัสดุก่อสร้างและรายงานผลการทดสอบ", "civil", "onet-quality-control-analysis", "onet"),
    ("CE-RC", "ออกแบบโครงสร้างเสาและคานคอนกรีตเสริมเหล็ก", "civil", None, "manual"),
    ("CE-SURVEY", "สำรวจและทำระดับพื้นที่ด้วยกล้องระดับ", "civil", None, "manual"),
    ("CE-BIM", "ทำแบบจำลองอาคาร BIM ที่ใช้ประสานงานข้ามทีมได้", "civil", "tool-autodesk-revit", "onet"),
    ("CE-COST", "ประมาณราคางานก่อสร้างแยกตามหมวดวัสดุและค่าแรง", "civil", None, "manual"),
    ("CE-FEM", "วิเคราะห์พฤติกรรมโครงสร้างด้วยซอฟต์แวร์", "civil", "tool-finite-element-analysis-fea-software", "onet"),

    # ══════════ เคมี ══════════
    ("CH-MASS", "วิเคราะห์สมดุลมวลเพื่อติดตามและบริหารจัดการวัตถุดิบในทุกขั้นตอน", "chemical", None, "manual"),
    ("CH-ENERGY", "ประยุกต์ใช้หลักอุณหพลศาสตร์เพื่อจัดการสมดุลพลังงานในกระบวนการผลิตจริง", "chemical", None, "manual"),
    ("CH-LAB", "ทำการทดลองในห้องปฏิบัติการอย่างปลอดภัยและทำซ้ำได้", "chemical", "onet-chemistry", "onet"),
    ("CH-PFD", "อ่านและออกแบบแผนภาพกระบวนการผลิต (P&ID) ได้อย่างเชี่ยวชาญ", "chemical", None, "manual"),
    ("CH-KIN", "หาอัตราการเกิดปฏิกิริยาจากข้อมูลการทดลอง", "chemical", "onet-science", "onet"),
    ("CH-SIM", "จำลองกระบวนการผลิตด้วยซอฟต์แวร์", "chemical", None, "market"),
    ("CH-SAFE", "ประเมินอันตรายของกระบวนการและออกมาตรการรองรับ", "chemical", "onet-production-and-processing", "onet"),

    # ══════════ ไฟฟ้า ══════════
    ("EE-CIRCUIT", "วิเคราะห์วงจรไฟฟ้ากระแสตรงและกระแสสลับ", "electrical", "onet-computers-and-electronics", "onet"),
    ("EE-MEASURE", "วัดสัญญาณจริงด้วยมัลติมิเตอร์และออสซิลโลสโคป", "electrical", "onet-troubleshooting", "onet"),
    ("EE-ANALOG", "ออกแบบวงจรแอนะล็อกและจำลองก่อนต่อจริง", "electrical", "tool-simulation-program-with-integrated-circu", "onet"),
    ("EE-PCB", "ออกแบบแผ่นวงจรพิมพ์จนสั่งผลิตแล้วใช้งานได้", "electrical", None, "market"),
    ("EE-DSP", "ประมวลผลสัญญาณดิจิทัลเพื่อดึงสิ่งที่ต้องการออกจากสัญญาณรบกวน", "electrical", None, "manual"),
    ("EE-CTRL", "ออกแบบระบบควบคุมป้อนกลับให้ระบบนิ่ง", "electrical", "tool-mathworks-simulink", "onet"),
    ("EE-POWER", "ออกแบบระบบไฟฟ้ากำลังและบูรณาการพลังงานทดแทน", "electrical", None, "manual"),
    ("EE-PLC", "เขียนโปรแกรม PLC ควบคุมสายการผลิต", "electrical", "tool-programmable-logic-controller-plc-softwa", "onet"),

    # ══════════ อุตสาหการ ══════════
    ("IE-FLOW", "เขียนแผนภาพลำดับงานของกระบวนการจริง", "industrial", "tool-microsoft-visio", "onet"),
    ("IE-TIME", "ศึกษาเวลาการทำงานเพื่อวิเคราะห์และแก้ไขปัญหาคอขวด (Bottleneck) ในสายการผลิต", "industrial", None, "manual"),
    ("IE-SPC", "ใช้แผนภูมิควบคุมจับสัญญาณว่ากระบวนการกำลังเพี้ยน", "industrial", "tool-minitab", "onet"),
    ("IE-LAYOUT", "วางผังพื้นที่ทำงานตามลำดับการไหลของงาน", "industrial", None, "manual"),
    ("IE-SIM", "จำลองระบบคิวและสายการผลิตด้วยซอฟต์แวร์", "industrial", "tool-rockwell-automation-arena", "onet"),
    ("IE-LP", "หาคำตอบที่ดีที่สุดภายใต้ข้อจำกัดด้วยการโปรแกรมเชิงเส้น", "industrial", "onet-operations-analysis", "onet"),
    ("IE-SCM", "วางแผนสินค้าคงคลังและโซ่อุปทานจากข้อมูลการใช้จริง", "industrial", None, "manual"),
    ("IE-LEAN", "ปรับปรุงกระบวนการด้วยแนวคิดลีนจนวัดผลได้", "industrial", None, "market"),

    # ══════════ เครื่องกล ══════════
    ("ME-STATICS", "คำนวณแรงและความเค้นเพื่อประเมินขีดความสามารถในการรับน้ำหนักของชิ้นส่วน", "mechanical", None, "manual"),
    ("ME-MATERIAL", "เลือกวัสดุและวิธีผลิตให้เหมาะกับงานและงบ", "mechanical", "onet-engineering-and-technology", "onet"),
    ("ME-FAB", "สร้างชิ้นงานต้นแบบด้วยเครื่องมือในโรงงาน", "mechanical", None, "manual"),
    ("ME-THERMO", "วิเคราะห์การไหลและการถ่ายเทความร้อนในระบบ", "mechanical", "tool-ansys-fluent", "onet"),
    ("ME-MACHINE", "ออกแบบกลไกส่งกำลังให้ได้ความเร็วและแรงบิดที่ต้องการ", "mechanical", None, "manual"),
    ("ME-FEA", "วิเคราะห์ชิ้นส่วนด้วยไฟไนต์เอลิเมนต์", "mechanical", "tool-ansys-simulation-software", "onet"),
    ("ME-MECHATRONIC", "ประกอบและทดสอบระบบที่มีทั้งกลไกและไฟฟ้า", "mechanical", "tool-national-instruments-labview", "onet"),

    # ══════════ ทักษะวิชาชีพที่ทุกสายต้องมี ══════════
    ("P-DOC", "ทำเอกสารโครงการที่ตรวจสอบย้อนหลังได้", "professional", None, "manual"),
    ("P-PRESENT", "นำเสนอผลงานเชิงเทคนิคให้คนนอกสายเข้าใจ", "professional", "onet-critical-thinking", "onet"),
    ("P-TEAM", "ทำงานกับทีมข้ามสาขาโดยใช้เครื่องมือร่วมกัน", "professional", None, "manual"),
]

SKILLS: list[dict] = [
    {"id": i, "name_th": th, "name_en": "", "category": cat, "onet_element_id": ref, "source": src}
    for i, th, cat, ref, src in _S
]

SKILL_IDS = [s["id"] for s in SKILLS]


# ═══════════ DAG ของ prerequisite — from ต้องมาก่อน to ═══════════
#
# 🔴 เส้นผิดหนึ่งเส้น = roadmap ผิดทั้งเส้น
#    ทุกเส้นในไฟล์นี้เขียนด้วยมือและอ่านทวนแล้ว (reviewed_by_human = True)
#    เส้นที่ท่อขั้นที่ 4 เสนอมาจาก LLM ต้องผ่านคนตรวจก่อนถึงจะเข้ามาอยู่ตรงนี้ได้

SKILL_EDGES: list[tuple[str, str]] = [
    # เครื่องมือกลาง
    ("F-SOLVE", "T-PY"), ("T-PY", "T-GIT"), ("F-DATA", "T-SQL"),
    ("T-PY", "T-LINUX"), ("F-MATH", "T-MATLAB"),
    ("F-DRAW", "T-CAD2D"), ("T-CAD2D", "T-CAD3D"),
    ("F-DATA", "T-STAT"), ("F-MATH", "T-STAT"),
    ("F-EXCEL", "T-VIZ"), ("F-DATA", "T-VIZ"),

    # ซอฟต์แวร์
    ("T-PY", "SW-DS"), ("SW-DS", "SW-OOP"),
    ("T-PY", "SW-TEST"), ("T-GIT", "SW-TEST"),
    ("T-SQL", "SW-DB"), ("SW-DS", "SW-DB"),
    ("SW-OOP", "SW-API"), ("SW-API", "SW-WEB"),
    ("SW-API", "SW-CLOUD"), ("T-LINUX", "SW-CLOUD"),
    ("T-LINUX", "SW-CONTAINER"), ("SW-API", "SW-CONTAINER"),

    # ข้อมูล
    ("T-PY", "DA-CLEAN"), ("T-SQL", "DA-CLEAN"),
    ("DA-CLEAN", "DA-ML"), ("T-STAT", "DA-ML"),
    ("DA-ML", "DA-DEPLOY"), ("SW-CLOUD", "DA-DEPLOY"),
    ("DA-CLEAN", "DA-PIPE"), ("SW-CONTAINER", "DA-PIPE"),

    # ระบบฝังตัว
    ("F-SOLVE", "EMB-C"), ("EMB-C", "EMB-MCU"), ("EE-CIRCUIT", "EMB-MCU"),
    ("EMB-MCU", "EMB-IOT"), ("SW-API", "EMB-IOT"),

    # โยธา
    ("F-PHYS", "CE-STATIC"), ("F-MATH", "CE-STATIC"),
    ("F-MEASURE", "CE-MATERIAL"),
    ("CE-STATIC", "CE-RC"), ("CE-MATERIAL", "CE-RC"),
    ("F-MEASURE", "CE-SURVEY"),
    ("T-CAD3D", "CE-BIM"),
    ("T-CAD2D", "CE-COST"), ("F-EXCEL", "CE-COST"),
    ("CE-RC", "CE-FEM"), ("T-MATLAB", "CE-FEM"),

    # เคมี
    ("F-MATH", "CH-MASS"), ("F-PHYS", "CH-MASS"),
    ("CH-MASS", "CH-ENERGY"),
    ("F-MEASURE", "CH-LAB"),
    ("F-DRAW", "CH-PFD"), ("CH-MASS", "CH-PFD"),
    ("CH-LAB", "CH-KIN"), ("T-STAT", "CH-KIN"),
    ("CH-PFD", "CH-SIM"), ("CH-ENERGY", "CH-SIM"),
    ("CH-PFD", "CH-SAFE"), ("CH-LAB", "CH-SAFE"),

    # ไฟฟ้า
    ("F-PHYS", "EE-CIRCUIT"), ("F-MATH", "EE-CIRCUIT"),
    ("F-MEASURE", "EE-MEASURE"), ("EE-CIRCUIT", "EE-MEASURE"),
    ("EE-CIRCUIT", "EE-ANALOG"), ("EE-MEASURE", "EE-ANALOG"),
    ("EE-ANALOG", "EE-PCB"), ("F-DRAW", "EE-PCB"),
    ("EE-CIRCUIT", "EE-DSP"), ("T-MATLAB", "EE-DSP"),
    ("EE-DSP", "EE-CTRL"),
    ("EE-CIRCUIT", "EE-POWER"), ("F-EXCEL", "EE-POWER"),
    ("EE-CIRCUIT", "EE-PLC"), ("EMB-C", "EE-PLC"),

    # อุตสาหการ
    ("F-DRAW", "IE-FLOW"),
    ("IE-FLOW", "IE-TIME"), ("F-MEASURE", "IE-TIME"),
    ("T-STAT", "IE-SPC"), ("IE-TIME", "IE-SPC"),
    ("IE-TIME", "IE-LAYOUT"),
    ("IE-LAYOUT", "IE-SIM"), ("T-PY", "IE-SIM"),
    ("T-STAT", "IE-LP"), ("T-PY", "IE-LP"),
    ("T-STAT", "IE-SCM"), ("F-EXCEL", "IE-SCM"),
    ("IE-TIME", "IE-LEAN"), ("IE-SPC", "IE-LEAN"),

    # เครื่องกล
    ("F-PHYS", "ME-STATICS"), ("F-MATH", "ME-STATICS"),
    ("ME-STATICS", "ME-MATERIAL"), ("T-CAD3D", "ME-MATERIAL"),
    ("ME-MATERIAL", "ME-FAB"),
    ("F-PHYS", "ME-THERMO"), ("F-MATH", "ME-THERMO"),
    ("ME-STATICS", "ME-MACHINE"), ("T-CAD3D", "ME-MACHINE"),
    ("ME-STATICS", "ME-FEA"), ("T-MATLAB", "ME-FEA"),
    ("ME-FAB", "ME-MECHATRONIC"), ("EMB-MCU", "ME-MECHATRONIC"),

    # ทักษะวิชาชีพ
    ("F-WRITE", "P-DOC"), ("F-WRITE", "P-PRESENT"),
    ("T-GIT", "P-TEAM"), ("P-DOC", "P-TEAM"),
]


# ทักษะที่ "ทำเมื่อไหร่ก็ได้" — ไม่บล็อกก้าวอื่นใน roadmap (กลไกจาก roadmap.sh)
#
# เกณฑ์: ทักษะที่พัฒนาไปเรื่อย ๆ ตลอดหลักสูตร ไม่ใช่ประตูที่ต้องผ่านก่อนถึงจะไปต่อได้
# ไม่ได้แปลว่าไม่สำคัญ — แปลว่าไม่ต้องรอให้เสร็จก่อนถึงจะเริ่มอย่างอื่น
ORDER_FLEXIBLE: set[str] = {
    "F-ENG",      # อ่านเอกสารอังกฤษ — ทำไปพร้อมทุกวิชา
    "F-WRITE",    # เขียนเอกสารทางเทคนิค
    "P-DOC",      # ทำเอกสารโครงการ
    "P-PRESENT",  # นำเสนอผลงาน
    "P-TEAM",     # ทำงานข้ามสาขา
}


def skill_by_id() -> dict[str, dict]:
    return {s["id"]: s for s in SKILLS}


def is_flexible(skill_id: str) -> bool:
    return skill_id in ORDER_FLEXIBLE
