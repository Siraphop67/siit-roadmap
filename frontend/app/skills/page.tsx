"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api, session, type SkillDetail, type SkillGraph, type SkillNode } from "@/lib/api";
import { Icon, InlineNotice, MobileWorkspaceNav, WorkspaceSidebar } from "@/components/student-ui";

const dots = ["#005bb2", "#d4402e", "#8b4c00", "#3274cd", "#585f6a", "#4d8b68", "#9b5ab6"];

export default function SkillsPage() {
  const [graph, setGraph] = useState<SkillGraph | null>(null);
  const [detail, setDetail] = useState<SkillDetail | null>(null);
  const [selected, setSelected] = useState("");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [error, setError] = useState("");
  const uid = session.read();
  const load = useCallback(() => { api.skills(uid).then((data) => { setGraph(data); if (data.nodes[0]) setSelected(data.nodes[0].id); }).catch((e: unknown) => setError(e instanceof Error ? e.message : "โหลดกราฟทักษะไม่สำเร็จ")); }, [uid]);
  useEffect(() => { api.skills(uid).then((data) => { setGraph(data); if (data.nodes[0]) setSelected(data.nodes[0].id); }).catch((e: unknown) => setError(e instanceof Error ? e.message : "โหลดกราฟทักษะไม่สำเร็จ")); }, [uid]);
  useEffect(() => { if (!selected) return; api.skill(selected, uid).then(setDetail).catch(() => setDetail(null)); }, [selected, uid]);

  const filtered = useMemo(() => (graph?.nodes ?? []).filter((node) => (category === "all" || node.category === category) && `${node.name_th} ${node.name_en}`.toLowerCase().includes(search.toLowerCase())), [graph, category, search]);
  const positions = useMemo(() => {
    const byCategory = new Map<string, SkillNode[]>(); filtered.forEach((node) => byCategory.set(node.category, [...(byCategory.get(node.category) ?? []), node]));
    const map = new Map<string, { x: number; y: number }>(); [...byCategory.values()].forEach((nodes, col) => nodes.forEach((node, row) => map.set(node.id, { x: 150 + col * 245, y: 95 + row * 92 })));
    return map;
  }, [filtered]);
  const canvasWidth = Math.max(1000, (new Set(filtered.map((n) => n.category)).size + 1) * 245);
  const canvasHeight = Math.max(650, Math.max(0, ...[...positions.values()].map((p) => p.y)) + 120);

  return <div className="flex h-screen w-full bg-surface-bg overflow-hidden pb-16 lg:pb-0">
    <WorkspaceSidebar active="skills" variant="graph" />
    <main className="flex-1 flex flex-col h-full relative min-w-0">
      <header className="px-margin-mobile md:px-gutter py-stack-md border-b border-border-low bg-surface-bg/90 backdrop-blur-sm z-10 flex flex-col sm:flex-row justify-between sm:items-center gap-3"><div><h1 className="text-headline-md font-headline-md font-semibold text-text-main">Skill Graph ของคุณ</h1><p className="text-sm sm:text-body-md text-text-subtle">สำรวจความเชื่อมโยงของทักษะทั้งหมด {graph?.counts.skills ?? 73} ทักษะ และ {graph?.counts.edges ?? 105} ความสัมพันธ์</p></div><div className="flex gap-2"><div className="relative"><Icon className="absolute left-2 top-1/2 -translate-y-1/2 text-base text-text-subtle">search</Icon><input value={search} onChange={(e) => setSearch(e.target.value)} className="w-40 pl-8 pr-2 py-2 text-sm bg-surface-muted border border-border-low rounded-lg" placeholder="ค้นหาทักษะ" /></div><select value={category} onChange={(e) => setCategory(e.target.value)} className="max-w-40 px-2 py-2 text-sm bg-surface-muted border border-border-low rounded-lg"><option value="all">ทุกหมวด</option>{graph?.categories.map((cat) => <option key={cat.id} value={cat.id}>{cat.label_th} ({cat.count})</option>)}</select></div></header>
          {error && <div className="p-4"><InlineNotice tone="error">{error} <button className="underline" onClick={() => { setError(""); load(); }}>ลองใหม่</button></InlineNotice></div>}
      {!graph && !error && <p className="m-auto text-text-subtle">กำลังสร้างกราฟ 73 ทักษะ…</p>}
      {graph && <div className="flex-1 flex flex-col lg:flex-row relative overflow-hidden">
        <section className="flex-1 graph-bg relative overflow-auto cursor-grab" aria-label="กราฟความสัมพันธ์ของทักษะ">
          <div className="relative" style={{ width: canvasWidth, height: canvasHeight }}>
            <svg className="absolute inset-0 w-full h-full pointer-events-none" aria-hidden="true">{graph.edges.map((edge, index) => { const from = positions.get(edge.from), to = positions.get(edge.to); if (!from || !to) return null; return <line key={`${edge.from}-${edge.to}-${index}`} stroke={edge.reviewed_by_human ? "#c2c6d4" : "#e9e9e7"} strokeWidth="1.5" x1={from.x} y1={from.y} x2={to.x} y2={to.y} />; })}</svg>
            {filtered.map((node) => { const pos = positions.get(node.id)!; const catIndex = graph.categories.findIndex((c) => c.id === node.category); const active = selected === node.id; const hasCv = node.level_from_cv != null; const hasSelf = node.level_self_reported != null; return <button key={node.id} onClick={() => setSelected(node.id)} className={`absolute -translate-x-1/2 -translate-y-1/2 bg-surface-bg rounded-lg p-3 text-left shadow-[0_4px_12px_rgba(0,0,0,.05)] transition-colors w-48 ${active ? "border-2 border-primary" : "border border-border-low hover:border-primary"}`} style={{ left: pos.x, top: pos.y }}><div className="flex items-start gap-2"><span className="w-3 h-3 rounded-full mt-1 shrink-0" style={{ background: dots[Math.max(0, catIndex) % dots.length] }} /><span className={`text-xs leading-snug ${active ? "text-primary font-bold" : "text-text-main font-semibold"}`}>{node.name_th ?? node.name_en}</span></div>{(hasCv || hasSelf) && <div className="mt-2 flex gap-1">{hasCv && <span className="text-[9px] bg-primary-fixed text-primary px-1.5 py-0.5 rounded">CV L{node.level_from_cv}</span>}{hasSelf && <span className="text-[9px] bg-tertiary-fixed text-tertiary px-1.5 py-0.5 rounded">ประเมินเอง L{node.level_self_reported}</span>}</div>}</button>; })}
          </div>
        </section>
        <aside className="w-full lg:w-80 bg-surface-bg border-l border-border-low flex flex-col h-[46%] lg:h-full z-20 shadow-[0_-4px_12px_rgba(0,0,0,.05)] lg:shadow-none">
          {!detail && <p className="m-auto text-text-subtle">เลือกทักษะเพื่อดูรายละเอียด</p>}
          {detail && <><div className="p-gutter border-b border-border-low"><div className="flex items-center gap-2 mb-2"><span className="w-3 h-3 rounded-full bg-primary"/><span className="text-label-sm font-label-sm text-text-subtle uppercase tracking-wider">{detail.category_th}</span></div><h2 className="text-headline-md font-headline-md font-semibold text-text-main">{detail.name_th ?? detail.name_en}</h2><div className="mt-2 flex flex-wrap gap-1">{detail.you?.level_from_cv != null && <span className="text-xs bg-primary-fixed text-primary px-2 py-1 rounded-full">จาก CV · ระดับ {detail.you.level_from_cv}</span>}{detail.you?.level_self_reported != null && <span className="text-xs bg-tertiary-fixed text-tertiary px-2 py-1 rounded-full">ประเมินเอง · ระดับ {detail.you.level_self_reported}</span>}</div></div>
            <div className="p-gutter flex-1 overflow-y-auto space-y-stack-lg">{detail.description && <p className="text-sm text-text-subtle">{detail.description}</p>}<section><h3 className="font-semibold mb-stack-sm flex items-center gap-2"><Icon className="text-text-subtle">work</Icon>Supported Careers</h3><div className="flex flex-wrap gap-2">{detail.supported_careers.map((career) => <span key={career.target_id} className="px-3 py-1.5 bg-surface-muted border border-border-low rounded-md text-xs text-text-main">{career.title_en}</span>)}</div></section><section><h3 className="font-semibold mb-stack-sm flex items-center gap-2"><Icon className="text-text-subtle">school</Icon>Recommended Resources</h3><div className="space-y-3">{detail.resources.map((resource) => <a key={resource.id} href={resource.url ?? "#"} target={resource.url ? "_blank" : undefined} rel="noreferrer" className="block p-3 border border-border-low rounded-lg hover:bg-surface-muted"><div className="flex items-start gap-3"><div className="p-2 bg-surface-container-low rounded-md text-primary"><Icon>menu_book</Icon></div><div><h4 className="text-label-sm font-label-sm text-text-main mb-1">{resource.title}</h4><p className="text-[12px] text-text-subtle">{resource.kind_label}{resource.est_hours != null && ` · ${resource.est_hours} ชั่วโมง`}{resource.data_status === "placeholder" && " · ข้อมูลตัวอย่าง"}</p></div></div></a>)}</div></section>{detail.you?.evidence.map((evidence, i) => <blockquote key={i} className="border-l-2 border-primary pl-3 text-xs text-text-subtle">“{evidence.span_text}”</blockquote>)}</div>
          </>}
        </aside>
      </div>}
    </main>
    <MobileWorkspaceNav active="skills" />
  </div>;
}
