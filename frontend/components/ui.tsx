"use client";

/**
 * ชุดคอมโพเนนต์กลาง — ทุกหน้าใช้ตัวนี้ ไม่ตั้งสไตล์เองรายหน้า
 *
 * ⚠️ ไฟล์นี้เป็นของ 🅲 ตาม docs/TEAM.md และทุกหน้าต่อกับมัน
 *    เพิ่มคอมโพเนนต์ = ปลอดภัย · เปลี่ยนรูปร่าง prop ที่มีอยู่ = ทำให้หน้าอื่นพัง
 *    บอกในกลุ่มก่อนแก้ของเดิม
 *
 * 🔴 `Blocked` แยก tone ตามชนิดเงื่อนไข ไม่ใช่ตามความรุนแรงที่รู้สึก
 *    เงื่อนไขถาวร (สาขา · ทุน) = stop · เงื่อนไขตามเวลา (ชั้นปี · เกรด) = warn
 *    ผู้ใช้ต้องแยกออกทันทีว่า "ไปไม่ได้" กับ "ยังไม่ถึงเวลา" ต่างกัน
 */

import Link from "next/link";
import type { ReactNode } from "react";

import type { Block, BlockKind } from "@/lib/api";

export function Page({
  eyebrow,
  title,
  lede,
  children,
}: {
  eyebrow?: string;
  title: string;
  lede?: ReactNode;
  children: ReactNode;
}) {
  return (
    <main className="min-h-dvh pb-20">
      <div className="shell pt-10 sm:pt-14">
        <header className="max-w-2xl">
          {eyebrow && (
            <p className="mb-2 text-[0.78rem] font-semibold uppercase tracking-[0.14em] text-faint">
              {eyebrow}
            </p>
          )}
          <h1 className="text-[1.7rem] font-bold leading-[1.3] tracking-tight sm:text-[2rem]">
            {title}
          </h1>
          {lede && <div className="mt-3 text-[1.02rem] text-muted">{lede}</div>}
        </header>
        <div className="mt-8">{children}</div>
      </div>
    </main>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-xl border border-line bg-surface p-5 ${className}`}>
      {children}
    </div>
  );
}

export function Note({
  tone = "neutral",
  title,
  children,
}: {
  tone?: "neutral" | "accent" | "warn" | "stop";
  title?: string;
  children: ReactNode;
}) {
  const map = {
    neutral: "border-line bg-surface text-muted",
    accent: "border-accent/30 bg-accent-soft text-accent",
    warn: "border-warn/30 bg-warn-soft text-warn",
    stop: "border-stop/30 bg-stop-soft text-stop",
  } as const;
  return (
    <div className={`rounded-lg border px-4 py-3 text-[0.9rem] ${map[tone]}`}>
      {title && <p className="mb-1 font-semibold">{title}</p>}
      <div>{children}</div>
    </div>
  );
}

/** เงื่อนไขที่ระบบใช้กรอง — แสดงเสมอพร้อมเหตุผล ไม่ซ่อน */
export function Blocked({ blocks }: { blocks: Block[] }) {
  if (!blocks.length) return null;
  const permanent = new Set<BlockKind>(["field", "obligation"]);
  return (
    <ul className="mt-3 space-y-1.5">
      {blocks.map((b) => {
        const hard = permanent.has(b.kind);
        return (
          <li
            key={`${b.kind}-${b.message}`}
            className={`flex gap-2 text-[0.88rem] ${hard ? "text-stop" : "text-warn"}`}
          >
            <span aria-hidden>{hard ? "✕" : "◷"}</span>
            <span>{b.message}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  full,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "ghost";
  disabled?: boolean;
  full?: boolean;
}) {
  const map = {
    primary:
      "bg-accent text-white hover:brightness-110 disabled:bg-line-strong disabled:text-faint",
    ghost: "border border-line-strong hover:border-accent hover:text-accent",
  } as const;
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`rounded-lg px-5 py-2.5 text-[0.95rem] font-semibold transition ${map[variant]} ${
        full ? "w-full" : ""
      }`}
    >
      {children}
    </button>
  );
}

export function LinkButton({
  href,
  children,
  variant = "primary",
}: {
  href: string;
  children: ReactNode;
  variant?: "primary" | "ghost";
}) {
  const map = {
    primary: "bg-accent text-white hover:brightness-110",
    ghost: "border border-line-strong hover:border-accent hover:text-accent",
  } as const;
  return (
    <Link
      href={href}
      className={`inline-block rounded-lg px-5 py-2.5 text-[0.95rem] font-semibold transition ${map[variant]}`}
    >
      {children}
    </Link>
  );
}

export function Loading({ label = "กำลังโหลดข้อมูล" }: { label?: string }) {
  return (
    <div className="shell py-24 text-center text-faint">
      <div className="mx-auto mb-3 h-6 w-6 animate-spin rounded-full border-2 border-line border-t-accent" />
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="shell py-20">
      <Card className="mx-auto max-w-lg text-center">
        <p className="text-[1.05rem] font-semibold">ยังไปต่อไม่ได้</p>
        <p className="mt-2 text-muted">{message}</p>
        <div className="mt-5 flex justify-center gap-3">
          {onRetry && (
            <Button variant="ghost" onClick={onRetry}>
              ลองอีกครั้ง
            </Button>
          )}
          <LinkButton href="/" variant="ghost">
            กลับหน้าแรก
          </LinkButton>
        </div>
      </Card>
    </div>
  );
}

/** ⚠️ ป้ายบอกว่าอะไรจริงอะไรยังไม่จริง — พูดเองก่อนกรรมการถาม (กติกาข้อ 5) */
export function DataNote({ children }: { children: ReactNode }) {
  return (
    <p className="mt-3 flex items-start gap-1.5 text-[0.82rem] text-faint">
      <span aria-hidden>⚠︎</span>
      <span>{children}</span>
    </p>
  );
}
