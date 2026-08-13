import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans_Thai } from "next/font/google";
import "./globals.css";

/**
 * 🔴 ฟอนต์ต้องมีอักษรไทย — ของเดิมเป็น Geist ซึ่งมีแต่ละติน
 *    ข้อความไทยทั้งเว็บจะตกไปใช้ฟอนต์สำรองของระบบ ซึ่งหน้าตาต่างกันทุกเครื่อง
 *    และตัวที่ใช้สาธิตบนเวทีจะไม่เหมือนตัวที่ออกแบบไว้
 */
const sans = IBM_Plex_Sans_Thai({
  variable: "--font-sans-th",
  subsets: ["thai", "latin"],
  weight: ["400", "500", "600", "700"],
});

const mono = IBM_Plex_Mono({
  variable: "--font-mono-th",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "SIIT Roadmap — จากจุดที่คุณอยู่ ไปถึงงานที่อยากทำ",
  description:
    "เว็บหางานบอกว่ามีงานอะไร — ของเราบอกว่าจะไปถึงงานนั้นได้ยังไง " +
    "โดยอ่านจากผลงานจริงของคุณ ไม่ใช่เชื่อสิ่งที่กรอกมาอย่างเดียว",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="th" className={`${sans.variable} ${mono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
