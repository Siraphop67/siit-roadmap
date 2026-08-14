"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, session, type RoadmapResponse, type RoadmapStep, type StepOption } from "@/lib/api";
import { Icon, InlineNotice, MobileWorkspaceNav, WorkspaceSidebar } from "@/components/student-ui";

const statusStyle = {
  current: { icon: "play_arrow", label: "ขั้นปัจจุบัน", node: "bg-primary text-on-primary", badge: "bg-primary-fixed text-primary", card: "border-primary/50", bar: "bg-primary" },
  in_progress: { icon: "data_object", label: "กำลังพัฒนา", node: "bg-surface-muted border-2 border-primary text-primary", badge: "bg-primary-fixed text-primary", card: "border-primary/50", bar: "bg-primary" },
  locked: { icon: "lock", label: "ยังไม่เปิด", node: "bg-surface-muted border-2 border-border-low text-outline", badge: "bg-surface-container text-text-subtle", card: "opacity-70", bar: "bg-outline" },
  flexible: { icon: "tune", label: "เลือกได้อิสระ", node: "bg-surface-muted border-2 border-secondary text-secondary", badge: "bg-secondary-container text-secondary", card: "border-secondary/50", bar: "bg-secondary" },
} as const;

const resourceIcon: Record<string, string> = { project: "construction", competition: "emoji_events", siit_course: "school", online_course: "workspace_premium", certificate: "verified", activity: "local_activity", internship: "work" };

function OptionCard({ option, locked, onOpen }: { option: StepOption; locked: boolean; onOpen: () => void }) {
  return <button type="button" onClick={onOpen} className={`w-full text-left bg-surface-bg border rounded p-3 transition-colors relative ${option.blocked_reason ? "border-error/30" : "border-border-low hover:border-primary"} ${locked ? "cursor-pointer opacity-80" : "cursor-pointer"}`} title={option.blocked_reason ?? undefined}>
    <div className="flex items-center gap-2 mb-1"><Icon className={`${locked ? "text-text-subtle" : "text-primary"} text-[18px]`}>{resourceIcon[option.kind] ?? "school"}</Icon><span className="font-label-sm text-label-sm text-text-main">{option.kind_label}</span>{option.generated && <span className="text-[10px] bg-tertiary-fixed text-tertiary px-1.5 py-0.5 rounded">ระบบสร้างขึ้น</span>}</div>
    <p className="text-sm text-text-subtle">{option.title}{option.est_hours != null && ` (${option.est_hours} ชม.)`}</p>
    {option.blocked_reason && <p className="mt-2 text-xs text-error flex gap-1"><Icon className="text-sm">lock</Icon>{option.blocked_reason}</p>}
    <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary"><Icon className="text-sm">arrow_forward</Icon>ดูรายละเอียดการเรียน</span>
  </button>;
}

function StepCard({ step, last, onOpenCourse }: { step: RoadmapStep; last: boolean; onOpenCourse: (resourceId: string) => void }) {
  const style = statusStyle[step.status];
  return <div className={`relative ${last ? "" : "mb-stack-lg"}`}>
    {!last && <div className="connector-line" />}
    <div className="flex items-start gap-4 md:gap-6 step-node">
      <div className={`w-12 h-12 rounded-full flex items-center justify-center shrink-0 z-10 mt-1 border-4 border-surface-bg shadow-sm ${style.node}`}><Icon className={step.status === "current" ? "icon-fill" : ""}>{style.icon}</Icon></div>
      <article className={`flex-1 notion-card p-stack-md notion-shadow relative overflow-hidden ${style.card}`}>
        {step.actionable && <div className={`absolute top-0 left-0 w-2 h-full ${style.bar}`} />}
        <div className="flex flex-col sm:flex-row justify-between items-start gap-2 mb-stack-sm pl-1"><h2 className="font-headline-md text-lg md:text-headline-md font-semibold text-text-main">{step.name_th}</h2><div className="flex flex-wrap sm:flex-col sm:items-end gap-1"><span className={`${style.badge} font-label-sm text-label-sm px-2 py-1 rounded flex items-center gap-1`}><Icon className="text-[14px]">{style.icon}</Icon>{style.label}</span>{step.evidence_kind && <span className="text-[11px] text-text-subtle flex items-center gap-1 bg-surface-container px-2 py-0.5 rounded-full"><Icon className="text-[12px]">verified</Icon>{step.evidence_kind === "extracted" ? "หลักฐานอ้างอิงจาก CV" : step.evidence_kind === "self_reported" ? "ผู้ใช้ประเมินด้วยตนเอง" : "CV และการประเมินตนเอง"}</span>}</div></div>
        <p className="text-text-subtle mb-stack-md pl-1">ระดับ {step.current_level} → {step.target_level}{step.unlock_count > 0 && ` · เปิดให้เข้าถึงเพิ่มอีก ${step.unlock_count} ทักษะ`}</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pl-1">{step.options.map((option) => <OptionCard key={option.resource_id} option={option} locked={step.status === "locked"} onOpen={() => onOpenCourse(option.resource_id)} />)}</div>
      </article>
    </div>
  </div>;
}

