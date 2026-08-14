"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ensureSession, type ActivityAnswer, type DiscoverNext } from "@/lib/api";
import { Icon, InlineNotice } from "@/components/student-ui";

const choiceStyle: Record<ActivityAnswer, { icon: string; tone: string; label: string }> = {
  [-2]: { icon: "close", tone: "border-white/15 bg-white/5 hover:bg-white/10", label: "ไม่ใช่ทางของฉัน" },
  [-1]: { icon: "arrow_back", tone: "border-white/15 bg-white/5 hover:bg-white/10", label: "ไม่ค่อยอิน" },
  [0]: { icon: "tune", tone: "border-white/15 bg-white/5 hover:bg-white/10", label: "ทำได้อยู่" },
  [1]: { icon: "bolt", tone: "border-primary/50 bg-primary/15 hover:bg-primary/25", label: "น่าสนุก" },
  [2]: { icon: "stars", tone: "border-roadmap-accent/70 bg-roadmap-accent/15 hover:bg-roadmap-accent/25", label: "นี่แหละฉัน" },
};

export default function DiscoverPage() {
  const router = useRouter();
  const [data, setData] = useState<DiscoverNext | null>(null);
  const [selected, setSelected] = useState<ActivityAnswer | null>(null);
  const [userId, setUserId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try { const uid = await ensureSession("unsure"); setUserId(uid); const next = await api.discoverNext(uid); setData(next); if (next.done) router.push("/discover/results"); }
    catch (e) { setError(e instanceof Error ? e.message : "โหลด Character Creation ไม่สำเร็จ"); }
  }, [router]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);

  async function next() {
    if (selected === null || !data?.item || !userId) return;
    setBusy(true); setError("");
    try { const result = await api.discoverAnswer({ user_id: userId, item_id: data.item.item_id, answer: selected }); setSelected(null); if (result.separated && result.can_finish) router.push("/discover/results"); else setData(await api.discoverNext(userId)); }
    catch (e) { setError(e instanceof Error ? e.message : "บันทึกคำตอบไม่สำเร็จ"); }
    finally { setBusy(false); }
  }

  const mission = data?.item?.no ?? 1;
  const progress = data ? Math.min(100, (data.answered / data.min_items) * 100) : 0;

  return <div className="min-h-screen overflow-hidden bg-[#08192d] text-white relative">
    <div className="absolute inset-0 opacity-60 pointer-events-none" style={{ backgroundImage: "radial-gradient(circle at 14% 19%, rgba(55,120,209,.28), transparent 25%), radial-gradient(circle at 82% 74%, rgba(225,141,43,.18), transparent 24%)" }} />
    <div className="absolute left-[7%] top-[15%] w-2 h-2 rounded-full bg-white/70 shadow-[0_0_24px_7px_rgba(255,255,255,.25)]" /><div className="absolute right-[12%] top-[30%] w-1.5 h-1.5 rounded-full bg-primary-fixed" /><div className="absolute right-[27%] bottom-[20%] w-2 h-2 rounded-full bg-roadmap-accent" />
    <header className="relative z-10 max-w-container-max mx-auto h-20 px-margin-mobile md:px-gutter flex items-center justify-between"><button onClick={() => router.push("/")} className="font-headline-md font-bold text-xl tracking-tight">SIIT <span className="text-primary-fixed">Quest</span></button><div className="text-right"><p className="text-[10px] tracking-[.18em] text-white/50">CHARACTER CREATION</p><p className="text-sm font-semibold">เลือก build ของคุณ</p></div></header>
    <main className="relative z-10 max-w-5xl mx-auto px-margin-mobile md:px-gutter py-5 md:py-10 min-h-[calc(100vh-80px)] flex items-center">
      <div className="w-full">
        {error && <div className="max-w-3xl mx-auto mb-5"><InlineNotice tone="error">{error} <button className="underline font-semibold" onClick={load}>ลองใหม่</button></InlineNotice></div>}
        {!data && !error && <div className="py-28 text-center text-white/65"><Icon className="text-4xl animate-pulse text-primary-fixed">hub</Icon><p className="mt-4">กำลังเตรียม mission แรกของคุณ…</p></div>}
        {data?.item && <section className="max-w-4xl mx-auto">
          <div className="flex items-center gap-3 mb-7"><span className="text-xs font-bold tracking-[.15em] text-primary-fixed">MISSION {String(mission).padStart(2, "0")}</span><div className="h-px flex-1 bg-white/15"><div className="h-full bg-primary-fixed transition-all duration-500" style={{ width: `${Math.max(4, progress)}%` }} /></div><span className="text-xs text-white/55">{data.can_finish ? "พร้อมเปิดผล" : `อย่างน้อย ${data.min_items - data.answered} mission`}</span></div>
          <div className="grid grid-cols-1 lg:grid-cols-[.72fr_1.28fr] gap-5 md:gap-8 items-stretch">
            <aside className="rounded-3xl border border-white/10 bg-white/[.045] p-6 md:p-8 flex flex-col justify-between overflow-hidden relative"><div className="absolute -right-16 -top-14 w-52 h-52 border border-primary/35 rounded-full" /><div className="relative"><span className="w-12 h-12 rounded-2xl grid place-items-center bg-primary text-white shadow-lg shadow-primary/30"><Icon className="text-2xl">explore</Icon></span><p className="mt-7 text-xs tracking-[.16em] font-bold text-primary-fixed">YOUR NEXT SIGNAL</p><h1 className="mt-3 font-display-lg text-3xl md:text-4xl font-bold leading-tight">อย่าเลือกคำตอบที่ดูเก่ง<br />เลือกสิ่งที่อยากทำจริง</h1><p className="mt-4 text-sm leading-relaxed text-white/60">ไม่มีคำตอบผิด ทุก choice จะกลายเป็นสัญญาณให้ระบบสร้างสายอาชีพที่เป็นไปได้สำหรับคุณ</p></div><div className="relative mt-8 rounded-2xl bg-black/15 p-4 border border-white/5"><p className="text-xs text-white/45">SYSTEM NOTE</p><p className="mt-1 text-sm text-white/75">{data.reason}</p></div></aside>
            <section className="rounded-3xl bg-white text-[#10213b] p-6 md:p-10 shadow-[0_24px_70px_rgba(0,0,0,.28)]"><div className="flex items-center gap-2 text-xs font-bold tracking-[.13em] text-primary"><Icon>route</Icon>{data.item.group_th}</div><h2 className="mt-5 font-headline-lg text-[28px] md:text-4xl leading-tight font-bold">{data.item.prompt_th}</h2>{data.item.context_th && <p className="mt-3 text-text-subtle text-base leading-relaxed">{data.item.context_th}</p>}
              <fieldset className="mt-7 grid grid-cols-1 sm:grid-cols-2 gap-3"><legend className="sr-only">เลือกแรงดึงดูดของกิจกรรม</legend>{data.answer_choices.map((choice) => { const style = choiceStyle[choice.value]; const active = selected === choice.value; return <label key={choice.value} className="cursor-pointer"><input checked={active} onChange={() => setSelected(choice.value)} className="sr-only" name="activity-answer" type="radio"/><span className={`min-h-[76px] px-4 py-3 rounded-2xl border flex items-center gap-3 transition-all ${active ? "border-primary bg-primary-fixed ring-2 ring-primary/25" : "border-border-low bg-surface-muted hover:border-primary/50"}`}><span className={`w-10 h-10 rounded-xl grid place-items-center border ${active ? "bg-primary text-white border-primary" : "bg-white text-primary border-border-low"}`}><Icon>{style.icon}</Icon></span><span><strong className="block text-sm">{style.label}</strong><span className="text-xs text-text-subtle">{choice.label_th}</span></span></span></label>; })}</fieldset>
              {data.interim && <div className="mt-6 rounded-2xl bg-[#f2f7ff] border border-primary/15 p-4"><p className="text-xs font-bold text-primary tracking-[.12em]">BUILD PREVIEW</p><p className="mt-1 text-sm text-on-surface-variant">ตอนนี้คุณมีสัญญาณไปทาง {data.interim.top.slice(0, 3).map((t) => t.title_th).join(" · ")}</p></div>}
              <div className="mt-7 pt-6 border-t border-border-low flex items-center justify-between gap-3"><button onClick={() => router.push("/")} className="text-sm text-text-subtle hover:text-primary">บันทึกไว้ก่อน</button><div className="flex gap-2">{data.can_finish && <button onClick={() => router.push("/discover/results")} className="px-4 py-3 rounded-xl border border-primary text-primary font-semibold hover:bg-primary-fixed">เปิดผลเบื้องต้น</button>}<button onClick={next} disabled={selected === null || busy} className="px-5 py-3 rounded-xl bg-primary text-white font-semibold disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-primary/20">{busy ? "กำลังบันทึก…" : data.can_finish ? "อีกหนึ่ง mission" : "ยืนยัน choice"}<Icon>arrow_forward</Icon></button></div></div>
            </section>
          </div>
        </section>}
      </div>
    </main>
  </div>;
}
