"""เทสต์ที่พิสูจน์ว่าแบบทดสอบฝั่ง "ยังไม่รู้" ไม่ได้ให้คำตอบเดียวกับทุกคน

เธรด r/findapath บ่นซ้ำ ๆ ว่าแบบทดสอบอาชีพ "แนะนำให้เป็นพยาบาลทุกคน"
ไฟล์นี้คือเครื่องมือที่จับปัญหานั้นได้ทุกครั้งที่มีคนไปแก้น้ำหนักหรือแก้ข้อคำถาม
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.engine.match_target import (
    ActivityAnswer,
    centered_profile,
    match_targets,
    next_best_item,
)
from app.seed.activities import ACTIVITY_ITEMS, WORK_ACTIVITIES_TH
from app.seed.careers import CAREER_TARGETS

PIPELINE_OUT = Path(__file__).resolve().parents[2] / "pipeline" / "out"


@pytest.fixture(scope="module")
def onet() -> dict:
    path = PIPELINE_OUT / "target_activity_profiles.json"
    if not path.exists():
        pytest.skip("ยังไม่ได้รัน pipeline/1b_import_instruments.py")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def profiles(onet) -> dict[str, dict[str, float]]:
    """โปรไฟล์กิจกรรมของ 8 อาชีพ โดยใช้ id ของเราแทนรหัส SOC

    ใช้ `onet_activity_soc` ไม่ใช่ `onet_soc_code` เพราะ 2 อาชีพต้องใช้อาชีพตัวแทน
    (O*NET ยังไม่มีข้อมูลกิจกรรมของ Software Developers และ Data Scientists)
    """
    by_soc = {t["onet_activity_soc"]: t["id"] for t in CAREER_TARGETS}
    return {
        by_soc[soc]: prof
        for soc, prof in onet["profiles"].items()
        if soc in by_soc and prof
    }


@pytest.fixture(scope="module")
def requirements() -> dict[str, list[tuple[str, int, float]]]:
    return {t["id"]: list(t["requirements"]) for t in CAREER_TARGETS}


def answers_matching(profile: dict[str, float], strength: float = 0.5) -> list[ActivityAnswer]:
    """ผู้ใช้จำลองที่ตอบตามลักษณะงานของอาชีพหนึ่ง

    หักค่ากลางแล้วตอบ +1 กับกิจกรรมที่อาชีพนั้นเน้น · −1 กับที่ไม่เน้น · 0 กับกลาง ๆ
    """
    centered = centered_profile(profile)
    out = []
    for aid, z in centered.items():
        out.append(ActivityAnswer(aid, 1 if z > strength else -1 if z < -strength else 0))
    return out


# ═══════════ ความถูกต้องของข้อมูลตั้งต้น ═══════════


def test_every_activity_id_exists_in_onet():
    """🔒 ข้ออ้างว่า "อิงมาตรฐานสากล" ต้องตรวจสอบได้ ไม่ใช่แค่พูด"""
    path = PIPELINE_OUT / "work_activities.json"
    if not path.exists():
        pytest.skip("ยังไม่ได้รัน pipeline/1b_import_instruments.py")
    real = {a["id"] for a in json.loads(path.read_text(encoding="utf-8"))}
    ours = {a["id"] for a in WORK_ACTIVITIES_TH}
    assert ours <= real, f"กิจกรรมที่ไม่มีอยู่จริงใน O*NET: {ours - real}"
    assert len(ours) == 41, f"ควรมีครบ 41 มิติ แต่มี {len(ours)}"


def test_proxy_occupations_are_recorded_not_hidden():
    """🔴 อาชีพที่ใช้โปรไฟล์ของอาชีพอื่น ต้องบันทึกไว้ให้เห็น ไม่ใช่เงียบ ๆ"""
    for t in CAREER_TARGETS:
        used_proxy = t["onet_activity_soc"] != t["onet_soc_code"]
        assert bool(t["activity_proxy_note"]) == used_proxy, (
            f'{t["id"]}: ใช้ตัวแทนแต่ไม่ได้บันทึก หรือบันทึกทั้งที่ไม่ได้ใช้'
        )


def test_every_item_points_at_a_real_activity():
    ids = {a["id"] for a in WORK_ACTIVITIES_TH}
    for item in ACTIVITY_ITEMS:
        assert item["activity_id"] in ids
    assert len({i["id"] for i in ACTIVITY_ITEMS}) == len(ACTIVITY_ITEMS), "id ข้อคำถามซ้ำ"


def test_items_ask_about_activities_not_about_the_person():
    """✅ "ตรวจเครื่องจักรว่าชิ้นไหนกำลังจะพัง"  ❌ "คุณเป็นคนละเอียดไหม" """
    banned = ("คุณเป็นคน", "บุคลิก", "นิสัย", "คุณชอบ", "คุณถนัด", "ตัวคุณ")
    for item in ACTIVITY_ITEMS:
        text = item["prompt_th"] + " " + (item["context_th"] or "")
        for b in banned:
            assert b not in text, f'{item["id"]} ถามถึงตัวคน: "{b}"'


def test_all_eight_targets_have_an_activity_profile(profiles):
    assert len(profiles) == 8, f"อาชีพที่ไม่มีโปรไฟล์กิจกรรม: {8 - len(profiles)}"
    for pid, prof in profiles.items():
        assert len(prof) == 41, f"{pid} มีโปรไฟล์ไม่ครบ 41 มิติ"


# ═══════════ 🔴 เทสต์กู้คืน — หัวใจของเรื่อง ═══════════


@pytest.mark.parametrize("target_id", [t["id"] for t in CAREER_TARGETS])
def test_recovery_simulated_user_gets_their_own_career_first(target_id, profiles, requirements):
    """🔴 คนที่ตอบตามลักษณะงานของอาชีพ X ต้องได้ X เป็นอันดับ 1

    ถ้าเทสต์นี้ตก แปลว่าแบบทดสอบให้คำตอบกลาง ๆ กับทุกคน
    ซึ่งคือข้อบกพร่องที่คนบ่นถึงมากที่สุดในแบบทดสอบอาชีพที่มีอยู่
    """
    outcome = match_targets(
        answers=answers_matching(profiles[target_id]),
        target_profiles=profiles,
        requirements=requirements,
    )
    assert outcome.ranked, "ไม่มีอาชีพถูกเสนอเลย"
    got = outcome.ranked[0].target_id
    assert got == target_id, (
        f"ผู้ใช้ที่ตอบตามลักษณะงานของ {target_id} กลับได้ {got} เป็นอันดับ 1\n"
        + "\n".join(f"  {s.rank_no}. {s.target_id:14} {s.score:+.4f}" for s in outcome.ranked)
    )


def test_different_users_get_different_answers(profiles, requirements):
    """ผู้ใช้ 8 แบบต้องได้อันดับ 1 ไม่ซ้ำกัน — ไม่ใช่ทุกคนได้อาชีพเดียวกัน"""
    firsts = {
        tid: match_targets(
            answers=answers_matching(profiles[tid]),
            target_profiles=profiles,
            requirements=requirements,
        ).ranked[0].target_id
        for tid in profiles
    }
    assert len(set(firsts.values())) == len(profiles), (
        f"อันดับ 1 ซ้ำกัน — ระบบให้คำตอบกลาง ๆ : {firsts}"
    )


# ═══════════ กติกากันผลลัพธ์ที่มั่นใจเกินจริง ═══════════


def test_no_answers_means_nothing_is_proposed(profiles, requirements):
    outcome = match_targets(
        answers=[], target_profiles=profiles, requirements=requirements)
    assert outcome.ranked == []
    assert not outcome.separated


def test_every_proposed_target_can_be_traced_back(profiles, requirements):
    """🔒 ย้อนที่มาไม่ได้ = ไม่แสดง"""
    outcome = match_targets(
        answers=answers_matching(profiles["SW-DEV"]),
        target_profiles=profiles, requirements=requirements)
    assert outcome.ranked
    for s in outcome.ranked:
        assert s.traced_to, f"{s.target_id} ถูกเสนอโดยไม่มีที่มา"
        for t in s.traced_to:
            assert t.ref_id and t.label


def test_flat_answers_report_not_separated(profiles, requirements):
    """ตอบ "เฉย ๆ" ทุกข้อ → ต้องบอกตรง ๆ ว่ายังแยกไม่ออก ไม่ใช่ยัดอันดับ"""
    flat = [ActivityAnswer(a["id"], 0) for a in WORK_ACTIVITIES_TH]
    outcome = match_targets(
        answers=flat, target_profiles=profiles, requirements=requirements)
    assert not outcome.separated
    assert outcome.separation_reason


def test_separation_reason_is_shown_when_top_two_are_close(profiles, requirements):
    outcome = match_targets(
        answers=answers_matching(profiles["MECH-DESIGN"], strength=2.0),
        target_profiles=profiles, requirements=requirements)
    if not outcome.separated:
        assert outcome.separation_reason, "บอกว่ายังแยกไม่ออก แต่ไม่บอกว่าเพราะอะไร"


# ═══════════ สัญญาณจาก CV ต้องหนักกว่าที่ผู้ใช้บอกเอง ═══════════


def test_evidence_from_cv_outweighs_self_reported(profiles, requirements):
    base = answers_matching(profiles["SW-DEV"])
    skills = {s: 3 for s, _, _ in requirements["DATA-ENG"]}

    with_cv = match_targets(
        answers=base, target_profiles=profiles, requirements=requirements,
        extracted_skills=skills)
    with_self = match_targets(
        answers=base, target_profiles=profiles, requirements=requirements,
        self_reported_skills=skills)

    cv = next(s for s in with_cv.ranked if s.target_id == "DATA-ENG")
    sr = next(s for s in with_self.ranked if s.target_id == "DATA-ENG")
    assert cv.score > sr.score, "ทักษะที่มีหลักฐานจาก CV ต้องมีน้ำหนักมากกว่าที่กรอกเอง"
    assert cv.score_extracted > 0 and cv.score_self_reported == 0
    assert sr.score_self_reported > 0 and sr.score_extracted == 0


def test_extracted_and_self_reported_never_merge(profiles, requirements):
    """จุดขายของผลิตภัณฑ์ — สองอย่างนี้ต้องแยกกันได้เสมอในผลลัพธ์"""
    outcome = match_targets(
        answers=answers_matching(profiles["SW-DEV"]),
        target_profiles=profiles, requirements=requirements,
        extracted_skills={"T-PY": 3}, self_reported_skills={"SW-DS": 2})
    top = outcome.ranked[0]
    kinds = {t.kind for t in top.traced_to}
    assert "extracted_skill" in kinds or "self_reported_skill" in kinds
    for t in top.traced_to:
        assert t.kind in {"activity", "extracted_skill", "self_reported_skill", "values"}


# ═══════════ การเลือกข้อถัดไป ═══════════


def test_next_item_picks_the_most_discriminating_question(profiles):
    """ข้อถัดไปต้องเป็นข้อที่แยกอันดับ 1 กับ 2 ได้ดีที่สุด"""
    a, b = "MECH-DESIGN", "MFG-ENG"
    pick = next_best_item(set(), profiles, (a, b))
    assert pick is not None

    ca, cb = centered_profile(profiles[a]), centered_profile(profiles[b])
    best = max(abs(ca[k] - cb[k]) for k in ca)
    assert abs(ca[pick] - cb[pick]) == pytest.approx(best), "ไม่ได้เลือกข้อที่แยกได้ดีที่สุด"


def test_next_item_never_repeats_an_answered_question(profiles):
    asked: set[str] = set()
    for _ in range(41):
        pick = next_best_item(asked, profiles, ("MECH-DESIGN", "MFG-ENG"))
        if pick is None:
            break
        assert pick not in asked
        asked.add(pick)
    assert len(asked) == 41


def test_matching_is_deterministic(profiles, requirements):
    """ตอนสาธิตห้ามมีอะไรขยับเอง"""
    runs = [
        [(s.target_id, round(s.score, 6))
         for s in match_targets(answers=answers_matching(profiles["ROBOT-ENG"]),
                                target_profiles=profiles,
                                requirements=requirements).ranked]
        for _ in range(3)
    ]
    assert runs[0] == runs[1] == runs[2]
