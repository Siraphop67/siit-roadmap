"""ตัวสกัดทักษะจาก CV ด้วยคำสำคัญ — ค่าเริ่มต้นของระบบ

⚠️ นี่ไม่ใช่ "ข้อมูลปลอมที่เตรียมไว้" — มันสกัดจากข้อความจริงที่ผู้ใช้ส่งเข้ามา
   ทำงานกับ CV อะไรก็ได้ ให้ผลเหมือนเดิมทุกครั้ง และไม่ต้องมี API key

ข้อจำกัดที่ต้องบอกตามตรง:
   · จับได้เฉพาะคำที่เขียนตรงตัว — "สร้าง REST API" จับได้ แต่ "ทำระบบให้สองฝั่งคุยกัน" จับไม่ได้
   · ไม่เข้าใจบริบท — "อยากเรียน Python" กับ "ใช้ Python ทำโปรเจกต์" ได้ผลเหมือนกัน
   · ไม่รู้ระดับความชำนาญจริง ใช้กติกาหยาบ ๆ จากจำนวนครั้งที่พบ

   สองข้อแรกคือเหตุผลที่ต้องต่อ LLM จริงในภายหลัง (app/llm/anthropic.py)
   แต่ span guard ทำงานเหมือนกันทั้งสองแบบ ผู้ใช้จึงยืนยัน/แก้ผลได้ตั้งแต่ตอนนี้
"""

from __future__ import annotations

import re
import unicodedata

from app.llm.base import ExtractedSpan, enforce_span_guard

