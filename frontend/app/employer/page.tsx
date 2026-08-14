"use client";

/**
 * หน้าฟอร์มให้บริษัทลงประกาศรับสมัคร
 *
 * 🔒 สองอย่างที่ต้องบอกบริษัทก่อนเขากรอก ไม่ใช่หลังกดส่ง
 *    ① ประกาศต้องผ่านการตรวจจากทีมก่อนขึ้นให้นักศึกษาเห็น
 *    ② ระบบนี้เป็นทางเดียว — บริษัทจะไม่เห็นข้อมูลนักศึกษา
 *    ข้อความทั้งสองมาจาก /api/employer/meta ไม่ได้เขียนตายตัวไว้ที่นี่
 *    เพราะถ้าฝั่ง backend เปลี่ยนกติกา หน้านี้ต้องเปลี่ยนตามเอง
 */

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  api,
  submissionErrors,
  type EmployerMeta,
  type EmploymentType,
  type PostingSubmission,
  type SubmissionResult,
} from "@/lib/api";
import { ErrorList, Field, Note, Page, inputClass } from "./ui";

const EMPTY: PostingSubmission = {
  org: "",
  title: "",
  url: "",
  sector: "private",
  employment_type: "new_grad",
  raw_text: "",
  submitted_by: "",
  target_id: null,
  location: null,
  salary_text: null,
  closes_at: null,
  contact_email: null,
};

