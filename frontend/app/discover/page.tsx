"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, ensureSession, session, type ActivityAnswer, type DiscoverNext } from "@/lib/api";
import { Icon, InlineNotice } from "@/components/student-ui";

/**
 * 🔒 เฉพาะ "หน้าตา" ของปุ่มเท่านั้น — ถ้อยคำมาจาก `answer_choices` ของ API เสมอ
 *    (กติกาเดียวกับที่เขียนไว้ใน lib/api.ts และ backend/app/seed/activities.py)
 */
const choiceStyle: Record<ActivityAnswer, { icon: string; tint: string }> = {
  [-2]: { icon: "close", tint: "from-slate-700 to-slate-800" },
  [-1]: { icon: "arrow_back", tint: "from-[#45566d] to-[#26394f]" },
  [0]: { icon: "explore", tint: "from-[#2475a9] to-[#18537e]" },
  [1]: { icon: "bolt", tint: "from-[#2476c7] to-[#104f98]" },
  [2]: { icon: "stars", tint: "from-[#d98222] to-[#aa4f0a]" },
};

const stageNames = ["ความสนใจแรก", "ความถนัด", "รูปแบบการทำงาน", "แนวทางของคุณ"];

export default function DiscoverPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [data, setData] = useState<DiscoverNext | null>(null);
  const [userId, setUserId] = useState("");
  const [busy, setBusy] = useState(false);
  const [picked, setPicked] = useState<ActivityAnswer | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try { const uid = await ensureSession("unsure"); setUserId(uid); const next = await api.discoverNext(uid); if (next.done) router.push("/discover/results"); else { setData(next); setPicked(null); } }
    catch (e) { setError(e instanceof Error ? e.message : "ไม่สามารถเริ่มแบบประเมินได้"); }
  }, [router]);
  useEffect(() => {
    if (searchParams.get("fresh") === "1") {
      session.clear();
      router.replace("/discover");
      return;
    }
    void Promise.resolve().then(load);
  }, [load, router, searchParams]);

  async function choose(answer: ActivityAnswer) {
    if (!data?.item || !userId || busy) return;
    setPicked(answer); setBusy(true); setError("");
    try {
      const result = await api.discoverAnswer({ user_id: userId, item_id: data.item.item_id, answer });
      await new Promise((resolve) => setTimeout(resolve, 420));
      if (result.answered >= 4) router.push("/discover/results");
      else { const next = await api.discoverNext(userId); setData(next); setPicked(null); }
    } catch (e) { setError(e instanceof Error ? e.message : "ไม่สามารถบันทึกคำตอบได้"); setPicked(null); }
    finally { setBusy(false); }
  }

  const stage = Math.min((data?.answered ?? 0) + 1, 4);
  // ครบทั้ง 5 ระดับตามที่ API ส่งมา — "เฉย ๆ" (0) เป็นระดับที่เครื่องยนต์ใช้จริง ไม่ตัดทิ้ง
  const options = data?.answer_choices ?? [];

  return <div className="min-h-screen bg-[#061323] text-white overflow-hidden relative">
    <div className="absolute inset-0 pointer-events-none" style={{ backgroundImage: "linear-gradient(115deg, rgba(20,74,126,.5), transparent 48%), radial-gradient(circle at 78% 22%, rgba(244,157,50,.22), transparent 0 9%, transparent 32%), radial-gradient(circle at 14% 88%, rgba(45,129,213,.2), transparent 0 12%, transparent 32%)" }} />
    <div className="absolute inset-0 opacity-[.12] pointer-events-none" style={{ backgroundImage: "linear-gradient(rgba(255,255,255,.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.5) 1px, transparent 1px)", backgroundSize: "44px 44px" }} />
    <header className="relative z-10 max-w-6xl mx-auto px-5 md:px-8 h-20 flex items-center justify-between"><button onClick={() => router.push("/")} className="text-xl font-bold tracking-tight">SIIT <span className="text-[#78b7ff]">Discover</span></button><div className="flex items-center gap-4"><button onClick={() => { session.clear(); void load(); }} className="text-sm text-white/60 hover:text-white">เริ่มแบบประเมินใหม่</button><button onClick={() => router.push("/targets")} className="text-sm text-white/60 hover:text-white">ข้ามไปเลือกอาชีพด้วยตนเอง</button></div></header>
    <main className="relative z-10 max-w-6xl mx-auto px-5 md:px-8 pb-10 min-h-[calc(100vh-80px)] flex items-center">
      {error && <div className="w-full max-w-3xl mx-auto"><InlineNotice tone="error">{error} <button className="underline" onClick={load}>ลองอีกครั้ง</button></InlineNotice></div>}
      {!data && !error && <div className="w-full text-center text-white/60"><Icon className="text-5xl animate-pulse text-[#78b7ff]">stars</Icon><p className="mt-4">กำลังอ่านความสนใจของคุณ</p></div>}
      {data?.item && <section className="w-full">
        <div className="flex items-center justify-between gap-4 mb-7"><div className="flex gap-2">{stageNames.map((name, index) => <div key={name} className="flex items-center gap-2"><span className={`w-7 h-7 rounded-full grid place-items-center text-xs font-bold ${index + 1 < stage ? "bg-[#89d9b1] text-[#0b3020]" : index + 1 === stage ? "bg-[#78b7ff] text-[#062142] shadow-[0_0_0_5px_rgba(120,183,255,.16)]" : "border border-white/20 text-white/45"}`}>{index + 1 < stage ? "✓" : index + 1}</span><span className={`hidden sm:inline text-[11px] tracking-[.13em] ${index + 1 === stage ? "text-white" : "text-white/45"}`}>{name}</span>{index < 3 && <span className="hidden sm:block h-px w-8 bg-white/20" />}</div>)}</div><p className="text-xs text-white/50">คำถาม 4 ข้อ · ไม่มีคำตอบที่ถูกหรือผิด</p></div>
        <div className="grid grid-cols-1 lg:grid-cols-[.9fr_1.1fr] rounded-[32px] overflow-hidden border border-white/10 shadow-[0_30px_90px_rgba(0,0,0,.35)]">
          <aside className="p-7 md:p-10 bg-gradient-to-br from-[#102f52] to-[#081a30] relative min-h-[360px] flex flex-col justify-between"><div className="absolute -right-16 -top-12 w-64 h-64 rounded-full border border-[#78b7ff]/25" /><div className="absolute bottom-9 right-9 w-24 h-24 rounded-full bg-[#e89437]/20 blur-2xl" /><div className="relative"><p className="text-xs font-bold tracking-[.2em] text-[#8fc4ff]">ขั้นที่ {String(stage).padStart(2, "0")} · {stageNames[stage - 1]}</p><h1 className="mt-5 text-4xl md:text-5xl font-bold leading-[1.05]">ค้นหาแนวทาง<br />ที่เหมาะกับคุณ</h1><p className="mt-5 text-white/65 leading-relaxed">เลือกตามความสนใจจริง ๆ ไม่ใช่คำตอบที่คิดว่าควรตอบ เราจะใช้คำตอบเหล่านี้ประกอบเป็นเส้นทางอาชีพของคุณ</p></div><div className="relative flex items-center gap-3 text-sm text-white/70"><span className="w-10 h-10 rounded-xl bg-white/10 grid place-items-center"><Icon className="text-[#8fc4ff]">hub</Icon></span><span>{stage === 4 ? "พร้อมดูผลแล้ว" : "เลือกแล้วไปขั้นถัดไปทันที"}</span></div></aside>
          <section className="bg-[#f8fbff] text-[#10213b] p-7 md:p-10"><div className="inline-flex items-center gap-2 rounded-full bg-[#e8f3ff] px-3 py-1.5 text-xs font-bold text-[#2368ad]"><Icon className="text-sm">explore</Icon>สถานการณ์</div><h2 className="mt-5 text-2xl md:text-4xl font-bold leading-tight">{data.item.prompt_th}</h2>{data.item.context_th && <p className="mt-3 text-text-subtle leading-relaxed">{data.item.context_th}</p>}<p className="mt-7 text-sm font-semibold text-[#44556c]">ถ้าเจอสถานการณ์นี้ คุณรู้สึกอย่างไร</p>
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">{options.map((choice) => { const c = choiceStyle[choice.value]; const active = picked === choice.value; return <button type="button" key={choice.value} disabled={busy} onClick={() => choose(choice.value)} className={`relative overflow-hidden text-left rounded-2xl bg-gradient-to-br ${c.tint} p-4 min-h-[92px] text-white transition-all hover:-translate-y-1 hover:shadow-xl disabled:opacity-65 ${active ? "ring-4 ring-[#f2b050] scale-[.98]" : ""}`}><div className="flex items-start justify-between gap-3"><span className="text-sm font-bold">{choice.label_th}</span><span className="w-9 h-9 rounded-xl bg-white/15 grid place-items-center shrink-0"><Icon>{c.icon}</Icon></span></div>{active && <span className="absolute inset-0 grid place-items-center bg-[#082442]/70 font-bold">บันทึกคำตอบแล้ว</span>}</button>; })}</div>
            <p className="mt-6 text-xs text-text-subtle">{busy ? "กำลังบันทึกคำตอบของคุณ" : "เลือก 1 ข้อเพื่อไปต่อ"}</p>
          </section>
        </div>
      </section>}
    </main>
  </div>;
}