function QuestMap({ steps }: { steps: RoadmapStep[] }) {
  return <section className="mt-6 rounded-2xl border border-border-low bg-[#0d2543] p-5 md:p-7 overflow-hidden relative">
    <div className="absolute -right-20 -top-24 w-80 h-80 rounded-full border border-white/10" aria-hidden="true" />
    <div className="relative flex items-center justify-between gap-4 mb-6"><div><p className="text-[11px] font-bold tracking-[.16em] text-primary-fixed">แผนผังทักษะ</p><h2 className="mt-1 text-xl md:text-2xl font-bold text-white">เส้นทางที่กำลังเปิดออกทีละก้าว</h2></div><span className="text-xs text-white/60">เลือกรายวิชาในขั้นด้านล่างเพื่อเริ่ม</span></div>
    <div className="relative flex gap-3 min-w-max overflow-x-auto pb-2">{steps.slice(0, 10).map((step, index) => { const current = step.status === "current"; const done = step.status === "in_progress"; return <div key={step.skill_id} className="flex items-center gap-3"><div className="w-32 sm:w-40"><div className={`w-12 h-12 rounded-2xl grid place-items-center border-2 ${current ? "bg-primary border-primary text-white shadow-[0_0_0_6px_rgba(82,145,229,.18)]" : done ? "bg-[#9ce2c3] border-[#9ce2c3] text-[#123c2a]" : step.status === "flexible" ? "bg-[#f5c36d] border-[#f5c36d] text-[#5a3300]" : "bg-white/10 border-white/20 text-white/55"}`}><Icon>{current ? "play_arrow" : done ? "check" : step.status === "flexible" ? "stars" : "lock"}</Icon></div><p className={`mt-3 text-xs font-semibold leading-snug ${current ? "text-white" : "text-white/70"}`}>{step.name_th}</p><p className="mt-1 text-[10px] text-white/45">{current ? "ขั้นถัดไป" : statusStyle[step.status].label}</p></div>{index < Math.min(steps.length, 10) - 1 && <div className={`h-px w-8 sm:w-12 ${current || done ? "bg-primary-fixed" : "bg-white/20"}`} />}</div>; })}</div>
  </section>;
}

