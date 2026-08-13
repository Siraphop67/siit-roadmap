"use client";

/**
 * หน้าอนุมัติประกาศ — สำหรับคนในทีมเท่านั้น
 *
 * 🔴 นี่คือด่านเดียวที่กันประกาศงานปลอมไม่ให้ถึงนักศึกษา
 *    หน้าจอจึงบังคับให้เห็นข้อความเต็มก่อน และวางเช็คลิสต์ไว้ข้างปุ่ม
 *    ไม่ทำเป็นตารางที่กดอนุมัติรัว ๆ ได้ เพราะการอนุมัติที่เร็วเกินไปคือการไม่ได้ตรวจ
 *
 * ⚠️ token เก็บใน sessionStorage — หายเมื่อปิดแท็บ และไม่ใช่ระบบบัญชี
 *    พอสำหรับต้นแบบที่มีคนอนุมัติคนเดียว ถ้าจะใช้จริงนอกทีมต้องเปลี่ยนเป็นบัญชีจริง
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { api, type PostingStatus, type ReviewQueue } from "@/lib/api";
import { Note, Page, inputClass } from "../ui";

const TOKEN_KEY = "siit-roadmap-review-token";

export default function ReviewPage() {
  const [token, setToken] = useState("");
  const [queue, setQueue] = useState<ReviewQueue | null>(null);
  const [status, setStatus] = useState<PostingStatus>("pending");
  const [failed, setFailed] = useState("");
  const [busy, setBusy] = useState("");
  const tokenInput = useRef<HTMLInputElement>(null);

  const load = useCallback(async (t: string, s: PostingStatus) => {
    try {
      const q = await api.reviewQueue(t, s);
      setFailed("");
      setQueue(q);
      setToken(t);
      setStatus(s);
      sessionStorage.setItem(TOKEN_KEY, t);
    } catch (e) {
      setQueue(null);
      setFailed(e instanceof Error ? e.message : "เปิดคิวไม่สำเร็จ");
    }
  }, []);

  /**
   * เติม token ที่เคยกรอกไว้กลับเข้าช่อง — รีเฟรชแล้วไม่ต้องพิมพ์ใหม่ · ปิดแท็บแล้วหาย
   *
   * 🔴 effect นี้แตะแค่ DOM ไม่ตั้ง state และไม่เรียก load() เอง
   *    เพราะกฎ react-hooks/set-state-in-effect ห้าม effect ทำให้เกิด render รอบใหม่
   *    (ห้ามถึงฟังก์ชันที่ setState ต่อ แม้จะ await ก่อนก็ตาม)
   *    ผลพลอยได้คือคิวไม่ถูกโหลดเองโดยที่คนตรวจยังไม่ได้ตั้งใจเปิด ซึ่งดีกว่าอยู่แล้ว
   */
  useEffect(() => {
    const saved = sessionStorage.getItem(TOKEN_KEY);
    if (saved && tokenInput.current) tokenInput.current.value = saved;
  }, []);

  const open = () => load(tokenInput.current?.value.trim() ?? "", "pending");

  async function decide(id: string, decision: "approved" | "rejected") {
    const note =
      decision === "rejected"
        ? window.prompt("เหตุผลที่ไม่อนุมัติ (บริษัทจะเห็นข้อความนี้)") ?? ""
        : "";
    setBusy(id);
    try {
      await api.reviewPosting(token, id, { decision, note: note || undefined });
      await load(token, status);
    } catch (e) {
      setFailed(e instanceof Error ? e.message : "บันทึกไม่สำเร็จ");
    } finally {
      setBusy("");
    }
  }

  if (!queue) {
    return (
      <Page title="ตรวจประกาศจากบริษัท" lede="เฉพาะคนในทีม">
        <div className="max-w-md space-y-4">
          {failed && <Note tone="warn">{failed}</Note>}
          <input
            ref={tokenInput}
            className={inputClass}
            type="password"
            onKeyDown={(e) => e.key === "Enter" && open()}
            placeholder="review token"
          />
          <button
            onClick={open}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-[0.95rem] font-semibold text-white dark:bg-zinc-100 dark:text-zinc-900"
          >
            เปิดคิว
          </button>
          <p className="text-[0.85rem] text-zinc-500">
            ตั้งค่า <code>EMPLOYER_REVIEW_TOKEN</code> ใน <code>backend/.env</code>
          </p>
        </div>
      </Page>
    );
  }

  return (
    <Page title="ตรวจประกาศจากบริษัท" lede={`${queue.count} อันในสถานะนี้`}>
      <div className="space-y-6">
        <div className="flex flex-wrap gap-2">
          {(["pending", "approved", "rejected"] as const).map((s) => (
            <button
              key={s}
              onClick={() => load(token, s)}
              className={
                "rounded-full px-3.5 py-1.5 text-[0.88rem] font-semibold transition " +
                (s === status
                  ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  : "border border-zinc-300 dark:border-zinc-700")
              }
            >
              {{ pending: "รอตรวจ", approved: "ผ่านแล้ว", rejected: "ไม่ผ่าน" }[s]}
            </button>
          ))}
        </div>

        {failed && <Note tone="warn">{failed}</Note>}

        {queue.postings.length === 0 && (
          <p className="text-zinc-500">ไม่มีประกาศในสถานะนี้</p>
        )}

        {queue.postings.map((p) => (
          <article
            key={p.posting_id}
            className="rounded-xl border border-zinc-300 p-5 dark:border-zinc-700"
          >
            <h2 className="text-[1.15rem] font-bold">{p.title}</h2>
            <p className="text-zinc-600 dark:text-zinc-400">{p.org}</p>

            <dl className="mt-3 grid gap-2 text-[0.88rem] sm:grid-cols-2">
              <div>
                <dt className="text-zinc-500">ลิงก์ประกาศ</dt>
                <dd>
                  {/* rel="noreferrer" — ไม่ส่ง referrer ไปให้ปลายทางที่เรายังไม่รู้ว่าเชื่อได้ไหม */}
                  <a
                    href={p.url ?? "#"}
                    target="_blank"
                    rel="noreferrer nofollow"
                    className="underline underline-offset-4 break-all"
                  >
                    {p.url}
                  </a>
                </dd>
              </div>
              <div>
                <dt className="text-zinc-500">ผู้กรอก · ติดต่อ</dt>
                <dd className="break-all">
                  {p.submitted_by}
                  {p.contact_email ? ` · ${p.contact_email}` : ""}
                </dd>
              </div>
            </dl>

            {/* 🔴 ต้องอ่านของจริง ไม่ใช่อ่านสรุป — จึงแสดงข้อความเต็มเสมอ */}
            <pre className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-zinc-200 bg-zinc-50 p-4 font-[inherit] text-[0.9rem] leading-relaxed dark:border-zinc-800 dark:bg-zinc-900">
              {p.raw_text}
            </pre>

            {status === "pending" && (
              <>
                <div className="mt-4 rounded-lg border border-amber-400/50 bg-amber-50 px-4 py-3 text-[0.88rem] dark:border-amber-500/40 dark:bg-amber-950/30">
                  <p className="font-semibold">ตรวจให้ครบก่อนกด</p>
                  <ul className="mt-1 list-disc space-y-0.5 pl-5">
                    {queue.checklist.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                </div>

                <div className="mt-4 flex flex-wrap gap-3">
                  <button
                    onClick={() => decide(p.posting_id, "approved")}
                    disabled={busy === p.posting_id}
                    className="rounded-lg bg-emerald-600 px-4 py-2 text-[0.92rem] font-semibold text-white disabled:bg-zinc-400"
                  >
                    อนุมัติ
                  </button>
                  <button
                    onClick={() => decide(p.posting_id, "rejected")}
                    disabled={busy === p.posting_id}
                    className="rounded-lg border border-red-500/50 px-4 py-2 text-[0.92rem] font-semibold text-red-700 disabled:opacity-50 dark:text-red-300"
                  >
                    ไม่อนุมัติ
                  </button>
                </div>
              </>
            )}
          </article>
        ))}

        {status === "approved" && queue.count > 0 && (
          <Note tone="info" title="อนุมัติแล้วยังไม่พอ">
            ต้องรัน <code>make postings</code> แล้ว <code>make backend</code> อีกครั้ง
            ประกาศพวกนี้ถึงจะมีผลกับ requirement ที่นักศึกษาเห็น
          </Note>
        )}
      </div>
    </Page>
  );
}
