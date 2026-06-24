"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import styles from "./report.module.css";
import ChatInput from "@/components/ChatInput";
import { submitQuery, QueryResponse } from "@/lib/api";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

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
  const charts = result?.data?.charts || [];

  const downloadPDF = async () => {
    setIsPrinting(true);
    
    // Give React time to re-render the DOM with plain styles and black text
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
        jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' },
        pagebreak:    { mode: ['avoid-all', 'css', 'legacy'] }
      };
      
      await html2pdf().set(opt).from(element).save();
      setIsPrinting(false);
    }, 500);
  };

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
        <div style={{ color: "var(--accent-rose)", marginBottom: "1rem" }}>
          Error: {result.data.error}
        </div>
      )}

      {result && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button 
              onClick={downloadPDF}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: 'var(--accent-primary)',
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
            {charts.length > 0 && charts.map((chartSpec, i) => (
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
