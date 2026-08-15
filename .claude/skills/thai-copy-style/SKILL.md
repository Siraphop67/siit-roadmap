---
name: thai-copy-style
description: Style guide and terminology glossary for all Thai user-facing copy in the SIIT Roadmap frontend. Use whenever writing, editing, or reviewing Thai text shown to users — page headings, button labels, error messages, loading states, placeholders, aria-labels. Target register is formal/semi-formal written Thai as used in news reporting and published prose.
---

# Thai copy style — SIIT Roadmap

Applies to **user-facing strings only**. Thai code comments are documentation and are left alone.

## 1. Register

Target: **กึ่งทางการ** — the register of a well-edited Thai magazine feature, not a government circular. Correct grammar and complete phrases, but written to be *read*: warm, concrete, with rhythm.

> Pairs with the global `thai-translate` skill, whose register matrix puts consumer/student UI at กึ่งทางการ (คุณ / เรา). When the two disagree on register, follow `thai-translate`; this file governs the project glossary in §3.

- Address the reader as **คุณ**. The product refers to itself as **เรา** in prose and **ระบบ** when describing mechanism. Never ฉัน/เธอ/นาย/มึง — except a first-person consent statement, where **ฉัน** is correct.
- Prefer complete noun phrases over clipped fragments. `ยังขาด` → `ทักษะที่ยังขาด`.
- **Cadence matters.** Short sentence, then a longer one. Use `—` or a line break for the turn in an argument. `รู้ว่ามีงานอะไร ยังไม่พอ ต้องรู้ว่าจะไปถึงได้อย่างไร` beats a single 40-character noun phrase.
- No sentence-final particles (นะ ค่ะ ครับ จ้า เลย) in UI chrome. They belong in conversation, not in an interface.
- No exclamation marks. No emoji in copy strings.

### Over-formality is a bug, not a safety margin

Reaching for the most formal option makes student-facing copy read like a summons. These were all corrected out of this codebase — do not reintroduce them:

| Too formal | Use instead |
|---|---|
| ข้าพเจ้า | ฉัน (consent), or drop the pronoun |
| มิใช่ | ไม่ใช่ |
| คณะผู้จัดทำ | ทีมงาน |
| ไม่สามารถ…ได้ *(every error)* | fine for validation; for transient failures prefer `…ไม่ได้ในตอนนี้` |
| ดำเนินการ… *(as filler)* | name the actual verb |
| กรุณา… *(on every action)* | keep for form validation; drop from ordinary buttons |
| ประกอบอาชีพใด | ทำงานอะไร |

The test: read it aloud. If it sounds like an announcement over a train-station PA, rewrite it.
- **Delete the RPG metaphor entirely.** quest, character sheet, build, signal, mission, unlock, XP, level-up. This vocabulary clashes with the institutional register and is the single largest source of the "odd wording" complaint.

## 2. English loanword policy

**Thai first, English in parentheses on first use per page. Thai alone thereafter.**

```
first use   เส้นทางพัฒนาอาชีพ (roadmap)
after       เส้นทางพัฒนาอาชีพ
```

Exceptions kept in English permanently:
- Proper nouns and brand: `SIIT`, `SIIT Roadmap`, `O*NET`
- Established abbreviations with no clean Thai form: `CV`, `GPA`, `AI`
- Code identifiers, URLs, file names

Never leave a bare English noun inside a Thai sentence (`บันทึก choice ไม่สำเร็จ`). Either translate it or give it the parenthetical treatment.

## 3. Glossary — use these exact renderings

| English / current | Use this |
|---|---|
| roadmap | เส้นทางพัฒนาอาชีพ (roadmap) → เส้นทางพัฒนาอาชีพ |
| Career Library / คลังอาชีพ | คลังข้อมูลอาชีพ (Career Library) |
| skill | ทักษะ |
| Skill Graph | แผนผังทักษะ (Skill Graph) |
| Activity Quiz | แบบประเมินความสนใจเชิงกิจกรรม (Activity Quiz) |
| portfolio / ผลงาน | แฟ้มผลงาน |
| CV | CV (keep) |
| course | รายวิชา |
| resource / learning option | ช่องทางการเรียนรู้ |
| target / goal | อาชีพเป้าหมาย |
| step / node | ขั้นการพัฒนา |
| quest | ขั้นการพัฒนา (never ภารกิจ/quest) |
| character sheet | ข้อมูลความสนใจของคุณ |
| signal / choice | คำตอบ |
| build | แนวทางที่เหมาะกับคุณ |
| unlock / ปลดล็อก | เปิดให้เข้าถึง — or rephrase to ผ่านเกณฑ์ |
| evidence | หลักฐานอ้างอิง |
| extracted (from CV) | สกัดจาก CV |
| self-reported / ประเมินเอง | ผู้ใช้ประเมินด้วยตนเอง |
| curated / ทีมเขียนเอง | คณะผู้จัดทำเรียบเรียง |
| job posting / ประกาศงาน | ประกาศรับสมัครงาน |
| employer | ผู้ประกอบการ |
| level | ระดับ |
| prerequisite | ทักษะที่ต้องมีก่อน |

## 4. Sentence patterns

**Errors** — use `ไม่สามารถ…ได้`, not `…ไม่สำเร็จ`:

```
✗ โหลดคลังอาชีพไม่สำเร็จ
✓ ไม่สามารถโหลดคลังข้อมูลอาชีพได้
```

**Loading** — `กำลัง` + verb + object. No trailing ellipsis character `…`; end the phrase cleanly:

```
✗ กำลังสร้าง character sheet ของคุณ…
✓ กำลังประมวลผลข้อมูลความสนใจของคุณ
```

**Empty states** — state the cause, then the next action:

```
✓ ยังไม่พบข้อมูลผู้ใช้ กรุณาเลือกอาชีพเป้าหมายก่อน
```

**Buttons** — verb phrase, no particles, no trailing punctuation: `เลือกอาชีพเป้าหมาย`, `ดูเส้นทางพัฒนา`, `ลองอีกครั้ง`.

## 5. Mechanics

- **Spacing.** No space between Thai words. One space before and after embedded Latin text or numerals: `ทักษะ 8 รายการ`, `อ้างอิง O*NET`.
- **Classifiers must match the noun.** `ทักษะ 8 ทักษะ`, `อาชีพ 8 อาชีพ`, `ประกาศรับสมัครงาน 3 ฉบับ`, `รายวิชา 5 รายวิชา`. Never the vague `เรื่อง` or `อัน` for countable domain objects.
- **Middle dot `·`** as a field separator is fine; keep one space either side.
- **Ranges** use `–` (en dash) with no spaces: `3–5 อาชีพ`.
- Avoid stacking `ที่` / `ซึ่ง` more than once per sentence.
- Avoid English syntax calques — especially passive constructions (`ถูก…โดย`) where Thai prefers an active or agentless form.

## 6. Consistency check before finishing

1. No bare English nouns inside Thai sentences.
2. No RPG vocabulary anywhere.
3. Every error string uses `ไม่สามารถ…ได้`.
4. A given concept uses one rendering across all files — check against §3.
5. Buttons and their loading states are in the same language.
