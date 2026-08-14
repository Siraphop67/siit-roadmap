"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ensureSession, type ActivityAnswer, type DiscoverNext } from "@/lib/api";
import { DiscoverNav, Icon, InlineNotice, SiteFooter } from "@/components/student-ui";

const mood: Record<ActivityAnswer, string> = { [-2]: "sentiment_very_dissatisfied", [-1]: "sentiment_dissatisfied", [0]: "sentiment_neutral", [1]: "sentiment_satisfied", [2]: "sentiment_very_satisfied" };

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
    catch (e) { setError(e instanceof Error ? e.message : "โหลดแบบทดสอบไม่สำเร็จ"); }
  }, [router]);
  useEffect(() => {
    ensureSession("unsure").then((uid) => {
      setUserId(uid);
      return api.discoverNext(uid);
    }).then((next) => {
      setData(next);
      if (next.done) router.push("/discover/results");
    }).catch((e: unknown) => setError(e instanceof Error ? e.message : "โหลดแบบทดสอบไม่สำเร็จ"));
  }, [router]);

  async function next() {
    if (selected === null || !data?.item || !userId) return;
    setBusy(true); setError("");
    try { const result = await api.discoverAnswer({ user_id: userId, item_id: data.item.item_id, answer: selected }); setSelected(null); if (result.separated && result.can_finish) router.push("/discover/results"); else setData(await api.discoverNext(userId)); }
    catch (e) { setError(e instanceof Error ? e.message : "บันทึกคำตอบไม่สำเร็จ"); }
    finally { setBusy(false); }
  }

  return <div className="min-h-screen flex flex-col bg-surface-bg text-on-surface">
    <DiscoverNav active="Pathfinding" />
    <main className="flex-grow flex flex-col items-center justify-center py-stack-lg px-margin-mobile md:px-gutter max-w-container-max mx-auto w-full">
      <div className="w-full max-w-3xl mb-stack-lg flex flex-col items-center text-center"><span className="inline-flex items-center gap-2 px-3 py-1 bg-surface-muted border border-border-low rounded-full font-label-sm text-label-sm text-text-subtle mb-stack-sm"><Icon className="text-[16px]">psychology</Icon>Adaptive Quiz Mode</span><p className="text-text-subtle max-w-lg">แบบประเมินนี้จะเลือกคำถามถัดไปให้แยกอาชีพที่ใกล้กันได้เร็วที่สุด คุณจึงไม่จำเป็นต้องตอบครบ 41 ข้อเสมอไป</p></div>
      {error && <div className="w-full max-w-3xl mb-4"><InlineNotice tone="error">{error} <button className="underline font-semibold" onClick={load}>ลองใหม่</button></InlineNotice></div>}
      {!data && !error && <div className="w-full max-w-3xl border border-border-low rounded-xl p-16 text-center text-text-subtle">กำลังเลือกคำถามที่เหมาะกับคุณ…</div>}
      {data?.item && <section className="w-full max-w-3xl bg-surface-container-lowest border border-border-low rounded-xl p-5 md:p-[48px] relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-1 bg-surface-muted"><div className="h-full bg-primary transition-all duration-500" style={{ width: `${Math.max(2.4, data.answered / data.max_items * 100)}%` }} /></div>
        <div className="flex justify-between items-center mb-stack-lg border-b border-border-low pb-stack-sm gap-3"><span className="font-label-sm text-label-sm text-text-subtle uppercase tracking-wider">ข้อ {data.item.no}</span><span className="font-label-sm text-label-sm text-text-subtle text-right">หมวด {data.item.group_th}</span></div>
        <div className="flex flex-col items-center text-center mb-stack-lg gap-stack-lg"><div className="w-32 h-32 md:w-40 md:h-40 flex items-center justify-center rounded-full bg-surface-muted border border-border-low relative overflow-hidden"><div className="absolute inset-5 border border-primary/30 rotate-6 rounded-lg"/><Icon className="text-6xl text-primary relative">design_services</Icon></div><h1 className="font-headline-lg text-[26px] md:text-headline-lg font-bold leading-tight max-w-2xl">{data.item.prompt_th}</h1>{data.item.context_th && <p className="font-body-lg text-body-lg text-text-subtle">{data.item.context_th}</p>}</div>
        <fieldset className="grid grid-cols-2 md:grid-cols-5 gap-stack-sm mb-stack-lg w-full"><legend className="sr-only">เลือกระดับความอยากทำ</legend>{data.answer_choices.map((choice) => <label key={choice.value} className="relative cursor-pointer group w-full h-full"><input checked={selected === choice.value} onChange={() => setSelected(choice.value)} className="sr-only radio-tile-input" name="activity-answer" type="radio"/><span className="radio-tile flex flex-col items-center justify-center h-full p-3 bg-surface-muted border border-border-low rounded-lg group-hover:bg-surface-variant text-center gap-stack-sm min-h-[100px]"><Icon className="text-[28px] text-text-subtle">{mood[choice.value]}</Icon><span className="text-sm leading-snug">{choice.label_th}</span></span></label>)}</fieldset>
        {data.interim && <div className="mb-stack-md bg-primary-fixed/50 rounded-lg p-3 text-sm text-on-primary-fixed-variant"><strong>แนวโน้มตอนนี้:</strong> {data.interim.top.slice(0, 3).map((t) => t.title_th).join(" · ")}<p className="text-xs mt-1">{data.reason}</p></div>}
        <div className="flex justify-between items-center border-t border-border-low pt-stack-lg gap-3"><button onClick={() => router.push("/")} className="px-3 sm:px-6 py-3 rounded-lg text-text-subtle hover:bg-surface-muted flex items-center gap-2"><Icon>arrow_back</Icon>ออกก่อน</button><div className="flex gap-2">{data.can_finish && <button onClick={() => router.push("/discover/results")} className="px-3 sm:px-5 py-3 rounded-lg border border-primary text-primary hover:bg-primary-fixed">ดูผลเลย</button>}<button onClick={next} disabled={selected === null || busy} className="px-5 sm:px-8 py-3 rounded-lg bg-primary text-on-primary hover:bg-primary-container disabled:opacity-50 flex items-center gap-2">{busy ? "กำลังบันทึก…" : "Next"}<Icon>arrow_forward</Icon></button></div></div>
      </section>}
    </main>
    <SiteFooter discover />
  </div>;
}
