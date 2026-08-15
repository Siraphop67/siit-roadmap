"""ให้ผู้ใช้เลือกเองว่าจะให้อ่าน repo ไหน — ชั้น ingest

🔴 ไม่ยิง GitHub จริงสักเทสต์เดียว · `from_github` รับ `client=` อยู่แล้ว เราจึงยัดตัวปลอมได้
   (`test_extraction.py` มีเทสต์ที่ยิงจริงอยู่หนึ่งตัวและ skip เมื่อไม่มีเน็ต —
   ที่นี่ไม่เอาแบบนั้น เพราะพฤติกรรมที่คุมอยู่ต้องเช็คได้แน่นอนทุกครั้ง)

🛡 หัวใจของไฟล์นี้: ชื่อ repo มาจากเบราว์เซอร์ แล้วถูกเอาไปต่อใน URL ที่เราเรียก
   ถ้าไม่ตรวจ ชื่อแบบ `../../users/someone` จะเปลี่ยนปลายทางทั้งเส้น
"""

from __future__ import annotations

import json

import httpx
import pytest

from app.ingest import IngestError, from_github, list_github_repos

OWNER = "nicha-example"

#: ผลลัพธ์ที่ GitHub ส่งกลับมาเวลาถามรายชื่อ repo ของผู้ใช้คนหนึ่ง
REPO_LIST = [
    {"name": "burn-ledger", "description": "บันทึกการเผา", "language": "Python",
     "updated_at": "2026-07-30T11:12:35Z", "fork": False},
    {"name": "math-notes", "description": None, "language": None,
     "updated_at": "2026-05-22T20:17:02Z", "fork": False},
    {"name": "somebody-elses-project", "description": "fork มา", "language": "Go",
     "updated_at": "2026-08-01T00:00:00Z", "fork": True},        # ← ต้องถูกข้าม
]


def fake_transport(*, list_status: int = 200, repos: list | None = None):
    """เลียนรูปร่างที่ GitHub API ตอบจริง — รายชื่อ · รายละเอียด · ภาษา · README"""
    body = REPO_LIST if repos is None else repos

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == f"/users/{OWNER}/repos":
            if list_status != 200:
                return httpx.Response(list_status, json={"message": "Not Found"})
            return httpx.Response(200, json=body)
        if path.endswith("/languages"):
            return httpx.Response(200, json={"Python": 1000})
        if path.endswith("/readme"):
            name = path.split("/")[3]
            return httpx.Response(200, text=f"README ของ {name}")
        if path.startswith(f"/repos/{OWNER}/"):
            name = path.split("/")[3]
            return httpx.Response(200, json={"name": name, "description": f"คำอธิบาย {name}"})
        return httpx.Response(404, json={"message": "Not Found"})

    return httpx.MockTransport(handler)


def client(**kw) -> httpx.Client:
    return httpx.Client(transport=fake_transport(**kw), base_url="https://api.github.com")


# ═════════════ อ่านรายชื่อมาให้ผู้ใช้เลือก ═════════════


def test_คืนรายชื่อrepoของผู้ใช้():
    repos = list_github_repos(f"github.com/{OWNER}", client=client())
    assert [r["name"] for r in repos] == ["burn-ledger", "math-notes"]


def test_ข้ามrepoที่forkมาเพราะไม่ใช่ผลงานของเจ้าของ():
    """เหตุผลเดียวกับที่ from_github ข้ามอยู่แล้ว — ต้องข้ามตั้งแต่ตอนให้เลือก"""
    names = [r["name"] for r in list_github_repos(f"github.com/{OWNER}", client=client())]
    assert "somebody-elses-project" not in names


def test_เรียงจากที่แก้ล่าสุดไปเก่าสุด():
    repos = list_github_repos(f"github.com/{OWNER}", client=client())
    assert [r["updated_at"] for r in repos] == sorted(
        (r["updated_at"] for r in repos), reverse=True)


