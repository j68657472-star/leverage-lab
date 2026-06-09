"use client";
import { useEffect, useState } from "react";

const KEY = "etf_lab_anon_id";

function generateId(): string {
  const rnd =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().replace(/-/g, "").slice(0, 16)
      : Math.random().toString(36).slice(2, 18);
  return `anon_${rnd}`;
}

/** Returns a stable anonymous user id stored in localStorage (no login). */
export function useAnonId(): string | null {
  const [id, setId] = useState<string | null>(null);
  useEffect(() => {
    let existing = localStorage.getItem(KEY);
    if (!existing) {
      existing = generateId();
      localStorage.setItem(KEY, existing);
    }
    setId(existing);
  }, []);
  return id;
}