export default function RoadmapPage() {
  const router = useRouter();
  const [data, setData] = useState<RoadmapResponse | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { const uid = session.read(); if (!uid) { Promise.resolve().then(() => setError("ยังไม่พบข้อมูลผู้ใช้ กรุณาเลือกอาชีพเป้าหมายก่อน")); return; } api.roadmap(uid, session.readTarget()).then(setData).catch((e: unknown) => setError(e instanceof Error ? e.message : "เปิดเส้นทางอาชีพไม่ได้ในตอนนี้")); }, []);

  return <div className="bg-background text-on-background min-h-screen lg:h-screen lg:overflow-hidden flex pb-20 lg:pb-0">
    <WorkspaceSidebar active="roadmap" variant="graph" />
    <main className="flex-1 h-full overflow-y-auto bg-surface relative">
      <header className="lg:hidden flex justify-between items-center h-16 px-gutter border-b border-border-low bg-surface-bg/90 backdrop-blur-md sticky top-0 z-40"><span className="font-headline-md text-xl font-bold text-primary">SIIT Roadmap</span><button onClick={() => router.push("/targets")}><Icon>add</Icon></button></header>
      <div className="max-w-container-max mx-auto px-margin-mobile md:px-gutter py-stack-lg pb-32">
        {error && <div className="mb-5"><InlineNotice tone="error">{error} <button onClick={() => router.push("/targets")} className="underline font-semibold">เลือกอาชีพเป้าหมาย</button></InlineNotice></div>}
        {!data && !error && <p className="py-24 text-center text-text-subtle">กำลังวางเส้นทางจากข้อมูลของคุณ</p>}
        {data && <>
          <section className="relative overflow-hidden rounded-3xl bg-[#0d2543] text-white p-6 md:p-9 shadow-[0_18px_48px_rgba(12,39,74,.18)]"><div className="absolute -right-16 -top-20 w-72 h-72 rounded-full border border-white/10" aria-hidden="true" /><div className="absolute right-[20%] bottom-[-100px] w-64 h-64 rounded-full bg-primary/25 blur-3xl" aria-hidden="true" /><div className="relative flex flex-col lg:flex-row lg:items-end justify-between gap-6"><div><p className="text-xs font-bold tracking-[.16em] text-primary-fixed">เส้นทางอาชีพของคุณ</p><h1 className="mt-3 font-display-lg text-3xl md:text-5xl font-bold">{data.target.title_en}</h1><p className="mt-3 max-w-2xl text-white/70">{data.target.summary}</p><div className="mt-6 flex flex-wrap gap-3"><span className="rounded-xl bg-white/10 px-3 py-2 text-sm">ผ่านแล้ว <strong>{data.steps_done}</strong> จาก {data.total_steps} ขั้น</span><span className="rounded-xl bg-white/10 px-3 py-2 text-sm">หลักฐานอ้างอิงจาก CV {data.evidence_summary.from_cv} ทักษะ</span></div></div><div className="rounded-2xl bg-white text-[#10213b] p-5 min-w-[280px] shadow-xl"><p className="text-xs font-bold tracking-[.12em] text-primary">ขั้นถัดไป</p><h2 className="mt-2 text-xl font-bold">{data.steps.find((step) => step.status === "current")?.name_th ?? "เลือกขั้นแรกของคุณ"}</h2><p className="mt-2 text-sm text-text-subtle">เริ่มจากขั้นนี้ แล้วขั้นถัดไปจะเปิดตามมาเอง</p><button onClick={() => document.getElementById("quest-list")?.scrollIntoView({ behavior: "smooth" })} className="mt-4 w-full rounded-xl bg-primary text-white py-2.5 font-semibold flex justify-center gap-2">ดูขั้นที่เริ่มได้เลย<Icon>arrow_forward</Icon></button></div></div></section>
          <QuestMap steps={data.steps} />
          <div className="mt-6"><InlineNotice>{data.evidence_summary.note} — จาก CV {data.evidence_summary.from_cv} ทักษะ · ประเมินด้วยตนเอง {data.evidence_summary.self_reported} ทักษะ</InlineNotice></div>
          <section id="quest-list" className="mt-stack-md bg-surface-bg border border-border-low rounded-xl p-4 md:p-stack-lg shadow-sm relative"><div className="flex items-center gap-2 mb-stack-lg text-text-subtle"><Icon className="text-[20px]">map</Icon><span className="font-label-sm text-label-sm tracking-widest uppercase text-outline">ขั้นทั้งหมด · เลือกรายวิชาเพื่อดูว่าจะได้ทักษะอะไร</span></div><div className="relative pl-1 md:pl-8">{data.steps.map((step, index) => <StepCard key={step.skill_id} step={step} last={index === data.steps.length - 1} onOpenCourse={(resourceId) => router.push(`/courses/${encodeURIComponent(resourceId)}`)} />)}</div></section>
        </>}
      </div>
    </main>
    <MobileWorkspaceNav active="roadmap" />
  </div>;
}
