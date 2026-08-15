import type { Metadata } from "next";

/**
 * ตั้งชื่อหน้าเฉพาะฝั่งบริษัท
 *
 * ทำที่นี่แทนการแก้ `app/layout.tsx` เพราะไฟล์นั้นเป็นของทั้งเว็บ (🅲 ตาม docs/TEAM.md)
 * และหน้าฝั่งบริษัทเป็น client component จึง export metadata เองไม่ได้
 */
export const metadata: Metadata = {
  title: "ลงประกาศรับสมัคร — SIIT Roadmap",
  description:
    "สำหรับองค์กรที่อยากให้นักศึกษา SIIT เห็นตำแหน่งที่เปิดรับ " +
    "ประกาศทุกฉบับผ่านการตรวจจากทีมงานก่อนขึ้นแสดง",
  // หน้าอนุมัติเป็นของคนในทีม ไม่ควรถูก index
  robots: { index: false, follow: false },
};

export default function EmployerLayout({ children }: LayoutProps<"/employer">) {
  return children;
}
