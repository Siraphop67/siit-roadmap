"use client";

/**
 * คลังอาชีพ — เลือกเป้าหมายก่อนไปดู roadmap
 *
 * 🔴 หัวใจของหน้านี้ไม่ใช่รายการอาชีพ แต่คือ **สิ่งที่ถูกกรองออกต้องยังเห็นพร้อมเหตุผล**
 *    เว็บหางานทั่วไปตัดตำแหน่งที่คุณสมบัติไม่ถึงออกจากผลการค้นหาเงียบ ๆ
 *    ผู้ใช้จึงไม่มีวันรู้ว่ามีอะไรอยู่ตรงนั้น และไม่มีวันรู้ว่าต้องทำอะไรถึงจะไปถึง
 *
 *    ระบบนี้แยกสองชนิด (ดู DECISIONS D6):
 *      ถาวร  สาขา · เงื่อนไขทุน → ย้ายไปกล่องล่างพร้อมเหตุผล
 *      ตามเวลา ชั้นปี · เกรด    → ยังอยู่ในรายการหลัก แสดงเป็น "สมัครได้เมื่อ…"
 */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Blocked, Card, DataNote, ErrorState, Loading, Note, Page } from "@/components/ui";
import { api, session, type TargetsResponse } from "@/lib/api";

export default function TargetsPage() {
  const router = useRouter();
  const [data, setData] = useState<TargetsResponse | null>(null);
  const [failed, setFailed] = useState("");
  const [picking, setPicking] = useState("");
  const [chosen, setChosen] = useState<{ id: string; title: string } | null>(null);

  /**
   * ส่ง user_id ไปด้วยถ้ามี — API จะได้กรองตามเงื่อนไขทุนและสาขาของคนนี้
   *
   * 🔴 เขียนเป็น .then(setData) ไม่ใช่ await ในฟังก์ชันห่อ
   *    กฎ react-hooks/set-state-in-effect ห้าม effect เรียกฟังก์ชันที่ setState ต่อ
   *    แต่อนุญาตให้ส่ง setState เป็น callback ของสิ่งที่มาจากภายนอก ซึ่งคือกรณีนี้พอดี
   */
  const load = useCallback(() => {
    api
      .targets(session.read())
      .then(setData)
      .catch((e: unknown) =>
        setFailed(e instanceof Error ? e.message : "โหลดคลังอาชีพไม่สำเร็จ"),
      );
  }, []);

  useEffect(load, [load]);

  async function choose(id: string, title: string) {
    const uid = session.read();
    if (!uid) return void router.push("/");
    setPicking(id);
    setFailed("");
    try {
      await api.setGoal({ user_id: uid, target_id: id });
      session.writeTarget(id);
      // 🔴 ยังไม่ push ไป /roadmap เพราะหน้านั้นยังไม่ได้สร้าง — ส่งไปจะเจอ 404
      //    พอหน้า roadmap เสร็จ เปลี่ยนบรรทัดนี้เป็น router.push("/roadmap") ได้เลย
      setChosen({ id, title });
    } catch (e) {
      setFailed(e instanceof Error ? e.message : "เลือกเป้าหมายไม่สำเร็จ");
    } finally {
      setPicking("");
    }
  }

  if (failed && !data) return <ErrorState message={failed} onRetry={load} />;
  if (!data) return <Loading label="กำลังโหลดคลังอาชีพ" />;

  return (
    <Page
      eyebrow="ขั้นที่ 1"
      title="อยากไปถึงงานแบบไหน"
      lede="เลือกสักอันแล้วระบบจะบอกว่าจากจุดที่คุณอยู่ตอนนี้ เหลืออีกกี่ก้าว และก้าวถัดไปคืออะไร"
    >
      {failed && (
        <div className="mb-5">
          <Note tone="warn">{failed}</Note>
        </div>
      )}

      {chosen && (
        <div className="mb-6">
          <Note tone="accent" title={`ตั้งเป้าหมายเป็น “${chosen.title}” แล้ว`}>
            หน้าเส้นทาง (roadmap) กำลังสร้าง — เครื่องยนต์ฝั่งนั้นเสร็จและทดสอบแล้ว
            เหลือหน้าจอ · ระหว่างนี้ดูได้ว่าอาชีพนี้ต้องแสดงความสามารถอะไรบ้างที่{" "}
            <a
              href={`/targets/${encodeURIComponent(chosen.id)}`}
              className="font-semibold underline underline-offset-4"
            >
              หน้ารายละเอียด
            </a>
          </Note>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {data.targets.map((t) => (
          <Card key={t.id} className="flex flex-col">
            {/* 🔴 จอแคบให้ป้ายลงมาอยู่ใต้ชื่อ — วางข้างกันบนมือถือทำให้ชื่อไทยยาว ๆ
                แตกเป็น 4 บรรทัดจนอ่านไม่ออก และกลุ่มเป้าหมายเข้าผ่านมือถือเป็นหลัก */}
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
              <div className="min-w-0">
                <h2 className="text-[1.15rem] font-bold leading-snug">{t.title_th}</h2>
                <p className="text-[0.86rem] text-faint">{t.title_en}</p>
              </div>
              <span className="self-start whitespace-nowrap rounded-full border border-line px-2.5 py-1 text-[0.75rem] text-muted sm:shrink-0">
                {t.sector_label}
              </span>
            </div>

            <p className="mt-3 flex-1 text-[0.95rem] leading-relaxed text-muted">
              {t.summary}
            </p>

            <p className="mt-3 text-[0.85rem] text-faint">
              ต้องแสดงความสามารถ {t.requirement_count} เรื่อง ·{" "}
              {t.posting_count > 0
                ? `อ้างอิงประกาศงานจริง ${t.posting_count} ประกาศ`
                : "ยังไม่ได้อ้างอิงประกาศงานจริง"}
            </p>

            {/* เงื่อนไขตามเวลา — ยังสมัครไม่ได้ตอนนี้ แต่ไม่ได้แปลว่าไปไม่ได้ */}
            <Blocked blocks={t.conditions_at_application} />

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => choose(t.id, t.title_th)}
                disabled={picking !== ""}
                className="rounded-lg bg-accent px-4 py-2.5 text-[0.93rem] font-semibold text-white transition hover:brightness-110 disabled:bg-line-strong disabled:text-faint"
              >
                {picking === t.id ? "กำลังเปิดเส้นทาง…" : "ดูเส้นทางไปอาชีพนี้ →"}
              </button>
              <a
                href={`/targets/${encodeURIComponent(t.id)}`}
                className="text-[0.9rem] font-semibold text-muted underline underline-offset-4 hover:text-accent"
              >
                งานนี้ทำอะไรบ้าง
              </a>
            </div>
          </Card>
        ))}
      </div>

      {/* 🔴 กล่องนี้คือจุดที่ต่างจากเว็บหางานชัดที่สุด — ห้ามซ่อน ห้ามยุบ */}
      {data.filtered_out.length > 0 && (
        <section className="mt-10">
          <h2 className="text-[1.05rem] font-bold">
            อีก {data.filtered_out.length} อาชีพที่เงื่อนไขของคุณไปไม่ถึง
          </h2>
          <p className="mt-1 text-[0.92rem] text-muted">
            เราแสดงไว้พร้อมเหตุผล ไม่ซ่อน — เพราะการไม่รู้ว่ามีอะไรอยู่ตรงนั้น
            แย่กว่าการรู้ว่าไปไม่ได้
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {data.filtered_out.map((f) => (
              <div
                key={f.id}
                className="rounded-xl border border-line border-dashed px-5 py-4"
              >
                <h3 className="font-semibold text-muted">{f.title_th}</h3>
                <Blocked blocks={f.reasons} />
              </div>
            ))}
          </div>
        </section>
      )}

      <DataNote>{data.data_note}</DataNote>
    </Page>
  );
}
