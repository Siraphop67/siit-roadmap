"use client";

/**
 * โปรไฟล์ของฉัน — หน้าที่ตอบว่า "ครั้งก่อนค้างไว้ตรงไหน แล้วไปต่อยังไง"
 *
 * 🔴 ระบบไม่มีการสมัครสมาชิกโดยตั้งใจ (ไม่เก็บชื่อ อีเมล เบอร์โทร)
 *    สิ่งที่ใช้จำผู้ใช้คือ user_id ในเครื่องนี้เท่านั้น · ปิดแท็บไม่หาย แต่ล้างข้อมูล
 *    เบราว์เซอร์หรือย้ายเครื่องแล้วหาย → หน้านี้จึงต้องโชว์รหัสให้เก็บไว้เอง
 *    และรับรหัสกลับเข้ามาได้ · รหัสนี้เท่ากับกุญแจ ใครถือก็เห็นข้อมูล ต้องเขียนบอกตรง ๆ
 *
 * ลำดับขั้นทั้งหมดมาจาก GET /me/resume — หน้านี้ไม่เดาลำดับเอง เพราะลำดับคือกติกา
 * ของระบบ (ยืนยันทักษะก่อนถึงนับ · มีเป้าหมายก่อนถึงมี roadmap)
 */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

import { Icon, InlineNotice, MobileWorkspaceNav, WorkspaceSidebar } from "@/components/student-ui";
import {
  api,
  session,
  type Meta,
  type ProfileBody,
  type ResumeState,
  type RoadmapListItem,
} from "@/lib/api";

/**
 * ลิงก์ไปยังขั้นถัดไป — ปลายทางที่เป็นจุดยึดในหน้านี้เองต้องใช้ <a> ธรรมดา
 *
 * 🔴 Next มองว่า /profile#basics คือ route เดิม เลยไม่เลื่อนจอให้
 *    (วัดตอนกดปุ่มแล้ว: scrollY ยังเป็น 0 ทั้งที่ฟอร์มอยู่ต่ำลงไป 759px)
 *    ปุ่มที่กดแล้วไม่มีอะไรเกิดขึ้นคือทางตัน ต่อให้ทางเทคนิคจะ "ไปถูกที่" แล้วก็ตาม
 */
