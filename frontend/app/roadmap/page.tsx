"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  api,
  session,
  type CharacterBuild,
  type QuestList,
  type RoadmapResponse,
  type RoadmapStep,
  type StepOption,
} from "@/lib/api";
import { Icon, InlineNotice, MobileWorkspaceNav, WorkspaceSidebar } from "@/components/student-ui";

const statusStyle = {
  current: { icon: "play_arrow", label: "เริ่มได้เลย", dot: "bg-[#78b7ff] border-[#a8d5ff] text-[#062142]", ring: "ring-[#78b7ff]/30", card: "border-[#78b7ff]/60 bg-[#112d51]" },
  in_progress: { icon: "trending_up", label: "กำลังพัฒนา", dot: "bg-[#8bdab2] border-[#d3f7e3] text-[#0d3c27]", ring: "ring-[#8bdab2]/25", card: "border-[#8bdab2]/50 bg-[#102d32]" },
  flexible: { icon: "auto_awesome", label: "เลือกทำได้", dot: "bg-[#f4bb61] border-[#ffe3a8] text-[#4d2e00]", ring: "ring-[#f4bb61]/25", card: "border-[#f4bb61]/50 bg-[#36260d]" },
  locked: { icon: "lock", label: "ยังไม่เปิด", dot: "bg-[#223a57] border-[#5b6d84] text-[#9fb1c8]", ring: "ring-transparent", card: "border-white/10 bg-[#0b1c30]" },
} as const;

const resourceIcon: Record<string, string> = {
  project: "construction", competition: "emoji_events", siit_course: "school",
  online_course: "workspace_premium", certificate: "verified", activity: "local_activity", internship: "work",
};

const builds: Array<{ value: CharacterBuild["archetype"]; playstyle: CharacterBuild["playstyle"]; title: string; subtitle: string; icon: string; color: string }> = [
  { value: "builder", playstyle: "create", title: "Builder", subtitle: "ชอบสร้างสิ่งที่จับต้องได้", icon: "construction", color: "border-[#78b7ff] bg-[#78b7ff]/15" },
  { value: "analyst", playstyle: "solve", title: "Analyst", subtitle: "ชอบแกะโจทย์ให้เห็นคำตอบ", icon: "analytics", color: "border-[#b9a5ff] bg-[#b9a5ff]/15" },
  { value: "maker", playstyle: "explore", title: "Maker", subtitle: "ชอบทดลองและลงมือไว", icon: "precision_manufacturing", color: "border-[#8bdab2] bg-[#8bdab2]/15" },
  { value: "optimizer", playstyle: "improve", title: "Optimizer", subtitle: "ชอบทำของเดิมให้ดีขึ้น", icon: "tune", color: "border-[#f4bb61] bg-[#f4bb61]/15" },
];

function progressPercent(done: number, total: number) {
  return total ? Math.round((done / total) * 100) : 0;
}

