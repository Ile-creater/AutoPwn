import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CTF Solver",
  description: "AI-Powered CTF Auto Solver",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        {children}
      </body>
    </html>
  );
}
