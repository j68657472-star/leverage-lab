"use client";
import { signClass } from "@/lib/format";

export function Card({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={`card p-5 ${className}`}>{children}</div>;
}

export function MetricTile({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: number | null;
}) {
  return (
    <div className="rounded-xl border border-line bg-white p-4">
      <div className="text-xs font-medium text-muted">{label}</div>
      <div
        className={`mt-1 text-2xl font-bold tracking-tight ${
          tone === undefined ? "text-ink" : signClass(tone)
        }`}
      >
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-muted">{sub}</div>}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-line border-t-brand" />
      {label && <div className="text-sm">{label}</div>}
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-line bg-white py-16 text-center">
      <div className="text-base font-semibold text-ink">{title}</div>
      <div className="mt-1 max-w-sm text-sm text-muted">{body}</div>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-neg/30 bg-red-50 px-4 py-3 text-sm text-neg">
      {message}
    </div>
  );
}

export function InfoBanner({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-brand/20 bg-blue-50 px-4 py-3 text-sm text-branddark">
      {children}
    </div>
  );
}

export function Pill({
  on,
  labelOn,
  labelOff,
}: {
  on: boolean;
  labelOn?: string;
  labelOff?: string;
}) {
  return (
    <span
      className={`pill ${on ? "bg-emerald-50 text-pos" : "bg-slate-100 text-muted"}`}
    >
      {on ? labelOn || "Yes" : labelOff || "No"}
    </span>
  );
}

export function SectionTitle({
  title,
  hint,
  right,
}: {
  title: string;
  hint?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="mb-3 flex items-end justify-between">
      <div>
        <h2 className="text-lg font-bold tracking-tight text-ink">{title}</h2>
        {hint && <p className="text-sm text-muted">{hint}</p>}
      </div>
      {right}
    </div>
  );
}
