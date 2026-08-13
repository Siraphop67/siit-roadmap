PY      := backend/.venv/bin/python
PIP     := backend/.venv/bin/pip
PYTHON  ?= /opt/homebrew/opt/python@3.13/bin/python3.13
ONET_URL := https://www.onetcenter.org/dl_files/database/db_29_1_text.zip

.PHONY: help setup venv deps onet pipeline backend frontend prod test lint clean reset demo-user check-postings postings

help:
	@echo "make setup      ตั้งเครื่องครั้งแรก — venv + deps + O*NET + ท่อข้อมูล"
	@echo "make backend    รัน API ที่พอร์ต 8000 (เอกสารที่ /docs)"
	@echo "make frontend   รันหน้าเว็บที่พอร์ต 3000"
	@echo "make prod       รันทั้งระบบโหมด production บนเครื่องนี้ — แผนสำรองวัน Demo Day"
	@echo "make test       รันเทสต์ทั้งหมด — ต้องเขียวก่อน push เสมอ"
	@echo "make demo-user  สร้างผู้ใช้ตัวอย่างที่เดินครบเส้นแล้ว (ต้องเปิด make backend ค้างไว้)"
	@echo "make check-postings  ตรวจประกาศงานที่เก็บมาว่ากรอกถูกรูปแบบไหม"
	@echo "make postings   แปลงประกาศงานที่เก็บมาเป็น requirement (ท่อขั้นที่ 2)"
	@echo "make pipeline   สร้างข้อมูลจาก O*NET ใหม่"
	@echo "make reset      ลบฐานข้อมูลแล้ว seed ใหม่"

setup: venv deps onet pipeline
	@echo ""
	@echo "พร้อมแล้ว — เปิดสองหน้าต่าง:  make backend   |   make frontend"

venv:
	@test -d backend/.venv || $(PYTHON) -m venv backend/.venv

deps: venv
	@$(PIP) install -q --upgrade pip
	@$(PIP) install -q -r backend/requirements.txt
	@echo "[deps] ติดตั้ง Python เรียบร้อย"
	@test -d frontend && (cd frontend && npm install) || echo "[deps] ยังไม่มี frontend/ — ข้ามไปก่อน"

# ไฟล์ O*NET 106 MB ไม่ได้อยู่ใน repo (ดู .gitignore) — ดึงใหม่ได้ตลอด
onet:
	@mkdir -p pipeline/cache
	@test -f pipeline/cache/onet.zip || \
		(echo "[onet] กำลังดาวน์โหลด 13 MB…" && curl -sL -o pipeline/cache/onet.zip $(ONET_URL))
	@test -d pipeline/cache/onet || unzip -q pipeline/cache/onet.zip -d pipeline/cache/onet
	@echo "[onet] พร้อมใช้"

pipeline: onet
	@$(PY) pipeline/1_import_onet.py
	@$(PY) pipeline/1b_import_instruments.py

backend:
	@cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000

frontend:
	@test -d frontend || (echo "ยังไม่มี frontend/ — ดู docs/TEAM.md ว่าใครเป็นเจ้าของ" && exit 1)
	@cd frontend && npm run dev

# รันจริงแบบที่จะสาธิต — build จริง ปิด hot reload ไม่ต้องใช้ Docker ไม่ต้องใช้เน็ต
prod:
	@./scripts/serve-prod.sh

test:
	@cd backend && .venv/bin/python -m pytest tests/ -q

# ผู้ใช้ตัวอย่างที่ตอบแบบทดสอบ ส่ง CV ยืนยันผลสกัด และเลือกเป้าหมายมาแล้ว
# สำหรับคนทำหน้าเว็บ จะได้ไม่ต้องเดินทั้งเส้นใหม่ทุกครั้งที่รีเฟรช
# persona: data (ค่าเริ่มต้น) · hands-on · people   →  make demo-user P=hands-on
demo-user:
	@cd backend && .venv/bin/python scripts/demo_user.py --persona $(or $(P),data)

# ด่านตรวจของคนเก็บประกาศงาน — ไม่ต้องเปิด backend ไม่แตะฐานข้อมูล
check-postings:
	@cd backend && .venv/bin/python scripts/check_postings.py

# ท่อขั้นที่ 2 — แปลงประกาศงานที่เก็บมาเป็น requirement
# รันทุกครั้งที่เก็บประกาศเพิ่ม แล้ว make backend อีกรอบ · MIN=1 ตอนยังเก็บได้น้อย
postings:
	@$(PY) pipeline/2_extract_postings.py --min-postings $(or $(MIN),2)

# typegen ก่อน tsc เสมอ — Next 16 สร้าง type ของ route/layout ตอน build
# clone ใหม่ที่ยังไม่เคย build จะเจอ "Cannot find name 'LayoutProps'" ถ้าข้ามขั้นนี้
lint:
	@test -d frontend && (cd frontend && npx next typegen && npx tsc --noEmit && npx eslint app lib) || true

reset:
	@rm -f backend/siit_roadmap.db
	@echo "[reset] ลบฐานข้อมูลแล้ว — seed ใหม่ตอนรัน make backend ครั้งถัดไป"

clean: reset
	@find . -name __pycache__ -type d -prune -exec rm -rf {} +
	@rm -rf backend/.pytest_cache frontend/.next
