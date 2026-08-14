"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, LEVEL_LABELS, session, type DocumentReview } from "@/lib/api";
import { Icon, InlineNotice, MobileWorkspaceNav, WorkspaceSidebar } from "@/components/student-ui";

type Decision = "confirmed" | "rejected" | "edited";

function ReviewContent() {
  const params = useSearchParams();
  const router = useRouter();
  const documentId = params.get("id") ?? session.readDocument();
  const [document, setDocument] = useState<DocumentReview | null>(null);
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const [levels, setLevels] = useState<Record<string, number>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!documentId) { Promise.resolve().then(() => setError("ไม่พบเอกสารสำหรับตรวจผล กรุณาอัปโหลดใหม่")); return; }
    api.document(documentId).then((data) => {
      setDocument(data);
      setDecisions(Object.fromEntries(data.extracted.map((item) => [item.id, item.user_status === "pending" ? "confirmed" : item.user_status as Decision])));
      setLevels(Object.fromEntries(data.extracted.map((item) => [item.id, item.level])));
    }).catch((e: unknown) => setError(e instanceof Error ? e.message : "โหลดผลสกัดไม่สำเร็จ"));
  }, [documentId]);

  const highlighted = useMemo(() => {
    if (!document) return null;
    const spans = [...document.extracted].sort((a, b) => a.span_start - b.span_start).filter((span, index, all) => index === 0 || span.span_start >= all[index - 1].span_end);
    const parts: React.ReactNode[] = []; let cursor = 0;
    spans.forEach((span) => { parts.push(document.raw_text.slice(cursor, span.span_start)); parts.push(<mark key={span.id} className="bg-primary-fixed text-on-primary-fixed px-0.5 rounded" title={span.name_th}>{document.raw_text.slice(span.span_start, span.span_end)}</mark>); cursor = span.span_end; });
    parts.push(document.raw_text.slice(cursor)); return parts;
  }, [document]);

  async function confirm() {
    const uid = session.read();
    if (!documentId || !uid) return setError("ไม่พบ session กรุณาเริ่มใหม่จากหน้าแรก");
    setBusy(true); setError("");
    try {
      await api.confirmExtraction(documentId, { user_id: uid, decisions, levels });
      router.push("/skills");
    } catch (e) { setError(e instanceof Error ? e.message : "บันทึกผลยืนยันไม่สำเร็จ"); }
    finally { setBusy(false); }
  }

  return <div className="flex min-h-screen bg-background pb-20 lg:pb-0">
    <WorkspaceSidebar active="portfolio" />
    <main className="flex-1 px-margin-mobile md:px-gutter py-stack-lg overflow-y-auto">
      <div className="max-w-container-max mx-auto">
        <div className="mb-stack-lg"><span className="text-label-sm text-primary font-semibold uppercase tracking-wider">ขั้นตอนยืนยันผล</span><h1 className="mt-2 font-headline-lg text-[28px] md:text-headline-lg font-bold">ตรวจทักษะที่ระบบพบ</h1><p className="mt-2 text-text-subtle max-w-3xl">ระบบจะยังไม่นับทักษะเหล่านี้จนกว่าคุณจะยืนยัน ตรวจข้อความต้นทาง ระดับ และปฏิเสธรายการที่ไม่ตรงได้ทีละข้อ</p></div>
        {error && <div className="mb-stack-md"><InlineNotice tone="error">{error}</InlineNotice></div>}
        {!document && !error && <p className="py-20 text-center text-text-subtle">กำลังโหลดผลวิเคราะห์…</p>}
        {document && <div className="grid lg:grid-cols-[1.1fr_.9fr] gap-gutter items-start">
          <section className="bg-white border border-border-low rounded-xl overflow-hidden lg:sticky lg:top-6"><div className="p-4 border-b border-border-low flex justify-between"><h2 className="font-headline-md text-lg font-semibold">ข้อความต้นทาง</h2><span className="text-xs text-text-subtle">{document.kind.toUpperCase()} · {document.raw_text.length.toLocaleString()} ตัวอักษร</span></div><div className="p-5 max-h-[68vh] overflow-auto whitespace-pre-wrap text-sm leading-7 text-on-surface-variant">{highlighted}</div></section>
          <section className="space-y-3"><div className="flex items-center justify-between mb-2"><h2 className="font-headline-md text-lg font-semibold">พบ {document.extracted.length} ทักษะ</h2><span className="text-xs text-text-subtle">ตัวสกัด: {document.extractor}</span></div>
            {document.extracted.map((item) => <article key={item.id} className={`bg-white border rounded-xl p-4 ${decisions[item.id] === "rejected" ? "border-error/30 opacity-70" : "border-border-low"}`}>
              <div className="flex gap-3 justify-between"><div><h3 className="font-semibold">{item.name_th}</h3><p className="text-xs text-text-subtle mt-1">หลักฐาน “{item.span_text}” · ความมั่นใจ {Math.round(item.confidence * 100)}%</p></div><span className="rounded-full bg-primary-fixed px-2 py-1 text-xs text-primary self-start">ระดับ {levels[item.id]}</span></div>
              <div className="mt-4 grid grid-cols-2 gap-2"><button onClick={() => setDecisions((d) => ({...d, [item.id]: "confirmed"}))} className={`rounded-lg border px-3 py-2 text-sm flex items-center justify-center gap-1 ${decisions[item.id] !== "rejected" ? "border-primary bg-primary-fixed text-primary" : "border-border-low"}`}><Icon className="text-base">check</Icon>ยืนยัน</button><button onClick={() => setDecisions((d) => ({...d, [item.id]: "rejected"}))} className={`rounded-lg border px-3 py-2 text-sm flex items-center justify-center gap-1 ${decisions[item.id] === "rejected" ? "border-error bg-error-container text-error" : "border-border-low"}`}><Icon className="text-base">close</Icon>ไม่ใช่</button></div>
              {decisions[item.id] !== "rejected" && <label className="mt-3 block text-xs text-text-subtle">ระดับทักษะ<select value={levels[item.id]} onChange={(e) => { const level = Number(e.target.value); setLevels((l) => ({...l, [item.id]: level})); setDecisions((d) => ({...d, [item.id]: level === item.level ? "confirmed" : "edited"})); }} className="mt-1 w-full border border-border-low rounded-lg p-2 text-sm text-on-surface bg-white">{[1,2,3].map((level) => <option key={level} value={level}>{level} — {LEVEL_LABELS[level]}</option>)}</select></label>}
            </article>)}
            {document.extracted.length === 0 && <InlineNotice>ยังไม่พบทักษะที่จับคู่กับคลัง 73 ทักษะ ลองเพิ่มรายละเอียดเครื่องมือหรือสิ่งที่คุณลงมือทำจริง</InlineNotice>}
            <button onClick={confirm} disabled={busy || document.extracted.length === 0} className="w-full bg-primary text-on-primary rounded-lg py-3 font-semibold hover:bg-primary-container disabled:opacity-50">{busy ? "กำลังบันทึก…" : "ยืนยันและดู Skill Graph"}</button>
          </section>
        </div>}
      </div>
    </main>
    <MobileWorkspaceNav active="portfolio" />
  </div>;
}

export default function ReviewPage() { return <Suspense fallback={<div className="p-10">กำลังโหลด…</div>}><ReviewContent /></Suspense>; }
