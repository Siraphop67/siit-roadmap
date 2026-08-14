"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, session, type DiscoverResult, type MatchCard } from "@/lib/api";
import { DiscoverNav, Icon, InlineNotice, SiteFooter } from "@/components/student-ui";

const resultIcons = ["precision_manufacturing", "electric_bolt", "architecture", "analytics", "code_blocks"];

function SignalMap() {
  return <div className="relative h-48 sm:h-56 w-full max-w-sm mx-auto" aria-hidden="true">
    <div className="absolute left-[12%] top-[62%] h-px w-[65%] -rotate-[24deg] bg-primary/35" />
    <div className="absolute left-[28%] top-[23%] h-px w-[56%] rotate-[47deg] bg-primary/30" />
    <div className="absolute left-[21%] top-[50%] h-px w-[44%] rotate-[8deg] bg-roadmap-accent/40" />
    <span className="absolute left-[7%] top-[58%] w-5 h-5 rounded-full bg-roadmap-accent border-4 border-white shadow" />
    <span className="absolute left-[25%] top-[20%] w-10 h-10 rounded-full bg-primary border-[7px] border-primary-fixed shadow-lg" />
    <span className="absolute left-[48%] top-[47%] w-7 h-7 rounded-full bg-secondary border-[5px] border-secondary-container shadow" />
    <span className="absolute right-[8%] top-[17%] w-6 h-6 rounded-full bg-tertiary border-4 border-tertiary-fixed shadow" />
    <span className="absolute right-[4%] bottom-[9%] w-11 h-11 rounded-full border-2 border-primary/35 bg-white/65 grid place-items-center"><Icon className="text-primary text-xl">stars</Icon></span>
    <p className="absolute left-[18%] bottom-0 text-[11px] text-text-subtle font-semibold tracking-wide">จุดเชื่อมโยงความสนใจของคุณ</p>
  </div>;
}

function Reasons({ target }: { target: MatchCard }) {
  return <ul className="space-y-2">{target.reasons.slice(0, 3).map((reason) => <li key={reason.ref_id} className="flex gap-2 text-sm text-text-subtle"><Icon className="text-primary mt-0.5 text-[15px]">check_circle</Icon><span><strong className="text-text-main">{reason.label}</strong> · {reason.reads_as}</span></li>)}</ul>;
}

