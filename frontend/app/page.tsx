"use client";

/**
 * หน้าแรก — สองทางเข้า เครื่องยนต์เดียว
 *
 * 🔴 ทางเข้าที่สำคัญกว่าคือ "ยังไม่รู้ว่าอยากเป็นอะไร"
 *    เพราะนั่นคือกลุ่มเป้าหมายจริงตาม Problem-Statement — คนที่ตอบคำถาม
 *    "คุณสนใจอะไร" ไม่ได้ตั้งแต่ต้น · หน้านี้จึงวางไว้เป็นทางเลือกแรกและอธิบายยาวกว่า
 *
 * สร้าง session ตอนกดเข้า ไม่ใช่ตอนเปิดหน้า — เปิดดูเฉย ๆ ไม่ควรสร้างผู้ใช้ค้างไว้
 */

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Card, DataNote, Note } from "@/components/ui";
import { api, session } from "@/lib/api";

type Entry = "unsure" | "known";

const DOORS: {
  entry: Entry;
  href: string;
  title: string;
  body: string;
  detail: string;
  ready: boolean;
}[] = [
  {
    entry: "unsure",
    href: "/discover",
    title: "ยังไม่รู้ว่าอยากเป็นอะไร",
    body: "ตอบคำถามเรื่องงานที่จับต้องได้ ไม่ใช่คำถามเรื่องตัวคุณ",
    detail:
      "ไม่ถามว่า “คุณสนใจอะไร” เพราะถ้ายังไม่เคยเห็นว่ามีอะไรอยู่บนโลก ก็ตอบไม่ได้ "
      + "· ระบบเลือกข้อถัดไปให้เอง จบใน 12–24 ข้อ และบอกตลอดว่าทำไมยังถามต่อ",
    ready: false,
  },
  {
    entry: "known",
    href: "/targets",
    title: "รู้แล้วว่าอยากไปไหน",
    body: "ดูว่าจากจุดที่คุณอยู่ตอนนี้ ต้องผ่านอะไรบ้างถึงจะไปถึง",
    detail:
      "เลือกอาชีพที่อยากเป็น แล้วระบบจะอ่านผลงานจริงของคุณ "
      + "และบอกว่าเหลืออีกกี่ก้าว ก้าวถัดไปคืออะไร และมีทางไปถึงทางไหนบ้าง",
    ready: true,
  },
];

export default function Home() {
  const router = useRouter();
  const [busy, setBusy] = useState<Entry | null>(null);
  const [failed, setFailed] = useState("");

  async function enter(entry: Entry, href: string) {
    setBusy(entry);
    setFailed("");
    try {
      const existing = session.read();
      if (!existing) {
        const { user_id } = await api.createSession(entry);
        session.write(user_id);
      }
      router.push(href);
    } catch (e) {
      setFailed(e instanceof Error ? e.message : "เข้าใช้งานไม่สำเร็จ");
      setBusy(null);
    }
  }

  return (
    <main className="min-h-dvh pb-20">
      <div className="shell pt-14 sm:pt-20">
        <header className="max-w-2xl">
          <p className="mb-3 text-[0.78rem] font-semibold uppercase tracking-[0.14em] text-faint">
            สำหรับนักศึกษา SIIT
          </p>
          <h1 className="text-[1.9rem] font-bold leading-[1.28] tracking-tight sm:text-[2.4rem]">
            เว็บหางานบอกว่ามีงานอะไร —<br />
            <span className="text-accent">ของเราบอกว่าจะไปถึงงานนั้นได้ยังไง</span>
          </h1>
          <p className="mt-4 text-[1.05rem] leading-relaxed text-muted">
            และเราไม่เชื่อสิ่งที่คุณกรอกอย่างเดียว —{" "}
            <strong className="text-foreground">เราอ่านจากผลงานจริงของคุณ</strong>{" "}
            แล้วบอกว่าคุณอยู่ตรงไหนบนเส้นทางไปสู่งานที่อยากทำ
          </p>
        </header>

        {failed && (
          <div className="mt-6 max-w-2xl">
            <Note tone="warn">{failed}</Note>
          </div>
        )}

        <div className="mt-10 grid gap-5 md:grid-cols-2">
          {DOORS.map((d) => (
            <Card key={d.entry} className="flex flex-col">
              <h2 className="text-[1.25rem] font-bold leading-snug">{d.title}</h2>
              <p className="mt-1.5 text-[1rem] text-foreground">{d.body}</p>
              <p className="mt-3 flex-1 text-[0.92rem] leading-relaxed text-muted">
                {d.detail}
              </p>

              {d.ready ? (
                <button
                  type="button"
                  onClick={() => enter(d.entry, d.href)}
                  disabled={busy !== null}
                  className="mt-5 rounded-lg bg-accent px-5 py-3 text-[0.98rem] font-semibold text-white transition hover:brightness-110 disabled:bg-line-strong disabled:text-faint"
                >
                  {busy === d.entry ? "กำลังเข้า…" : "เริ่มตรงนี้ →"}
                </button>
              ) : (
                // 🔴 บอกตามตรงว่ายังไม่เสร็จ ดีกว่าให้กดแล้วเจอหน้าว่าง
                <div className="mt-5">
                  <div className="rounded-lg border border-line-strong px-5 py-3 text-center text-[0.95rem] font-semibold text-faint">
                    กำลังสร้าง
                  </div>
                  <p className="mt-2 text-[0.85rem] text-faint">
                    เครื่องยนต์ฝั่งนี้เสร็จและทดสอบแล้ว เหลือหน้าจอ —
                    ระหว่างนี้เข้าทางขวาแล้วเลือกจากคลังอาชีพได้
                  </p>
                </div>
              )}
            </Card>
          ))}
        </div>

        <section className="mt-12 max-w-2xl">
          <h2 className="text-[1.05rem] font-bold">ต่างจากเว็บหางานตรงไหน</h2>
          <dl className="mt-4 space-y-3 text-[0.95rem]">
            {[
              ["ใช้ได้ตอนไหน", "เว็บหางานใช้ได้เมื่อคุณพร้อมสมัครแล้ว — ของเราใช้ได้ตอนที่ยังห่างอีก 5 ก้าว"],
              ["รู้จักคุณจากอะไร", "จากผลงานที่คุณเคยทำจริง ซึ่งชี้กลับไปที่บรรทัดในเอกสารได้ ไม่ใช่จากช่องที่คุณกรอกว่ามี"],
              ["ถ้าคุณสมบัติยังไม่ถึง", "ยังแสดงอยู่ พร้อมบอกว่าติดอะไร — ไม่หายไปจากผลการค้นหา"],
            ].map(([k, v]) => (
              <div key={k} className="border-l-2 border-line pl-4">
                <dt className="font-semibold">{k}</dt>
                <dd className="text-muted">{v}</dd>
              </div>
            ))}
          </dl>
          <DataNote>
            ต้นแบบ — อาชีพและเงื่อนไขในระบบยังเป็นชุดที่ทีมเขียนขึ้นเอง
            ยังไม่ได้มาจากประกาศงานจริง และเราจะบอกตรงนี้เสมอจนกว่าจะมี
          </DataNote>
        </section>
      </div>
    </main>
  );
}
