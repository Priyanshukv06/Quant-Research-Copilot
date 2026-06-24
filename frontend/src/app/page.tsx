import styles from "./page.module.css";
import { indicators, sectors } from "@/data/indicators";
import { BookOpen, Layers } from "lucide-react";

export default function KnowledgeBase() {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>System Knowledge Base</h1>
        <p className={styles.subtitle}>
          Explore the exact language and capabilities the Quant Copilot understands.
        </p>
      </header>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          <BookOpen size={24} />
          Supported Indicators
        </h2>
        <div className={styles.grid}>
          {indicators.map((ind) => (
            <div key={ind.id} className={`glass-panel ${styles.card}`}>
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>{ind.name}</h3>
                <span className={styles.cardId}>{ind.id}</span>
              </div>
              <p className={styles.cardDescription}>{ind.description}</p>
              
              <div className={styles.examplesContainer}>
                <div className={styles.exampleLabel}>Usage Examples</div>
                {ind.examples.map((ex, idx) => (
                  <div key={idx} className={styles.example}>&quot;{ex}&quot;</div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>
          <Layers size={24} />
          Supported Sectors
        </h2>
        <div className={styles.sectorGrid}>
          {sectors.map((sector) => (
            <div key={sector} className={styles.sectorTag}>
              {sector}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
