"use client";

/**
 * ชิ้นส่วนหน้าจอเฉพาะฝั่งบริษัท
 *
 * 🔒 ตั้งใจไม่แตะ `components/**` กับ `globals.css` — สองอันนั้นเป็นของ 🅲 ตาม docs/TEAM.md
 *    และชุดคอมโพเนนต์กลางยังไม่ถูกสร้าง · ถ้าเขียนไว้ตรงนั้นตอนนี้จะชนกันตอน merge
 *    เมื่อชุดกลางเสร็จแล้ว ย้ายไฟล์นี้ไปใช้ของกลางแทนได้เลย
 */

import type { ReactNode } from "react";

export function Field({
  label,
  required,
  hint,
  children,
}: {
  label: string;
  required?: boolean;
  hint?: ReactNode;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-[0.95rem] font-semibold">
        {label}
        {required && <span className="ml-1 text-red-600 dark:text-red-400">*</span>}
      </span>
      {hint && <span className="mt-0.5 block text-[0.85rem] text-zinc-500">{hint}</span>}
      <div className="mt-1.5">{children}</div>
    </label>
  );
}

export const inputClass =
  "w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-[0.95rem] outline-none " +
  "transition focus:border-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:focus:border-zinc-300";

export function Note({
  tone = "info",
  title,
  children,
}: {
  tone?: "info" | "warn" | "ok";
  title?: string;
  children: ReactNode;
}) {
  const map = {
    info: "border-zinc-300 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900",
    warn: "border-amber-400/50 bg-amber-50 dark:border-amber-500/40 dark:bg-amber-950/30",
    ok: "border-emerald-500/40 bg-emerald-50 dark:border-emerald-500/30 dark:bg-emerald-950/30",
  } as const;
  return (
    <div className={`rounded-lg border px-4 py-3 text-[0.9rem] ${map[tone]}`}>
      {title && <p className="mb-1 font-semibold">{title}</p>}
      <div className="text-zinc-700 dark:text-zinc-300">{children}</div>
    </div>
  );
}

/** รายการข้อผิดพลาดจากฟอร์ม — API ส่งมาทุกข้อพร้อมกัน จึงต้องแสดงทั้งหมด ไม่ใช่ข้อแรก */
export function ErrorList({ errors }: { errors: string[] }) {
  return (
    <div className="rounded-lg border border-red-500/40 bg-red-50 px-4 py-3 dark:bg-red-950/30">
      <p className="font-semibold text-red-700 dark:text-red-300">
ยังส่งไม่ได้ — แก้อีก {errors.length} จุด
      </p>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-[0.9rem] text-red-800 dark:text-red-200">
        {errors.map((e) => (
          <li key={e}>{e}</li>
        ))}
      </ul>
    </div>
  );
}

export function Page({
  title,
  lede,
  children,
}: {
  title: string;
  lede?: ReactNode;
  children: ReactNode;
}) {
  return (
    <main className="mx-auto w-full max-w-3xl px-5 py-10 sm:py-14">
      <h1 className="text-[1.75rem] font-bold leading-snug tracking-tight">{title}</h1>
      {lede && <div className="mt-2 text-zinc-600 dark:text-zinc-400">{lede}</div>}
      <div className="mt-7">{children}</div>
    </main>
  );
}
