import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SIIT Roadmap — เส้นทางพัฒนาอาชีพสำหรับนักศึกษา SIIT",
  description:
    "เส้นทางพัฒนาอาชีพเฉพาะบุคคลสำหรับนักศึกษา SIIT วิเคราะห์จากความสามารถจริงของคุณ",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="th" data-scroll-behavior="smooth">
      <body>{children}</body>
    </html>
  );
}
