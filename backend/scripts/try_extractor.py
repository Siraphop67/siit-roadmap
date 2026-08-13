"""ลองตัวสกัดกับ CV จริง แล้วดูว่าจับอะไรได้ อะไรหลุด — ไม่ต้องเปิด backend

    make try-extractor                                  # ตัวที่ตั้งไว้ใน .env
    make try-extractor P=keyword                        # เทียบกับตัวจับคำสำคัญ
    make try-extractor P=local M=qwen2.5:14b            # LLM ในเครื่อง
    make try-extractor P=local CV=~/resume.pdf          # CV ของตัวเอง

    python scripts/try_extractor.py --provider local --compare   # เทียบสองตัวข้าง ๆ กัน

🔴 สิ่งที่สคริปต์นี้ทำให้เห็น และเป็นเหตุผลที่ต้องมีมัน
   ตัวเลข "สกัดได้ 11 ทักษะ" ไม่บอกอะไรเลย ถ้าไม่รู้ว่า **หลุดอะไรไปบ้าง**
   สคริปต์จึงแสดงทั้งที่จับได้ ที่โดน span guard ตัดทิ้ง และประโยคที่อ้างจริง ๆ

   สำหรับ LLM ในเครื่อง สิ่งที่จะเห็นบ่อยคือ "เรียกได้ แต่โดน guard ตัดเกือบหมด"
   เพราะตัวเล็กชอบเรียบเรียงใหม่แทนที่จะคัดลอกตรงตัว — นั่นคือข้อมูล ไม่ใช่ระบบพัง
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.llm.base import ExtractorError  # noqa: E402
from app.seed.skills import SKILLS  # noqa: E402

SKILL_TH = {s["id"]: s["name_th"] for s in SKILLS}

SAMPLE_CV = """สมชาย ใจดี — นักศึกษาวิศวกรรมคอมพิวเตอร์ ปี 3

โครงงานและประสบการณ์
- ทำระบบวิเคราะห์ข้อมูลการใช้ห้องเรียนด้วย Python และ pandas
- สร้าง REST API ด้วย FastAPI ต่อกับ PostgreSQL ใช้ SQL ดึงข้อมูล
- ดูแลโค้ดด้วย Git เขียน unit test ด้วย pytest ทุกฟีเจอร์
- ทำ dashboard ด้วย Power BI ให้หัวหน้าไลน์ดูของเสียรายวัน
- ใช้ Docker และ Linux ในการ deploy
- เป็นหัวหน้ากลุ่มโครงงาน 4 คน นำเสนอหน้าชั้นทุกสัปดาห์

ประโยคที่เขียนอ้อม — ตัวจับคำสำคัญจะไม่เห็น แต่ LLM ควรเห็น
- ทำให้สองระบบที่เดิมไม่คุยกัน ส่งข้อมูลหากันได้อัตโนมัติ
- เขียนสคริปต์ให้เครื่องทำงานซ้ำ ๆ แทนคนทุกเช้า
TOEIC 780
"""


def load_cv(path: str | None) -> str:
    if not path:
        return SAMPLE_CV
    p = Path(path).expanduser()
    if not p.exists():
        sys.exit(f"ไม่พบไฟล์ {p}")
    if p.suffix.lower() == ".pdf":
        from app.ingest import from_pdf
        return from_pdf(p.read_bytes(), p.name).raw_text
    return p.read_text(encoding="utf-8")


def run(provider: str, raw_text: str) -> tuple[list, float, str | None]:
    settings.llm_provider = provider
    from app.llm import get_extractor

    started = time.monotonic()
    try:
        spans = get_extractor().extract(raw_text)
    except (ExtractorError, RuntimeError, ValueError) as exc:
        return [], time.monotonic() - started, str(exc)
    return spans, time.monotonic() - started, None


def show(provider: str, spans: list, seconds: float, error: str | None, raw_text: str) -> None:
    head = f"── {provider} "
    print(f"\n{head}{'─' * max(0, 66 - len(head))}")
    if error:
        print(f"🔴 {error}")
        return

    print(f"สกัดได้ {len(spans)} ทักษะ · ใช้เวลา {seconds:.1f} วินาที\n")
    for s in sorted(spans, key=lambda x: (-x.confidence, x.skill_id)):
        name = SKILL_TH.get(s.skill_id, s.skill_id)
        quoted = raw_text[s.span_start:s.span_end].replace("\n", " ")
        print(f"  ระดับ {s.level} · {s.confidence:.2f}  {name}")
        print(f'      ← "{quoted}"')

    # 🛡 พิสูจน์ว่าทุกอันชี้กลับไปที่เอกสารได้จริง ไม่ใช่เชื่อว่าได้
    bad = [s for s in spans if raw_text[s.span_start:s.span_end] != s.span_text]
    print(f"\n  {'🔴' if bad else '✓'} span ที่ชี้กลับไปที่เอกสารได้: "
          f"{len(spans) - len(bad)}/{len(spans)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--provider", default=settings.llm_provider)
    ap.add_argument("--model", help="ทับ LOCAL_LLM_MODEL")
    ap.add_argument("--base-url", help="ทับ LOCAL_LLM_BASE_URL")
    ap.add_argument("--cv", help="ไฟล์ CV (.pdf หรือ .txt) · ไม่ใส่ = ใช้ตัวอย่างในสคริปต์")
    ap.add_argument("--compare", action="store_true", help="เทียบกับ keyword ข้าง ๆ กัน")
    args = ap.parse_args()

    if args.model:
        settings.local_llm_model = args.model
    if args.base_url:
        settings.local_llm_base_url = args.base_url

    raw_text = load_cv(args.cv)
    print(f"เอกสาร {len(raw_text)} ตัวอักษร"
          + (f" · จาก {args.cv}" if args.cv else " · ตัวอย่างในสคริปต์"))
    if args.provider == "local":
        print(f"ปลายทาง {settings.local_llm_base_url} · รุ่น {settings.local_llm_model}")

    providers = [args.provider] + (["keyword"] if args.compare
                                   and args.provider != "keyword" else [])
    results = {}
    for p in providers:
        spans, secs, err = run(p, raw_text)
        results[p] = {s.skill_id for s in spans}
        show(p, spans, secs, err, raw_text)

    if len(results) == 2:
        a, b = providers
        only_a, only_b = results[a] - results[b], results[b] - results[a]
        print(f"\n── เทียบกัน {'─' * 52}")
        print(f"  เจอทั้งคู่ {len(results[a] & results[b])} ทักษะ")
        for label, ids in ((f"เฉพาะ {a}", only_a), (f"เฉพาะ {b}", only_b)):
            if ids:
                print(f"  {label}: {', '.join(SKILL_TH.get(i, i) for i in sorted(ids))}")
        if not only_a and results[a]:
            print(f"  ⚠️  {a} ไม่เจออะไรที่ {b} ไม่เจอเลย — ยังไม่คุ้มกับที่รันช้ากว่า")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
