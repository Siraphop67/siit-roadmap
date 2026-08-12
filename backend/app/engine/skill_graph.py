"""เครื่องมือบน DAG ของ skill_edge (ยกมาจาก draft 1 — prototype/backend/app/engine/graph.py)

🔴 skill_edge แบกน้ำหนักสองอย่างพร้อมกัน (Tech-Architecture §3):
   ตัวเลือกก้าวถัดไป และลำดับของ roadmap ทั้งเส้น
   เส้นผิด = frontier ผิด และ เส้นทางผิด พร้อมกัน
"""

from __future__ import annotations

from collections import defaultdict


class SkillGraph:
    def __init__(self, skill_ids: list[str], edges: list[tuple[str, str]]):
        self.nodes = set(skill_ids)
        self.edges = [(a, b) for a, b in edges]
        self._prereqs: dict[str, set[str]] = defaultdict(set)  # to → {from}
        self._unlocks: dict[str, set[str]] = defaultdict(set)  # from → {to}
        for a, b in self.edges:
            self._prereqs[b].add(a)
            self._unlocks[a].add(b)
        self._assert_acyclic()

    # ── โครงสร้างพื้นฐาน ──────────────────────────────────────

    def prereqs(self, skill_id: str) -> set[str]:
        """ตัวที่ต้องมีก่อนโดยตรง"""
        return set(self._prereqs.get(skill_id, set()))

    def unlocks(self, skill_id: str) -> set[str]:
        """ตัวที่ปลดล็อกได้โดยตรง"""
        return set(self._unlocks.get(skill_id, set()))

    def transitive_prereqs(self, skill_ids: set[str]) -> set[str]:
        """ตัวที่ต้องมีก่อนทั้งหมด รวมตัวเองด้วย"""
        seen: set[str] = set()
        stack = list(skill_ids)
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(self._prereqs.get(cur, set()))
        return seen

    def transitive_unlocks(self, skill_id: str, within: set[str] | None = None) -> set[str]:
        """ตัวที่ปลดล็อกได้ทั้งหมด (ไม่รวมตัวเอง) — จำกัดขอบเขตด้วย within ได้"""
        seen: set[str] = set()
        stack = list(self._unlocks.get(skill_id, set()))
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            if within is not None and cur not in within:
                continue
            seen.add(cur)
            stack.extend(self._unlocks.get(cur, set()))
        return seen

    # ── การเรียงลำดับ ─────────────────────────────────────────

    def topo_sort(self, nodes: set[str], priority: dict[str, float] | None = None) -> list[str]:
        """เรียงลำดับตาม prerequisite โดยใช้ priority เป็นตัวตัดสินว่าใครออกก่อน

        🔒 นี่คือกลไกที่ทำให้ invariant `path[0] == frontier ที่ RANK เลือก` เป็นจริง
           โดยโครงสร้าง ไม่ใช่โดยบังเอิญ:
           ถ้าส่ง priority = คะแนน RANK เข้ามา ตัวที่ RANK ให้คะแนนสูงสุด
           ในบรรดาตัวที่ลงมือได้ทันที จะถูกปล่อยออกมาเป็นตัวแรกเสมอ

        เสมอกันตัดด้วย id เพื่อให้ผลรันซ้ำได้เหมือนเดิมทุกครั้ง
        """
        priority = priority or {}
        pending = set(nodes)
        indeg = {n: len(self._prereqs.get(n, set()) & pending) for n in pending}
        out: list[str] = []

        while pending:
            ready = [n for n in pending if indeg[n] == 0]
            if not ready:  # ไม่ควรเกิด เพราะ _assert_acyclic ผ่านแล้ว
                raise ValueError("พบวงจรใน skill_edge")
            ready.sort(key=lambda n: (-priority.get(n, 0.0), n))
            chosen = ready[0]
            out.append(chosen)
            pending.discard(chosen)
            for nxt in self._unlocks.get(chosen, set()):
                if nxt in indeg:
                    indeg[nxt] -= 1
        return out

    # ── ความถูกต้องของกราฟ ────────────────────────────────────

    def _assert_acyclic(self) -> None:
        color: dict[str, int] = {}

        def visit(n: str) -> None:
            color[n] = 1
            for m in self._unlocks.get(n, set()):
                if color.get(m) == 1:
                    raise ValueError(f"skill_edge มีวงจรที่ {n} → {m}")
                if color.get(m) is None:
                    visit(m)
            color[n] = 2

        for n in self.nodes:
            if color.get(n) is None:
                visit(n)

    def dangling_edges(self) -> list[tuple[str, str]]:
        """เส้นที่ชี้ไปยัง ทักษะที่ไม่มีอยู่จริง"""
        return [(a, b) for a, b in self.edges if a not in self.nodes or b not in self.nodes]
