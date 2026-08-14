"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, session, type ResourceDetail } from "@/lib/api";
import { Icon, InlineNotice, MobileWorkspaceNav, WorkspaceSidebar } from "@/components/student-ui";

const kindIcon: Record<string, string> = {
  siit_course: "school", online_course: "workspace_premium", certificate: "verified",
  project: "construction", activity: "local_activity", internship: "work", competition: "emoji_events",
};

const statusLabel: Record<string, string> = {
  current: "เริ่มได้ทันที", in_progress: "กำลังพัฒนา", locked: "รอทักษะที่ต้องมีก่อน", flexible: "เลือกทำได้ตามสะดวก",
};

export default function CoursePage() {
  const router = useRouter();
  const params = useParams<{ resourceId: string }>();
  const [course, setCourse] = useState<ResourceDetail | null>(null);
  const [error, setError] = useState("");
  const resourceId = Array.isArray(params.resourceId) ? params.resourceId[0] : params.resourceId;

  useEffect(() => {
    if (!resourceId) return;
    const userId = session.read();
    api.resource(resourceId, userId, session.readTarget())
      .then(setCourse)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "ไม่สามารถโหลดรายละเอียดรายวิชาได้"));
  }, [resourceId]);

  return <div className="min-h-screen bg-surface-bg text-text-main flex pb-20 lg:pb-0">
    <WorkspaceSidebar active="roadmap" variant="graph" />
    <main className="flex-1 min-w-0">
      <header className="border-b border-border-low bg-surface-bg sticky top-0 z-20">
        <div className="max-w-container-max mx-auto px-margin-mobile md:px-gutter h-16 flex items-center gap-3">
          <button onClick={() => router.back()} className="w-9 h-9 grid place-items-center rounded-lg hover:bg-surface-muted" aria-label="กลับไปยังเส้นทางพัฒนาอาชีพ"><Icon>arrow_back</Icon></button>
          <div className="min-w-0"><p className="text-xs text-text-subtle">เส้นทางพัฒนาอาชีพ / รายละเอียดรายวิชา</p><p className="text-sm font-semibold truncate">{course?.roadmap_context?.title_en ?? "SIIT Roadmap"}</p></div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-margin-mobile md:px-gutter py-stack-lg pb-32">
        {error && <InlineNotice tone="error">{error} <button onClick={() => router.push("/roadmap")} className="underline font-semibold">กลับไปยังเส้นทางพัฒนาอาชีพ</button></InlineNotice>}
        {!course && !error && <p className="py-24 text-center text-text-subtle">กำลังโหลดรายวิชาและผลที่มีต่อเส้นทางพัฒนา</p>}
        {course && <>
          <section className="rounded-2xl bg-surface-container-low border border-border-low p-5 md:p-8 relative overflow-hidden">
            <div className="absolute -right-8 -top-8 w-36 h-36 rounded-full bg-primary-fixed opacity-70" aria-hidden="true" />
            <div className="relative max-w-3xl">
              <div className="flex items-center gap-2 text-primary mb-4"><span className="w-10 h-10 grid place-items-center rounded-xl bg-primary text-on-primary"><Icon>{kindIcon[course.kind] ?? "school"}</Icon></span><span className="text-sm font-semibold">{course.kind_label}</span></div>
              <h1 className="font-display-lg text-3xl md:text-display-lg font-bold leading-tight">{course.title}</h1>
              <p className="mt-3 text-text-subtle">{course.provider ?? "ไม่ระบุผู้ให้บริการ"} · ประมาณ {course.est_hours} ชั่วโมง · {course.cost_baht === 0 ? "ไม่มีค่าใช้จ่าย" : `${course.cost_baht.toLocaleString()} บาท`}</p>
              {course.description && <p className="mt-5 text-on-surface-variant leading-relaxed">{course.description}</p>}
              {course.url && <a href={course.url} target="_blank" rel="noreferrer" className="mt-6 inline-flex items-center gap-2 bg-primary text-on-primary px-4 py-2.5 rounded-lg font-semibold hover:bg-primary-container"><Icon>open_in_new</Icon>เปิดรายวิชาของผู้ให้บริการ</a>}
            </div>
          </section>

          <section className="mt-6 grid grid-cols-1 lg:grid-cols-[1.1fr_.9fr] gap-6">
            <article className="bg-surface-bg border border-border-low rounded-xl p-5 md:p-6">
              <div className="flex items-center gap-2"><Icon className="text-primary">route</Icon><h2 className="text-xl font-semibold">รายวิชานี้ส่งผลต่อเส้นทางพัฒนาอย่างไร</h2></div>
              {course.roadmap_context && <p className="mt-2 text-sm text-text-subtle">สำหรับเส้นทาง <span className="font-semibold text-text-main">{course.roadmap_context.title_en}</span></p>}
              <div className="mt-5 space-y-3">
                {course.teaches.map((skill) => <div key={skill.skill_id} className="p-4 rounded-lg bg-surface-muted border border-border-low">
                  <div className="flex flex-col sm:flex-row gap-2 sm:items-start sm:justify-between"><div><p className="font-semibold">{skill.name_th}</p><p className="mt-1 text-xs text-text-subtle">เมื่อเรียนรายวิชานี้ครบถ้วน ระบบคาดว่าคุณจะพัฒนาถึงระดับ {skill.reaches_level}</p></div>{skill.roadmap_status && <span className="w-fit text-xs px-2 py-1 rounded-full bg-primary-fixed text-primary">{statusLabel[skill.roadmap_status]}</span>}</div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-text-subtle">{skill.current_level != null && <span className="bg-surface-bg px-2 py-1 rounded">ระดับปัจจุบัน {skill.current_level}</span>}{skill.roadmap_target_level != null && <span className="bg-surface-bg px-2 py-1 rounded">ระดับเป้าหมาย {skill.roadmap_target_level}</span>}{skill.unlock_count > 0 && <span className="bg-secondary-container text-secondary px-2 py-1 rounded">เปิดให้เข้าถึงเพิ่มอีก {skill.unlock_count} ทักษะ</span>}</div>
                </div>)}
              </div>
            </article>

            <article className="bg-surface-bg border border-border-low rounded-xl p-5 md:p-6">
              <div className="flex items-center gap-2"><Icon className="text-primary">checklist</Icon><h2 className="text-xl font-semibold">ตัวอย่างแนวทางการลงมือปฏิบัติ</h2></div>
              <p className="mt-2 text-sm text-text-subtle">{course.note}</p>
              <ol className="mt-5 space-y-5">{course.example_learning_flow.map((item, index) => <li key={item.order} className="flex gap-3"><span className="w-7 h-7 shrink-0 rounded-full bg-primary text-on-primary grid place-items-center text-sm font-semibold">{index + 1}</span><div><h3 className="font-semibold">{item.title} <span className="font-normal text-text-subtle">· {item.est_hours} ชม.</span></h3><p className="mt-1 text-sm text-text-subtle leading-relaxed">{item.detail}</p></div></li>)}</ol>
              <div className="mt-6 p-4 rounded-lg bg-tertiary-fixed border border-tertiary-fixed-dim"><p className="text-xs font-semibold text-tertiary">หลักฐานอ้างอิงเมื่อดำเนินการเสร็จสิ้น</p><p className="mt-1 text-sm text-on-surface-variant">{course.proof_of_done}</p></div>
              {course.data_status === "placeholder" && <p className="mt-4 text-xs text-text-subtle">ข้อมูลรายวิชานี้เป็นข้อมูลตัวอย่าง กรุณาตรวจสอบรายละเอียดที่แท้จริงกับผู้ให้บริการก่อนสมัคร</p>}
            </article>
          </section>
        </>}
      </div>
    </main>
    <MobileWorkspaceNav active="roadmap" />
  </div>;
}
