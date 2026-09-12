"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import styles from "./report.module.css";
import ChatInput from "@/components/ChatInput";
import { submitQuery, QueryResponse } from "@/lib/api";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

// ── Helpers ──

function signalEmoji(signal: string): string {
  switch (signal?.toUpperCase()) {
    case "STRONG": return "🟢";
    case "CAUTION": return "🔴";
    default: return "🟡";
  }
}

function signalClass(signal: string): string {
  switch (signal?.toUpperCase()) {
    case "STRONG": return styles.signalStrong;
    case "CAUTION": return styles.signalCaution;
    default: return styles.signalWatch;
  }
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-IN", {
      day: "numeric", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

// ── Signal Card ──

function SignalCard({ stock }: { stock: any }) {
  return (
    <div className={`${styles.signalCard} ${signalClass(stock.signal)}`}>
      <div className={styles.signalHeader}>
        <span className={styles.signalEmoji}>{signalEmoji(stock.signal)}</span>
        <span className={styles.signalSymbol}>{stock.symbol}</span>
        <span className={styles.signalLabel}>{stock.signal}</span>
      </div>
      <p className={styles.signalSummary}>{stock.fundamental_summary}</p>
      {stock.risk_flags && stock.risk_flags.length > 0 && (
        <div className={styles.riskFlags}>
          {stock.risk_flags.map((flag: string, i: number) => (
            <span key={i} className={styles.riskTag}>⚠ {flag}</span>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Metadata Bar ──

function MetadataBar({ metadata }: { metadata: any }) {
  const dist = metadata?.signal_distribution || {};
  return (
    <div className={`glass-panel ${styles.metadataBar}`}>
      <div className={styles.metaItem}>
        <span className={styles.metaLabel}>Query</span>
        <span className={styles.metaValue}>{metadata?.query || "—"}</span>
      </div>
      <div className={styles.metaItem}>
        <span className={styles.metaLabel}>Generated</span>
        <span className={styles.metaValue}>
          {metadata?.generated_at ? formatDate(metadata.generated_at) : "—"}
        </span>
      </div>
      <div className={styles.metaItem}>
        <span className={styles.metaLabel}>Stocks</span>
        <span className={styles.metaValue}>{metadata?.stocks_analyzed ?? "—"}</span>
      </div>
      <div className={styles.metaItem}>
        <span className={styles.metaLabel}>Signals</span>
        <span className={styles.metaValue}>
          {dist.STRONG > 0 && <span>🟢{dist.STRONG} </span>}
          {dist.WATCH > 0 && <span>🟡{dist.WATCH} </span>}
          {dist.CAUTION > 0 && <span>🔴{dist.CAUTION}</span>}
          {!dist.STRONG && !dist.WATCH && !dist.CAUTION && "—"}
        </span>
      </div>
      {metadata?.overall_market_stance && (
        <div className={styles.metaItem}>
          <span className={styles.metaLabel}>Market Stance</span>
          <span className={styles.metaValue}>{metadata.overall_market_stance}</span>
        </div>
      )}
    </div>
  );
}

// ── Main Page ──

export default function ReportPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [isPrinting, setIsPrinting] = useState(false);

  useEffect(() => {
    const saved = sessionStorage.getItem("report_result");
    if (saved) setResult(JSON.parse(saved));
  }, []);

  const handleSearch = async (query: string) => {
    setIsLoading(true);
    setResult(null);
    try {
      const res = await submitQuery(query);
      setResult(res);
      sessionStorage.setItem("report_result", JSON.stringify(res));
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const markdown = result?.data?.report_markdown;
  const reportMeta = result?.data?.report_metadata;
  const synthesis = result?.data?.synthesis;
  const charts = result?.data?.charts || [];
  const stocks = synthesis?.stocks || [];

  const downloadPDF = async () => {
    setIsPrinting(true);
    
    setTimeout(async () => {
      const element = document.getElementById('report-content');
      if (!element) {
        setIsPrinting(false);
        return;
      }
      
      const html2pdf = (await import('html2pdf.js')).default;
      
      const opt = {
        margin:       0.5,
        filename:     'Quant_Research_Report.pdf',
        image:        { type: 'jpeg' as const, quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true, windowWidth: 1000 },
        jsPDF:        { unit: 'in' as const, format: 'letter' as const, orientation: 'portrait' as const },
        pagebreak:    { mode: ['avoid-all', 'css', 'legacy'] }
      };
      
      await html2pdf().set(opt).from(element).save();
      setIsPrinting(false);
    }, 500);
  };

  // Determine what kind of result we have
  const isReportQuery = result?.data?.intent?.action === "SCREEN_AND_NEWS";
  const isNonReportQuery = result && !isReportQuery;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Report Agent</h1>
        <p className={styles.subtitle}>
          Comprehensive Synthesis. The Copilot screens the market, reads the latest news, cross-references the intelligence, and writes a professional Markdown Research Note.
        </p>
      </header>

      <ChatInput 
        placeholder="e.g. Find IT stocks with PE < 30 and write a deep dive report based on the news." 
        onSubmit={handleSearch} 
        isLoading={isLoading} 
        storageKey="report"
      />

      {result?.data?.error && (
        <div className={styles.errorBanner}>
          <strong>Error:</strong> {result.data.error}
        </div>
      )}

      {isNonReportQuery && !result?.data?.error && (
        <div className={styles.infoBanner}>
          Your query was routed as a <strong>{result?.data?.intent?.action}</strong> action.
          To generate a full research report, try a query that combines screening with news
          (e.g. &quot;Find IT stocks with PE below 30 and check their news&quot;).
        </div>
      )}

      {isReportQuery && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%' }}>
          
          {/* Metadata Bar */}
          {reportMeta && <MetadataBar metadata={reportMeta} />}

          {/* Signal Cards Row */}
          {stocks.length > 0 && (
            <div className={styles.signalRow}>
              {stocks.map((stock: any, i: number) => (
                <SignalCard key={i} stock={stock} />
              ))}
            </div>
          )}

          {/* Download Button */}
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button 
              onClick={downloadPDF}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: 'var(--accent-primary, var(--accent-cyan))',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: '0.9rem',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}
            >
              ↓ Download as PDF
            </button>
          </div>

          {/* Report Content */}
          <div id="report-content" className={`${styles.layout} ${isPrinting ? styles.plainPdfMode : ''}`}>
            <div className={`${isPrinting ? '' : 'glass-panel'} ${styles.markdownContainer}`}>
              {markdown ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
              ) : (
                <p style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
                  No report generated. Ensure your query asks for a synthesis or report, or that data was found.
                </p>
              )}
            </div>

            <div className={styles.sidebarContainer}>
              {charts.length > 0 && charts.map((chartSpec: any, i: number) => (
                <div key={i} className={`${isPrinting ? 'pdf-page-break' : 'glass-panel'} ${styles.chartCard}`}>
                  <Plot
                    data={chartSpec.data}
                    layout={{
                      ...chartSpec.layout,
                      autosize: true,
                      margin: { t: 40, b: 30, l: 30, r: 10 },
                      paper_bgcolor: 'transparent',
                      plot_bgcolor: 'transparent',
                      font: { color: isPrinting ? '#000000' : '#f8fafc', size: 10 }
                    }}
                    useResizeHandler={true}
                    style={{ width: "100%", height: "100%" }}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
