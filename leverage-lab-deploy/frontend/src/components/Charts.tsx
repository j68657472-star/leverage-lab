"use client";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";

const fmtAxisDate = (s: string) => {
  const d = new Date(s);
  return isNaN(d.getTime()) ? s : `${d.getFullYear()}`;
};
const fmtK = (v: number) =>
  Math.abs(v) >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v.toFixed(0)}`;
const fmtPctAxis = (v: number) => `${(v * 100).toFixed(0)}%`;

const TooltipBox = ({ active, payload, label, kind }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-line bg-white px-3 py-2 text-xs shadow-card">
      <div className="mb-1 font-semibold text-ink">{label}</div>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ background: p.color }}
          />
          <span className="text-muted">{p.name}:</span>
          <span className="font-medium text-ink">
            {kind === "pct"
              ? `${(p.value * 100).toFixed(2)}%`
              : `$${Number(p.value).toLocaleString("en-US", {
                  maximumFractionDigits: 0,
                })}`}
          </span>
        </div>
      ))}
    </div>
  );
};

export function EquityChart({
  data,
  showSpy = true,
  splitDate,
}: {
  data: { date: string; portfolio_value: number; spy_value: number }[];
  showSpy?: boolean;
  splitDate?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={fmtAxisDate}
          minTickGap={48}
          tick={{ fontSize: 12, fill: "#94a3b8" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={fmtK}
          tick={{ fontSize: 12, fill: "#94a3b8" }}
          axisLine={false}
          tickLine={false}
          width={52}
        />
        <Tooltip content={<TooltipBox kind="money" />} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Line
          type="monotone"
          dataKey="portfolio_value"
          name="Strategy"
          stroke="#1d4ed8"
          strokeWidth={2}
          dot={false}
        />
        {showSpy && (
          <Line
            type="monotone"
            dataKey="spy_value"
            name="SPY"
            stroke="#94a3b8"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            dot={false}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function DrawdownChart({
  data,
}: {
  data: { date: string; drawdown: number; spy_drawdown: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
        <defs>
          <linearGradient id="dd" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#dc2626" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#dc2626" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={fmtAxisDate}
          minTickGap={48}
          tick={{ fontSize: 12, fill: "#94a3b8" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={fmtPctAxis}
          tick={{ fontSize: 12, fill: "#94a3b8" }}
          axisLine={false}
          tickLine={false}
          width={48}
        />
        <Tooltip content={<TooltipBox kind="pct" />} />
        <Area
          type="monotone"
          dataKey="drawdown"
          name="Strategy DD"
          stroke="#dc2626"
          strokeWidth={1.5}
          fill="url(#dd)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

const COLORS = ["#1d4ed8", "#0ea5e9", "#10b981", "#f59e0b", "#8b5cf6"];

export function CompareChart({
  series,
}: {
  series: { name: string; data: { date: string; value: number }[] }[];
}) {
  // Merge into a single dataset keyed by date.
  const map = new Map<string, any>();
  series.forEach((s, i) => {
    s.data.forEach((p) => {
      const row = map.get(p.date) || { date: p.date };
      row[`s${i}`] = p.value;
      map.set(p.date, row);
    });
  });
  const data = Array.from(map.values()).sort((a, b) =>
    a.date < b.date ? -1 : 1
  );
  return (
    <ResponsiveContainer width="100%" height={360}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={fmtAxisDate}
          minTickGap={48}
          tick={{ fontSize: 12, fill: "#94a3b8" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={fmtK}
          tick={{ fontSize: 12, fill: "#94a3b8" }}
          axisLine={false}
          tickLine={false}
          width={52}
        />
        <Tooltip content={<TooltipBox kind="money" />} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {series.map((s, i) => (
          <Line
            key={i}
            type="monotone"
            dataKey={`s${i}`}
            name={s.name}
            stroke={COLORS[i % COLORS.length]}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function AllocationBar({
  weights,
}: {
  weights: { label: string; value: number; color: string }[];
}) {
  const total = weights.reduce((a, w) => a + Math.max(0, w.value), 0) || 1;
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-slate-100">
        {weights.map((w) => (
          <div
            key={w.label}
            style={{
              width: `${(Math.max(0, w.value) / total) * 100}%`,
              background: w.color,
            }}
          />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1">
        {weights.map((w) => (
          <div key={w.label} className="flex items-center gap-1.5 text-xs">
            <span
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ background: w.color }}
            />
            <span className="text-muted">{w.label}</span>
            <span className="font-semibold text-ink">
              {(w.value * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
