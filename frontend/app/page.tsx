"use client";

import { useMemo, useState } from "react";
import { Building2, CheckCircle2, FileBadge2, Gavel, Globe2, Landmark, RefreshCcw, ShieldCheck } from "lucide-react";
import { useWallet } from "@/lib/genlayer/wallet";
import {
  useAcceptLease,
  useClaimRent,
  useCompleteLease,
  useDisputePrecedents,
  useLease,
  useListing,
  usePayDepositAndFirstMonth,
  usePayMonthlyRent,
  usePlatformStats,
  useRaiseDispute,
  useResolveDispute,
  useVerifyOwnership,
} from "@/lib/hooks/useGenZLease";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

function StatCard({ title, value, subtitle }: { title: string; value: string; subtitle: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-3 text-3xl font-semibold text-slate-900">{value}</p>
      <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
    </div>
  );
}

function WorkflowStep({ icon, title, description, status }: { icon: React.ReactNode; title: string; description: string; status: "Live" | "v2"; }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-slate-900">{icon}<span className="font-semibold">{title}</span></div>
        <Badge className={status === "Live" ? "bg-emerald-100 text-emerald-700 hover:bg-emerald-100" : "bg-slate-100 text-slate-700 hover:bg-slate-100"}>{status}</Badge>
      </div>
      <p className="text-sm text-slate-600">{description}</p>
    </div>
  );
}