function StepLink({
  href,
  className,
  children,
}: {
  href: string;
  className?: string;
  children: React.ReactNode;
}) {
  const hash = href.startsWith("/profile#") ? href.slice("/profile".length) : null;
  if (hash) {
    return (
      <a href={hash} className={className}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}

const noopSubscribe = () => () => {};
/** อ่าน localStorage แบบที่ server กับ client วาดตรงกัน (ดูเหตุผลเต็มในหน้า /skills) */
function useSessionUser(): string | null {
  return useSyncExternalStore(
    noopSubscribe,
    () => session.read(),
    () => null,
  );
}

export default function ProfilePage() {
  const router = useRouter();
  const stored = useSessionUser();
  /**
   * 🔴 useSessionUser ไม่ได้ subscribe อะไรจริง (localStorage ไม่ยิง event ให้แท็บตัวเอง)
   *    พอกู้คืนรหัสสำเร็จแล้วเขียนลงเครื่อง หน้านี้จะยังไม่รู้ตัวจนกว่าจะ remount
   *    — เจอตอนทดสอบว่ากดแล้วหน้าไม่เปลี่ยน · เก็บค่าที่เพิ่งกู้ไว้ใน state ตรง ๆ แทน
   */
  const [restored, setRestored] = useState<string | null>(null);
  const uid = restored ?? stored;
  const [state, setState] = useState<ResumeState | null>(null);
  const [paths, setPaths] = useState<RoadmapListItem[]>([]);
  const [error, setError] = useState("");
  const [code, setCode] = useState("");
  const [restoring, setRestoring] = useState(false);
  const [copied, setCopied] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [reload, setReload] = useState(0);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [form, setForm] = useState<ProfileBody | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let alive = true;
    api.meta().then((m) => alive && setMeta(m)).catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!uid) return;
    let alive = true;
    api
      .getProfile(uid)
      .then((p) => {
        if (!alive) return;
        setForm({
          user_id: uid,
          field: p.field ?? null,
          education_level: p.education_level ?? null,
          year: p.year ?? null,
          gpa: p.gpa ?? null,
          hours_per_week: p.hours_per_week ?? null,
          budget_baht: p.budget_baht ?? null,
          obligation_id: p.obligation_id ?? null,
        });
      })
      .catch(() => alive && setForm({ user_id: uid }));
    return () => {
      alive = false;
    };
  }, [uid]);

  const saveProfile = useCallback(async () => {
    if (!form) return;
    setSaving(true);
    setSaved(false);
    try {
      // ไม่ส่ง self_reported_skills = ไม่แตะทักษะที่ผู้ใช้เคยกรอกไว้ (สัญญาของ API)
      await api.saveProfile(form);
      setSaved(true);
      setReload((n) => n + 1);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "ไม่สามารถบันทึกข้อมูลได้");
    } finally {
      setSaving(false);
    }
  }, [form]);

  const set = <K extends keyof ProfileBody>(key: K, value: ProfileBody[K]) =>
    setForm((f) => (f ? { ...f, [key]: value } : f));

  /** ช่องตัวเลขที่ว่างได้ — "" ต้องกลายเป็น null ไม่ใช่ 0 เพราะ 0 แปลว่า "ตอบว่าไม่มีเลย" */
  const num = (v: string) => (v.trim() === "" ? null : Number(v));

  useEffect(() => {
    if (!uid) return;
    let alive = true;
    api
      .resume(uid)
      .then((data) => {
        if (!alive) return;
        setState(data);
        setError("");
      })
      .catch((e: unknown) => {
        if (alive) setError(e instanceof Error ? e.message : "ไม่สามารถโหลดข้อมูลของคุณได้");
      });
    api
      .roadmaps(uid)
      .then((d) => alive && setPaths(d.roadmaps))
      .catch(() => alive && setPaths([]));
    return () => {
      alive = false;
    };
  }, [uid, reload]);

  /** ตรวจรหัสกับ API ก่อนค่อยเขียนลงเครื่อง — รหัสผิดต้องไม่ทำให้ session เดิมหาย */
  const restore = useCallback(async () => {
    const value = code.trim();
    if (!value) return;
    setRestoring(true);
    setError("");
    try {
      await api.resume(value);
      session.write(value);
      setCode("");
      setRestored(value);
      setReload((n) => n + 1);
    } catch {
      setError("ไม่พบรหัสนี้ในระบบ กรุณาตรวจสอบว่าคัดลอกมาครบถ้วนทุกตัวอักษรแล้วหรือไม่");
    } finally {
      setRestoring(false);
    }
  }, [code]);

  const wipe = useCallback(async () => {
    if (!uid) return;
    await api.deleteMe(uid);
    session.clear();
    setRestored(null);
    router.push("/");
  }, [uid, router]);

  const done = state ? state.steps.filter((s) => s.done).length : 0;

  return (
    <div className="flex min-h-screen w-full bg-surface-bg pb-20 lg:pb-0">
      <WorkspaceSidebar active="profile" />
      <main className="flex-1 min-w-0 px-margin-mobile md:px-gutter py-stack-lg max-w-3xl mx-auto w-full">
        <h1 className="text-headline-lg font-headline-lg font-bold text-text-main">
          ข้อมูลส่วนตัว
        </h1>
        <p className="text-body-md text-text-subtle mt-1">
          ระบบบันทึกความคืบหน้าของคุณไว้แล้ว เมื่อกลับมาใช้งานอีกครั้งสามารถดำเนินการต่อจากจุดเดิมได้
        </p>

        {error && (
          <div className="mt-stack-md">
            <InlineNotice tone="error">{error}</InlineNotice>
          </div>
        )}

        {/* ยังไม่มี session ในเครื่องนี้ — ให้ทางเลือกสองทาง ไม่ใช่หน้าเปล่า */}
        {!uid && (
          <section className="mt-stack-lg p-gutter border border-border-low rounded-xl bg-surface-muted">
            <h2 className="font-semibold text-text-main mb-stack-sm">
              อุปกรณ์นี้ยังไม่มีข้อมูลของคุณ
            </h2>
            <p className="text-sm text-text-subtle mb-stack-md">
              หากเคยใช้งานจากอุปกรณ์อื่นและเก็บรหัสไว้ กรุณาวางรหัสที่นี่เพื่อเรียกข้อมูลกลับคืน
            </p>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="วางรหัสของคุณที่นี่"
                className="flex-1 px-3 py-2 text-sm bg-surface-bg border border-border-low rounded-lg"
              />
              <button
                onClick={restore}
                disabled={!code.trim() || restoring}
                className="px-4 py-2 bg-primary text-on-primary rounded-lg disabled:opacity-40"
              >
                {restoring ? "กำลังตรวจสอบรหัส" : "เรียกข้อมูลกลับคืน"}
              </button>
            </div>
            <Link href="/" className="inline-block mt-stack-md underline text-sm text-text-subtle">
              หรือเริ่มใหม่จากหน้าแรก
            </Link>
          </section>
        )}

        {uid && state && (
          <>
            {/* ★ สิ่งแรกที่ต้องเห็น — ไปต่อตรงไหน */}
            {state.next ? (
              <section className="mt-stack-lg p-gutter border border-primary rounded-xl bg-primary-fixed/40">
                <p className="text-label-sm font-label-sm uppercase tracking-wider text-primary">
                  ดำเนินการค้างไว้ที่ขั้นนี้
                </p>
                <h2 className="text-headline-md font-headline-md font-semibold text-text-main mt-1">
                  {state.next.title}
                </h2>
                <p className="text-sm text-text-subtle mt-1">{state.next.detail}</p>
                <StepLink
                  href={state.next.href}
                  className="inline-flex items-center gap-2 mt-stack-md px-4 py-2.5 bg-primary text-on-primary rounded-lg"
                >
                  ดำเนินการต่อจากขั้นนี้ <Icon className="text-base">arrow_forward</Icon>
                </StepLink>
              </section>
            ) : (
              <section className="mt-stack-lg p-gutter border border-border-low rounded-xl bg-surface-muted">
                <h2 className="font-semibold text-text-main">ดำเนินการครบทุกขั้นแล้ว</h2>
                <p className="text-sm text-text-subtle mt-1">
                  คุณสามารถส่งผลงานเพิ่มเติมหรือเลือกอาชีพอื่นได้ตลอดเวลา ระบบจะคำนวณเส้นทางใหม่ให้โดยอัตโนมัติ
                </p>
              </section>
            )}

            <section className="mt-stack-lg">
              <h2 className="font-semibold text-text-main mb-stack-md">
                ขั้นตอนของคุณ ({done}/{state.steps.length})
              </h2>
              <ol className="space-y-2">
                {state.steps.map((step) => (
                  <li key={step.id}>
                    <StepLink
                      href={step.href}
                      className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${
                        step.id === state.next?.id
                          ? "border-primary bg-surface-bg"
                          : "border-border-low bg-surface-bg hover:bg-surface-muted"
                      }`}
                    >
                      <Icon className={step.done ? "text-primary" : "text-text-subtle"}>
                        {step.done ? "check_circle" : "radio_button_unchecked"}
                      </Icon>
                      <span className="min-w-0">
                        <span className="block text-sm font-semibold text-text-main">
                          {step.title}
                        </span>
                        <span className="block text-xs text-text-subtle">{step.detail}</span>
                      </span>
                    </StepLink>
                  </li>
                ))}
              </ol>
            </section>

            {/* ข้อมูลพื้นฐาน — เครื่องยนต์ใช้ค่าพวกนี้กรองอาชีพและตัวเลือกใน roadmap จริง */}
            <section
              id="basics"
              className="mt-stack-lg p-gutter border border-border-low rounded-xl scroll-mt-4"
            >
              <h2 className="font-semibold text-text-main mb-stack-sm">ข้อมูลพื้นฐาน</h2>
              <p className="text-sm text-text-subtle mb-stack-md">
                ใช้สำหรับคัดกรองอาชีพที่ไม่สามารถสมัครได้ออก และคัดเลือกช่องทางการเรียนรู้ให้เหมาะสมกับเวลา
                และงบประมาณของคุณ กรุณากรอกเท่าที่ต้องการเปิดเผย โดยสามารถเว้นว่างได้
              </p>
              {form && (
                <div className="grid sm:grid-cols-2 gap-3">
                  <label className="text-sm">
                    <span className="block text-text-subtle mb-1">สาขา</span>
                    <select
                      value={form.field ?? ""}
                      onChange={(e) => set("field", e.target.value || null)}
                      className="w-full px-3 py-2 bg-surface-muted border border-border-low rounded-lg"
                    >
                      <option value="">ยังไม่ระบุ</option>
                      {meta?.fields.map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.name_th}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="text-sm">
                    <span className="block text-text-subtle mb-1">ชั้นปี</span>
                    <select
                      value={form.education_level ?? ""}
                      onChange={(e) => set("education_level", e.target.value || null)}
                      className="w-full px-3 py-2 bg-surface-muted border border-border-low rounded-lg"
                    >
                      <option value="">ยังไม่ระบุ</option>
                      {meta?.education_levels.map((level) => (
                        <option key={level} value={level}>
                          {level}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="text-sm">
                    <span className="block text-text-subtle mb-1">ปีที่กำลังเรียน (1–8)</span>
                    <input
                      type="number"
                      min={1}
                      max={8}
                      value={form.year ?? ""}
                      onChange={(e) => set("year", num(e.target.value))}
                      className="w-full px-3 py-2 bg-surface-muted border border-border-low rounded-lg"
                    />
                  </label>
                  <label className="text-sm">
                    <span className="block text-text-subtle mb-1">GPA</span>
                    <input
                      type="number"
                      step="0.01"
                      min={0}
                      max={4}
                      value={form.gpa ?? ""}
                      onChange={(e) => set("gpa", num(e.target.value))}
                      className="w-full px-3 py-2 bg-surface-muted border border-border-low rounded-lg"
                    />
                  </label>
                  <label className="text-sm">
                    <span className="block text-text-subtle mb-1">เวลาว่างต่อสัปดาห์ (ชม.)</span>
                    <input
                      type="number"
                      min={1}
                      max={80}
                      value={form.hours_per_week ?? ""}
                      onChange={(e) => set("hours_per_week", num(e.target.value))}
                      className="w-full px-3 py-2 bg-surface-muted border border-border-low rounded-lg"
                    />
                  </label>
                  <label className="text-sm">
                    <span className="block text-text-subtle mb-1">งบประมาณที่ใช้ได้ (บาท)</span>
                    <input
                      type="number"
                      min={0}
                      value={form.budget_baht ?? ""}
                      onChange={(e) => set("budget_baht", num(e.target.value))}
                      className="w-full px-3 py-2 bg-surface-muted border border-border-low rounded-lg"
                    />
                  </label>
                  <label className="text-sm sm:col-span-2">
                    <span className="block text-text-subtle mb-1">เงื่อนไขทุน</span>
                    <select
                      value={form.obligation_id ?? ""}
                      onChange={(e) => set("obligation_id", e.target.value || null)}
                      className="w-full px-3 py-2 bg-surface-muted border border-border-low rounded-lg"
                    >
                      <option value="">ยังไม่ระบุ</option>
                      {meta?.obligations.map((o) => (
                        <option key={o.id} value={o.id}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              )}
              <div className="mt-stack-md flex items-center gap-3">
                <button
                  onClick={saveProfile}
                  disabled={!form || saving}
                  className="px-4 py-2 bg-primary text-on-primary rounded-lg disabled:opacity-40"
                >
                  {saving ? "กำลังบันทึก" : "บันทึก"}
                </button>
                {saved && <span className="text-sm text-primary">บันทึกแล้ว</span>}
              </div>
            </section>

            <section className="mt-stack-lg grid grid-cols-2 sm:grid-cols-3 gap-3">
              {/* 🔒 กติกาข้อ 1 — สองช่องนี้แยกกัน ห้ามรวมเป็น "ทักษะทั้งหมด" */}
              {[
                ["ทักษะจาก CV (ยืนยันแล้ว)", state.summary.skills_from_cv],
                ["ทักษะที่ประเมินด้วยตนเอง", state.summary.skills_self_reported],
                ["รอการตรวจสอบ", state.summary.pending_skills],
                ["ผลงานที่ส่งแล้ว", state.summary.documents],
                ["จำนวนข้อที่ตอบในแบบประเมิน", state.summary.quiz_answered],
                ["เส้นทางที่สร้างไว้", state.summary.roadmaps],
              ].map(([label, value]) => (
                <div key={label} className="p-3 border border-border-low rounded-lg bg-surface-muted">
                  <div className="text-headline-md font-headline-md font-bold text-text-main">
                    {value}
                  </div>
                  <div className="text-xs text-text-subtle">{label}</div>
                </div>
              ))}
            </section>

            {paths.length > 0 && (
              <section className="mt-stack-lg">
                <h2 className="font-semibold text-text-main mb-stack-md">เส้นทางที่เคยเปิดดู</h2>
                <ul className="space-y-2">
                  {paths.map((path) => (
                    <li key={path.target_id}>
                      <Link
                        href="/roadmap"
                        onClick={() => session.writeTarget(path.target_id)}
                        className="flex items-center justify-between gap-3 p-3 border border-border-low rounded-lg hover:bg-surface-muted"
                      >
                        <span className="min-w-0">
                          <span className="block text-sm font-semibold text-text-main">
                            {path.title_th}
                            {path.is_primary_goal && (
                              <span className="ml-2 text-[10px] bg-primary-fixed text-primary px-1.5 py-0.5 rounded">
                                เป้าหมายปัจจุบัน
                              </span>
                            )}
                          </span>
                          <span className="block text-xs text-text-subtle">
                            {path.steps_done}/{path.total_steps} ขั้น
                            {path.next_step && ` · ขั้นถัดไป: ${path.next_step.name_th}`}
                          </span>
                        </span>
                        <Icon className="text-text-subtle">arrow_forward</Icon>
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* รหัสสำหรับกลับมาใช้ต่อ — ต้องบอกตรง ๆ ว่ามันคือกุญแจ */}
            <section className="mt-stack-lg p-gutter border border-border-low rounded-xl bg-surface-muted">
              <h2 className="font-semibold text-text-main mb-stack-sm">
                รหัสสำหรับกลับมาใช้ต่อ
              </h2>
              <p className="text-sm text-text-subtle mb-stack-md">{state.note}</p>
              <div className="flex flex-col sm:flex-row gap-2">
                <code className="flex-1 px-3 py-2 bg-surface-bg border border-border-low rounded-lg text-xs break-all">
                  {state.user_id}
                </code>
                <button
                  onClick={() => {
                    navigator.clipboard?.writeText(state.user_id);
                    setCopied(true);
                  }}
                  className="px-4 py-2 border border-border-low rounded-lg text-sm hover:bg-surface-bg"
                >
                  {copied ? "คัดลอกแล้ว" : "คัดลอกรหัส"}
                </button>
              </div>
              <p className="text-xs text-tertiary mt-stack-sm">
                ⚠️ ผู้ที่มีรหัสนี้จะสามารถเข้าถึงข้อมูลของคุณได้ทั้งหมด รวมถึง CV ที่ส่งเข้าระบบ
                กรุณาเก็บรักษาไว้เช่นเดียวกับรหัสผ่าน และไม่เผยแพร่ในที่สาธารณะ
              </p>
            </section>

            {/* PDPA — ลบได้จริง และต้องกดยืนยันก่อน */}
            <section className="mt-stack-lg mb-stack-lg p-gutter border border-error-container rounded-xl">
              <h2 className="font-semibold text-text-main mb-stack-sm">ลบข้อมูลทั้งหมด</h2>
              <p className="text-sm text-text-subtle mb-stack-md">
                ระบบจะลบ CV ทักษะที่ยืนยันแล้ว คำตอบแบบประเมิน และเส้นทางทั้งหมดออกจากเซิร์ฟเวอร์
                อย่างถาวร และไม่สามารถกู้คืนได้
              </p>
              {!confirmDelete ? (
                <button
                  onClick={() => setConfirmDelete(true)}
                  className="px-4 py-2 border border-error text-error rounded-lg text-sm"
                >
                  ลบข้อมูลของฉัน
                </button>
              ) : (
                <div className="flex flex-wrap gap-2 items-center">
                  <span className="text-sm text-text-main">คุณแน่ใจหรือไม่ เมื่อลบแล้วจะไม่สามารถกู้คืนได้</span>
                  <button
                    onClick={wipe}
                    className="px-4 py-2 bg-error text-on-error rounded-lg text-sm"
                  >
                    ยืนยันลบ
                  </button>
                  <button
                    onClick={() => setConfirmDelete(false)}
                    className="px-4 py-2 border border-border-low rounded-lg text-sm"
                  >
                    ยกเลิก
                  </button>
                </div>
              )}
            </section>
          </>
        )}

        {uid && !state && !error && <p className="mt-stack-lg text-text-subtle">กำลังโหลดข้อมูล</p>}
      </main>
      <MobileWorkspaceNav active="profile" />
    </div>
  );
}
