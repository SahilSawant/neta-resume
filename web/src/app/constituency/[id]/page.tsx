import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { SiteHeader } from "@/components/SiteHeader";
import { SectionHero } from "@/components/parliament/SectionHero";
import { IndicatorCard } from "@/components/constituency/IndicatorCard";
import { getConstituencyReport, type ConstituencyReportCard, type IndicatorComparison } from "@/lib/api";

export const revalidate = 3600;

const INDICATORS: { key: string; label: string; kind: "rupees" | "int" | "pct"; note: string; source: string }[] = [
  { key: "assets", label: "Declared assets", kind: "rupees", note: "The sitting MP's total declared assets — latest ECI affidavit.", source: "MP · ECI AFFIDAVIT" },
  { key: "pending_cases", label: "Pending criminal cases", kind: "int", note: "Self-declared and pending/unproven — the MP's latest affidavit. Asserts no guilt.", source: "MP · ECI AFFIDAVIT" },
  { key: "attendance_pct", label: "House attendance", kind: "pct", note: "The MP's cumulative Lok Sabha attendance. Rule-exempt members show no figure.", source: "MP · PRS" },
  { key: "questions", label: "Questions asked", kind: "int", note: "Questions the MP tabled this term.", source: "MP · PRS" },
];

async function load(id: string): Promise<ConstituencyReportCard | null> {
  const pc = Number(id);
  if (!Number.isFinite(pc)) return null;
  try { return await getConstituencyReport(pc); } catch { return null; }
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const r = await load((await params).id);
  if (!r) return { title: "Constituency · Neta·Resume" };
  return {
    title: `${r.pc_name} — constituency report card · Neta·Resume`,
    description: `${r.pc_name} (${r.state_name}) — its sitting MP's declared assets, pending cases, attendance and questions, compared to state and national averages.`,
  };
}

export default async function ConstituencyPage({ params }: { params: Promise<{ id: string }> }) {
  const report = await load((await params).id);
  if (!report) notFound();
  const cmp = report.comparisons;

  return (
    <>
      <SiteHeader />
      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "28px clamp(14px,4vw,28px) 72px", width: "100%" }}>
        <SectionHero
          eyebrow={`LOK SABHA CONSTITUENCY${report.pc_category && report.pc_category !== "GEN" ? ` · ${report.pc_category}` : ""}`}
          title={report.pc_name}
          subtitle={
            <>
              {report.state_name}
              {report.mp_name ? (
                <> · represented by{" "}
                  {report.mp_person_id
                    ? <Link href={`/person/${report.mp_person_id}`} style={{ color: "var(--accent-2)", textDecoration: "none", fontWeight: 600 }}>{report.mp_name}</Link>
                    : <strong style={{ color: "var(--ink2)" }}>{report.mp_name}</strong>}
                  {report.party ? ` (${report.party})` : ""}
                </>
              ) : <> · no sitting-MP record matched yet</>}
            </>
          }
          backHref="/directory"
          backLabel="Directory"
        />

        <p style={{ fontSize: 13.5, color: "var(--ink2)", margin: "0 2px 20px", maxWidth: "76ch", lineHeight: 1.55 }}>
          A descriptive profile of how this constituency&rsquo;s representation compares to the rest of the
          country — its sitting MP&rsquo;s declared record against the <strong style={{ color: "var(--ink2)" }}>state</strong> and{" "}
          <strong style={{ color: "var(--ink2)" }}>national</strong> average. Never a ranking of merit; every figure
          traces to its source. <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>Socio-economic indicators (roads, schools, literacy…) arrive in a later release.</span>
        </p>

        <div className="nr-cardgrid fadeUp">
          {INDICATORS.map((ind) => (
            <IndicatorCard
              key={ind.key}
              label={ind.label}
              kind={ind.kind}
              cmp={cmp[ind.key] as IndicatorComparison | undefined}
              note={ind.note}
              sourceLabel={ind.source}
            />
          ))}
        </div>

        {report.nearby.length > 0 && (
          <section style={{ marginTop: 34 }}>
            <h2 className="serif" style={{ fontSize: "clamp(18px,3.4vw,22px)", fontWeight: 500, letterSpacing: "-0.015em", margin: "0 0 4px" }}>Nearby constituencies</h2>
            <p style={{ fontSize: 13, color: "var(--muted)", margin: "0 0 14px" }}>The closest constituencies by location — compare their representation.</p>
            <div className="nr-cardgrid">
              {report.nearby.map((n) => (
                <Link key={n.pc_id} href={`/constituency/${n.pc_id}`} className="liftsm" style={{ minWidth: 0, display: "block", border: "1px solid var(--rule)", borderRadius: 12, background: "var(--card2)", padding: "14px 16px", textDecoration: "none", color: "var(--ink)" }}>
                  <div style={{ fontWeight: 600, fontSize: 14.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{n.pc_name}</div>
                  <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{n.mp_name ?? "—"}</div>
                  <div className="mono" style={{ fontSize: 11.5, color: "var(--faint)", marginTop: 8 }}>{n.state_name}</div>
                </Link>
              ))}
            </div>
          </section>
        )}

        <div style={{ display: "flex", gap: 9, alignItems: "flex-start", fontSize: 11.5, color: "var(--muted)", lineHeight: 1.5, marginTop: 28, maxWidth: "80ch" }}>
          <span className="mono" style={{ color: "var(--accent)", flexShrink: 0 }}>i</span>
          <span>
            &ldquo;Representation&rdquo; indicators describe the constituency&rsquo;s sitting Lok Sabha member, matched to official
            boundaries by name. Averages are computed across all constituencies with data for that indicator; a
            missing value means unmatched or unreported (rendered &ldquo;&mdash;&rdquo;), never zero.
          </span>
        </div>
      </main>
    </>
  );
}