export default function HomePage() {
  const { address, isConnected, connectWallet, isLoading } = useWallet();

  const [listingId, setListingId] = useState("");
  const [leaseId, setLeaseId] = useState("");
  const [precedentQuery, setPrecedentQuery] = useState("deposit damage dispute with partial refund");
  const [disputeReason, setDisputeReason] = useState("Missed handover standards and cleaning obligations");
  const [evidenceUrls, setEvidenceUrls] = useState("https://example.com/report-1, https://example.com/photo-set");

  const { data: platformStats, isFetching: isRefreshingStats, refetch: refetchStats } = usePlatformStats();
  const { data: listingData } = useListing(listingId || null);
  const { data: leaseData } = useLease(leaseId || null);
  const { data: precedents = [] } = useDisputePrecedents(precedentQuery, 5);

  const verifyOwnership = useVerifyOwnership();
  const acceptLease = useAcceptLease();
  const payDepositAndFirstMonth = usePayDepositAndFirstMonth();
  const payMonthlyRent = usePayMonthlyRent();
  const claimRent = useClaimRent();
  const completeLease = useCompleteLease();
  const raiseDispute = useRaiseDispute();
  const resolveDispute = useResolveDispute();

  const parsedEvidenceUrls = useMemo(
    () => evidenceUrls.split(",").map((item) => item.trim()).filter(Boolean),
    [evidenceUrls]
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <main className="mx-auto max-w-7xl px-4 py-10 md:px-8">
        <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
                <Landmark className="h-3.5 w-3.5" />
                Institutional Leasing Control Tower
              </div>
              <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">GenZLease Institutional Flow</h1>
              <p className="mt-3 max-w-3xl text-slate-600">
                Registry verification, evidence-aware decisions, and continuous lease operations for institutions.
                This interface is structured for your v2 expansion: verifier adapters by country, standardized evidence schemas,
                and monthly lease-state automations.
              </p>
            </div>

            <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center">
              {isConnected ? (
                <Badge className="justify-center bg-emerald-100 px-3 py-2 text-emerald-700 hover:bg-emerald-100">
                  Wallet connected: {address?.slice(0, 6)}...{address?.slice(-4)}
                </Badge>
              ) : (
                <Button onClick={connectWallet} disabled={isLoading} className="bg-slate-900 text-white hover:bg-slate-800">
                  <Building2 className="mr-2 h-4 w-4" />
                  {isLoading ? "Connecting..." : "Connect Institution Wallet"}
                </Button>
              )}

              <Button
                variant="outline"
                onClick={() => refetchStats()}
                disabled={isRefreshingStats}
                className="border-slate-200 bg-white text-slate-700"
              >
                <RefreshCcw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
            </div>
          </div>
        </section>

        <section className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard title="Total listings" value={String(platformStats?.total_listings ?? "-")} subtitle="Institution portfolio visibility" />
          <StatCard title="Leases created" value={String(platformStats?.total_leases_created ?? "-")} subtitle="Demand + conversion pipeline" />
          <StatCard title="Disputes" value={String(platformStats?.total_disputes ?? "-")} subtitle="Risk and operations signal" />
          <StatCard title="Escrow total" value={String(platformStats?.total_escrow ?? "-")} subtitle="Capital currently in escrow" />
        </section>

        <section className="mt-8 grid grid-cols-1 gap-4 lg:grid-cols-3">
          <WorkflowStep
            icon={<ShieldCheck className="h-4 w-4 text-indigo-600" />}
            title="Registry verification layer"
            status="Live"
            description="Operators can trigger ownership checks per listing and review listing state before accepting lease operations."
          />
          <WorkflowStep
            icon={<FileBadge2 className="h-4 w-4 text-indigo-600" />}
            title="Evidence / decision schema"
            status="v2"
            description="Structured evidence packs, machine-readable decision outputs, and auditable legal decision trails for regulators."
          />
          <WorkflowStep
            icon={<Globe2 className="h-4 w-4 text-indigo-600" />}
            title="Monthly lease automations"
            status="v2"
            description="Scheduled rent due, grace handling, breach detection, and renewal automation across country-specific policies."
          />
        </section>

        <section className="mt-8 grid grid-cols-1 gap-6 xl:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Verification & Monitoring</h2>
            <p className="mt-1 text-sm text-slate-600">Lookup listing and lease state, then trigger institutional verification actions.</p>

            <div className="mt-5 space-y-4">
              <div>
                <label className="text-sm font-medium text-slate-700">Listing ID</label>
                <Input value={listingId} onChange={(e) => setListingId(e.target.value)} placeholder="0xowner:title_number" className="mt-1 border-slate-200 bg-white" />
              </div>

              <div>
                <label className="text-sm font-medium text-slate-700">Lease ID</label>
                <Input value={leaseId} onChange={(e) => setLeaseId(e.target.value)} placeholder="listing:tenant:start_ts" className="mt-1 border-slate-200 bg-white" />
              </div>

              <div className="flex flex-wrap gap-2">
                <Button onClick={() => verifyOwnership.mutate(listingId)} disabled={!listingId || verifyOwnership.isPending} className="bg-slate-900 text-white hover:bg-slate-800">
                  Verify Ownership
                </Button>
                <Button variant="outline" onClick={() => acceptLease.mutate(leaseId)} disabled={!leaseId || acceptLease.isPending} className="border-slate-200 bg-white">
                  Accept Lease
                </Button>
                <Button variant="outline" onClick={() => completeLease.mutate(leaseId)} disabled={!leaseId || completeLease.isPending} className="border-slate-200 bg-white">
                  Complete Lease
                </Button>
              </div>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Listing Snapshot</p>
                <pre className="max-h-52 overflow-auto text-xs text-slate-700">{JSON.stringify(listingData, null, 2) || "null"}</pre>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Lease Snapshot</p>
                <pre className="max-h-52 overflow-auto text-xs text-slate-700">{JSON.stringify(leaseData, null, 2) || "null"}</pre>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Escrow & Dispute Operations</h2>
            <p className="mt-1 text-sm text-slate-600">Institution operator controls for rent movement and dispute escalation.</p>

            <div className="mt-5 flex flex-wrap gap-2">
              <Button variant="outline" onClick={() => payDepositAndFirstMonth.mutate(leaseId)} disabled={!leaseId || payDepositAndFirstMonth.isPending} className="border-slate-200 bg-white">
                Pay Deposit + First Month
              </Button>
              <Button variant="outline" onClick={() => payMonthlyRent.mutate(leaseId)} disabled={!leaseId || payMonthlyRent.isPending} className="border-slate-200 bg-white">
                Pay Monthly Rent
              </Button>
              <Button variant="outline" onClick={() => claimRent.mutate(leaseId)} disabled={!leaseId || claimRent.isPending} className="border-slate-200 bg-white">
                Claim Rent
              </Button>
              <Button variant="outline" onClick={() => resolveDispute.mutate(leaseId)} disabled={!leaseId || resolveDispute.isPending} className="border-slate-200 bg-white">
                Resolve Dispute
              </Button>
            </div>

            <div className="mt-6 space-y-3">
              <label className="text-sm font-medium text-slate-700">Dispute reason</label>
              <Input value={disputeReason} onChange={(e) => setDisputeReason(e.target.value)} className="border-slate-200 bg-white" />
              <label className="text-sm font-medium text-slate-700">Evidence URLs (comma-separated)</label>
              <Input value={evidenceUrls} onChange={(e) => setEvidenceUrls(e.target.value)} className="border-slate-200 bg-white" />
              <Button
                onClick={() => raiseDispute.mutate({ leaseId, reason: disputeReason, evidenceUrls: parsedEvidenceUrls })}
                disabled={!leaseId || !disputeReason || raiseDispute.isPending}
                className="bg-slate-900 text-white hover:bg-slate-800"
              >
                <Gavel className="mr-2 h-4 w-4" />
                Raise Dispute
              </Button>
            </div>

            <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-3">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Similar Precedents</p>
              <Input value={precedentQuery} onChange={(e) => setPrecedentQuery(e.target.value)} className="mb-3 border-slate-200 bg-white" />
              <div className="max-h-52 space-y-2 overflow-auto text-sm text-slate-700">
                {precedents.length === 0 ? (
                  <p className="text-slate-500">No precedent results yet.</p>
                ) : (
                  precedents.map((item, index) => (
                    <div key={`${item.outcome}-${index}`} className="rounded-lg border border-slate-200 bg-white p-3">
                      <div className="mb-1 flex items-center justify-between">
                        <span className="font-medium">{item.outcome}</span>
                        <span className="text-xs text-slate-500">Similarity: {item.similarity}</span>
                      </div>
                      <p className="text-xs text-slate-600">{item.dispute_summary}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </section>

        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            <h3 className="text-lg font-semibold">Institution-ready v2 blueprint placeholders</h3>
          </div>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4">
              <p className="font-medium">Verifier adapters by country</p>
              <p className="mt-1 text-sm text-slate-600">AGIS, eCitizen, Lands Commission, Deeds Office adapter modules slot here.</p>
            </div>
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4">
              <p className="font-medium">Evidence / decision schema</p>
              <p className="mt-1 text-sm text-slate-600">Canonical evidence bundle + adjudication JSON model for legal and audit systems.</p>
            </div>
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4">
              <p className="font-medium">Lease-state automation engine</p>
              <p className="mt-1 text-sm text-slate-600">Monthly rent due, grace, breach, and renewal policy orchestration for institutions.</p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
