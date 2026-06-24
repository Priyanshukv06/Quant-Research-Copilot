"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import styles from "./screener.module.css";
import ChatInput from "@/components/ChatInput";
import { submitQuery, QueryResponse } from "@/lib/api";

// Dynamically import Plotly to avoid SSR issues
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

export default function ScreenerPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);

  useEffect(() => {
    const saved = sessionStorage.getItem("screener_result");
    if (saved) setResult(JSON.parse(saved));
  }, []);

  const handleSearch = async (query: string) => {
    setIsLoading(true);
    setResult(null);
    try {
      const res = await submitQuery(query);
      setResult(res);
      sessionStorage.setItem("screener_result", JSON.stringify(res));
    } catch (error) {
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const symbols = result?.data?.screened_symbols || [];
  const charts = result?.data?.charts || [];
  const columns = symbols.length > 0 ? Object.keys(symbols[0]) : [];

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Query Agent</h1>
        <p className={styles.subtitle}>
          Natural language stock screening. The agent translates your query into BigQuery SQL, executes it, and visualizes the results.
        </p>
      </header>

      <ChatInput 
        placeholder="e.g. Find top 5 IT sector stocks with the lowest live PE..." 
        onSubmit={handleSearch} 
        isLoading={isLoading} 
        storageKey="screener"
      />

      {result?.data?.error && (
        <div className={styles.error}>
          <strong>Execution Error:</strong> {result.data.error}
        </div>
      )}

      {result && (
        <div className={styles.resultsGrid}>
          {result.data?.bq_query && (
            <div className={styles.sqlBox}>
              <div style={{ color: "var(--text-muted)", marginBottom: "0.5rem" }}>Executed SQL:</div>
              {result.data.bq_query}
            </div>
          )}

          <div className={`glass-panel ${styles.tableContainer}`}>
            <h3 style={{ marginBottom: "1rem" }}>Screened Stocks ({symbols.length})</h3>
            {symbols.length > 0 ? (
              <table>
                <thead>
                  <tr>
                    {columns.map(col => <th key={col}>{col.replace(/_/g, " ")}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {symbols.map((row, i) => (
                    <tr key={i}>
                      {columns.map(col => (
                        <td key={col}>
                          {typeof row[col] === 'number' ? Number(row[col]).toFixed(2) : row[col]}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ color: "var(--text-muted)" }}>No stocks matched the criteria.</p>
            )}
          </div>

          {charts.length > 0 && (
            <div className={styles.chartGrid}>
              {charts.map((chartSpec, i) => (
                <div key={i} className={`glass-panel ${styles.chartCard}`}>
                  <Plot
                    data={chartSpec.data}
                    layout={{
                      ...chartSpec.layout,
                      autosize: true,
                      paper_bgcolor: 'transparent',
                      plot_bgcolor: 'transparent',
                      font: { color: '#f8fafc' }
                    }}
                    useResizeHandler={true}
                    style={{ width: "100%", height: "100%" }}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
