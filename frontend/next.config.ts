import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // สร้าง .next/standalone ที่รันได้เองโดยไม่ต้องมี node_modules
  // ใช้ทั้งตอนรันบนเครื่องวัน Demo Day และตอนใส่ container — คนละที่ แต่ของชิ้นเดียวกัน
  output: "standalone",
};

export default nextConfig;
