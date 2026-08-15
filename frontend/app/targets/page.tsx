"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ensureSession, session, type TargetCard, type TargetsResponse } from "@/lib/api";
import { Icon, InlineNotice, MobileWorkspaceNav, WorkspaceSidebar } from "@/components/student-ui";

const careerIcons: Record<string, string> = {
  "SW-DEV": "code_blocks", "DATA-ENG": "analytics", "ROBOT-ENG": "precision_manufacturing",
  "STRUCT-ENG": "architecture", "PROCESS-ENG": "factory", "MFG-ENG": "settings_suggest",
  "POWER-ENG": "bolt", "MECH-DESIGN": "construction",
};

export default function TargetsPage() {
  const router = useRouter();
  const [data, setData] = useState<TargetsResponse | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [picking, setPicking] = useState("");
  const load = useCallback(() => {
    api.targets(session.read()).then(setData).catch((e: unknown) => setError(e instanceof Error ? e.message : "เปิดคลังอาชีพไม่ได้ในตอนนี้"));
  }, []);
  useEffect(() => {
    api.targets(session.read()).then(setData).catch((e: unknown) => setError(e instanceof Error ? e.message : "เปิดคลังอาชีพไม่ได้ในตอนนี้"));
  }, []);

  const targets = useMemo(() => (data?.targets ?? []).filter((t) => `${t.title_th} ${t.title_en} ${t.summary} ${t.top_skills.map((s) => s.name_en).join(" ")}`.toLowerCase().includes(search.trim().toLowerCase())), [data, search]);

  async function choose(target: TargetCard) {
    setPicking(target.id); setError("");
    try {
      const uid = await ensureSession("known");
      await api.setGoal({ user_id: uid, target_id: target.id });
      session.writeTarget(target.id);
      await api.roadmap(uid, target.id);
      router.push("/roadmap");
    } catch (e) { setError(e instanceof Error ? e.message : "ไม่สามารถสร้างเส้นทางพัฒนาอาชีพได้"); }
    finally { setPicking(""); }
  }

  return (
    <div className="font-body-md text-body-md bg-surface-bg flex min-h-screen lg:h-screen lg:overflow-hidden pb-20 lg:pb-0">
      <WorkspaceSidebar active="targets" />
      <main className="flex-1 overflow-y-auto bg-surface-bg relative">
        <div className="max-w-container-max mx-auto px-margin-mobile md:px-gutter py-stack-lg">
          <header className="mb-stack-lg">
            <h1 className="font-display-lg text-[32px] md:text-display-lg font-bold text-on-surface mb-2 tracking-tight">คลังอาชีพ (Career Library)</h1>
            <p className="font-body-lg text-body-lg text-text-subtle max-w-2xl">8 สายอาชีพดาวรุ่งที่คัดสรรมาเพื่อนักศึกษา SIIT โดยเฉพาะ พร้อมเจาะลึกทักษะสำคัญและเส้นทางสู่ความสำเร็จ</p>
            <div className="mt-stack-md relative max-w-xl">
              <Icon className="absolute left-4 top-1/2 -translate-y-1/2 text-text-subtle">search</Icon>
              <input value={search} onChange={(e) => setSearch(e.target.value)} className="w-full pl-12 pr-4 py-3 bg-surface-muted border border-border-low rounded-lg text-on-surface focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary ambient-shadow" placeholder="ค้นหาอาชีพ ทักษะ หรือตำแหน่งงาน" aria-label="ค้นหาอาชีพ" />
            </div>
          </header>

          {error && <div className="mb-stack-md"><InlineNotice tone="error">{error} <button className="underline font-semibold" onClick={() => { setError(""); load(); }}>ลองอีกครั้ง</button></InlineNotice></div>}
          {!data && !error && <div className="py-24 text-center text-text-subtle"><Icon className="text-4xl animate-pulse">route</Icon><p className="mt-3">กำลังเปิดคลังอาชีพ</p></div>}

          <section className="bento-grid">
            {targets.map((target, index) => (
              <article key={target.id} className="bg-surface-muted border border-border-low rounded-xl p-6 flex flex-col hover:ambient-shadow transition-shadow duration-300 relative group overflow-hidden">
                {index === 0 && <div className="absolute top-0 right-0 bg-primary-fixed text-on-primary-fixed-variant text-xs px-3 py-1 rounded-bl-lg font-semibold">ได้รับความสนใจ</div>}
                {target.conditions_at_application[0] && <div className="absolute top-0 right-0 bg-secondary-container text-on-secondary-container text-xs px-3 py-1 rounded-bl-lg font-semibold flex items-center gap-1"><Icon className="text-xs">schedule</Icon>{target.conditions_at_application[0].message}</div>}
                <div className="w-12 h-12 bg-white rounded-lg border border-border-low flex items-center justify-center mb-4 shadow-sm"><Icon className={`text-2xl ${index % 3 === 1 ? "text-tertiary" : index % 3 === 2 ? "text-roadmap-accent" : "text-primary"}`}>{careerIcons[target.id] ?? "work"}</Icon></div>
                <h2 className="font-headline-md text-xl sm:text-headline-md font-semibold text-on-surface mb-1">{target.title_th}</h2>
                <p className="font-label-sm text-label-sm text-text-subtle mb-2">{target.title_en} · {target.sector_label}</p>
                <p className="text-text-subtle mb-4 flex-grow">{target.summary}</p>
                <div className="flex flex-wrap gap-1.5 mb-5">{target.top_skills.slice(0, 3).map((skill) => <span key={skill.skill_id} className="px-2 py-1 rounded bg-surface-container text-[11px] text-on-surface-variant">{skill.name_en_is_placeholder ? skill.name_th : skill.name_en}</span>)}</div>
                <button onClick={() => choose(target)} disabled={picking !== ""} className="w-full py-2.5 bg-white border border-border-low rounded-lg text-primary font-label-sm text-label-sm hover:bg-surface-container-low transition-colors flex justify-center items-center gap-2 group-hover:border-primary disabled:opacity-60">{picking === target.id ? "กำลังวางเส้นทางให้" : "ดูเส้นทางไปอาชีพนี้"}<Icon className="text-sm">arrow_forward</Icon></button>
              </article>
            ))}
            {data && targets.length === 0 && <div className="col-span-full p-12 text-center bg-surface-muted rounded-xl text-text-subtle">ไม่พบอาชีพที่ตรงกับคำค้น “{search}”</div>}
          </section>

          {!!data?.filtered_out.length && <section className="mt-stack-lg">
            <div className="flex items-center gap-2 mb-6"><Icon className="text-error">block</Icon><h2 className="font-headline-lg text-2xl md:text-headline-lg font-bold text-on-surface">อาชีพที่เงื่อนไขยังไม่ผ่าน</h2></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">{data.filtered_out.map((target) => <div key={target.id} className="bg-surface-muted border border-border-low rounded-xl p-6 opacity-75"><h3 className="font-headline-md text-xl font-semibold text-on-surface mb-1">{target.title_th}</h3><div className="mt-4 flex flex-col gap-2">{target.reasons.map((reason, i) => <div key={`${reason.kind}-${i}`} className="flex gap-2 text-sm text-error"><Icon className="text-sm shrink-0">cancel</Icon><p>{reason.message}</p></div>)}</div></div>)}</div>
          </section>}
          {data?.data_note && <div className="mt-stack-lg"><InlineNotice>{data.data_note}</InlineNotice></div>}
        </div>
      </main>
      <MobileWorkspaceNav active="targets" />
    </div>
  );
}
