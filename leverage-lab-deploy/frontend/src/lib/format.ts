export const fmtPct = (v?: number | null, digits = 1) =>
  v == null ? "—" : `${(v * 100).toFixed(digits)}%`;

export const fmtMoney = (v?: number | null, digits = 0) =>
  v == null
    ? "—"
    : v.toLocaleString("en-US", {
        style: "currency",
        currency: "USD",
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });

export const fmtNum = (v?: number | null, digits = 2) =>
  v == null ? "—" : v.toLocaleString("en-US", { maximumFractionDigits: digits });

export const fmtDate = (s?: string | null) => {
  if (!s) return "—";
  const d = new Date(s);
  if (isNaN(d.getTime())) return s;
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
};

export const signClass = (v?: number | null) =>
  v == null ? "text-ink" : v >= 0 ? "text-pos" : "text-neg";