def test_ส่งฟิลด์ที่หน้าจอต้องใช้ครบ():
    """หน้าจอต้องบอกได้ว่าแต่ละอันคืออะไร ไม่ใช่โชว์แค่ชื่อเปล่า ๆ"""
    first = list_github_repos(f"github.com/{OWNER}", client=client())[0]
    assert set(first) >= {"name", "description", "language", "updated_at"}


def test_ไม่พบผู้ใช้บอกตรงๆว่าไม่พบ():
    with pytest.raises(IngestError) as exc:
        list_github_repos(f"github.com/{OWNER}", client=client(list_status=404))
    assert OWNER in str(exc.value)


def test_บัญชีที่ไม่มีrepoสาธารณะบอกตรงๆไม่ใช่คืนลิสต์ว่างเงียบๆ():
    """🔒 กติกาข้อ 5 — ผู้ใช้ต้องรู้ว่าทำไมไม่มีอะไรให้เลือก"""
    with pytest.raises(IngestError):
        list_github_repos(f"github.com/{OWNER}", client=client(repos=[]))


# ═════════════ 🛡 ชื่อ repo มาจากเบราว์เซอร์ ═════════════


@pytest.mark.parametrize("evil", [
    "../../users/someone",
    "burn-ledger/../../../etc",
    "repo name with spaces",
    "repo?query=1",
    "",
])
def test_ชื่อrepoที่ผิดรูปแบบถูกปฏิเสธก่อนเอาไปต่อurl(evil):
    """ชื่อนี้ถูกเอาไปต่อใน /repos/{owner}/{name} — ถ้าไม่ตรวจ ปลายทางเปลี่ยนได้"""
    with pytest.raises(IngestError):
        from_github(f"github.com/{OWNER}", repos=[evil], client=client())


def test_ชื่อที่ไม่ใช่repoของเจ้าของบัญชีถูกปฏิเสธ():
    """รูปแบบถูกต้องก็ยังไม่พอ — ต้องเป็นของบัญชีนั้นจริง"""
    with pytest.raises(IngestError) as exc:
        from_github(f"github.com/{OWNER}", repos=["repo-ที่ไม่ได้เป็นเจ้าของ"],
                    client=client())
    assert "repo-ที่ไม่ได้เป็นเจ้าของ" in str(exc.value)


# ═════════════ ดึงเฉพาะที่เลือก ═════════════


def test_เลือกอันเดียวอ่านแค่อันนั้น():
    r = from_github(f"github.com/{OWNER}", repos=["math-notes"], client=client())
    assert "math-notes" in r.raw_text
    assert "burn-ledger" not in r.raw_text


def test_เลือกสองอันได้ทั้งสองอัน():
    r = from_github(f"github.com/{OWNER}", repos=["burn-ledger", "math-notes"],
                    client=client())
    assert "burn-ledger" in r.raw_text and "math-notes" in r.raw_text


def test_บอกจำนวนที่อ่านจริงตามที่เลือก():
    """🔒 กติกาข้อ 5 — note ขึ้นหน้าจอ ต้องตรงกับที่ทำจริง"""
    r = from_github(f"github.com/{OWNER}", repos=["math-notes"], client=client())
    assert "1" in r.note


def test_ไม่ส่งrepoมาเลยทำงานเหมือนเดิม():
    """ของเดิมต้องไม่พัง — คนที่เรียกแบบเก่ายังได้ผลแบบเก่า"""
    r = from_github(f"github.com/{OWNER}", client=client())
    assert "burn-ledger" in r.raw_text and "math-notes" in r.raw_text


def test_เลือกศูนย์อันถือว่าไม่ได้เลือกไม่ใช่อ่านทั้งหมด():
    """🔴 ถ้าตีความ [] ว่า "ไม่ได้ส่งมา" ระบบจะอ่านทุก repo ทั้งที่ผู้ใช้ไม่ได้เลือกอะไรเลย
    ซึ่งตรงข้ามกับทั้งฟีเจอร์นี้
    """
    with pytest.raises(IngestError):
        from_github(f"github.com/{OWNER}", repos=[], client=client())
