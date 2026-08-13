/* ══════════════════════════════════════════════════════════
   extract.js — keyword extractor. Mirrors backend/app/llm/keyword.py
   Deterministic. No LLM. Returns real span offsets into raw text.
   Contract: raw.slice(span_start, span_end) === span_text
   ══════════════════════════════════════════════════════════ */
(function(){

/* skill_id → { th, level, keywords[] }  — names from backend/app/seed/skills.py */
const DICT={
 "T-PY":{th:"เขียนโปรแกรม Python แก้โจทย์ที่มีเงื่อนไขหลายชั้น",lv:2,kw:["Python","ไพทอน","django","flask"]},
 "T-SQL":{th:"เขียน SQL ดึงและรวมข้อมูลจากฐานข้อมูล",lv:2,kw:["SQL","MySQL","PostgreSQL","query"]},
 "SW-DB":{th:"ออกแบบฐานข้อมูลเชิงสัมพันธ์ที่ไม่เก็บข้อมูลซ้ำซ้อน",lv:2,kw:["PostgreSQL","MySQL","ฐานข้อมูล","database","MongoDB"]},
 "T-GIT":{th:"ใช้ Git จัดการเวอร์ชันและทำงานร่วมกับคนอื่น",lv:2,kw:["Git","GitHub","GitLab"]},
 "SW-WEB":{th:"สร้างเว็บที่ดึงข้อมูลจาก API มาแสดงและใช้งานได้จริง",lv:2,kw:["React","JavaScript","TypeScript","HTML","CSS","Next.js","Vue","เว็บไซต์"]},
 "SW-API":{th:"ออกแบบและเรียกใช้ API เชื่อมสองระบบเข้าด้วยกัน",lv:2,kw:["API","REST","FastAPI","endpoint","GraphQL"]},
 "T-VIZ":{th:"ทำภาพข้อมูลที่คนดูแล้วตัดสินใจได้ทันที",lv:1,kw:["dashboard","Power BI","Tableau","matplotlib","แดชบอร์ด"]},
 "DA-CLEAN":{th:"เก็บและทำความสะอาดชุดข้อมูลจนพร้อมใช้",lv:2,kw:["pandas","numpy","ทำความสะอาดข้อมูล","data cleaning","scraping","scrape"]},
 "DA-PIPE":{th:"ทำท่อข้อมูลที่เดินเองทุกวันโดยไม่มีคนมากด",lv:2,kw:["pipeline","cron","ETL","Airflow","scheduler"]},
 "SW-CLOUD":{th:"นำระบบขึ้นคลาวด์และดูแลให้ทำงานต่อเนื่อง",lv:2,kw:["AWS","Azure","GCP","cloud","Vercel","Heroku"]},
 "SW-CONTAINER":{th:"ห่อระบบด้วยคอนเทนเนอร์ให้รันที่ไหนก็ได้ผลเหมือนกัน",lv:2,kw:["Docker","container","Kubernetes"]},
 "SW-TEST":{th:"เขียนเทสต์อัตโนมัติจนคนอื่น clone ไปรันแล้วได้ผลเดิม",lv:2,kw:["pytest","unit test","เทสต์","jest","CI"]},
 "DA-ML":{th:"ฝึกโมเดล machine learning กับข้อมูลจริงและวัดว่าดีแค่ไหน",lv:2,kw:["machine learning","TensorFlow","PyTorch","scikit","โมเดล"]},
 "EMB-C":{th:"เขียนโปรแกรมภาษา C ที่จัดการหน่วยความจำเองได้",lv:2,kw:["C++","ภาษา C","embedded"]},
 "EMB-MCU":{th:"เขียนโปรแกรมไมโครคอนโทรลเลอร์ให้ควบคุมของจริง",lv:2,kw:["Arduino","ESP32","STM32","ไมโครคอนโทรลเลอร์","Raspberry Pi"]},
 "T-CAD3D":{th:"เขียนแบบและโมเดลชิ้นส่วน 3 มิติจนนำไปผลิตได้",lv:2,kw:["SolidWorks","Fusion 360","Inventor","CATIA"]},
 "T-CAD2D":{th:"เขียนแบบ 2 มิติด้วย CAD ให้ช่างอ่านแล้วสร้างได้",lv:2,kw:["AutoCAD","CAD"]},
 "T-MATLAB":{th:"ใช้ MATLAB คำนวณเชิงตัวเลขและจำลองระบบ",lv:2,kw:["MATLAB","Simulink"]},
 "T-STAT":{th:"ใช้สถิติบอกได้ว่าตัวเลขที่เห็นผิดปกติจริงหรือแค่บังเอิญ",lv:2,kw:["สถิติ","statistics","regression","SPSS"]},
 "F-EXCEL":{th:"ใช้สเปรดชีตคำนวณและทำกราฟจากข้อมูลของตัวเอง",lv:2,kw:["Excel","สเปรดชีต","Google Sheets"]},
 "T-LINUX":{th:"ใช้ Linux สั่งงานผ่านบรรทัดคำสั่ง",lv:2,kw:["Linux","Ubuntu","bash","shell"]},
 "F-WRITE":{th:"เขียนเอกสารทางเทคนิคที่คนอื่นอ่านแล้วทำตามได้",lv:2,kw:["documentation","เอกสาร","รายงาน","report"]},
 "CE-BIM":{th:"ทำแบบจำลองอาคาร BIM ที่ใช้ประสานงานข้ามทีมได้",lv:2,kw:["Revit","BIM"]},
 "CH-SIM":{th:"จำลองกระบวนการผลิตด้วยซอฟต์แวร์",lv:2,kw:["Aspen","HYSYS"]}
};

/* find every keyword occurrence, keep first hit per skill, longest keyword wins */
window.extractSkills=function(raw){
  const found=[];
  const lower=raw.toLowerCase();

  for(const id in DICT){
    const d=DICT[id];
    let best=null;
    for(const k of d.kw){
      const i=lower.indexOf(k.toLowerCase());
      if(i<0) continue;
      if(!best || k.length>best.w.length) best={i,w:raw.substr(i,k.length)};
    }
    if(best){
      found.push({
        id, th:d.th, lv:d.lv,
        span_start:best.i,
        span_end:best.i+best.w.length,
        span_text:best.w,
        status:"pending"           /* 🔒 always pending — user must confirm */
      });
    }
  }
  /* guard: span must really slice back to the same text (backend has this test) */
  return found
    .filter(s=>raw.slice(s.span_start,s.span_end)===s.span_text)
    .sort((a,b)=>a.span_start-b.span_start);
};

window.EXTRACT_DICT_SIZE=Object.keys(DICT).length;
})();
