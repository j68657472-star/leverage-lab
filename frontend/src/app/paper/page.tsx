"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAnonId } from "@/lib/user";
import { fmtDate, fmtMoney, signClass } from "@/lib/format";
import { Card, EmptyState, ErrorBanner, InfoBanner, Spinner } from "@/components/ui";

export default function PaperList() {
  const uid = useAnonId();
  const router = useRouter();
  const [list, setList] = useState<any[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [capital, setCapital] = useState(100000);
  const [name, setName] = useState("");
  const [showForm, setShowForm] = useState(false);

  const load = () => {
    if (!uid) return;
    api.listPaper(uid).then(setList).catch((e) => setError(e.message));
  };
  useEffect(load, [uid]);

  async function create() {
    if (!uid) return;
    setCreating(true);
    try {
      const p = await api.createPaper({
        anonymous_user_id: uid,
        name: name || undefined,
        initial_capital: capital,
      });
      router.push(`/paper/${p.portfolio_id}`);
    } catch (e: any) {
      setError(e.message);
      setCreating(false);
    }
  }

  if (error) return <ErrorBanner message={error} />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">
            Paper trading
          </h1>
          <p className="text-sm text-muted">
            Simulate the strategy going forward. No real money, no broker.
          </p>
        </div>
        <button onClick={() => setShowForm((s) => !s)} className="btn-primary">
          {showForm ? "Cancel" : "New paper portfolio"}
        </button>
      </div>

      <InfoBanner>
        <strong>Simulated trading.</strong> This is a paper account for learning.
        It is not connected to any brokerage and places no real orders.
      </InfoBanner>

      {showForm && (
        <Card className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label">Starting capital</label>
              <input
                type="number"
                value={capital}
                onChange={(e) => setCapital(Number(e.target.value))}
                className="input"
              />
            </div>
            <div>
              <label className="label">Name (optional)</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Live test"
                className="input"
              />
            </div>
          </div>
          <button onClick={create} disabled={creating} className="btn-primary">
            {creating ? "Creating…" : "Create portfolio"}
          </button>
        </Card>
      )}

      {list == null ? (
        <Card><Spinner /></Card>
      ) : list.length === 0 ? (
        <EmptyState
          title="No paper portfolios yet"
          body="Create one to simulate the strategy day by day."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {list.map((p) => {
            const pnl = p.current_value - p.initial_capital;
            return (
              <Link key={p.portfolio_id} href={`/paper/${p.portfolio_id}`}>
                <Card className="h-full transition-shadow hover:shadow-md">
                  <div className="text-sm font-semibold text-ink">{p.name}</div>
                  <div className="mt-3 text-2xl font-bold text-ink">
                    {fmtMoney(p.current_value)}
                  </div>
                  <div className={`text-sm font-medium ${signClass(pnl)}`}>
                    {pnl >= 0 ? "+" : ""}
                    {fmtMoney(pnl)} ({fmtMoney(p.initial_capital)} start)
                  </div>
                  <div className="mt-3 text-xs text-muted">
                    Updated{" "}
                    {p.last_updated_at ? fmtDate(p.last_updated_at) : "never"}
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