# skill_id → คำที่ถ้าเจอใน CV แปลว่าน่าจะมีทักษะนี้
# เขียนทั้งไทยและอังกฤษเพราะ CV นักศึกษาไทยผสมกันเสมอ
KEYWORDS: dict[str, list[str]] = {
    # พื้นฐานร่วม
    "F-MATH": ["แคลคูลัส", "พีชคณิตเชิงเส้น", "calculus", "linear algebra", "สมการเชิงอนุพันธ์"],
    "F-DATA": ["วิเคราะห์ข้อมูล", "data analysis", "ตีความข้อมูล", "สรุปข้อมูล"],
    "F-WRITE": ["รายงานทางเทคนิค", "technical writing", "เขียนรายงาน", "documentation"],
    "F-SOLVE": ["แก้ปัญหา", "problem solving", "troubleshoot", "หาสาเหตุ"],
    "F-EXCEL": ["excel", "spreadsheet", "google sheets", "สเปรดชีต", "pivot"],
    "F-MEASURE": ["ปฏิบัติการ", "laboratory", "การวัด", "measurement", "เก็บข้อมูลภาคสนาม"],
    "F-DRAW": ["เขียนแบบ", "engineering drawing", "อ่านแบบ", "blueprint", "drafting"],
    "F-ENG": ["toeic", "ielts", "toefl", "english proficiency"],
    "F-PHYS": ["ฟิสิกส์", "physics", "กลศาสตร์", "mechanics"],
    # เครื่องมือกลาง
    "T-PY": ["python", "ไพทอน", "pandas", "numpy"],
    "T-GIT": ["git", "github", "gitlab", "version control", "pull request"],
    "T-SQL": ["sql", "postgres", "mysql", "sqlite", "ฐานข้อมูล", "database"],
    "T-LINUX": ["linux", "ubuntu", "bash", "shell script", "command line"],
    "T-MATLAB": ["matlab", "simulink", "octave"],
    "T-CAD2D": ["autocad", "cad", "เขียนแบบ 2 มิติ", "drafting"],
    "T-CAD3D": ["solidworks", "fusion 360", "catia", "inventor", "creo", "3d model", "โมเดล 3 มิติ"],
    "T-STAT": ["สถิติ", "statistics", "hypothesis", "regression", "spss", "minitab"],
    "T-VIZ": ["power bi", "tableau", "visualization", "dashboard", "แดชบอร์ด", "matplotlib"],
    # ซอฟต์แวร์ · ข้อมูล · ระบบฝังตัว
    "SW-DS": ["data structure", "algorithm", "อัลกอริทึม", "leetcode", "โครงสร้างข้อมูล"],
    "SW-OOP": ["object oriented", "oop", "design pattern", "เชิงวัตถุ"],
    "SW-TEST": ["unit test", "pytest", "jest", "ci/cd", "automated test", "เทสต์อัตโนมัติ"],
    "SW-DB": ["database design", "schema", "normalization", "er diagram", "ออกแบบฐานข้อมูล"],
    "SW-API": ["rest api", "api", "graphql", "fastapi", "express", "endpoint"],
    "SW-WEB": ["react", "next.js", "vue", "javascript", "typescript", "html", "css", "เว็บ"],
    "SW-CLOUD": ["aws", "azure", "gcp", "google cloud", "cloud", "คลาวด์"],
    "SW-CONTAINER": ["docker", "kubernetes", "container", "คอนเทนเนอร์"],
    "DA-CLEAN": ["data cleaning", "etl", "ทำความสะอาดข้อมูล", "data pipeline"],
    "DA-ML": ["machine learning", "tensorflow", "pytorch", "scikit", "โมเดล", "deep learning"],
    "DA-DEPLOY": ["model deployment", "mlops", "inference", "นำโมเดลขึ้นใช้"],
    "DA-PIPE": ["airflow", "data pipeline", "etl pipeline", "ท่อข้อมูล"],
    "EMB-C": ["ภาษา c", " c++", "embedded c", "programming in c"],
    "EMB-MCU": ["arduino", "esp32", "stm32", "raspberry pi", "ไมโครคอนโทรลเลอร์", "microcontroller"],
    "EMB-IOT": ["iot", "mqtt", "sensor node", "อินเทอร์เน็ตของสรรพสิ่ง"],
    # โยธา
    "CE-STATIC": ["สถิตยศาสตร์", "statics", "โครงถัก", "truss", "แรงในโครงสร้าง"],
    "CE-MATERIAL": ["ทดสอบวัสดุ", "concrete test", "compressive strength", "กำลังอัด"],
    "CE-RC": ["คอนกรีตเสริมเหล็ก", "reinforced concrete", "ออกแบบคาน", "beam design"],
    "CE-SURVEY": ["สำรวจ", "surveying", "total station", "กล้องระดับ", "ทำระดับ"],
    "CE-BIM": ["bim", "revit", "building information"],
    "CE-COST": ["ประมาณราคา", "cost estimation", "boq", "ปริมาณงาน"],
    "CE-FEM": ["sap2000", "etabs", "structural analysis software", "วิเคราะห์โครงสร้าง"],
    # เคมี
    "CH-MASS": ["สมดุลมวล", "mass balance", "material balance"],
    "CH-ENERGY": ["สมดุลพลังงาน", "energy balance", "อุณหพลศาสตร์", "thermodynamics"],
    "CH-LAB": ["ปฏิบัติการเคมี", "chemical laboratory", "titration", "ไทเทรต"],
    "CH-PFD": ["process flow diagram", "pfd", "p&id", "แผนภาพกระบวนการ"],
    "CH-KIN": ["จลนพลศาสตร์", "reaction kinetics", "อัตราการเกิดปฏิกิริยา"],
    "CH-SIM": ["aspen", "hysys", "process simulation", "จำลองกระบวนการ"],
    "CH-SAFE": ["hazop", "process safety", "ความปลอดภัยกระบวนการ", "msds"],
    # ไฟฟ้า
    "EE-CIRCUIT": ["วงจรไฟฟ้า", "circuit analysis", "kirchhoff", "วิเคราะห์วงจร"],
    "EE-MEASURE": ["oscilloscope", "multimeter", "ออสซิลโลสโคป", "มัลติมิเตอร์"],
    "EE-ANALOG": ["op-amp", "opamp", "analog circuit", "spice", "ltspice", "วงจรแอนะล็อก"],
    "EE-PCB": ["pcb", "altium", "kicad", "eagle", "แผ่นวงจรพิมพ์"],
    "EE-DSP": ["signal processing", "fft", "filter design", "ประมวลผลสัญญาณ"],
    "EE-CTRL": ["control system", "pid", "feedback control", "ระบบควบคุม"],
    "EE-POWER": ["power system", "ไฟฟ้ากำลัง", "solar", "โซลาร์", "renewable", "หม้อแปลง"],
    "EE-PLC": ["plc", "ladder logic", "scada", "โปรแกรมเมเบิล"],
    # อุตสาหการ
    "IE-FLOW": ["process flow", "flowchart", "value stream", "แผนภาพกระบวนการ", "visio"],
    "IE-TIME": ["time study", "จับเวลา", "work study", "motion study", "คอขวด", "bottleneck"],
    "IE-SPC": ["spc", "control chart", "แผนภูมิควบคุม", "six sigma", "ซิกซ์ ซิกม่า"],
    "IE-LAYOUT": ["plant layout", "ผังโรงงาน", "facility layout", "จัดผัง"],
    "IE-SIM": ["arena simulation", "discrete event", "จำลองสายการผลิต", "flexsim"],
    "IE-LP": ["linear programming", "optimization", "solver", "โปรแกรมเชิงเส้น", "การหาค่าเหมาะที่สุด"],
    "IE-SCM": ["supply chain", "inventory", "โซ่อุปทาน", "สินค้าคงคลัง", "warehouse"],
    "IE-LEAN": ["lean", "kaizen", "5s", "ลีน", "ไคเซ็น", "ลดความสูญเปล่า"],
    # เครื่องกล
    "ME-STATICS": ["strength of materials", "ความเค้น", "stress analysis", "กลศาสตร์วัสดุ"],
    "ME-MATERIAL": ["material selection", "เลือกวัสดุ", "manufacturing process", "กระบวนการผลิต"],
    "ME-FAB": ["cnc", "lathe", "3d printing", "พิมพ์ 3 มิติ", "กลึง", "เชื่อม", "welding"],
    "ME-THERMO": ["heat transfer", "fluid mechanics", "cfd", "ถ่ายเทความร้อน", "กลศาสตร์ของไหล"],
    "ME-MACHINE": ["machine design", "gear", "เฟือง", "ออกแบบเครื่องจักร", "transmission"],
    "ME-FEA": ["ansys", "finite element", "fea", "ไฟไนต์เอลิเมนต์", "abaqus"],
    "ME-MECHATRONIC": ["mechatronics", "labview", "เมคคาทรอนิกส์", "หุ่นยนต์", "robot"],
    # ทักษะวิชาชีพ
    "P-DOC": ["project documentation", "เอกสารโครงการ", "sop", "รายงานความก้าวหน้า"],
    "P-PRESENT": ["นำเสนอ", "presentation", "pitch", "บรรยาย"],
    "P-TEAM": ["teamwork", "ทำงานเป็นทีม", "collaboration", "cross-functional", "โครงงานกลุ่ม"],
}


