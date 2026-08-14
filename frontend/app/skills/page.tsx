"use client";

/**
 * Skill Graph — ค่าเริ่มต้นคือ *กราฟของคุณ* ไม่ใช่กราฟของระบบ
 *
 * 🔴 ทำไมไม่โชว์ 73 ทักษะทั้งใบตั้งแต่แรก
 *    คนที่มี 6 ทักษะไม่ควรต้องหาตัวเองใน 73 กล่อง · กราฟทั้งใบตอบคำถามว่า
 *    "ระบบรู้จักทักษะอะไรบ้าง" ซึ่งไม่ใช่คำถามที่ผู้ใช้ถาม เขาถามว่า
 *    "ตอนนี้ฉันอยู่ตรงไหน แล้วไปต่อทางไหนได้" → API มี scope=mine ให้แล้ว
 *    ทั้งใบยังดูได้ แต่ต้องกดเอง
 *
 * มุมมอง "ของฉัน" วางเป็น 3 คอลัมน์ให้เส้นอ่านจากซ้ายไปขวาเป็นลำดับ:
 *    ยังขาด (ขวางอยู่)  →  คุณมีแล้ว  →  ไปต่อได้ทันที
 */

import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import {
  api,
  session,
  type SkillDetail,
  type SkillGraph,
  type SkillNode,
  type SkillRelation,
} from "@/lib/api";
import { Icon, InlineNotice, MobileWorkspaceNav, WorkspaceSidebar } from "@/components/student-ui";

const dots = ["#005bb2", "#d4402e", "#8b4c00", "#3274cd", "#585f6a", "#4d8b68", "#9b5ab6"];

/** ลำดับคอลัมน์ = ลำดับเวลา · ยังขาดต้องอยู่ก่อนสิ่งที่มี ไม่งั้นเส้นจะย้อนทาง */
const COLUMNS: { relation: SkillRelation; title: string; hint: string; color: string }[] = [
  {
    relation: "prereq_missing",
    title: "ยังขาด",
    hint: "ต้องมีก่อนถึงจะต่อยอดสิ่งที่คุณมีได้",
    color: "#8b4c00",
  },
  { relation: "have", title: "คุณมีแล้ว", hint: "ยืนยันจาก CV หรือประเมินเอง", color: "#005bb2" },
  { relation: "next", title: "ไปต่อได้ทันที", hint: "ต่อยอดจากสิ่งที่คุณมีตอนนี้", color: "#4d8b68" },
];

const COL_X = [190, 520, 850];
const ROW_H = 104;

/**
 * อ่าน user_id จาก localStorage แบบที่ hydration ไม่พัง
 *
 * 🔴 เรียก `session.read()` ตอน render ตรง ๆ ไม่ได้ — ฝั่ง server ไม่มี localStorage
 *    จึงได้ null แล้วฝั่ง client ได้ id ทำให้ React บ่นว่า server กับ client วาดไม่ตรงกัน
 *    (หน้านี้เห็นชัดเพราะหัวข้อเปลี่ยนไปเลยระหว่าง "ของคุณ" กับ "ทั้งหมด")
 *    useSyncExternalStore มี snapshot แยกสำหรับ server ให้อยู่แล้ว — ใช้ตัวนั้น
 *    หน้าอื่นที่เรียก session.read() ตอน render ก็มีปัญหาเดียวกัน แค่ยังไม่แสดงออก
 */
const noopSubscribe = () => () => {};
function useSessionUser(): string | null {
  return useSyncExternalStore(
    noopSubscribe,
    () => session.read(),
    () => null,
  );
}

