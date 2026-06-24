"use client";

import { useState, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import styles from "./ChatInput.module.css";

interface ChatInputProps {
  placeholder?: string;
  onSubmit: (query: string) => Promise<void>;
  isLoading: boolean;
  storageKey?: string;
}

export default function ChatInput({ placeholder = "Ask the Copilot...", onSubmit, isLoading, storageKey }: ChatInputProps) {
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (storageKey) {
      const saved = sessionStorage.getItem(`${storageKey}_query`);
      if (saved) setQuery(saved);
    }
  }, [storageKey]);

  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    if (storageKey) {
      sessionStorage.setItem(`${storageKey}_query`, val);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;
    await onSubmit(query);
  };

  return (
    <form className={styles.container} onSubmit={handleSubmit}>
      <input
        type="text"
        className={styles.input}
        value={query}
        onChange={handleQueryChange}
        placeholder={placeholder}
        disabled={isLoading}
      />
      <button type="submit" className={styles.button} disabled={isLoading || !query.trim()}>
        {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
        <span>{isLoading ? "Running..." : "Run"}</span>
      </button>
    </form>
  );
}
