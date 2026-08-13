#!/usr/bin/env bash
# รันทั้งระบบในโหมด production บนเครื่องนี้ — ไม่ต้องใช้ Docker ไม่ต้องใช้เน็ต
#
#     make prod
#
# 🔴 นี่คือแผนสำรองของวัน Demo Day และควรเป็นแผนหลักจนกว่าจะมีที่ deploy จริง
#    การสาธิตที่พึ่งอินเทอร์เน็ตในห้องประชุมคือความเสี่ยงที่ไม่จำเป็น
#    ต่างจาก make backend/make frontend ตรงที่ตัวนี้ build จริงและปิด hot reload
#    จึงเจอปัญหาที่โผล่เฉพาะตอน build production ตั้งแต่วันนี้ ไม่ใช่เช้าวันงาน

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
API_BASE="${NEXT_PUBLIC_API_BASE:-http://localhost:${API_PORT}/api}"

cd "$REPO"

if [[ ! -x backend/.venv/bin/python ]]; then
  echo "ยังไม่ได้ตั้งเครื่อง — รัน make setup ก่อน" >&2
  exit 1
fi

echo "▸ build หน้าเว็บ (API_BASE=${API_BASE})"
# NEXT_PUBLIC_* ฝังตอน build ไม่ใช่ตอนรัน จึงต้อง build ใหม่เมื่อที่อยู่ API เปลี่ยน
( cd frontend && NEXT_PUBLIC_API_BASE="$API_BASE" npm run build >/dev/null )

# standalone ไม่คัดลอก public กับ .next/static ให้เอง
cp -r frontend/public frontend/.next/standalone/
cp -r frontend/.next/static frontend/.next/standalone/.next/

cleanup() { kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "▸ API   :${API_PORT}"
( cd backend && .venv/bin/python -m uvicorn app.main:app \
    --host 0.0.0.0 --port "$API_PORT" ) &

echo "▸ เว็บ  :${WEB_PORT}"
( cd frontend/.next/standalone && PORT="$WEB_PORT" HOSTNAME=0.0.0.0 node server.js ) &

sleep 4
if curl -fsS "http://127.0.0.1:${API_PORT}/api/health" >/dev/null; then
  echo
  echo "✅ พร้อมสาธิต — http://localhost:${WEB_PORT}"
  echo "   API      http://localhost:${API_PORT}/docs"
  echo "   ผู้ใช้ตัวอย่าง  make demo-user"
  echo "   หยุด     Ctrl-C"
else
  echo "🔴 API ไม่ตอบที่พอร์ต ${API_PORT}" >&2
fi

wait
