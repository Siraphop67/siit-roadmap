"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, session, type RoadmapResponse, type RoadmapStep, type StepOption } from "@/lib/api";
import { Icon, InlineNotice, MobileWorkspaceNav, WorkspaceSidebar } from "@/components/student-ui";

const statusStyle = {
  current: { icon: "play_arrow", label: "Current", node: "bg-primary text-on-primary", badge: "bg-primary-fixed text-primary", card: "border-primary/50", bar: "bg-primary" },
  in_progress: { icon: "data_object", label: "In Progress", node: "bg-surface-muted border-2 border-primary text-primary", badge: "bg-primary-fixed text-primary", card: "border-primary/50", bar: "bg-primary" },
  locked: { icon: "lock", label: "Locked", node: "bg-surface-muted border-2 border-border-low text-outline", badge: "bg-surface-container text-text-subtle", card: "opacity-70", bar: "bg-outline" },
  flexible: { icon: "tune", label: "Flexible", node: "bg-surface-muted border-2 border-secondary text-secondary", badge: "bg-secondary-container text-secondary", card: "border-secondary/50", bar: "bg-secondary" },
} as const;

const resourceIcon: Record<string, string> = { project: "construction", competition: "emoji_events", siit_course: "school", online_course: "workspace_premium", certificate: "verified", activity: "local_activity", internship: "work" };

function OptionCard({ option, locked }: { option: StepOption; locked: boolean }) {
  return <div className={`bg-surface-bg border rounded p-3 transition-colors relative ${option.blocked_reason ? "border-error/30" : "border-border-low hover:border-primary"} ${locked ? "cursor-not-allowed" : "cursor-pointer"}`} title={option.blocked_reason ?? undefined}>
    <div className="flex items-center gap-2 mb-1"><Icon className={`${locked ? "text-text-subtle" : "text-primary"} text-[18px]`}>{resourceIcon[option.kind] ?? "school"}</Icon><span className="font-label-sm text-label-sm text-text-main">{option.kind_label}</span>{option.generated && <span className="text-[10px] bg-tertiary-fixed text-tertiary px-1.5 py-0.5 rounded">ระบบสร้าง</span>}</div>
    <p className="text-sm text-text-subtle">{option.title}{option.est_hours != null && ` (${option.est_hours} ชม.)`}</p>
    {option.blocked_reason && <p className="mt-2 text-xs text-error flex gap-1"><Icon className="text-sm">lock</Icon>{option.blocked_reason}</p>}
  </div>;
}

function StepCard({ step, last }: { step: RoadmapStep; last: boolean }) {
  const style = statusStyle[step.status];
  return <div className={`relative ${last ? "" : "mb-stack-lg"}`}>
    {!last && <div className="connector-line" />}
    <div className="flex items-start gap-4 md:gap-6 step-node">
      <div className={`w-12 h-12 rounded-full flex items-center justify-center shrink-0 z-10 mt-1 border-4 border-surface-bg shadow-sm ${style.node}`}><Icon className={step.status === "current" ? "icon-fill" : ""}>{style.icon}</Icon></div>
      <article className={`flex-1 notion-card p-stack-md notion-shadow relative overflow-hidden ${style.card}`}>
        {step.actionable && <div className={`absolute top-0 left-0 w-2 h-full ${style.bar}`} />}
        <div className="flex flex-col sm:flex-row justify-between items-start gap-2 mb-stack-sm pl-1"><h2 className="font-headline-md text-lg md:text-headline-md font-semibold text-text-main">{step.name_th}</h2><div className="flex flex-wrap sm:flex-col sm:items-end gap-1"><span className={`${style.badge} font-label-sm text-label-sm px-2 py-1 rounded flex items-center gap-1`}><Icon className="text-[14px]">{style.icon}</Icon>{style.label}</span>{step.evidence_kind && <span className="text-[11px] text-text-subtle flex items-center gap-1 bg-surface-container px-2 py-0.5 rounded-full"><Icon className="text-[12px]">verified</Icon>{step.evidence_kind === "extracted" ? "หลักฐานจาก CV" : step.evidence_kind === "self_reported" ? "ผู้ใช้ประเมินเอง" : "CV + ประเมินเอง"}</span>}</div></div>
        <p className="text-text-subtle mb-stack-md pl-1">ระดับ {step.current_level}→{step.target_level}{step.unlock_count > 0 && ` · ปลดล็อกอีก ${step.unlock_count} ทักษะ`}</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pl-1">{step.options.map((option) => <OptionCard key={option.resource_id} option={option} locked={step.status === "locked"} />)}</div>
      </article>
    </div>
  </div>;
}

