import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "실버 금융가드",
  description: "고령층 금융소비자를 위한 가입 전 위험 점검과 금융사고 대응 도우미",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
