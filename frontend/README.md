# SIIT Roadmap — Frontend

หน้าเว็บ Next.js สำหรับ SIIT Roadmap ออกแบบตาม visual direction ของ Stitch: โทนสี Academic Pathfinding, Plus Jakarta Sans, Inter และ layout แบบ clean workspace ที่รองรับมือถือ แท็บเล็ต และเดสก์ท็อป

## เริ่มใช้งาน

ครั้งแรกให้ติดตั้ง dependencies และเตรียมข้อมูลจากโฟลเดอร์ `siit-roadmap`:

```bash
make setup
```

จากนั้นเปิดเทอร์มินัล 2 หน้าต่าง:

```bash
make backend
make frontend
```

จากนั้นเปิด [http://localhost:3000](http://localhost:3000)

## หน้าที่พร้อมใช้งาน

- `/` เลือกทางเข้า “ยังไม่รู้” หรือ “รู้เป้าหมายแล้ว”
- `/discover` แบบทดสอบกิจกรรม 5 ระดับแบบ adaptive
- `/discover/results` ผลจับคู่อาชีพ พร้อมเหตุผลและข้อควรรู้
- `/targets` คลังอาชีพ 8 อาชีพ พร้อมเงื่อนไขที่ถูกกรอง
- `/portfolio` รับ PDF, ข้อความ, GitHub และข้อความจาก LinkedIn
- `/portfolio/review` ไฮไลต์หลักฐานและให้ผู้ใช้ยืนยัน/ปฏิเสธ/แก้ระดับ
- `/roadmap` Roadmap ที่คำนวณจาก skill gap พร้อมตัวเลือกการเรียนรู้
- `/skills` กราฟ 73 ทักษะและ 105 ความสัมพันธ์ พร้อมหลักฐานแยกตามแหล่ง

หน้าเว็บเรียกข้อมูลและ logic ผ่าน FastAPI จริงทั้งหมด หาก backend ไม่ได้เปิดอยู่ หน้าจอจะแสดงข้อความบอกวิธีแก้โดยไม่สร้างข้อมูลสมมติขึ้นมาแทน

## ตรวจสอบก่อนส่งงาน

```bash
npm run lint
npm run build
```