export default function ResultsPage() {
  const router = useRouter();
  const [data, setData] = useState<DiscoverResult | null>(null);
  const [error, setError] = useState("");
  const [picking, setPicking] = useState("");
  useEffect(() => { const uid = session.read(); if (!uid) { Promise.resolve().then(() => setError("ยังไม่พบผลการประเมิน กรุณาเริ่มจากหน้าแรก")); return; } api.discoverResult(uid).then(setData).catch((e: unknown) => setError(e instanceof Error ? e.message : "ไม่สามารถโหลดผลการประเมินได้")); }, []);
  async function choose(target: MatchCard) { const uid = session.read(); if (!uid) return; setPicking(target.target_id); try { await api.setGoal({ user_id: uid, target_id: target.target_id }); session.writeTarget(target.target_id); await api.roadmap(uid, target.target_id); router.push("/roadmap"); } catch (e) { setError(e instanceof Error ? e.message : "ไม่สามารถสร้างเส้นทางพัฒนาอาชีพได้"); } finally { setPicking(""); } }

  const top = data?.targets[0];
  const alternatives = data?.targets.slice(1) ?? [];

  return <div className="min-h-screen flex flex-col bg-surface-bg text-on-surface overflow-hidden">
    <DiscoverNav active="Roadmaps" />
    <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-gutter py-8 md:py-12">
      {error && <div className="mb-5"><InlineNotice tone="error">{error} <button onClick={() => router.push("/discover")} className="underline font-semibold">กลับไปทำแบบประเมิน</button></InlineNotice></div>}
      {!data && !error && <div className="py-28 text-center text-text-subtle"><Icon className="text-4xl animate-pulse text-primary">hub</Icon><p className="mt-4">กำลังวิเคราะห์ความสนใจของคุณ</p></div>}
      {data && <>
        <section className="relative overflow-hidden rounded-3xl bg-[#112d51] text-white px-6 py-8 md:px-10 md:py-10 shadow-[0_18px_50px_rgba(14,42,78,.18)]">
          <div className="absolute -left-20 -top-28 w-72 h-72 rounded-full border border-white/10" aria-hidden="true" />
          <div className="absolute right-[16%] -bottom-36 w-72 h-72 rounded-full bg-primary/25 blur-3xl" aria-hidden="true" />
          <div className="relative grid grid-cols-1 md:grid-cols-[1.15fr_.85fr] items-center gap-5">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full bg-white/10 border border-white/15 px-3 py-1.5 text-xs font-semibold tracking-[.12em]"><Icon className="text-sm">stars</Icon>ผลวิเคราะห์ความสนใจด้านอาชีพ</p>
              <h1 className="mt-5 font-display-lg text-3xl sm:text-4xl md:text-5xl font-bold leading-[1.12]">ไม่ใช่เพียงการค้นพบอาชีพที่ใช่สำหรับคุณ<br className="hidden sm:block" />แต่คือการวาดเส้นทาง<br className="hidden sm:block" />เพื่อนำพาคุณก้าวไปสู่ความสำเร็จ</h1>
              <p className="mt-4 max-w-xl text-white/75 leading-relaxed">จาก {data.answered} กิจกรรมที่คุณให้ความสนใจ เราได้นำมาประมวลผลและเทียบเคียงกับ {data.compared_count} เส้นทางอาชีพแห่งอนาคต เพื่อเฟ้นหาจุดเริ่มต้นที่เหมาะสมและดีที่สุดสำหรับคุณในเวลานี้</p>
              <div className="mt-6 flex flex-wrap gap-3"><span className="rounded-xl bg-white/10 px-3 py-2 text-sm"><strong className="text-white">{data.targets.length}</strong> เส้นทางอาชีพที่น่าจับตามอง</span><span className="rounded-xl bg-white/10 px-3 py-2 text-sm">เริ่มต้นพัฒนาจาก <strong className="text-white">1</strong> เส้นทางที่คุณเลือกเอง</span></div>
            </div>
            <SignalMap />
          </div>
        </section>

        {data.separation_message && <div className="mt-5"><InlineNotice>{data.separation_message}</InlineNotice></div>}

        {top && <section className="mt-8 md:mt-10">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2 mb-4"><div><p className="text-primary text-xs font-bold tracking-[.16em]">จุดเริ่มต้นที่เหมาะสมที่สุด</p><h2 className="mt-1 font-headline-md text-2xl md:text-3xl font-bold">เส้นทางที่น่าเริ่มที่สุดตอนนี้</h2></div><p className="text-sm text-text-subtle">คะแนนเป็นตำแหน่งสัมพัทธ์ ไม่ใช่เปอร์เซ็นต์ความเหมาะสม</p></div>
          <article className="relative overflow-hidden rounded-2xl border border-primary/25 bg-gradient-to-br from-primary-fixed via-white to-secondary-container/60 p-5 md:p-8 shadow-[0_12px_28px_rgba(31,88,155,.10)]">
            <div className="absolute right-[-25px] top-[-25px] w-40 h-40 rounded-full border-[22px] border-primary/10" aria-hidden="true" />
            <div className="relative grid grid-cols-1 lg:grid-cols-[1fr_.8fr] gap-7 items-start">
              <div><div className="flex items-center gap-3"><div className="w-14 h-14 rounded-2xl bg-primary text-on-primary grid place-items-center shadow-lg"><Icon className="text-3xl">{resultIcons[0]}</Icon></div><div><span className="inline-flex items-center gap-1 text-xs bg-white text-primary font-bold px-2.5 py-1 rounded-full"><Icon className="text-sm icon-fill">stars</Icon>ตรงที่สุด · {top.relative_score}/100</span><h3 className="mt-2 font-headline-md text-2xl md:text-3xl font-bold">{top.title_th}</h3></div></div><p className="mt-5 max-w-xl text-on-surface-variant leading-relaxed">{top.summary}</p></div>
              <div className="rounded-xl bg-white/80 border border-white p-5"><p className="text-xs font-bold tracking-[.12em] text-text-subtle mb-3">เหตุผลที่เหมาะกับคุณ</p><Reasons target={top} /></div>
            </div>
            {top.heads_up.length > 0 && <div className="relative mt-5 pt-5 border-t border-primary/15 text-sm text-on-surface-variant"><span className="font-semibold">สิ่งที่ควรรู้ก่อนเริ่ม:</span> {top.heads_up[0].reads_as}</div>}
            <div className="relative mt-6 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4"><p className="text-sm text-text-subtle flex items-center gap-2"><Icon className="text-primary">route</Icon>เลือกแล้วเราจะสร้างเส้นทางทักษะเฉพาะของคุณให้ทันที</p><button onClick={() => choose(top)} disabled={picking !== ""} className="bg-primary text-on-primary px-5 py-3 rounded-xl font-semibold hover:bg-primary-container disabled:opacity-60 flex items-center justify-center gap-2 shadow-lg shadow-primary/20">{picking === top.target_id ? "กำลังสร้างเส้นทางพัฒนา" : "เริ่มเส้นทางนี้"}<Icon>arrow_forward</Icon></button></div>
          </article>
        </section>}

        {alternatives.length > 0 && <section className="mt-10"><div className="flex items-end justify-between gap-4 mb-4"><div><p className="text-text-subtle text-xs font-bold tracking-[.16em]">เส้นทางอื่นที่น่าพิจารณา</p><h2 className="mt-1 font-headline-md text-2xl font-bold">อีกไม่กี่เส้นทางที่สัญญาณของคุณชี้ไปถึง</h2></div></div><div className="grid grid-cols-1 md:grid-cols-2 gap-5">{alternatives.map((target, index) => <article key={target.target_id} className="rounded-2xl border border-border-low bg-white p-5 flex flex-col transition duration-300 hover:-translate-y-1 hover:shadow-xl"><div className="flex items-start justify-between gap-3"><div className="w-11 h-11 rounded-xl bg-surface-container-low grid place-items-center text-primary"><Icon className="text-2xl">{resultIcons[(index + 1) % resultIcons.length]}</Icon></div><span className="text-sm font-bold text-primary bg-primary-fixed px-2.5 py-1 rounded-full">{target.relative_score}/100</span></div><h3 className="mt-5 font-headline-md text-xl font-bold">{target.title_th}</h3><p className="mt-2 text-sm text-text-subtle flex-grow">{target.summary}</p><div className="mt-5 pt-4 border-t border-border-low"><Reasons target={target} /></div><button onClick={() => choose(target)} disabled={picking !== ""} className="mt-5 w-full py-2.5 rounded-xl border border-primary text-primary font-semibold hover:bg-primary hover:text-on-primary disabled:opacity-60 flex justify-center gap-2">{picking === target.target_id ? "กำลังสร้าง" : "ดูเส้นทางพัฒนานี้"}<Icon className="text-sm">arrow_forward</Icon></button></article>)}</div></section>}

        {data.unconsidered && <section className="mt-10 rounded-2xl p-5 md:p-7 border border-roadmap-accent/25 bg-[#fff8ec]"><div className="grid grid-cols-1 md:grid-cols-[auto_1fr_auto] gap-5 items-center"><div className="w-16 h-16 rounded-2xl bg-white text-roadmap-accent grid place-items-center shadow-sm"><Icon className="text-3xl">explore</Icon></div><div><p className="text-xs font-bold tracking-[.14em] text-roadmap-accent">เส้นทางที่คุณอาจยังไม่เคยพิจารณา</p><h2 className="mt-1 font-headline-md text-xl font-bold">{data.unconsidered.title_th}</h2><p className="mt-2 text-sm text-text-subtle">{data.unconsidered_note || data.unconsidered.summary}</p></div><button onClick={() => choose(data.unconsidered!)} disabled={picking !== ""} className="border border-roadmap-accent text-roadmap-accent hover:bg-roadmap-accent hover:text-white px-5 py-2.5 rounded-xl font-semibold disabled:opacity-60">ดูเส้นทางนี้</button></div></section>}

        <div className="mt-8"><InlineNotice>{data.scale_note} · คะแนนทุกค่าเป็นตำแหน่งสัมพัทธ์จากอาชีพที่เปรียบเทียบ</InlineNotice></div>
        <section className="flex justify-center mt-7"><button onClick={() => router.push("/targets")} className="text-secondary hover:text-primary font-semibold flex items-center gap-2 py-2 px-4 rounded-lg hover:bg-surface-container-low"><Icon>library_books</Icon>ดูคลังข้อมูลอาชีพทั้งหมด</button></section>
      </>}
    </main>
    <SiteFooter discover />
  </div>;
}
