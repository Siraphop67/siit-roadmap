"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ensureSession } from "@/lib/api";
import { Icon, SiteFooter, TopNav } from "@/components/student-ui";

export default function Home() {
  const router = useRouter();
  const [starting, setStarting] = useState<"known" | "unsure" | null>(null);

  async function start(entry: "known" | "unsure") {
    setStarting(entry);
    try {
      await ensureSession(entry);
      router.push(entry === "unsure" ? "/discover" : "/targets");
    } finally {
      setStarting(null);
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-surface-bg font-body-md">
      <TopNav />
      <main className="flex-grow flex flex-col items-center justify-center py-stack-lg px-gutter max-w-container-max mx-auto w-full">
        <section className="text-center w-full max-w-3xl mb-stack-lg flex flex-col items-center">
          <div className="flex justify-center mb-stack-md gap-4" aria-hidden="true">
            {[["face_3", "border-primary", "text-primary"], ["explore", "border-text-main", "text-text-main"], ["school", "border-roadmap-accent", "text-roadmap-accent"], ["emoji_objects", "border-tertiary-fixed-dim", "text-tertiary"]].map(([icon, border, color]) => (
              <div key={icon} className={`w-14 h-14 sm:w-16 sm:h-16 rounded-full border-2 ${border} flex items-center justify-center bg-white`}><Icon className={`text-3xl sm:text-4xl icon-fill ${color}`}>{icon}</Icon></div>
            ))}
          </div>
          <h1 className="font-display-lg text-[34px] sm:text-display-lg font-bold text-on-surface mb-stack-sm">เว็บสำหรับนักศึกษา SIIT ที่ยังไม่รู้ roadmap ไปถึงสิ่งที่ตัวเองต้องการ</h1>
          <p className="font-body-lg text-base sm:text-body-lg text-text-subtle mb-stack-md">เว็บหางานบอกว่ามีงานอะไร — ของเราบอกว่าจะไปถึงงานนั้นได้ยังไง<br className="hidden sm:block"/> และต่างจากเว็บหางานตรงที่เราไม่เชื่อสิ่งที่ผู้ใช้กรอกอย่างเดียว เราอ่านจากผลงานจริงของเขา</p>
        </section>

        <section className="w-full grid grid-cols-1 md:grid-cols-2 gap-gutter mt-stack-md">
          <article className="bg-surface-muted border border-border-low rounded-xl p-stack-lg flex flex-col items-center text-center hover:ambient-shadow transition-all duration-300">
            <div className="w-16 h-16 bg-surface-container rounded-full flex items-center justify-center mb-stack-md"><Icon className="text-3xl text-primary">psychology</Icon></div>
            <h2 className="font-headline-md text-headline-md font-semibold text-on-surface mb-base-unit">ยังไม่รู้ว่าอยากเป็นอะไร</h2>
            <p className="text-text-subtle mb-stack-md">(Don&apos;t know what to be yet)</p>
            <p className="text-on-surface-variant mb-stack-lg flex-grow">แบบทดสอบกิจกรรม 41 มิติแบบ adaptive เพื่อหาอาชีพที่เป็นไปได้ 3–5 อัน</p>
            <button onClick={() => start("unsure")} disabled={starting !== null} className="bg-primary text-on-primary px-6 py-3 rounded-lg w-full hover:bg-primary-container disabled:opacity-60 transition-colors">{starting === "unsure" ? "กำลังเริ่ม…" : "Take Activity Quiz"}</button>
          </article>
          <article className="bg-surface-muted border border-border-low rounded-xl p-stack-lg flex flex-col items-center text-center hover:ambient-shadow transition-all duration-300">
            <div className="w-16 h-16 bg-surface-container rounded-full flex items-center justify-center mb-stack-md"><Icon className="text-3xl text-primary">menu_book</Icon></div>
            <h2 className="font-headline-md text-headline-md font-semibold text-on-surface mb-base-unit">รู้แล้ว อยากรู้ทางไป</h2>
            <p className="text-text-subtle mb-stack-md">(Know your goal, need the path)</p>
            <p className="text-on-surface-variant mb-stack-lg flex-grow">เลือกเป้าหมายจากคลังอาชีพ 8 อาชีพ พร้อม requirement ที่ตรวจสอบย้อนกลับได้</p>
            <button onClick={() => start("known")} disabled={starting !== null} className="bg-secondary-container text-primary px-6 py-3 rounded-lg w-full hover:bg-secondary-fixed disabled:opacity-60 transition-colors font-semibold">{starting === "known" ? "กำลังเปิดคลัง…" : "Explore Career Library"}</button>
          </article>
        </section>

        <section className="w-full mt-stack-lg flex justify-center" aria-hidden="true">
          <div className="max-w-md w-full h-32 sm:h-40 relative flex items-end justify-center gap-7 opacity-80">
            {["engineering", "data_object", "architecture", "precision_manufacturing", "bolt"].map((icon, i) => <div key={icon} className={`w-14 sm:w-16 rounded-t-full border-2 border-text-main bg-white grid place-items-center ${i % 2 ? "h-24 sm:h-28" : "h-28 sm:h-36"}`}><Icon className={`text-3xl ${i === 2 ? "text-roadmap-accent" : "text-primary"}`}>{icon}</Icon></div>)}
          </div>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