export default function EmployerFormPage() {
  const [meta, setMeta] = useState<EmployerMeta | null>(null);
  const [form, setForm] = useState<PostingSubmission>(EMPTY);
  const [errors, setErrors] = useState<string[]>([]);
  const [failed, setFailed] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<SubmissionResult | null>(null);

  useEffect(() => {
    api.employerMeta().then(setMeta).catch((e) => setFailed(String(e.message)));
  }, []);

  function set<K extends keyof PostingSubmission>(key: K, value: PostingSubmission[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function submit() {
    setBusy(true);
    setErrors([]);
    setFailed("");
    try {
      // ช่องที่ว่างส่งเป็น null ไม่ใช่สตริงว่าง — ฝั่ง API แยกสองอย่างนี้ออกจากกัน
      const clean = Object.fromEntries(
        Object.entries(form).map(([k, v]) => [k, v === "" ? null : v]),
      ) as unknown as PostingSubmission;
      setDone(await api.submitPosting(clean));
    } catch (e) {
      // API ส่งข้อผิดพลาดกลับทุกข้อพร้อมกัน แสดงทั้งหมดเพื่อให้แก้รอบเดียว
      const detail = submissionErrors(e);
      if (detail) setErrors(detail.errors);
      else setFailed(e instanceof Error ? e.message : "ไม่สามารถส่งประกาศได้");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <Page title="ได้รับประกาศเรียบร้อยแล้ว">
        <div className="space-y-5">
          <Note tone="ok" title="ประกาศเข้าคิวรอตรวจแล้ว">
            {done.message}
          </Note>

          <div className="rounded-lg border border-zinc-300 px-4 py-3.5 dark:border-zinc-700">
            <p className="text-[0.8rem] font-semibold uppercase tracking-wider text-zinc-500">
              กรุณาเก็บรหัสนี้ไว้สำหรับตรวจสอบสถานะ
            </p>
            <p className="mt-1 font-mono text-[1.05rem] font-bold break-all">
              {done.posting_id}
            </p>
            <Link
              href={`/employer/status/${done.posting_id}`}
              className="mt-2 inline-block text-[0.92rem] font-semibold underline underline-offset-4"
            >
              เปิดหน้าตรวจสอบสถานะ →
            </Link>
          </div>

          {done.warnings.length > 0 && (
            <Note tone="warn" title="ข้อสังเกต — ส่งได้แล้ว แต่เพิ่มอีกนิดจะดีกว่า">
              <ul className="list-disc space-y-1 pl-5">
                {done.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </Note>
          )}

          <button
            onClick={() => {
              setDone(null);
              setForm(EMPTY);
            }}
            className="rounded-lg border border-zinc-400 px-4 py-2 text-[0.95rem] font-semibold dark:border-zinc-600"
          >
            ลงประกาศฉบับใหม่
          </button>
        </div>
      </Page>
    );
  }

  if (failed && !meta) {
    return (
      <Page title="ลงประกาศรับสมัคร">
        <Note tone="warn" title="ไม่สามารถโหลดหน้านี้ได้">
          {failed}
        </Note>
      </Page>
    );
  }

  if (!meta) {
    return (
      <Page title="ลงประกาศรับสมัคร">
        <p className="text-zinc-500">กำลังโหลดข้อมูล</p>
      </Page>
    );
  }

  const ready =
    form.org.trim() && form.title.trim() && form.url.trim() &&
    form.raw_text.trim() && form.submitted_by.trim();

  return (
    <Page
      title="ลงประกาศรับสมัคร"
      lede="สำหรับองค์กรที่อยากให้นักศึกษา SIIT เห็นตำแหน่งที่เปิดรับ"
    >
      <div className="space-y-6">
        {/* 🔒 บอกกติกาก่อนเขาเสียเวลากรอก ไม่ใช่หลังกดส่ง */}
        <Note tone="info" title="โปรดอ่านก่อนกรอกข้อมูล">
          <ul className="list-disc space-y-1 pl-5">
            <li>{meta.notes.review}</li>
            <li>{meta.notes.privacy}</li>
          </ul>
        </Note>

        {errors.length > 0 && <ErrorList errors={errors} />}
        {failed && <Note tone="warn">{failed}</Note>}

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="ชื่อองค์กร" required>
            <input
              className={inputClass}
              value={form.org}
              onChange={(e) => set("org", e.target.value)}
              placeholder="บริษัท ตัวอย่าง จำกัด (มหาชน)"
            />
          </Field>

          <Field label="ชื่อตำแหน่ง" required>
            <input
              className={inputClass}
              value={form.title}
              onChange={(e) => set("title", e.target.value)}
              placeholder="Process Engineer (New Graduate)"
            />
          </Field>
        </div>

        <Field label="ลิงก์ประกาศ" required hint="หน้าเว็บที่นักศึกษาจะใช้สมัคร">
          <input
            className={inputClass}
            value={form.url}
            onChange={(e) => set("url", e.target.value)}
            placeholder="https://…"
          />
        </Field>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="ประเภทองค์กร" required>
            <select
              className={inputClass}
              value={form.sector}
              onChange={(e) => set("sector", e.target.value)}
            >
              {Object.entries(meta.sectors).map(([id, label]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
          </Field>

          <Field label="ประเภทการจ้าง" required>
            <select
              className={inputClass}
              value={form.employment_type}
              onChange={(e) => set("employment_type", e.target.value as EmploymentType)}
            >
              {Object.entries(meta.employment_types).map(([id, label]) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <Field
          label="ข้อความประกาศ"
          required
          hint={meta.notes.raw_text}
        >
          <textarea
            className={`${inputClass} min-h-64 font-[inherit] leading-relaxed`}
            value={form.raw_text}
            onChange={(e) => set("raw_text", e.target.value)}
            placeholder={
              "หน้าที่ความรับผิดชอบ\n- …\n\nคุณสมบัติผู้สมัคร\n- …"
            }
          />
          <p className="mt-1 text-[0.82rem] text-zinc-500">
            {form.raw_text.length} ตัวอักษร · หากระบุคุณสมบัติและหน้าที่ความรับผิดชอบครบถ้วน
            ระบบจะแจ้งนักศึกษาได้แม่นยำยิ่งขึ้นว่าต้องเตรียมความพร้อมด้านใด
          </p>
        </Field>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field label="อีเมลติดต่อ" hint="กรอกในช่องนี้ ไม่ใช่ในเนื้อความประกาศ">
            <input
              className={inputClass}
              value={form.contact_email ?? ""}
              onChange={(e) => set("contact_email", e.target.value)}
              placeholder="jobs@example.com"
            />
          </Field>

          <Field label="ผู้กรอกแบบฟอร์ม" required hint="สำหรับติดต่อกลับเมื่อข้อมูลไม่ชัดเจน">
            <input
              className={inputClass}
              value={form.submitted_by}
              onChange={(e) => set("submitted_by", e.target.value)}
              placeholder="ชื่อ หรือชื่อฝ่าย"
            />
          </Field>
        </div>

        <details className="rounded-lg border border-zinc-300 px-4 py-3 dark:border-zinc-700">
          <summary className="cursor-pointer text-[0.95rem] font-semibold">
            ข้อมูลเพิ่มเติม ช่วยให้การจับคู่กับนักศึกษาแม่นยำยิ่งขึ้น
          </summary>
          <div className="mt-4 grid gap-5 sm:grid-cols-2">
            <Field label="อาชีพที่ตรงที่สุด" hint="หากไม่แน่ใจสามารถข้ามได้">
              <select
                className={inputClass}
                value={form.target_id ?? ""}
                onChange={(e) => set("target_id", e.target.value || null)}
              >
                <option value="">— ยังไม่ระบุ —</option>
                {meta.targets.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.title_th}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="สถานที่ทำงาน">
              <input
                className={inputClass}
                value={form.location ?? ""}
                onChange={(e) => set("location", e.target.value)}
                placeholder="ระยอง"
              />
            </Field>

            <Field label="เงินเดือน" hint="ตามที่ประกาศระบุ">
              <input
                className={inputClass}
                value={form.salary_text ?? ""}
                onChange={(e) => set("salary_text", e.target.value)}
                placeholder="25,000–30,000 บาท/เดือน"
              />
            </Field>

            <Field label="ปิดรับสมัคร">
              <input
                type="date"
                className={inputClass}
                value={form.closes_at ?? ""}
                onChange={(e) => set("closes_at", e.target.value)}
              />
            </Field>
          </div>
        </details>

        <div className="flex flex-wrap items-center gap-4 border-t border-zinc-200 pt-5 dark:border-zinc-800">
          <button
            onClick={submit}
            disabled={!ready || busy}
            className="rounded-lg bg-zinc-900 px-5 py-2.5 text-[0.95rem] font-semibold text-white transition disabled:bg-zinc-400 dark:bg-zinc-100 dark:text-zinc-900 dark:disabled:bg-zinc-700"
          >
            {busy ? "กำลังส่งข้อมูล" : "ส่งประกาศเพื่อรอการตรวจสอบ"}
          </button>
          {!ready && (
            <span className="text-[0.9rem] text-zinc-500">
              กรอกช่องที่มี * ให้ครบก่อน
            </span>
          )}
        </div>
      </div>
    </Page>
  );
}
