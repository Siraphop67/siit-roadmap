# เอาระบบขึ้นให้คนอื่นใช้ได้

> อ่านหัวข้อแรกก่อน — มันเปลี่ยนวิธีตัดสินใจของทุกหัวข้อที่เหลือ

---

## อะไรทดสอบแล้ว อะไรยัง

พูดเองก่อนจะไปเจอตอนตี 2 ของวันที่ 11

| | สถานะ |
|---|---|
| `make prod` — รันโหมด production บนเครื่อง | 🟢 **รันจริงแล้ว** standalone server ตอบ HTTP 200 |
| backend อ่าน `CORS_ORIGINS` จาก env | 🟢 **ทดสอบแล้ว** origin ที่ตั้งไว้ผ่าน origin อื่นถูกปฏิเสธ |
| `Dockerfile.backend` · `Dockerfile.frontend` · `docker-compose.yml` | 🟡 **เขียนแล้ว แต่ยังไม่มีใครสั่ง build บนเครื่องจริง** |
| ที่ deploy จริงบนคลาวด์ | 🔴 **ยังไม่มี** ต้องมีบัญชีก่อน ดูหัวข้อสุดท้าย |

**ทำไม Docker ยังเป็น 🟡** — เครื่องที่เขียนไฟล์พวกนี้ไม่มี Docker ติดตั้ง จึงสั่ง build
ทดสอบเองไม่ได้ · เพื่อไม่ให้ซ้ำรอย `prototype/docker-compose.yml` ที่เขียนไว้แล้วไม่เคยรัน
งาน `docker` ใน [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) จึง build ทั้งสอง image
**แล้วรันจริงและ curl เข้าไปดูว่ามันตอบ** ทุกครั้งที่มี PR

👉 **เปิด PR แล้วดูผลงาน `docker` — ถ้าเขียว แปลว่า Dockerfile ใช้ได้จริง ไม่ใช่แค่หน้าตาถูก**

---

## แผนที่ผมแนะนำสำหรับวัน Demo Day

**รันบนเครื่อง ไม่ใช่บนคลาวด์**

```bash
make prod
```

build จริง ปิด hot reload เปิด API ที่ :8000 และหน้าเว็บที่ :3000 พร้อมกัน

เหตุผล: การสาธิตที่พึ่งอินเทอร์เน็ตในห้องประชุมคือความเสี่ยงที่ไม่จำเป็น
เน็ตงานอีเวนต์ล่ม โฮสต์ฟรีหลับ (cold start) DNS ยังไม่กระจาย — สามอย่างนี้เกิดบ่อยกว่าที่คิด
และเกิดตอนที่แก้อะไรไม่ทันแล้ว

ใช้คลาวด์เป็น**ของแถม** ไว้ให้กรรมการกดดูทีหลัง ไม่ใช่ของที่ต้องพึ่งตอนขึ้นเวที

> ⚠️ ซ้อมด้วย `make prod` ไม่ใช่ `make backend` + `make frontend`
> เพราะปัญหาบางอย่างโผล่เฉพาะตอน build production เช่นค่า `NEXT_PUBLIC_*` ที่ฝังผิด
> เจอตั้งแต่วันนี้ยังแก้ทัน เจอเช้าวันงานคือจบ

---

## ค่า env ที่ต้องตั้ง

คัดลอกจากไฟล์ตัวอย่าง แล้วแก้:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

### 🔴 กับดักที่คนพลาดบ่อยที่สุด

**`NEXT_PUBLIC_API_BASE` ถูกฝังลงไปตอน build ไม่ใช่ตอนรัน**

เปลี่ยนที่อยู่ API แล้ว**ต้อง build ใหม่** — ส่ง env ตอน `docker run` หรือ restart ไม่มีผลใด ๆ
อาการที่จะเจอ: หน้าเว็บขึ้นปกติแต่ทุกปุ่มขึ้น *"ต่อกับ API ไม่ได้ที่ http://localhost:8000/api"*
ทั้งที่ตั้ง env ถูกแล้ว

**`CORS_ORIGINS` ต้องตรงกับ origin จริงเป๊ะ** รวม `https` และพอร์ต
`https://app.example.com` กับ `https://app.example.com/` (มี / ท้าย) ไม่เหมือนกัน

---

## 🔴 SQLite หรือ Postgres — ตัดสินก่อน Hack Days ไม่ใช่หลัง

