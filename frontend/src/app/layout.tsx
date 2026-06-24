import type { Metadata } from "next";
import "./globals.css";
import styles from "./layout.module.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Quant Copilot | Agentic Terminal",
  description: "Agentic Financial Screener and Research Terminal",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className={styles.container}>
          <Sidebar />
          <main className={styles.main}>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
