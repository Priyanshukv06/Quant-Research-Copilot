"use client";

import { useState, useEffect } from "react";
import styles from "./news.module.css";
import ChatInput from "@/components/ChatInput";
import { submitQuery, QueryResponse } from "@/lib/api";

// ── Helpers ──

function timeAgo(dateStr: string): string {
  if (!dateStr) return "";
  try {
    const then = new Date(dateStr).getTime();
    if (isNaN(then)) return "";
    const diffMs = Date.now() - then;
    const mins = Math.floor(diffMs / 60_000);
    if (mins < 1) return "Just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  } catch {
    return "";
  }
}

function stripHtml(html: string): string {
  if (!html) return "";
  try {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return doc.body.textContent || "";
  } catch {
    return html.replace(/<[^>]*>?/gm, '').replace(/&nbsp;/g, ' ');
  }
}

function sentimentColor(s: string): string {
  switch (s?.toUpperCase()) {
    case "POSITIVE": return styles.tagPositive;
    case "NEGATIVE": return styles.tagNegative;
    default: return styles.tagNeutral;
  }
}

// ── Article Card ──

function NewsCard({ item }: { item: any }) {
  return (
    <div className={`glass-panel ${styles.newsCard}`}>
      <div className={styles.newsHeader}>
        <span className={styles.source}>{item.source}</span>
        <span className={styles.freshness}>{timeAgo(item.published)}</span>
      </div>

      <h3 className={styles.newsTitle}>
        <a href={item.url || item.link} target="_blank" rel="noreferrer">
          {item.title}
        </a>
      </h3>

      {item.description && (
        <p className={styles.description}>{stripHtml(item.description)}</p>
      )}

      {item.summary && (
        <p className={styles.summary}>
          <span className={styles.summaryLabel}>AI:</span> {item.summary}
        </p>
      )}

      <div className={styles.tags}>
        {item.sentiment && (
          <span className={`${styles.tag} ${sentimentColor(item.sentiment)}`}>
            {item.sentiment}
          </span>
        )}
        {item.category && (
          <span className={`${styles.tag} ${styles.tagCategory}`}>
            {item.category}
          </span>
        )}
      </div>
    </div>
  );
}

// ── Collapsible Section ──

function NewsSection({
  title,
  subtitle,
  articles,
  defaultOpen = true,
}: {
  title: string;
  subtitle: string;
  articles: any[];
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  if (!articles) return null;

  return (
    <div className={styles.section}>
      <button
        className={styles.sectionHeader}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <div>
          <h2 className={styles.sectionTitle}>
            {title}
            <span className={styles.badge}>{articles.length}</span>
          </h2>
          <p className={styles.sectionSubtitle}>{subtitle}</p>
        </div>
        <span className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`}>
          ▸
        </span>
      </button>

      {open && articles.length > 0 && (
        <div className={styles.grid}>
          {articles.map((item, idx) => (
            <NewsCard key={idx} item={item} />
          ))}
        </div>
      )}

      {open && articles.length === 0 && (
        <div style={{ color: "var(--text-muted)", padding: "1rem" }}>
          No latest news available for this section.
        </div>
      )}
    </div>
  );
}

// ── Main Page ──

export default function NewsPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);

  useEffect(() => {
    const saved = sessionStorage.getItem("news_result");
    if (saved) setResult(JSON.parse(saved));
  }, []);

  const handleSearch = async (query: string) => {
    setIsLoading(true);
    setResult(null);
    try {
      const res = await submitQuery(query);
      setResult(res);
      sessionStorage.setItem("news_result", JSON.stringify(res));
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  // ── Parse the structured news response ──
  const newsData = result?.data?.news;

  // Entity news is an object: { "TCS": [...], "INFY": [...] }
  const entityNewsMap: Record<string, any[]> = {};
  if (newsData?.entity_news && typeof newsData.entity_news === "object") {
    for (const [key, val] of Object.entries(newsData.entity_news)) {
      if (key !== "_warning" && Array.isArray(val)) {
        entityNewsMap[key] = val;
      }
    }
  }

  const sectorNews: any[] = Array.isArray(newsData?.sector_news) ? newsData.sector_news : [];
  const macroNews: any[] = Array.isArray(newsData?.macro_news) ? newsData.macro_news : [];
  const sourcesUsed: string[] = Array.isArray(newsData?.sources_used) ? newsData.sources_used : [];
  const entityWarning: string = newsData?.entity_news?._warning || "";
  
  const askedForSector = result?.data?.intent?.sector_filter || result?.data?.indicators_extracted?.some((ind: any) => ind.id === "sector_filter");
  const shouldShowSector = sectorNews.length > 0 || !!askedForSector;
  
  const intentData = result?.data?.intent;
  const hasNoSpecificTargets = intentData?.action === "NEWS" && (!intentData?.symbols || intentData.symbols.length === 0) && !askedForSector && !!intentData?.news_query;

  const hasAnyNews =
    Object.keys(entityNewsMap).length > 0 || shouldShowSector || hasNoSpecificTargets || macroNews.length > 0;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>News Agent</h1>
        <p className={styles.subtitle}>
          Multi-source intelligence. Ask for news about a specific stock, sector,
          or macroeconomic conditions — aggregated from {sourcesUsed.length > 0
            ? sourcesUsed.join(", ")
            : "Google News, ET Markets, Moneycontrol & more"}.
        </p>
      </header>

      <ChatInput
        placeholder="e.g. What is the latest news for TCS and the IT sector?"
        onSubmit={handleSearch}
        isLoading={isLoading}
        storageKey="news"
      />

      {result?.data?.error && (
        <div className={styles.errorBanner}>
          <strong>Error:</strong> {result.data.error}
        </div>
      )}

      {entityWarning && (
        <div className={styles.warningBanner}>{entityWarning}</div>
      )}

      {result && hasAnyNews && (
        <div className={styles.newsContainer}>
          {/* Entity News — one section per symbol */}
          {Object.entries(entityNewsMap).map(([symbol, articles]) => (
            <NewsSection
              key={symbol}
              title={`${symbol} News`}
              subtitle={`Company-level news intelligence for ${symbol}`}
              articles={articles}
              defaultOpen={true}
            />
          ))}

          {/* Unresolved Query Fallback */}
          {hasNoSpecificTargets && (
            <NewsSection
              title={`News for "${intentData.news_query}"`}
              subtitle="Specific stock or sector could not be identified from this query."
              articles={[]}
              defaultOpen={true}
            />
          )}

          {/* Sector News */}
          {shouldShowSector && (
            <NewsSection
              title="Sector News"
              subtitle="Sector-level market intelligence"
              articles={sectorNews}
              defaultOpen={true}
            />
          )}

          {/* Macro News */}
          <NewsSection
            title="Market & Macro"
            subtitle="Broad market and macroeconomic context"
            articles={macroNews}
            defaultOpen={Object.keys(entityNewsMap).length === 0 && (!shouldShowSector || sectorNews.length === 0) && !hasNoSpecificTargets}
          />
        </div>
      )}

      {result && !hasAnyNews && !result?.data?.error && (
        <p style={{ color: "var(--text-muted)" }}>
          No relevant news articles found for this query.
        </p>
      )}
    </div>
  );
}