export default function SkillsPage() {
  const uid = useSessionUser();
  // ยังไม่ได้เลือกเอง = ใครมี session ให้เริ่มที่กราฟของตัวเอง · ไม่มีก็ดูทั้งใบไปก่อน
  const [chosen, setChosen] = useState<"mine" | "all" | null>(null);
  const scope = chosen ?? (uid ? "mine" : "all");
  const [graph, setGraph] = useState<SkillGraph | null>(null);
  const [detail, setDetail] = useState<SkillDetail | null>(null);
  const [selected, setSelected] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const load = useCallback(() => setRetry((n) => n + 1), []);

  // ทุก setState อยู่ใน callback ของ promise — ไม่ใช่ในตัว effect เอง (react-hooks/set-state-in-effect)
  useEffect(() => {
    let alive = true;
    api
      .skills(uid, scope)
      .then((data) => {
        if (!alive) return;
        setError("");
        setGraph(data);
        const first = data.nodes.find((n) => n.relation === "have") ?? data.nodes[0];
        if (first) setSelected(first.id);
      })
      .catch((e: unknown) => {
        if (alive) setError(e instanceof Error ? e.message : "โหลดกราฟทักษะไม่สำเร็จ");
      });
    return () => {
      alive = false;
    };
  }, [uid, scope, retry]);

  useEffect(() => {
    if (!selected) return;
    let alive = true;
    api
      .skill(selected, uid)
      .then((d) => alive && setDetail(d))
      .catch(() => alive && setDetail(null));
    return () => {
      alive = false;
    };
  }, [selected, uid]);

  // 🔴 วางผังตาม scope ที่ *ข้อมูลบอกว่าตัวเองเป็น* ไม่ใช่ปุ่มที่เพิ่งกด
  //    ไม่งั้นช่วงที่คำขอใหม่ยังไม่กลับ จะเอา node ทั้ง 73 ตัวไปเรียงลง 3 คอลัมน์
  const view = graph?.scope ?? scope;

  const filtered = useMemo(
    () =>
      (graph?.nodes ?? []).filter(
        (node) =>
          (view === "mine" || category === "all" || node.category === category) &&
          `${node.name_th} ${node.name_en}`.toLowerCase().includes(search.toLowerCase()),
      ),
    [graph, category, search, view],
  );

  const positions = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    if (view === "mine") {
      COLUMNS.forEach((col, index) =>
        filtered
          .filter((node) => node.relation === col.relation)
          .forEach((node, row) => map.set(node.id, { x: COL_X[index], y: 150 + row * ROW_H })),
      );
      return map;
    }
    const byCategory = new Map<string, SkillNode[]>();
    filtered.forEach((node) =>
      byCategory.set(node.category, [...(byCategory.get(node.category) ?? []), node]),
    );
    [...byCategory.values()].forEach((nodes, col) =>
      nodes.forEach((node, row) => map.set(node.id, { x: 150 + col * 245, y: 95 + row * 92 })),
    );
    return map;
  }, [filtered, view]);

  const canvasWidth =
    view === "mine"
      ? 1040
      : Math.max(1000, (new Set(filtered.map((n) => n.category)).size + 1) * 245);
  const canvasHeight = Math.max(
    650,
    Math.max(0, ...[...positions.values()].map((p) => p.y)) + 140,
  );

  const subtitle =
    view === "mine" && graph
      ? `คุณมี ${graph.counts.have} ทักษะ · ยังขาด ${graph.counts.prereq_missing} ตัวที่ขวางอยู่ · ไปต่อได้ทันที ${graph.counts.next} ตัว`
      : `ทักษะทั้งหมดที่ระบบรู้จัก ${graph?.counts.skills ?? 73} ตัว และ ${graph?.counts.edges ?? 105} ความสัมพันธ์`;

  return (
    <div className="flex h-screen w-full bg-surface-bg overflow-hidden pb-16 lg:pb-0">
      <WorkspaceSidebar active="skills" variant="graph" />
      <main className="flex-1 flex flex-col h-full relative min-w-0">
        <header className="px-margin-mobile md:px-gutter py-stack-md border-b border-border-low bg-surface-bg/90 backdrop-blur-sm z-10 flex flex-col sm:flex-row justify-between sm:items-center gap-3">
          <div>
            <h1 className="text-headline-md font-headline-md font-semibold text-text-main">
              {view === "mine" ? "Skill Graph ของคุณ" : "Skill Graph ทั้งหมด"}
            </h1>
            <p className="text-sm sm:text-body-md text-text-subtle">{subtitle}</p>
          </div>
          <div className="flex gap-2 items-center">
            {/* สลับมุมมอง — ทั้งใบยังดูได้ แต่ไม่ใช่หน้าแรกที่เจอ */}
            <div className="flex rounded-lg border border-border-low overflow-hidden text-sm">
              {(["mine", "all"] as const).map((value) => (
                <button
                  key={value}
                  onClick={() => setChosen(value)}
                  disabled={value === "mine" && !uid}
                  title={
                    value === "mine" && !uid ? "ต้องเริ่มใช้งานก่อนถึงจะมีกราฟของตัวเอง" : undefined
                  }
                  className={`px-3 py-2 disabled:opacity-40 ${
                    scope === value
                      ? "bg-primary text-on-primary"
                      : "bg-surface-muted text-text-subtle hover:text-text-main"
                  }`}
                >
                  {value === "mine" ? "ของฉัน" : "ทั้งหมด"}
                </button>
              ))}
            </div>
            <div className="relative">
              <Icon className="absolute left-2 top-1/2 -translate-y-1/2 text-base text-text-subtle">
                search
              </Icon>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-36 pl-8 pr-2 py-2 text-sm bg-surface-muted border border-border-low rounded-lg"
                placeholder="ค้นหาทักษะ"
              />
            </div>
            {view === "all" && (
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="max-w-40 px-2 py-2 text-sm bg-surface-muted border border-border-low rounded-lg"
              >
                <option value="all">ทุกหมวด</option>
                {graph?.categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.label_th} ({cat.count})
                  </option>
                ))}
              </select>
            )}
          </div>
        </header>

        {error && (
          <div className="p-4">
            <InlineNotice tone="error">
              {error}{" "}
              <button className="underline" onClick={load}>
                ลองใหม่
              </button>
            </InlineNotice>
          </div>
        )}
        {!graph && !error && <p className="m-auto text-text-subtle">กำลังสร้างกราฟ…</p>}

        {/* 🔒 ว่างเปล่าเงียบ ๆ ไม่ได้ — บอกเหตุผลและทางไปต่อ ตามที่ API ส่งมา */}
        {graph && graph.empty_message && (
          <div className="m-auto max-w-md text-center px-gutter">
            <p className="text-body-md text-text-subtle mb-stack-md">{graph.empty_message}</p>
            <a
              href="/portfolio"
              className="inline-block px-4 py-2 bg-primary text-on-primary rounded-lg"
            >
              ส่งผลงานของคุณ
            </a>
            <button className="block mx-auto mt-stack-md underline text-sm text-text-subtle" onClick={() => setChosen("all")}>
              หรือดูทักษะทั้งหมดที่ระบบรู้จักก่อน
            </button>
          </div>
        )}

        {graph && !graph.empty_message && (
          <div className="flex-1 flex flex-col lg:flex-row relative overflow-hidden">
            <section
              className="flex-1 graph-bg relative overflow-auto cursor-grab"
              aria-label="กราฟความสัมพันธ์ของทักษะ"
            >
              <div className="relative" style={{ width: canvasWidth, height: canvasHeight }}>
                <svg
                  className="absolute inset-0 w-full h-full pointer-events-none"
                  aria-hidden="true"
                >
                  {graph.edges.map((edge, index) => {
                    const from = positions.get(edge.from);
                    const to = positions.get(edge.to);
                    if (!from || !to) return null;
                    const touchesSelected = selected === edge.from || selected === edge.to;
                    return (
                      <line
                        key={`${edge.from}-${edge.to}-${index}`}
                        stroke={touchesSelected ? "#005bb2" : "#c2c6d4"}
                        strokeWidth={touchesSelected ? 2.5 : 1.5}
                        x1={from.x}
                        y1={from.y}
                        x2={to.x}
                        y2={to.y}
                      />
                    );
                  })}
                </svg>

                {view === "mine" &&
                  COLUMNS.map((col, index) => (
                    <div
                      key={col.relation}
                      className="absolute -translate-x-1/2 text-center w-56"
                      style={{ left: COL_X[index], top: 40 }}
                    >
                      <div className="flex items-center justify-center gap-2">
                        <span
                          className="w-2.5 h-2.5 rounded-full"
                          style={{ background: col.color }}
                        />
                        <span className="text-label-sm font-label-sm uppercase tracking-wider text-text-main">
                          {col.title}
                        </span>
                      </div>
                      <p className="text-[11px] text-text-subtle mt-1">{col.hint}</p>
                    </div>
                  ))}

                {filtered.map((node) => {
                  const pos = positions.get(node.id);
                  if (!pos) return null;
                  const active = selected === node.id;
                  const hasCv = node.level_from_cv != null;
                  const hasSelf = node.level_self_reported != null;
                  const column = COLUMNS.find((c) => c.relation === node.relation);
                  const catIndex = graph.categories.findIndex((c) => c.id === node.category);
                  const dot =
                    view === "mine" && column
                      ? column.color
                      : dots[Math.max(0, catIndex) % dots.length];
                  return (
                    <button
                      key={node.id}
                      onClick={() => setSelected(node.id)}
                      title={node.relation_th}
                      className={`absolute -translate-x-1/2 -translate-y-1/2 bg-surface-bg rounded-lg p-3 text-left shadow-[0_4px_12px_rgba(0,0,0,.05)] transition-colors w-48 ${
                        active ? "border-2 border-primary" : "border border-border-low hover:border-primary"
                      }`}
                      style={{ left: pos.x, top: pos.y }}
                    >
                      <div className="flex items-start gap-2">
                        <span
                          className="w-3 h-3 rounded-full mt-1 shrink-0"
                          style={{ background: dot }}
                        />
                        <span
                          className={`text-xs leading-snug ${
                            active ? "text-primary font-bold" : "text-text-main font-semibold"
                          }`}
                        >
                          {node.name_th ?? node.name_en}
                        </span>
                      </div>
                      {/* 🔒 กติกาข้อ 1 — มาจาก CV กับกรอกเอง ต้องดูออกว่าต่างกัน */}
                      {(hasCv || hasSelf) && (
                        <div className="mt-2 flex gap-1">
                          {hasCv && (
                            <span className="text-[9px] bg-primary-fixed text-primary px-1.5 py-0.5 rounded">
                              CV L{node.level_from_cv}
                            </span>
                          )}
                          {hasSelf && (
                            <span className="text-[9px] bg-tertiary-fixed text-tertiary px-1.5 py-0.5 rounded">
                              ประเมินเอง L{node.level_self_reported}
                            </span>
                          )}
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </section>

            <aside className="w-full lg:w-80 bg-surface-bg border-l border-border-low flex flex-col h-[46%] lg:h-full z-20 shadow-[0_-4px_12px_rgba(0,0,0,.05)] lg:shadow-none">
              {!detail && <p className="m-auto text-text-subtle">เลือกทักษะเพื่อดูรายละเอียด</p>}
              {detail && (
                <>
                  <div className="p-gutter border-b border-border-low">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="w-3 h-3 rounded-full bg-primary" />
                      <span className="text-label-sm font-label-sm text-text-subtle uppercase tracking-wider">
                        {detail.category_th}
                      </span>
                    </div>
                    <h2 className="text-headline-md font-headline-md font-semibold text-text-main">
                      {detail.name_th ?? detail.name_en}
                    </h2>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {detail.you?.level_from_cv != null && (
                        <span className="text-xs bg-primary-fixed text-primary px-2 py-1 rounded-full">
                          จาก CV · ระดับ {detail.you.level_from_cv}
                        </span>
                      )}
                      {detail.you?.level_self_reported != null && (
                        <span className="text-xs bg-tertiary-fixed text-tertiary px-2 py-1 rounded-full">
                          ประเมินเอง · ระดับ {detail.you.level_self_reported}
                        </span>
                      )}
                    </div>
                    {detail.unlocks_total > 0 && (
                      <p className="mt-2 text-xs text-text-subtle">
                        ได้ทักษะนี้แล้วเปิดทางไปอีก {detail.unlocks_total} ทักษะ
                      </p>
                    )}
                  </div>
                  <div className="p-gutter flex-1 overflow-y-auto space-y-stack-lg">
                    {detail.description && (
                      <p className="text-sm text-text-subtle">{detail.description}</p>
                    )}
                    <section>
                      <h3 className="font-semibold mb-stack-sm flex items-center gap-2">
                        <Icon className="text-text-subtle">work</Icon>อาชีพที่ใช้ทักษะนี้
                      </h3>
                      <div className="flex flex-wrap gap-2">
                        {detail.supported_careers.map((career) => (
                          <span
                            key={career.target_id}
                            className="px-3 py-1.5 bg-surface-muted border border-border-low rounded-md text-xs text-text-main"
                          >
                            {career.title_th}
                          </span>
                        ))}
                      </div>
                      {detail.supported_careers.length === 0 && (
                        <p className="text-xs text-text-subtle">
                          ยังไม่มีอาชีพในคลังที่ระบุทักษะนี้เป็นข้อกำหนด
                        </p>
                      )}
                    </section>
                    <section>
                      <h3 className="font-semibold mb-stack-sm flex items-center gap-2">
                        <Icon className="text-text-subtle">school</Icon>เรียนจากไหนได้
                      </h3>
                      <div className="space-y-3">
                        {detail.resources.map((resource) => (
                          <a
                            key={resource.id}
                            href={resource.url ?? "#"}
                            target={resource.url ? "_blank" : undefined}
                            rel="noreferrer"
                            className="block p-3 border border-border-low rounded-lg hover:bg-surface-muted"
                          >
                            <div className="flex items-start gap-3">
                              <div className="p-2 bg-surface-container-low rounded-md text-primary">
                                <Icon>menu_book</Icon>
                              </div>
                              <div>
                                <h4 className="text-label-sm font-label-sm text-text-main mb-1">
                                  {resource.title}
                                </h4>
                                <p className="text-[12px] text-text-subtle">
                                  {resource.kind_label}
                                  {resource.est_hours != null && ` · ${resource.est_hours} ชั่วโมง`}
                                  {resource.data_status === "placeholder" && " · ข้อมูลตัวอย่าง"}
                                </p>
                              </div>
                            </div>
                          </a>
                        ))}
                      </div>
                    </section>
                    {/* ⭐ กติกาข้อ 2 — ทักษะจาก CV ต้องชี้กลับไปที่ประโยคจริงได้เสมอ */}
                    {detail.you?.evidence.map((evidence, i) => (
                      <blockquote
                        key={i}
                        className="border-l-2 border-primary pl-3 text-xs text-text-subtle"
                      >
                        “{evidence.span_text}”
                      </blockquote>
                    ))}
                  </div>
                </>
              )}
            </aside>
          </div>
        )}
      </main>
      <MobileWorkspaceNav active="skills" />
    </div>
  );
}
