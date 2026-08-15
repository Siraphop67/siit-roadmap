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
      .catch((e) => setFailed(e instanceof Error ? e.message : "ไม่สามารถโหลดข้อมูลประกาศได้"));
  }, [id]);

  if (failed) {
    return (
      <Page title="ตรวจสอบสถานะประกาศ">
        <Note tone="warn" title="ไม่พบประกาศนี้">
          {failed} กรุณาตรวจสอบว่ารหัสที่ได้รับเมื่อส่งประกาศถูกต้องหรือไม่
        </Note>
      </Page>
    );
  }

  if (!row) {
    return (
      <Page title="ตรวจสอบสถานะประกาศ">
        <p className="text-zinc-500">กำลังโหลดข้อมูล</p>
      </Page>
    );
  }

  return (
    <Page title={row.title} lede={row.org}>
      <div className="space-y-5">
        <Note tone={TONE[row.status]} title={row.status_th}>
          {row.status === "pending" &&
            "ทีมงานจะอ่านประกาศทั้งฉบับก่อนอนุมัติ เพราะเรายังไม่มีระบบยืนยันตัวตนองค์กร " +
              "และไม่อยากให้ประกาศที่ไม่จริงหลุดไปถึงนักศึกษา"}
          {/* 🔒 ไม่พูดว่า "ถูกนับแล้ว" — ต้องรันท่อขั้นที่ 2 ก่อนถึงจะจริง (กติกาข้อ 5) */}
          {row.status === "approved" &&
            "ทีมงานตรวจและอนุมัติแล้ว ประกาศฉบับนี้จะถูกนับรวมในข้อมูลที่เราใช้บอกนักศึกษา " +
              "ว่าต้องเตรียมอะไรบ้าง ในการอัปเดตข้อมูลรอบถัดไป"}
          {row.status === "rejected" && (row.review_note || "ทีมงานไม่อนุมัติประกาศฉบับนี้")}
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
          <Note tone="info" title="หมายเหตุจากทีมงาน">
            {row.review_note}
          </Note>
        )}

        <Link
          href="/employer"
          className="inline-block text-[0.95rem] font-semibold underline underline-offset-4"
        >
          ← ลงประกาศฉบับใหม่
        </Link>
      </div>
    </Page>
  );
}