function SkillTree({ steps, activeId, onSelect }: { steps: RoadmapStep[]; activeId: string | null; onSelect: (id: string) => void }) {
  return (
    <section className="relative overflow-hidden rounded-[28px] border border-[#244766] bg-[#071a2e] p-5 md:p-8 shadow-[0_24px_64px_rgba(3,15,30,.34)]">
      <div className="pointer-events-none absolute inset-0 opacity-35" style={{ backgroundImage: "linear-gradient(rgba(122,183,255,.13) 1px, transparent 1px), linear-gradient(90deg, rgba(122,183,255,.13) 1px, transparent 1px)", backgroundSize: "38px 38px" }} />
      <div className="pointer-events-none absolute -left-20 bottom-[-100px] h-72 w-72 rounded-full bg-[#1778ca]/20 blur-3xl" />
      <div className="pointer-events-none absolute right-0 top-[-70px] h-56 w-56 rounded-full border border-[#f4bb61]/25" />
      <div className="relative flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="text-[11px] font-bold tracking-[.18em] text-[#8fc4ff]">แผนผังทักษะของคุณ</p><h2 className="mt-1 text-2xl font-bold text-white">เลือกทักษะ แล้วเริ่มภารกิจได้เลย</h2></div>
        <div className="flex flex-wrap gap-3 text-[11px] text-white/65"><span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-[#78b7ff]" />เริ่มได้ตอนนี้</span><span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-[#8bdab2]" />กำลังพัฒนา</span><span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-[#f4bb61]" />ทำเมื่อไหร่ก็ได้</span></div>
      </div>
      <div className="relative mt-8 grid grid-cols-2 gap-x-3 gap-y-6 sm:grid-cols-3 lg:grid-cols-4">
        {steps.map((step, index) => {
          const style = statusStyle[step.status];
          const active = activeId === step.skill_id;
          return <button key={step.skill_id} type="button" onClick={() => onSelect(step.skill_id)} className={`group relative min-h-36 rounded-2xl border p-3 text-left transition duration-200 hover:-translate-y-1 hover:shadow-2xl ${style.card} ${active ? `ring-4 ${style.ring} -translate-y-1` : ""}`}>
            {index > 0 && <span className="pointer-events-none absolute -left-3 top-1/2 hidden h-px w-3 bg-white/20 lg:block" />}
            <span className={`grid h-10 w-10 place-items-center rounded-xl border-2 shadow-lg ${style.dot}`}><Icon className={step.status === "current" ? "icon-fill" : ""}>{style.icon}</Icon></span>
            <p className="mt-4 text-[10px] font-bold tracking-[.12em] text-white/50">{String(step.order_no).padStart(2, "0")} · {style.label}</p>
            <p className="mt-1 line-clamp-2 text-sm font-bold leading-snug text-white">{step.name_th}</p>
            <p className="mt-2 text-[11px] text-white/55">Lv. {step.current_level} → {step.target_level}</p>
            {step.unlock_count > 0 && <span className="absolute right-3 top-3 text-[10px] text-[#f7d18a]">+{step.unlock_count} ✦</span>}
          </button>;
        })}
      </div>
    </section>
  );
}

function ResourceQuest({ option, step, questStatus, busy, onStart, onComplete, onOpen }: { option: StepOption; step: RoadmapStep; questStatus?: "started" | "completed"; busy: boolean; onStart: () => void; onComplete: () => void; onOpen: () => void }) {
  const unavailable = step.status === "locked" || Boolean(option.blocked_reason);
  const done = questStatus === "completed";
  return <article className={`rounded-2xl border p-4 ${done ? "border-[#8bdab2]/50 bg-[#dff7eb]" : unavailable ? "border-white/10 bg-white/[.035] opacity-65" : "border-white/10 bg-white/[.07]"}`}>
    <div className="flex items-start justify-between gap-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-white/10 text-[#9fcaff]"><Icon>{resourceIcon[option.kind] ?? "school"}</Icon></span><span className="rounded-full bg-white/10 px-2 py-1 text-[10px] font-bold text-white/70">{option.kind_label}</span></div>
    <h4 className="mt-4 text-sm font-bold leading-snug text-white">{option.title}</h4>
    <p className="mt-2 text-xs text-white/60">{option.est_hours ?? "—"} ชม. · {option.cost_baht ? `${option.cost_baht.toLocaleString()} บาท` : "ไม่มีค่าใช้จ่าย"}</p>
    {option.blocked_reason && <p className="mt-3 text-xs text-[#ffd2cc]">🔒 {option.blocked_reason}</p>}
    {done && <p className="mt-3 text-xs font-semibold text-[#1e6a47]">✓ ทำภารกิจเสร็จแล้ว เพิ่มผลงานเพื่อยืนยันทักษะต่อได้</p>}
    <div className="mt-4 flex gap-2"><button type="button" onClick={onOpen} className="rounded-lg border border-white/20 px-3 py-2 text-xs font-semibold text-white hover:bg-white/10">รายละเอียด</button>{!unavailable && !done && questStatus !== "started" && <button type="button" disabled={busy} onClick={onStart} className="rounded-lg bg-[#78b7ff] px-3 py-2 text-xs font-bold text-[#062142] disabled:opacity-60">เริ่มภารกิจ</button>}{!unavailable && !done && questStatus === "started" && <button type="button" disabled={busy} onClick={onComplete} className="rounded-lg bg-[#8bdab2] px-3 py-2 text-xs font-bold text-[#0a3221] disabled:opacity-60">ทำเสร็จแล้ว</button>}</div>
  </article>;
}

export default function RoadmapPage() {
  const router = useRouter();
  const [data, setData] = useState<RoadmapResponse | null>(null);
  const [quests, setQuests] = useState<QuestList | null>(null);
  const [build, setBuild] = useState<CharacterBuild | null>(null);
  const [activeSkillId, setActiveSkillId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busyResource, setBusyResource] = useState("");
  const [savingBuild, setSavingBuild] = useState(false);
  const [notice, setNotice] = useState("");
  const [userId, setUserId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    Promise.resolve().then(() => {
      setUserId(session.read());
      setHydrated(true);
    });
  }, []);

  useEffect(() => {
    if (!userId) return;
    let alive = true;
    Promise.all([api.roadmap(userId, session.readTarget()), api.quests(userId), api.characterBuild(userId)])
      .then(([roadmap, questData, character]) => {
        if (!alive) return;
        setData(roadmap); setQuests(questData); setBuild(character.build);
        setActiveSkillId(roadmap.steps.find((step) => step.status === "current")?.skill_id ?? roadmap.steps[0]?.skill_id ?? null);
      })
      .catch((e: unknown) => alive && setError(e instanceof Error ? e.message : "โหลด Roadmap ไม่สำเร็จ"));
    return () => { alive = false; };
  }, [userId]);

  const activeStep = useMemo(() => data?.steps.find((step) => step.skill_id === activeSkillId) ?? data?.steps[0] ?? null, [data, activeSkillId]);
  const questByResource = useMemo(() => new Map((quests?.quests ?? []).map((quest) => [quest.resource_id, quest.status])), [quests]);
  const questDone = quests?.counts.completed ?? 0;
  const questStarted = quests?.counts.started ?? 0;

  async function refreshQuests() {
    if (!userId) return;
    setQuests(await api.quests(userId));
  }

  async function startQuest(resourceId: string) {
    if (!userId) return;
    setBusyResource(resourceId); setNotice("");
    try { await api.startQuest(resourceId, userId); await refreshQuests(); setNotice("Quest เริ่มแล้ว! บันทึกความคืบหน้าของคุณไว้ให้แล้ว"); }
    catch (e) { setError(e instanceof Error ? e.message : "เริ่ม Quest ไม่สำเร็จ"); }
    finally { setBusyResource(""); }
  }

  async function completeQuest(resourceId: string) {
    if (!userId) return;
    setBusyResource(resourceId); setNotice("");
    try { const result = await api.completeQuest(resourceId, userId); await refreshQuests(); setNotice(result.note); }
    catch (e) { setError(e instanceof Error ? e.message : "บันทึก Quest ไม่สำเร็จ"); }
    finally { setBusyResource(""); }
  }

  async function chooseBuild(choice: (typeof builds)[number]) {
    if (!userId) return;
    setSavingBuild(true); setNotice("");
    try {
      const saved = await api.saveCharacterBuild({ user_id: userId, archetype: choice.value, playstyle: choice.playstyle, intensity: "steady", completed_missions: 4 });
      setBuild(saved); setNotice(`เลือก ${choice.title} build แล้ว — เปลี่ยนได้ตลอดเวลา`);
    } catch (e) { setError(e instanceof Error ? e.message : "บันทึก Character Build ไม่สำเร็จ"); }
    finally { setSavingBuild(false); }
  }

  return <div className="min-h-screen bg-[#061323] text-white lg:flex">
    <WorkspaceSidebar active="roadmap" variant="graph" />
    <main className="min-w-0 flex-1 pb-24 lg:pb-0">
      <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-white/10 bg-[#061323]/90 px-5 backdrop-blur lg:hidden"><span className="text-lg font-bold">SIIT <span className="text-[#78b7ff]">QUEST</span></span><button onClick={() => router.push("/targets")} className="text-sm text-[#9fcaff]">เปลี่ยนเป้าหมาย</button></header>
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 md:py-9 lg:px-10">
        {hydrated && !userId && <div className="mb-5"><InlineNotice tone="error">ยังไม่มีข้อมูลผู้ใช้ กรุณาเลือกอาชีพเป้าหมายก่อน <button onClick={() => router.push("/targets")} className="underline font-semibold">เลือกอาชีพ</button></InlineNotice></div>}
        {error && <div className="mb-5"><InlineNotice tone="error">{error} <button onClick={() => router.push("/targets")} className="underline font-semibold">เลือกอาชีพ</button></InlineNotice></div>}
        {!data && !error && (!hydrated || userId) && <div className="grid min-h-[65vh] place-items-center text-center text-white/65"><div><Icon className="text-5xl animate-pulse text-[#78b7ff]">hub</Icon><p className="mt-4">กำลังสร้าง Skill Tree ของคุณ…</p></div></div>}
        {data && <>
          <section className="relative overflow-hidden rounded-[30px] border border-[#254c70] bg-gradient-to-br from-[#10345b] via-[#092540] to-[#061a31] p-6 shadow-[0_30px_80px_rgba(0,0,0,.28)] md:p-10">
            <div className="pointer-events-none absolute -right-14 -top-20 h-80 w-80 rounded-full border border-[#89c6ff]/20" /><div className="pointer-events-none absolute bottom-[-135px] left-[38%] h-64 w-64 rounded-full bg-[#e89437]/20 blur-3xl" />
            <div className="relative grid gap-8 xl:grid-cols-[1.25fr_.75fr] xl:items-end">
              <div><p className="text-xs font-bold tracking-[.2em] text-[#9fcaff]">เส้นทางอาชีพ · ระดับ 01</p><h1 className="mt-3 text-3xl font-bold leading-tight sm:text-4xl md:text-5xl">{data.target.title_th}<span className="mt-2 block text-lg font-medium text-white/55 md:text-xl">{data.target.title_en}</span></h1><p className="mt-5 max-w-2xl leading-relaxed text-white/72">{data.target.summary} ทุกจุดคือทักษะที่พาไปสู่งานจริงได้ เริ่มจากจุดที่เปิดอยู่ แล้วค่อยปลดล็อกเส้นต่อไป</p><div className="mt-6 flex flex-wrap gap-3"><span className="rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-sm"><strong className="text-[#9fcaff]">{data.steps_done}/{data.total_steps}</strong> ทักษะที่ยืนยันแล้ว</span><span className="rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-sm"><strong className="text-[#8bdab2]">{questDone}</strong> ภารกิจที่ทำเสร็จ</span><span className="rounded-xl border border-white/10 bg-white/10 px-3 py-2 text-sm">ความคืบหน้า <strong>{data.coverage}%</strong></span></div></div>
              <div className="rounded-2xl border border-white/10 bg-[#041526]/55 p-5 backdrop-blur"><div className="flex items-center justify-between text-xs font-bold tracking-[.14em] text-[#9fcaff]"><span>ความคืบหน้าภารกิจ</span><span>{questDone}/{Math.max(data.total_steps, 1)}</span></div><div className="mt-3 h-3 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-gradient-to-r from-[#78b7ff] to-[#8bdab2] transition-all" style={{ width: `${progressPercent(questDone, data.total_steps)}%` }} /></div><p className="mt-4 text-sm leading-relaxed text-white/65">เริ่มแล้ว {questStarted} ภารกิจ · ทำเสร็จแล้ว {questDone} ภารกิจ <span className="text-white/40">— ทำเสร็จคือความคืบหน้า ยังไม่ใช่หลักฐานยืนยันทักษะ</span></p><button onClick={() => document.getElementById("active-quest")?.scrollIntoView({ behavior: "smooth" })} className="mt-5 inline-flex items-center gap-2 rounded-xl bg-[#78b7ff] px-4 py-2.5 text-sm font-bold text-[#062142]">ดูภารกิจที่เลือก <Icon className="text-base">arrow_downward</Icon></button></div>
            </div>
          </section>

          <section className="mt-6 rounded-2xl border border-[#25415c] bg-[#0b2036] p-5 md:p-6"><div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"><div><p className="text-[11px] font-bold tracking-[.16em] text-[#f7d18a]">รูปแบบการเรียนของคุณ</p><h2 className="mt-1 text-xl font-bold">{build ? `${builds.find((item) => item.value === build.archetype)?.title ?? build.archetype} · ${build.playstyle} style` : "เลือกสไตล์การเติบโตของคุณ"}</h2><p className="mt-1 text-sm text-white/60">เป็นรูปแบบที่คุณเลือกเพื่อปรับประสบการณ์บนเว็บ ไม่ใช่การประเมินทักษะ</p></div><div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{builds.map((choice) => <button key={choice.value} type="button" disabled={savingBuild} onClick={() => chooseBuild(choice)} className={`rounded-xl border px-3 py-2 text-left transition hover:-translate-y-0.5 disabled:opacity-60 ${build?.archetype === choice.value ? choice.color : "border-white/10 bg-white/5 hover:border-white/30"}`}><Icon className="text-lg text-[#9fcaff]">{choice.icon}</Icon><span className="mt-1 block text-xs font-bold">{choice.title}</span><span className="block text-[10px] text-white/50">{choice.subtitle}</span></button>)}</div></div></section>

          {notice && <div className="mt-5"><InlineNotice>{notice}</InlineNotice></div>}
          <div className="mt-6"><SkillTree steps={data.steps} activeId={activeSkillId} onSelect={setActiveSkillId} /></div>

          {activeStep && <section id="active-quest" className="mt-6 scroll-mt-24 rounded-[28px] border border-[#2a5277] bg-[#0c2743] p-5 md:p-8"><div className="flex flex-col gap-4 border-b border-white/10 pb-6 md:flex-row md:items-start md:justify-between"><div><p className="text-[11px] font-bold tracking-[.17em] text-[#9fcaff]">ภารกิจที่เลือก · {String(activeStep.order_no).padStart(2, "0")}</p><h2 className="mt-2 text-2xl font-bold md:text-3xl">{activeStep.name_th}</h2><p className="mt-3 text-white/65">จากระดับ {activeStep.current_level} ไปถึงระดับ {activeStep.target_level}{activeStep.unlock_count > 0 ? ` · ปลดล็อกได้อีก ${activeStep.unlock_count} ทักษะ` : ""}</p></div><span className={`w-fit rounded-full px-3 py-2 text-xs font-bold ${activeStep.status === "locked" ? "bg-white/10 text-white/55" : activeStep.status === "flexible" ? "bg-[#f4bb61]/20 text-[#f7d18a]" : "bg-[#78b7ff]/20 text-[#9fcaff]"}`}>{statusStyle[activeStep.status].label}</span></div>
            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">{activeStep.options.map((option) => <ResourceQuest key={option.resource_id} option={option} step={activeStep} questStatus={questByResource.get(option.resource_id)} busy={busyResource === option.resource_id} onStart={() => startQuest(option.resource_id)} onComplete={() => completeQuest(option.resource_id)} onOpen={() => router.push(`/courses/${encodeURIComponent(option.resource_id)}`)} />)}</div>
            {activeStep.options.length === 0 && <p className="text-sm text-white/60">ยังไม่มีตัวเลือกการเรียนสำหรับทักษะนี้</p>}
          </section>}

          <section className="mt-6 grid gap-5 lg:grid-cols-[1.1fr_.9fr]"><div className="rounded-2xl border border-white/10 bg-[#0b2036] p-5"><p className="text-[11px] font-bold tracking-[.16em] text-[#9fcaff]">โอกาสในการทำงาน</p><h2 className="mt-2 text-xl font-bold">เรียนจบสายนี้ ไปทำงานอะไรได้บ้าง?</h2><p className="mt-3 leading-relaxed text-white/65">ทุกภารกิจที่คุณเลือกคือหลักฐานว่าคุณได้ลงมือทำจริง และต่อยอดไปยังบทบาท <strong className="text-white">{data.target.title_th}</strong> ได้ พร้อมทักษะที่ทีมวิศวกรรมและไอทีใช้จริง เช่น การแก้ปัญหา การสื่อสารงาน และการสร้างสิ่งที่ตรวจสอบได้</p><p className="mt-4 text-sm text-[#8bdab2]">เริ่มทีละจุดก็พอ ความต่อเนื่องสำคัญกว่าการเก่งทุกอย่างตั้งแต่วันแรก</p></div><div className="rounded-2xl border border-white/10 bg-[#0b2036] p-5"><p className="text-[11px] font-bold tracking-[.16em] text-[#f7d18a]">ความสำเร็จที่ได้</p><div className="mt-4 flex flex-wrap gap-2">{quests?.badges.length ? quests.badges.map((badge) => <span key={badge.id} title={badge.description} className="inline-flex items-center gap-2 rounded-xl border border-[#f4bb61]/30 bg-[#f4bb61]/10 px-3 py-2 text-sm text-[#ffe1a3]"><Icon className="text-base">workspace_premium</Icon>{badge.label}</span>) : <p className="text-sm text-white/55">เริ่มภารกิจแรกเพื่อรับป้ายแรกของคุณ ✦</p>}</div><p className="mt-4 text-xs leading-relaxed text-white/45">ป้ายบอกความคืบหน้าที่คุณลงมือทำ ไม่ใช่ใบรับรองความสามารถ</p></div></section>
          <div className="mt-6"><InlineNotice>{data.evidence_summary.note} — CV {data.evidence_summary.from_cv} ทักษะ · ประเมินเอง {data.evidence_summary.self_reported} ทักษะ</InlineNotice></div>
        </>}
      </div>
    </main>
    <MobileWorkspaceNav active="roadmap" />
  </div>;
}
