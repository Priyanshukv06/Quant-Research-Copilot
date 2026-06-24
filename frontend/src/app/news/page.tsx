"use client";

import { useState, useEffect } from "react";
import styles from "./news.module.css";
import ChatInput from "@/components/ChatInput";
import { submitQuery, QueryResponse } from "@/lib/api";

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

  const entityNews = result?.data?.news?.entity_news || [];
  const sectorNews = result?.data?.news?.sector_news || [];
  const macroNews = result?.data?.news?.macro_news || [];

  // Flatten the news arrays for rendering
  let allNews: any[] = [];
  if (Array.isArray(entityNews)) allNews = [...allNews, ...entityNews];
  if (Array.isArray(sectorNews)) allNews = [...allNews, ...sectorNews];
  if (Array.isArray(macroNews)) allNews = [...allNews, ...macroNews];

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>News Agent</h1>
        <p className={styles.subtitle}>
          Gather raw intelligence. Ask for news about a specific stock, sector, or macroeconomic conditions.
        </p>
      </header>

      <ChatInput 
        placeholder="e.g. What is the latest news for TCS and the IT sector?" 
        onSubmit={handleSearch} 
        isLoading={isLoading} 
        storageKey="news"
      />

      {result?.data?.error && (
        <div style={{ color: "var(--accent-rose)", marginBottom: "1rem" }}>
          Error: {result.data.error}
        </div>
      )}

      {result && allNews.length > 0 && (
        <div className={styles.grid}>
          {allNews.map((item, idx) => (
            <div key={idx} className={`glass-panel ${styles.newsCard}`}>
              <div className={styles.newsHeader}>
                <span className={styles.source}>{item.source}</span>
                <span className={styles.date}>
                  {new Date(item.published).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                </span>
              </div>
              
              <h3 className={styles.newsTitle}>
                <a href={item.link} target="_blank" rel="noreferrer">
                  {item.title}
                </a>
              </h3>
              
              <p className={styles.summary}>{item.summary}</p>
              
              <div className={styles.tags}>
                {item.sentiment && (
                  <span className={`${styles.tag} ${
                    item.sentiment === 'POSITIVE' ? styles.tagPositive : 
                    item.sentiment === 'NEGATIVE' ? styles.tagNegative : styles.tagNeutral
                  }`}>
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
          ))}
        </div>
      )}

      {result && allNews.length === 0 && !result?.data?.error && (
        <p style={{ color: "var(--text-muted)" }}>No news articles found for this query.</p>
      )}
    </div>
  );
}
