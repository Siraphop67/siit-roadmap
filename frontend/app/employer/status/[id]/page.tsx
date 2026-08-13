"use client";

/**
 * บริษัทเช็คว่าประกาศของตัวเองผ่านหรือยัง
 *
 * `posting_id` ที่ได้ตอนส่งคือกุญแจ — เดาไม่ได้ และไม่มีหน้าไหนที่ list ประกาศทั้งหมด
 * ให้คนนอกดู · จึงไม่ต้องมีระบบบัญชีสำหรับบริษัท
 */

import Link from "next/link";
import { use, useEffect, useState } from "react";

import { api, type PostingStatusView } from "@/lib/api";
import { Note, Page } from "../../ui";

const TONE = {
  pending: "warn",
  approved: "ok",
  rejected: "info",
} as const;

export default function PostingStatusPage(props: PageProps<"/employer/status/[id]">) {
  const { id } = use(props.params);
  const [row, setRow] = useState<PostingStatusView | null>(null);
  const [failed, setFailed] = useState("");

  useEffect(() => {
    api
      .postingStatus(id)
      .then(setRow)
      .catch((e) => setFailed(e instanceof Error ? e.message : "โหลดไม่สำเร็จ"));
  }, [id]);

  if (failed) {
    return (
      <Page title="เช็คสถานะประกาศ">
        <Note tone="warn" title="ไม่พบประกาศนี้">
          {failed} — ตรวจว่ารหัสที่ได้ตอนส่งถูกต้องไหม
        </Note>
      </Page>
    );
  }

  if (!row) {
    return (
      <Page title="เช็คสถานะประกาศ">
        <p className="text-zinc-500">กำลังโหลด…</p>
      </Page>
    );
  }

  return (
    <Page title={row.title} lede={row.org}>
      <div className="space-y-5">
        <Note tone={TONE[row.status]} title={row.status_th}>
          {row.status === "pending" &&
            "ทีมจะอ่านประกาศทั้งฉบับก่อนอนุมัติ เพราะเรายังไม่มีระบบยืนยันตัวตนองค์กร " +
              "และไม่อยากให้ประกาศปลอมหลุดถึงนักศึกษา"}
          {/* 🔒 ไม่พูดว่า "ถูกนับแล้ว" — ต้องรันท่อขั้นที่ 2 ก่อนถึงจะจริง (กติกาข้อ 5) */}
          {row.status === "approved" &&
            "ทีมตรวจแล้วและอนุมัติ — ประกาศนี้จะถูกนับรวมในข้อมูลที่ระบบใช้บอกนักศึกษา " +
              "ว่าต้องเตรียมอะไรบ้าง ในการอัปเดตข้อมูลรอบถัดไป"}
          {row.status === "rejected" && (row.review_note || "ทีมไม่ได้อนุมัติประกาศนี้")}
        </Note>

        <dl className="grid gap-3 text-[0.93rem] sm:grid-cols-2">
          <div>
            <dt className="text-zinc-500">ส่งเมื่อ</dt>
            <dd className="font-semibold">{row.submitted_at.slice(0, 10)}</dd>
          </div>
          {row.reviewed_at && (
            <div>
              <dt className="text-zinc-500">ตรวจเมื่อ</dt>
              <dd className="font-semibold">{row.reviewed_at.slice(0, 10)}</dd>
            </div>
          )}
          <div className="sm:col-span-2">
            <dt className="text-zinc-500">รหัสประกาศ</dt>
            <dd className="font-mono break-all">{row.posting_id}</dd>
          </div>
        </dl>

        {row.review_note && row.status !== "rejected" && (
          <Note tone="info" title="หมายเหตุจากทีม">
            {row.review_note}
          </Note>
        )}

        <Link
          href="/employer"
          className="inline-block text-[0.95rem] font-semibold underline underline-offset-4"
        >
          ← ลงประกาศอีกอัน
        </Link>
      </div>
    </Page>
  );
}
