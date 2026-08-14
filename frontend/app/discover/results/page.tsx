"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, session, type DiscoverResult, type MatchCard } from "@/lib/api";
import { DiscoverNav, Icon, InlineNotice, SiteFooter } from "@/components/student-ui";

const resultIcons = ["precision_manufacturing", "electric_bolt", "architecture", "analytics", "code_blocks"];

export default function ResultsPage() {
  const router = useRouter();
  const [data, setData] = useState<DiscoverResult | null>(null);
  const [error, setError] = useState("");
  const [picking, setPicking] = useState("");
  useEffect(() => { const uid = session.read(); if (!uid) { Promise.resolve().then(() => setError("ยังไม่มีผลแบบทดสอบ กรุณาเริ่มจากหน้าแรก")); return; } api.discoverResult(uid).then(setData).catch((e: unknown) => setError(e instanceof Error ? e.message : "โหลดผลลัพธ์ไม่สำเร็จ")); }, []);
  async function choose(target: MatchCard) { const uid = session.read(); if (!uid) return; setPicking(target.target_id); try { await api.setGoal({ user_id: uid, target_id: target.target_id }); session.writeTarget(target.target_id); await api.roadmap(uid, target.target_id); router.push("/roadmap"); } catch (e) { setError(e instanceof Error ? e.message : "สร้าง Roadmap ไม่สำเร็จ"); } finally { setPicking(""); } }

  return <div className="bg-background text-on-background min-h-screen flex flex-col">
    <DiscoverNav active="Roadmaps" />
    <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-gutter py-stack-lg">
      <section className="mb-stack-lg text-center md:text-left"><h1 className="font-headline-lg text-[28px] md:text-headline-lg font-bold text-text-main mb-stack-sm">อาชีพที่เหมาะกับคุณที่สุด</h1><p className="font-body-lg text-body-lg text-text-subtle max-w-2xl">จากคำตอบ {data?.answered ?? 0} ข้อ นี่คืออาชีพที่ระบบแนะนำจากกิจกรรมที่คุณอยากลงมือทำจริง</p></section>
      {error && <div className="mb-5"><InlineNotice tone="error">{error} <button onClick={() => router.push("/discover")} className="underline font-semibold">กลับไปทำแบบทดสอบ</button></InlineNotice></div>}
      {!data && !error && <p className="py-20 text-center text-text-subtle">กำลังวิเคราะห์ผล…</p>}
      {data?.separation_message && <div className="mb-5"><InlineNotice>{data.separation_message}</InlineNotice></div>}
      {data && <>
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-stack-md mb-stack-lg">{data.targets.map((target, index) => <article key={target.target_id} className="bg-surface-muted border border-border-low rounded-lg p-stack-md flex flex-col hover:shadow-lg transition-shadow duration-300 relative group">
          <div className={`absolute top-stack-sm right-stack-sm ${index === 0 ? "bg-primary-fixed text-primary" : "bg-secondary-fixed text-on-secondary-fixed-variant"} px-2 py-1 rounded font-label-sm text-label-sm flex items-center gap-1`}><Icon className="text-sm icon-fill">{index === 0 ? "stars" : "analytics"}</Icon>{target.relative_score}/100</div>
          <div className="w-12 h-12 bg-surface-container rounded-full flex items-center justify-center mb-stack-sm border border-border-low"><Icon className="text-primary text-2xl">{resultIcons[index % resultIcons.length]}</Icon></div>
          <h2 className="font-headline-md text-xl sm:text-headline-md font-semibold text-text-main mb-2 pr-16">{target.title_th}{target.is_unconsidered && <span className="ml-2 bg-surface-container text-on-surface-variant px-2 py-0.5 rounded text-xs border border-outline-variant whitespace-nowrap">Hidden Gem</span>}</h2>
          <p className="text-text-subtle mb-stack-md flex-grow">{target.summary}</p>
          <div className="mb-stack-md"><h3 className="font-label-sm text-label-sm text-secondary mb-2 uppercase tracking-wide">ทำไมถึงเสนอ</h3><ul className="text-sm text-text-subtle mb-4 space-y-1">{target.reasons.map((reason) => <li key={reason.ref_id}><span className="text-primary font-semibold">{reason.label}</span> — {reason.reads_as}</li>)}</ul>{target.heads_up.length > 0 && <><h3 className="font-label-sm text-label-sm text-secondary mb-2 uppercase tracking-wide">ควรรู้ก่อนเลือก</h3><ul className="text-sm text-text-subtle space-y-1">{target.heads_up.map((reason) => <li key={reason.ref_id}><span className="text-error font-semibold">{reason.label}</span> — {reason.reads_as}</li>)}</ul></>}</div>
          <button onClick={() => choose(target)} disabled={picking !== ""} className={`w-full ${index === 0 ? "bg-[#3778D1] text-white" : "bg-[#EBF2FF] text-[#3778D1]"} font-label-sm text-label-sm py-3 rounded transition-colors flex items-center justify-center gap-2 mt-auto disabled:opacity-60`}>{picking === target.target_id ? "กำลังสร้าง…" : "เลือกอาชีพนี้เพื่อสร้าง Roadmap"}<Icon className="text-sm">arrow_forward</Icon></button>
        </article>)}</section>
        {data.unconsidered && <section className="mt-stack-lg mb-stack-lg"><h2 className="font-headline-md text-headline-md font-semibold text-text-main mb-stack-sm flex items-center gap-2"><Icon className="text-roadmap-accent">explore</Icon>อาชีพที่คุณอาจไม่เคยคิดถึง</h2><div className="bg-surface-bright border border-border-low rounded-lg p-stack-md md:p-stack-lg flex flex-col md:flex-row gap-stack-md items-center"><div className="w-20 h-20 bg-tertiary-fixed rounded-full grid place-items-center shrink-0"><Icon className="text-tertiary text-4xl">explore</Icon></div><div className="flex-grow text-center md:text-left"><h3 className="font-headline-md text-headline-md font-semibold">{data.unconsidered.title_th}</h3><p className="text-text-subtle mt-2">{data.unconsidered_note || data.unconsidered.summary}</p></div><button onClick={() => choose(data.unconsidered!)} className="border border-[#3778D1] text-[#3778D1] hover:bg-[#EBF2FF] font-label-sm text-label-sm py-2 px-6 rounded">ดู Roadmap</button></div></section>}
        <InlineNotice>{data.scale_note} · เปรียบเทียบทั้งหมด {data.compared_count} อาชีพ — คะแนนนี้เป็นตำแหน่งสัมพัทธ์ ไม่ใช่เปอร์เซ็นต์ความเหมาะสม</InlineNotice>
        <section className="flex justify-center mt-stack-lg"><button onClick={() => router.push("/targets")} className="text-secondary hover:text-text-main font-label-sm text-label-sm flex items-center gap-2 py-2 px-4 rounded hover:bg-surface-container-low"><Icon>library_books</Icon>View All 8 Careers in Library</button></section>
      </>}
    </main>
    <SiteFooter discover />
  </div>;
}
