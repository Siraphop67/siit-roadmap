import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SIIT Roadmap — Find your path to the future",
  description:
    "แผนที่อาชีพเฉพาะบุคคลสำหรับนักศึกษา SIIT จากความสนใจ ทักษะ และผลงานจริง",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="th" data-scroll-behavior="smooth">
      <body>{children}</body>
    </html>
  );
}
