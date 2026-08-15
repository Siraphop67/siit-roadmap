"""รับผลงานเข้ามาจาก 4 ทาง แล้วแปลงเป็นข้อความดิบให้ตัวสกัดอ่าน

  pdf        อัปโหลดไฟล์ CV        → PyMuPDF
  text       วางข้อความ / กรอกฟอร์ม → ใช้ตรง ๆ
  github     ลิงก์ repo หรือผู้ใช้  → GitHub API (สาธารณะ ไม่ต้องมี token)
  linkedin   ลิงก์โปรไฟล์ / พอร์ต   → 🔴 ดึงอัตโนมัติไม่ได้ ให้ผู้ใช้วางข้อความเอง

🔴 ทำไม LinkedIn ถึงไม่ดึงให้อัตโนมัติ
   LinkedIn ปิดกั้นการดึงข้อมูลและระบุห้ามไว้ในเงื่อนไขการใช้งาน
   เราจึงให้ผู้ใช้กด export หรือคัดลอกข้อความมาวางเอง แล้วบอกเหตุผลบนหน้าจอตรง ๆ
   แทนที่จะเขียนตัวดึงที่ผิดเงื่อนไขและพังเมื่อไหร่ก็ได้
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

MAX_CHARS = 60_000
GITHUB_API = "https://api.github.com"


@dataclass
class IngestResult:
    raw_text: str
    source_ref: str
    kind: str
    note: str = ""

    @property
    def char_count(self) -> int:
        return len(self.raw_text)


class IngestError(ValueError):
    pass


def _clip(text: str) -> str:
    return text[:MAX_CHARS]


# ─────────────────────────── PDF ───────────────────────────


def from_pdf(data: bytes, filename: str) -> IngestResult:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover
        raise IngestError("ระบบยังไม่ได้ติดตั้งตัวอ่าน PDF") from exc

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise IngestError("เปิดไฟล์ PDF ไม่ได้ — ไฟล์อาจเสียหรือมีรหัสผ่าน") from exc

    with doc:
        pages = [page.get_text("text") for page in doc]

    text = "\n".join(pages).strip()
    if not text:
        raise IngestError(
            "อ่านตัวอักษรจาก PDF นี้ไม่ได้ — ถ้าเป็นไฟล์สแกนเป็นรูป "
            "ให้คัดลอกข้อความมาวางแทน"
        )
    return IngestResult(raw_text=_clip(text), source_ref=filename, kind="pdf")


# ─────────────────────────── ข้อความ ───────────────────────────


def from_text(text: str, label: str = "ข้อความที่วางเอง") -> IngestResult:
    text = (text or "").strip()
    if len(text) < 40:
        raise IngestError("ข้อความสั้นเกินไป — ใส่รายละเอียดผลงานหรือประสบการณ์เพิ่ม")
    return IngestResult(raw_text=_clip(text), source_ref=label, kind="text")


def from_linkedin(text: str, url: str | None = None) -> IngestResult:
    r = from_text(text, label=url or "โปรไฟล์ที่วางเอง")
    return IngestResult(
        raw_text=r.raw_text, source_ref=r.source_ref, kind="linkedin",
        note="LinkedIn ไม่อนุญาตให้ดึงข้อมูลอัตโนมัติ จึงใช้ข้อความที่คุณวางมาเอง",
    )


# ─────────────────────────── GitHub ───────────────────────────

_GH_URL = re.compile(r"github\.com/([A-Za-z0-9-]+)(?:/([A-Za-z0-9._-]+))?")

#: ชื่อ repo ที่ยอมรับได้ — ต้องตรงทั้งสตริง ไม่ใช่แค่เจอที่ไหนก็ได้
#: 🔴 ชื่อนี้ถูกเอาไปต่อใน /repos/{owner}/{name} ที่เราเรียก · ปล่อยผ่านชื่อแบบ
#:    "../../users/someone" เท่ากับให้คนนอกเปลี่ยนปลายทางที่เราจะไปเรียก
_GH_NAME = re.compile(r"\A[A-Za-z0-9._-]+\Z")


def parse_github(url: str) -> tuple[str, str | None]:
    m = _GH_URL.search(url or "")
    if not m:
        raise IngestError("ลิงก์ GitHub ไม่ถูกต้อง — ตัวอย่าง github.com/ชื่อผู้ใช้")
    return m.group(1), m.group(2)


def _own_repos(client: httpx.Client, owner: str) -> list[dict]:
    """รายชื่อ repo ที่เจ้าของเขียนเอง เรียงจากที่แก้ล่าสุด

    ข้ามที่ fork มาเพราะไม่ใช่ผลงานของเจ้าของ — เหตุผลเดียวกับ from_github
    """
    resp = client.get(f"{GITHUB_API}/users/{owner}/repos",
                      params={"sort": "updated", "per_page": 100})
    if resp.status_code == 404:
        raise IngestError(f"ไม่พบผู้ใช้ GitHub ชื่อ {owner}")
    resp.raise_for_status()
    rows = [r for r in resp.json() if not r.get("fork")]
    rows.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
    return rows


def list_github_repos(url: str, *, client: httpx.Client | None = None) -> list[dict]:
    """รายชื่อ repo สาธารณะให้ผู้ใช้เลือกเองว่าจะให้อ่านอันไหน

    🔓 ขั้นนี้ไม่เก็บอะไรและไม่ต้องขอความยินยอม — ชื่อ repo สาธารณะยังไม่ใช่ผลงาน
       ความยินยอมไปขอตอนกดวิเคราะห์ ซึ่งเป็นตอนที่เนื้อหาถูกอ่านจริง

    🔴 เห็นเฉพาะ repo สาธารณะ เพราะเรียก API แบบไม่ล็อกอิน — repo ส่วนตัวจะไม่โผล่
       ที่นี่เลย หน้าจอต้องบอกผู้ใช้ตรง ๆ ไม่ใช่ปล่อยให้เข้าใจว่านั่นคือทั้งหมดที่เขามี
    """
    owner, _ = parse_github(url)
    own = client or httpx.Client(timeout=20, headers={"Accept": "application/vnd.github+json"})
    try:
        rows = _own_repos(own, owner)
    except httpx.HTTPError as exc:
        raise IngestError(f"ต่อ GitHub ไม่ได้: {exc}") from exc
    finally:
        if client is None:
            own.close()

    if not rows:
        raise IngestError(
            f"บัญชี {owner} ยังไม่มี repo สาธารณะที่เขียนเอง — "
            "repo ส่วนตัวไม่แสดงที่นี่ ให้คัดลอกข้อความมาวางแทน"
        )

    return [{
        "name": r["name"],
        "description": r.get("description") or "",
        "language": r.get("language") or "",
        "updated_at": r.get("updated_at") or "",
    } for r in rows]


def from_github(
    url: str,
    *,
    repos: list[str] | None = None,
    client: httpx.Client | None = None,
    limit: int = 8,
) -> IngestResult:
    """อ่าน README + ภาษาที่ใช้ ของ repo ที่เจ้าของเขียนเอง

    ใช้ API สาธารณะ ไม่ต้องมี token · ข้ามที่ fork มาเพราะไม่ใช่ผลงานของเจ้าของ

    `repos` — รายชื่อที่ผู้ใช้ติ๊กเลือกมาเอง
        ไม่ส่งมา (None) = พฤติกรรมเดิม คือหยิบ `limit` อันที่แก้ล่าสุดให้เอง
        ส่งมาเป็นลิสต์ว่าง = "ผู้ใช้ยังไม่ได้เลือก" ซึ่ง **ไม่ใช่** "อ่านทั้งหมด"
    """
    owner, repo = parse_github(url)
    own = client or httpx.Client(timeout=20, headers={"Accept": "application/vnd.github+json"})
    parts: list[str] = []
    chosen = repos is not None

    try:
        if chosen:
            # 🛡 ชื่อมาจากเบราว์เซอร์ · ตรวจสองชั้นก่อนเอาไปต่อ URL
            if not repos:
                raise IngestError("ยังไม่ได้เลือก repo — ติ๊กอย่างน้อยหนึ่งอันก่อน")
            for name in repos:
                if not _GH_NAME.match(name or ""):
                    raise IngestError(f"ชื่อ repo ไม่ถูกต้อง: {name!r}")
            owned = {r["name"] for r in _own_repos(own, owner)}
            if unknown := [n for n in repos if n not in owned]:
                raise IngestError(
                    f"ไม่พบ repo นี้ในบัญชี {owner}: {', '.join(unknown)}"
                )
        elif repo:
            repos = [repo]
        else:
            repos = [r["name"] for r in _own_repos(own, owner)][:limit]
            if not repos:
                raise IngestError(f"บัญชี {owner} ยังไม่มี repo ที่เขียนเอง")

        for name in repos:
            meta = own.get(f"{GITHUB_API}/repos/{owner}/{name}")
            if meta.status_code != 200:
                continue
            info = meta.json()
            langs = own.get(f"{GITHUB_API}/repos/{owner}/{name}/languages")
            lang_text = " ".join(langs.json().keys()) if langs.status_code == 200 else ""

            readme = own.get(
                f"{GITHUB_API}/repos/{owner}/{name}/readme",
                headers={"Accept": "application/vnd.github.raw"})
            body = readme.text if readme.status_code == 200 else ""

            parts.append(
                f"## {name}\n{info.get('description') or ''}\n"
                f"ภาษาที่ใช้: {lang_text}\n{body}".strip())
    except httpx.HTTPError as exc:
        raise IngestError(f"ต่อ GitHub ไม่ได้: {exc}") from exc
    finally:
        if client is None:
            own.close()

    text = "\n\n".join(p for p in parts if p).strip()
    if not text:
        raise IngestError("ดึงข้อมูลจาก GitHub ได้ แต่ไม่มีเนื้อหาให้อ่าน")

    return IngestResult(
        raw_text=_clip(text), source_ref=f"github.com/{owner}" + (f"/{repo}" if repo else ""),
        kind="github",
        # 🔒 กติกาข้อ 5 — ข้อความนี้ขึ้นหน้าจอ ต้องบอกตามที่ทำจริง
        #    "ที่คุณเลือก" กับ "ที่ระบบเลือกให้" เป็นคนละเรื่อง ห้ามเขียนเหมือนกัน
        note=(f"อ่านจาก {len(parts)} repo ที่คุณเลือก" if chosen else
              f"อ่านจาก {len(parts)} repo ที่เจ้าของเขียนเอง (ข้ามที่ fork มา)"),
    )
