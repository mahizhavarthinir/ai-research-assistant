import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/hooks/useAuth";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "AI Research Assistant — Intelligent Document Research",
  description:
    "Upload documents, ask questions, and get cited answers powered by RAG and large language models.",
  keywords: ["AI", "research", "RAG", "documents", "LLM", "assistant"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <AuthProvider>
          <div className="mesh-bg" />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
