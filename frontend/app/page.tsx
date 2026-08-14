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
          <figure className="mb-stack-md max-w-2xl">
            <blockquote className="text-sm sm:text-base text-text-subtle italic leading-relaxed">“A goal without a plan is just a wish. — เป้าหมายที่ปราศจากแผนการ ก็เป็นเพียงแค่ความเพ้อฝัน”</blockquote>
            <figcaption className="mt-1.5 text-xs sm:text-sm text-text-subtle not-italic">— Antoine de Saint-Exupéry</figcaption>
          </figure>
          <h1 className="font-display-lg text-[34px] sm:text-display-lg font-bold text-on-surface mb-stack-sm">รู้เพียงแค่ว่ามีอาชีพอะไรอาจยังไม่พอ คุณจำเป็นต้องมีแผนที่นำทางเพื่อก้าวไปให้ถึงฝันนั้นด้วย</h1>
          <p className="font-body-lg text-base sm:text-body-lg text-text-subtle mb-stack-md">แพลตฟอร์มหางานทั่วไปอาจบอกคุณได้เพียงว่ามีตำแหน่งใดเปิดรับบ้าง แต่เว็บไซต์นี้จะวิเคราะห์จากศักยภาพและผลงานจริงของคุณ เพื่อชี้แนะเส้นทางสู่ความสำเร็จที่จับต้องได้<br className="hidden sm:block"/> ออกแบบมาเพื่อนักศึกษา SIIT โดยเฉพาะ สำหรับผู้ที่กำลังค้นหาทิศทางและก้าวต่อไปของตนเองในอนาคต</p>
        </section>

        <section className="w-full grid grid-cols-1 md:grid-cols-2 gap-gutter mt-stack-md">
          <article className="bg-surface-muted border border-border-low rounded-xl p-stack-lg flex flex-col items-center text-center hover:ambient-shadow transition-all duration-300">
            <div className="w-16 h-16 bg-surface-container rounded-full flex items-center justify-center mb-stack-md"><Icon className="text-3xl text-primary">psychology</Icon></div>
            <h2 className="font-headline-md text-headline-md font-semibold text-on-surface mb-base-unit">ยังค้นหาตัวตน หรือไม่แน่ใจว่าอยากทำงานอะไร</h2>
            <p className="text-on-surface-variant mb-stack-lg flex-grow">ทำแบบประเมินความสนใจเชิงลึกผ่านกิจกรรมจริงกว่า 41 มิติ ระบบจะปรับเปลี่ยนคำถามแบบไดนามิกตามคำตอบของคุณ เพื่อคัดกรองและแนะนำ 3-5 สายอาชีพที่ตอบโจทย์ความเป็นคุณมากที่สุด</p>
            <button onClick={() => start("unsure")} disabled={starting !== null} className="bg-primary text-on-primary px-6 py-3 rounded-lg w-full hover:bg-primary-container disabled:opacity-60 transition-colors">{starting === "unsure" ? "กำลังเริ่มแบบประเมิน" : "เริ่มทำแบบประเมิน"}</button>
          </article>
          <article className="bg-surface-muted border border-border-low rounded-xl p-stack-lg flex flex-col items-center text-center hover:ambient-shadow transition-all duration-300">
            <div className="w-16 h-16 bg-surface-container rounded-full flex items-center justify-center mb-stack-md"><Icon className="text-3xl text-primary">menu_book</Icon></div>
            <h2 className="font-headline-md text-headline-md font-semibold text-on-surface mb-base-unit">มีเป้าหมายชัดเจน แต่ยังมองไม่เห็นเส้นทางสู่ความสำเร็จ</h2>
            <p className="text-on-surface-variant mb-stack-lg flex-grow">สำรวจคลังอาชีพ 8 สายงานศักยภาพ พร้อมเจาะลึกเงื่อนไขและทักษะที่จำเป็น (Prerequisites) ซึ่งสามารถตรวจสอบย้อนกลับได้อย่างเป็นระบบ เพื่อให้คุณรู้แน่ชัดว่าควรเริ่มต้นพัฒนาตนเองจากจุดใด</p>
            <button onClick={() => start("known")} disabled={starting !== null} className="bg-secondary-container text-primary px-6 py-3 rounded-lg w-full hover:bg-secondary-fixed disabled:opacity-60 transition-colors font-semibold">{starting === "known" ? "กำลังเปิดคลังอาชีพ" : "เปิดคลังอาชีพ"}</button>
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