export default function RoadmapPage() {
  const router = useRouter();
  const [data, setData] = useState<RoadmapResponse | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { const uid = session.read(); if (!uid) { Promise.resolve().then(() => setError("ยังไม่มีข้อมูลผู้ใช้ กรุณาเลือกอาชีพเป้าหมายก่อน")); return; } api.roadmap(uid, session.readTarget()).then(setData).catch((e: unknown) => setError(e instanceof Error ? e.message : "โหลด Roadmap ไม่สำเร็จ")); }, []);

  return <div className="bg-background text-on-background min-h-screen lg:h-screen lg:overflow-hidden flex pb-20 lg:pb-0">
    <WorkspaceSidebar active="roadmap" variant="graph" />
    <main className="flex-1 h-full overflow-y-auto bg-surface relative">
      <header className="lg:hidden flex justify-between items-center h-16 px-gutter border-b border-border-low bg-surface-bg/90 backdrop-blur-md sticky top-0 z-40"><span className="font-headline-md text-xl font-bold text-primary">SIIT Roadmap</span><button onClick={() => router.push("/targets")}><Icon>add</Icon></button></header>
      <div className="max-w-container-max mx-auto px-margin-mobile md:px-gutter py-stack-lg pb-32">
        {error && <div className="mb-5"><InlineNotice tone="error">{error} <button onClick={() => router.push("/targets")} className="underline font-semibold">เลือกอาชีพ</button></InlineNotice></div>}
        {!data && !error && <p className="py-24 text-center text-text-subtle">กำลังคำนวณเส้นทางจากข้อมูลของคุณ…</p>}
        {data && <>
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-stack-md mb-stack-lg border-b border-border-low pb-stack-md"><div><h1 className="font-display-lg text-[32px] md:text-display-lg font-bold text-text-main mb-stack-sm">Your {data.target.title_en} Roadmap</h1><div className="flex flex-wrap items-center gap-4 text-text-subtle"><span className="flex items-center gap-2"><Icon className="text-primary text-[20px]">school</Icon>SIIT Curated Path</span><span className="font-label-sm text-label-sm text-primary bg-primary-fixed px-2 py-1 rounded-full">{Math.round(data.coverage * 100)}% Completed</span></div></div><div className="flex gap-3 no-print"><button onClick={() => window.print()} className="bg-surface-muted border border-border-low text-text-subtle hover:bg-surface-container py-2 px-4 rounded flex items-center gap-2"><Icon className="text-[18px]">print</Icon>Print PDF</button><button onClick={() => router.push("/targets")} className="bg-primary text-on-primary py-2 px-4 rounded hover:bg-on-primary-fixed-variant flex items-center gap-2"><Icon className="text-[18px]">add</Icon>New Roadmap</button></div></div>
          <InlineNotice>{data.evidence_summary.note} — จาก CV {data.evidence_summary.from_cv} ทักษะ · ประเมินเอง {data.evidence_summary.self_reported} ทักษะ</InlineNotice>
          <section className="mt-stack-md bg-surface-bg border border-border-low rounded-xl p-4 md:p-stack-lg shadow-sm relative"><div className="flex items-center gap-2 mb-stack-lg text-text-subtle"><Icon className="text-[20px]">map</Icon><span className="font-label-sm text-label-sm tracking-widest uppercase text-outline">★ ROADMAP ★</span></div><div className="relative pl-1 md:pl-8">{data.steps.map((step, index) => <StepCard key={step.skill_id} step={step} last={index === data.steps.length - 1} />)}</div></section>
        </>}
      </div>
    </main>
    <MobileWorkspaceNav active="roadmap" />
  </div>;
}