ค่าเริ่มต้นคือ SQLite ไฟล์เดียว รันได้ทันที ไม่ต้องติดตั้งอะไร **แต่**

ถ้ารันใน container ด้วย SQLite **ข้อมูลผู้ใช้หายทุกครั้งที่ deploy ใหม่**

[`docs/TEAM.md`](TEAM.md) §3 🅴 เขียนไว้เองว่างานเก็บข้อมูลผู้ใช้จริง ≥10 คน
**"เก็บย้อนหลังไม่ได้"** — ถ้าข้อมูลหายรอบเดียวระหว่าง Hack Days วันที่ 11 จะไม่มีตัวเลขพูด

| สถานการณ์ | ใช้อะไร |
|---|---|
| พัฒนาบนเครื่อง · สาธิตอย่างเดียว | SQLite (ค่าเริ่มต้น) — ไม่ต้องทำอะไร |
| **Hack Days ที่มีผู้ใช้จริงมาลอง** | **Postgres เท่านั้น** |
| deploy ขึ้นคลาวด์ | Postgres เท่านั้น |

`docker-compose.yml` ตั้ง Postgres พร้อม volume ไว้ให้แล้ว — ข้อมูลอยู่ข้ามการ deploy

---

## รันด้วย Docker

```bash
cp backend/.env.example backend/.env    # แก้ POSTGRES_PASSWORD ก่อน
docker compose up --build
```

| | |
|---|---|
| หน้าเว็บ | http://localhost:3000 |
| API | http://localhost:8000/docs |

เปลี่ยนที่อยู่ API ต้อง build หน้าเว็บใหม่:

```bash
NEXT_PUBLIC_API_BASE=https://api.example.com/api docker compose build web
```

---

## เอาขึ้นคลาวด์

ทั้งสองอย่างเป็น Docker image ธรรมดา จึงขึ้นได้กับโฮสต์ที่รับ Dockerfile ทุกเจ้า
(Render · Railway · Fly.io · Google Cloud Run · VPS ที่มี Docker)

**ผมทำขั้นตอนพวกนี้ให้ไม่ได้** — ต้องสมัครบัญชี ผูกบัตร และกดยืนยันสิทธิ์ ซึ่งเป็นเรื่องที่
เจ้าของบัญชีต้องทำเอง สิ่งที่เตรียมไว้ให้แล้วคือทุกอย่างที่เหลือ

ลำดับที่ต้องทำ และลำดับสำคัญ:

1. **สร้าง Postgres ก่อน** แล้วเก็บ connection string ไว้
2. **deploy API** — `Dockerfile.backend` · context เป็น root ของ repo (**ไม่ใช่ `backend/`** เพราะ
   ตอนบูตต้องอ่าน `pipeline/out/` กับ `data/`) · ตั้ง `DATABASE_URL` · เปิดพอร์ต 8000
3. **จด URL ของ API ที่ได้** ← ขั้นที่ 4 ต้องใช้
4. **deploy หน้าเว็บ** — `Dockerfile.frontend` · ส่ง build arg `NEXT_PUBLIC_API_BASE=<URL จากข้อ 3>/api`
5. **กลับไปตั้ง `CORS_ORIGINS` ของ API** ให้เป็น URL ของหน้าเว็บ แล้ว restart
   ข้ามข้อนี้แล้วหน้าเว็บจะขึ้นได้แต่เรียก API ไม่ได้เลย

ตรวจว่าขึ้นสำเร็จ:

```bash
curl https://<API ของคุณ>/api/health
```

ต้องได้ `skills: 73 · skill_edges: 105 · career_targets: 8`
ถ้าได้ 0 แปลว่า `pipeline/out/` ไม่ได้ติดเข้า image — เช็ค build context

---

## 🔴 ห้ามพลาด

| | |
|---|---|
| **`.env` ห้ามเข้า repo** | repo เป็น public · หลุดแล้วต้อง revoke key ทันที |
| **เปลี่ยนรหัส Postgres ก่อนขึ้นจริง** | ค่าเริ่มต้นใน compose คือ `siit`/`siit` |
| **`LLM_PROVIDER` อย่าตั้งเป็น `anthropic` ถ้ายังไม่มี key** | `/health` จะรายงานว่ามี LLM จริงทั้งที่ไม่มี — ผิดกติกาข้อ 5 |
| **อย่า deploy ทับตอนมีคนกำลังทดสอบ** | ถ้ายังใช้ SQLite ข้อมูลหายทันที |