def _normalize(text: str) -> str:
    """ทำให้เทียบได้โดยไม่เปลี่ยนความยาว — ตำแหน่ง span จึงยังตรงกับต้นฉบับ"""
    return unicodedata.normalize("NFC", text).lower()


class KeywordExtractor:
    name = "keyword"

    def extract(self, raw_text: str) -> list[ExtractedSpan]:
        if not raw_text.strip():
            return []
        haystack = _normalize(raw_text)
        found: dict[str, list[tuple[int, int, str]]] = {}

        for skill_id, words in KEYWORDS.items():
            for word in words:
                needle = _normalize(word)
                for m in re.finditer(re.escape(needle), haystack):
                    start, end = m.start(), m.end()
                    found.setdefault(skill_id, []).append((start, end, raw_text[start:end]))

        spans: list[ExtractedSpan] = []
        for skill_id, hits in found.items():
            hits.sort()
            start, end, text = hits[0]          # อ้างจุดแรกที่พบเป็นหลักฐาน
            spans.append(ExtractedSpan(
                skill_id=skill_id,
                span_start=start, span_end=end, span_text=text,
                # กติกาหยาบ ๆ: พบหลายที่ = น่าจะใช้จริงมากกว่าเอ่ยผ่าน
                level=3 if len(hits) >= 4 else 2 if len(hits) >= 2 else 1,
                confidence=round(min(0.9, 0.4 + 0.12 * len(hits)), 2),
            ))

        spans.sort(key=lambda s: (-s.confidence, s.skill_id))
        return enforce_span_guard(spans, raw_text)
