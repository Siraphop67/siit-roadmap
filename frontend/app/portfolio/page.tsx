"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ensureSession, session } from "@/lib/api";
import { Icon, InlineNotice, MobileWorkspaceNav, SiteFooter, TopNav, WorkspaceSidebar } from "@/components/student-ui";

type Mode = "pdf" | "text" | "github" | "linkedin";

export default function PortfolioPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("pdf");
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    setError("");
    if (!consent) return setError("กรุณายินยอมให้ระบบประมวลผลเอกสารก่อนเริ่มวิเคราะห์");
    if (mode === "pdf" && !file) return setError("กรุณาเลือกไฟล์ PDF");
    if (mode === "text" && text.trim().length < 20) return setError("กรุณาวางข้อความอย่างน้อย 20 ตัวอักษร");
    if ((mode === "github" || mode === "linkedin") && !url.trim()) return setError("กรุณาใส่ลิงก์");
    setBusy(true);
    try {
      const uid = await ensureSession("known");
      const result = mode === "pdf"
        ? await api.portfolioUpload(uid, file!, true)
        : mode === "text"
          ? await api.portfolioText({ user_id: uid, text, consent: true })
          : mode === "github"
            ? await api.portfolioGithub({ user_id: uid, url, consent: true })
            : await api.portfolioLinkedin({ user_id: uid, url, text, consent: true });
      session.writeDocument(result.document_id);
      router.push(`/portfolio/review?id=${encodeURIComponent(result.document_id)}`);
    } catch (e) { setError(e instanceof Error ? e.message : "วิเคราะห์ผลงานไม่สำเร็จ"); }
    finally { setBusy(false); }
  }

  const options: { id: Mode; icon: string; title: string; description: string }[] = [
    { id: "text", icon: "description", title: "วางข้อความ (Text)", description: "วางข้อความจาก Resume หรือรายละเอียดโปรเจกต์" },
    { id: "github", icon: "code", title: "เชื่อมต่อ GitHub", description: "ดึงข้อมูลทักษะจาก Repository ของคุณ" },
    { id: "linkedin", icon: "work", title: "นำเข้าจาก LinkedIn", description: "วางข้อความโปรไฟล์พร้อมลิงก์เพื่ออ้างอิง" },
  ];

  return (
    <div className="bg-background text-text-main min-h-screen flex flex-col pb-20 lg:pb-0">
      <div className="lg:hidden"><TopNav active="Profile" /></div>
      <div className="flex flex-1">
        <WorkspaceSidebar active="portfolio" />
        <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-gutter py-stack-lg flex flex-col gap-stack-lg">
          <section className="mb-stack-md">
            <h1 className="font-headline-lg text-[28px] md:text-headline-lg font-bold text-on-surface mb-stack-sm">วิเคราะห์ทักษะจากตัวตนของคุณ</h1>
            <p className="font-body-lg text-body-lg text-text-subtle max-w-3xl">ระบบจะวิเคราะห์ทักษะของคุณจากประสบการณ์ทำงานและผลงานจริง (Resume/CV หรือ Portfolio) เพื่อค้นหาจุดแข็งที่ซ่อนอยู่ และนำไปใช้วางแผน Roadmap ที่เหมาะสมกับคุณที่สุด</p>
          </section>
          {error && <InlineNotice tone="error">{error}</InlineNotice>}
          <section className="bg-surface-bg border border-border-low rounded-xl p-5 md:p-stack-lg shadow-[0_4px_12px_rgba(0,0,0,0.02)]">
            <h2 className="font-headline-md text-headline-md font-semibold text-on-surface mb-stack-md">อัปโหลดข้อมูลของคุณ</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-stack-md mb-stack-lg">
              <label onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); setMode("pdf"); setFile(e.dataTransfer.files[0] ?? null); }} className={`border-2 border-dashed ${mode === "pdf" ? "border-primary bg-primary-fixed/30" : "border-border-low bg-surface-muted"} hover:border-primary rounded-xl p-stack-lg flex flex-col items-center justify-center text-center transition-colors min-h-[230px] cursor-pointer`}>
                <Icon className="text-4xl text-secondary mb-stack-sm">upload_file</Icon>
                <h3 className="font-label-sm text-label-sm text-on-surface mb-1">{file ? file.name : "ลากไฟล์มาวางที่นี่"}</h3>
                <p className="text-xs text-text-subtle mb-stack-sm">รองรับ PDF (สูงสุด 10MB)</p>
                <span className="px-4 py-2 bg-secondary-container text-primary rounded-lg font-label-sm text-label-sm">เลือกไฟล์</span>
                <input className="sr-only" type="file" accept="application/pdf" onChange={(e) => { setMode("pdf"); setFile(e.target.files?.[0] ?? null); }} />
              </label>
              <div className="flex flex-col gap-stack-sm">{options.map((item) => <button key={item.id} type="button" onClick={() => setMode(item.id)} className={`flex items-center gap-3 p-4 border rounded-xl hover:border-primary transition-all text-left ${mode === item.id ? "border-primary bg-primary-fixed/30" : "border-border-low bg-white"}`}><Icon className="text-secondary">{item.icon}</Icon><div><h3 className="font-label-sm text-label-sm text-on-surface">{item.title}</h3><p className="text-xs text-text-subtle">{item.description}</p></div></button>)}</div>
            </div>

            {mode === "text" && <textarea value={text} onChange={(e) => setText(e.target.value)} className="w-full min-h-44 border border-border-low rounded-lg p-4 focus:outline-none focus:border-primary" placeholder="วางข้อความจาก Resume, CV หรือรายละเอียดโปรเจกต์ของคุณ…" />}
            {mode === "github" && <input value={url} onChange={(e) => setUrl(e.target.value)} className="w-full border border-border-low rounded-lg p-3 focus:outline-none focus:border-primary" placeholder="https://github.com/username/repository" type="url" />}
            {mode === "linkedin" && <div className="grid gap-3"><input value={url} onChange={(e) => setUrl(e.target.value)} className="w-full border border-border-low rounded-lg p-3 focus:outline-none focus:border-primary" placeholder="https://linkedin.com/in/username" type="url"/><textarea value={text} onChange={(e) => setText(e.target.value)} className="w-full min-h-36 border border-border-low rounded-lg p-4 focus:outline-none focus:border-primary" placeholder="เพื่อเคารพข้อกำหนดของ LinkedIn กรุณาคัดลอกข้อความโปรไฟล์มาวางที่นี่" /></div>}

            <label className="mt-stack-md flex items-start gap-3 text-sm text-text-subtle cursor-pointer"><input checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 size-4 accent-primary" type="checkbox"/><span>ฉันยินยอมให้ SIIT Roadmap ประมวลผลเอกสารนี้เพื่อสกัดทักษะ และเข้าใจว่าฉันต้องตรวจยืนยันผลก่อนนำไปใช้</span></label>
            <button onClick={submit} disabled={busy} className="mt-stack-md w-full md:w-auto bg-primary text-on-primary px-7 py-3 rounded-lg font-semibold hover:bg-primary-container disabled:opacity-60 transition-colors">{busy ? "กำลังวิเคราะห์…" : "วิเคราะห์ทักษะ"}</button>
            <div className="mt-stack-md bg-surface-container-low border border-border-low rounded-lg p-stack-md flex items-start gap-3"><Icon className="text-primary mt-0.5">info</Icon><div><h4 className="font-label-sm text-label-sm text-on-surface mb-1">ความโปร่งใสในการวิเคราะห์</h4><p className="text-sm text-text-subtle">ทุกทักษะที่ระบบสกัดได้ จะถูกโยงกลับไปยังประโยคหรือแหล่งที่มาในเอกสารของคุณ เพื่อให้คุณตรวจสอบและยืนยันความถูกต้องได้เสมอ</p></div></div>
          </section>
          <div className="bg-surface-muted border border-border-low rounded-xl p-stack-md flex flex-col sm:flex-row sm:items-center justify-between gap-3"><div className="flex items-center gap-3"><div className="w-10 h-10 rounded-full bg-tertiary-fixed flex items-center justify-center text-tertiary"><Icon>tune</Icon></div><div><h4 className="font-label-sm text-label-sm text-on-surface">บริบทการสร้าง Roadmap</h4><p className="text-xs text-text-subtle">ระบบจะพิจารณา ชั้นปี, GPA, เวลาที่จัดสรรได้ และทักษะที่ยืนยันแล้วร่วมกัน</p></div></div></div>
        </main>
      </div>
      <div className="lg:hidden"><SiteFooter /></div>
      <MobileWorkspaceNav active="portfolio" />
    </div>
  );
}
