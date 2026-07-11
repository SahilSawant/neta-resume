import { rupees } from "@/lib/format";
import type { IndicatorComparison } from "@/lib/api";

type Kind = "rupees" | "int" | "pct";

function fmt(v: number | null, kind: Kind): string {
  if (v == null) return "—";
  if (kind === "rupees") return rupees(v);
  if (kind === "pct") return `${Math.round(v)}%`;
  return Math.round(v).toLocaleString("en-IN");
}

/** One indicator on the Constituency Report Card: a headline value plus a benchmark bar comparing it to the
 *  state average and national average, with a neutral percentile. Descriptive — never a ranking of merit.
 *  "Missing ≠ zero": a null value renders "—" with a "not reported" note, never a 0. */
export function IndicatorCard({
  label, kind, cmp, note, sourceLabel,
}: {
  label: string;
  kind: Kind;
  cmp: IndicatorComparison | undefined;
  note: string;         // what the number means / provenance ("This MP's ECI affidavit")
  sourceLabel: string;  // granularity + source tag ("Constituency · ECI affidavit")
}) {
  const value = cmp?.value ?? null;
  const stateAvg = cmp?.state_avg ?? null;
  const natAvg = cmp?.national_avg ?? null;
  const pct = cmp?.percentile ?? null;
  const scale = Math.max(value ?? 0, stateAvg ?? 0, natAvg ?? 0, 1) * 1.12;

  const cardStyle: React.CSSProperties = {
    minWidth: 0, border: "1px solid var(--rule)", borderRadius: 14, background: "var(--card2)",
    padding: "clamp(15px,3.5vw,20px)", display: "flex", flexDirection: "column", gap: 12,
  };
  const head = (
    <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 10 }}>
      <span style={{ fontSize: 13, fontWeight: 600, color: "var(--ink2)", letterSpacing: "0.01em" }}>{label}</span>
      <span className="mono" style={{ fontSize: 9.5, color: "var(--faint)", letterSpacing: "0.05em", textAlign: "right", whiteSpace: "nowrap" }}>{sourceLabel}</span>
    </div>
  );

  if (value == null) {
    return (
      <div style={cardStyle}>
        {head}
        <div className="mono" style={{ fontSize: 26, fontWeight: 700, color: "var(--faint)" }}>—</div>
        <div style={{ fontSize: 11.5, color: "var(--muted)" }}>Not reported for this constituency. {note}</div>
      </div>
    );
  }

  const barPct = (v: number | null) => (v == null ? 0 : Math.min(100, (v / scale) * 100));

  return (
    <div style={cardStyle}>
      {head}
      <div className="mono" style={{ fontSize: "clamp(22px,4vw,28px)", fontWeight: 700, lineHeight: 1, color: "var(--ink)" }}>{fmt(value, kind)}</div>

      {/* benchmark bar: value fill + state-avg & national-avg markers */}
      <div>
        <div style={{ position: "relative", height: 10, borderRadius: 6, background: "var(--rule)", overflow: "visible" }}>
          <div style={{ position: "absolute", top: 0, bottom: 0, left: 0, width: `${barPct(value)}%`, background: "var(--accent-2)", borderRadius: 6 }} />
          {stateAvg != null && <Marker at={barPct(stateAvg)} color="var(--ink)" title={`State avg ${fmt(stateAvg, kind)}`} />}
          {natAvg != null && <Marker at={barPct(natAvg)} color="var(--accent-soft-fg)" title={`National avg ${fmt(natAvg, kind)}`} />}
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "2px 10px", marginTop: 8, fontSize: 11, color: "var(--muted)" }}>
          {stateAvg != null && <span><Swatch c="var(--ink)" /> State avg {fmt(stateAvg, kind)}</span>}
          {natAvg != null && <span><Swatch c="var(--accent-soft-fg)" /> National avg {fmt(natAvg, kind)}</span>}
          {pct != null && <span style={{ marginLeft: "auto" }}>Higher than {pct}% of constituencies</span>}
        </div>
      </div>
      <div style={{ fontSize: 11, color: "var(--faint)" }}>{note}</div>
    </div>
  );
}

function Marker({ at, color, title }: { at: number; color: string; title: string }) {
  return <div title={title} style={{ position: "absolute", top: -3, bottom: -3, left: `${at}%`, width: 2, background: color, borderRadius: 2 }} />;
}
function Swatch({ c }: { c: string }) {
  return <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: 2, background: c, marginRight: 5, verticalAlign: "middle" }} />;
}
