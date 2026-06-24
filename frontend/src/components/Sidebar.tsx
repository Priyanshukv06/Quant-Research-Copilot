"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LineChart, Search, Newspaper, FileText, Database } from "lucide-react";
import styles from "../app/layout.module.css";

export default function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { name: "Knowledge Base", href: "/", icon: Database },
    { name: "Query Agent", href: "/screener", icon: Search },
    { name: "News Agent", href: "/news", icon: Newspaper },
    { name: "Report Agent", href: "/report", icon: FileText },
  ];

  return (
    <aside className={styles.sidebar}>
      <div className={styles.logo}>
        <LineChart className={styles.logoIcon} size={28} />
        <span>Quant Copilot</span>
      </div>
      <nav className={styles.nav}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`${styles.navLink} ${isActive ? styles.active : ""}`}
            >
              <Icon size={20} />
              {item.name}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
