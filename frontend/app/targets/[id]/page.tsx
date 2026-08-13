"use client";

/**
 * รายละเอียดอาชีพ — "งานนี้ทำอะไรบ้าง" ก่อนตัดสินใจเลือก
 *
 * 🔴 requirement ทุกข้อติดป้ายว่ามาจากไหน (`source`)
 *    curated  ทีมเขียนเอง ยังไม่มีประกาศงานยืนยัน
 *    postings พบในประกาศงานจริง
 *    both     ทั้งคู่ — แข็งแรงที่สุด
 *    ห้ามแสดงเหมือนกัน เพราะข้อที่ตลาดยืนยันแล้วกับข้อที่เราเดาเอง มีน้ำหนักต่างกัน
 *    (ตอนนี้ทุกข้อยังเป็น curated เพราะยังไม่มีประกาศงาน — และหน้าจอบอกตามนั้น)
 */

import Link from "next/link";
import { use, useEffect, useState } from "react";

import { Card, DataNote, ErrorState, Loading, Page } from "@/components/ui";
import { api, type TargetDetail } from "@/lib/api";

const SOURCE_LABEL = {
  both: { text: "ประกาศงานจริงยืนยัน", cls: "border-accent/40 text-accent" },
  postings: { text: "จากประกาศงานจริง", cls: "border-accent/40 text-accent" },
  curated: { text: "ทีมเขียนเอง", cls: "border-line-strong text-faint" },
} as const;

export default function TargetDetailPage(props: PageProps<"/targets/[id]">) {
  const { id } = use(props.params);
  const [t, setT] = useState<TargetDetail | null>(null);
  const [failed, setFailed] = useState("");

  useEffect(() => {
    api
      .target(id)
      .then(setT)
      .catch((e) => setFailed(e instanceof Error ? e.message : "โหลดไม่สำเร็จ"));
  }, [id]);

  if (failed) return <ErrorState message={failed} />;
  if (!t) return <Loading />;

  const verified = t.requirements.filter((r) => r.source !== "curated").length;

  return (
    <Page eyebrow={t.sector_label} title={t.title_th} lede={t.summary}>
      <Card>
        <h2 className="text-[0.8rem] font-semibold uppercase tracking-wider text-faint">
          วันหนึ่งของคนทำงานนี้
        </h2>
        <p className="mt-2 leading-relaxed">{t.day_in_the_life}</p>
      </Card>

      <dl className="mt-5 grid gap-4 text-[0.93rem] sm:grid-cols-3">
        {[
          ["สาขาที่รับ", t.field_whitelist.join(" · ")],
          ["วุฒิขั้นต่ำ", t.min_education ?? "ไม่ระบุ"],
          ["เกรดขั้นต่ำ", t.min_gpa ? t.min_gpa.toFixed(2) : "ไม่ระบุ"],
        ].map(([k, v]) => (
          <div key={k} className="border-l-2 border-line pl-4">
            <dt className="text-faint">{k}</dt>
            <dd className="font-semibold">{v}</dd>
          </div>
        ))}
      </dl>

      <section className="mt-9">
        <h2 className="text-[1.1rem] font-bold">
          ต้องแสดงความสามารถ {t.requirements.length} เรื่อง
        </h2>
        <p className="mt-1 text-[0.92rem] text-muted">
          {verified > 0
            ? `${verified} เรื่องยืนยันได้จากประกาศงานจริง`
            : "ทั้งหมดยังเป็นชุดที่ทีมเขียนขึ้นเอง ยังไม่มีประกาศงานจริงยืนยัน"}
        </p>

        <ul className="mt-4 space-y-2">
          {t.requirements.map((r) => {
            const src = SOURCE_LABEL[r.source] ?? SOURCE_LABEL.curated;
            return (
              <li
                key={r.skill_id}
                className="flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-lg border border-line px-4 py-3"
              >
                <span className="flex-1 font-medium">{r.name_th}</span>
                <span className="text-[0.85rem] text-faint">ระดับ {r.min_level}</span>
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-[0.75rem] ${src.cls}`}
                >
                  {src.text}
                  {r.appears_in_n_postings > 0 && ` · ${r.appears_in_n_postings} ประกาศ`}
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      <div className="mt-8 flex flex-wrap gap-4">
        <Link
          href="/targets"
          className="rounded-lg border border-line-strong px-4 py-2.5 text-[0.93rem] font-semibold transition hover:border-accent hover:text-accent"
        >
          ← กลับไปเลือกอาชีพ
        </Link>
      </div>

      <DataNote>
        {t.salary_note}
        {t.onet_soc_code && ` · โครงสร้างอาชีพอ้างอิง O*NET ${t.onet_soc_code}`}
      </DataNote>
    </Page>
  );
}
