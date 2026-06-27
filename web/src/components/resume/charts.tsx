// Pure SVG chart components (no client hooks) — usable in server or client components.

export interface DonutSeg {
  label: string;
  value: number;
  color: string;
}

/** Severity / distribution donut with a centred count + legend. */
export function Donut({
  segments,
  centerNum,
  centerLabel,
  size = 140,
}: {
  segments: DonutSeg[];
  centerNum: string | number;
  centerLabel: string;
  size?: number;
}) {
  const r = 54;
  const circ = 2 * Math.PI * r;
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  let offset = 0;
  const arcs = segments
    .filter((s) => s.value > 0)
    .map((s) => {
      const len = (s.value / total) * circ;
      const dash = `${len} ${circ - len}`;
      const arc = { color: s.color, dash, off: -offset };
      offset += len;
      return arc;
    });

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
      <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
        <svg viewBox="0 0 140 140" style={{ width: size, height: size }}>
          <circle cx="70" cy="70" r={r} fill="none" stroke="var(--rule2)" strokeWidth="18" />
          <g style={{ transformOrigin: "70px 70px", transform: "rotate(-90deg)" }}>
            {arcs.map((a, i) => (
              <circle key={i} cx="70" cy="70" r={r} fill="none" stroke={a.color} strokeWidth="18" strokeDasharray={a.dash} strokeDashoffset={a.off} />
            ))}
          </g>
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <div className="mono" style={{ fontSize: 26, fontWeight: 600, lineHeight: 1 }}>{centerNum}</div>
          <div style={{ fontSize: 9.5, color: "var(--muted)", marginTop: 2 }}>{centerLabel}</div>
        </div>
      </div>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 9 }}>
        {segments.map((s) => (
          <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 9 }}>
            <span style={{ width: 10, height: 10, borderRadius: 3, background: s.color, flexShrink: 0 }} />
            <span style={{ fontSize: 12, color: "var(--ink2)", flex: 1, lineHeight: 1.1 }}>{s.label}</span>
            <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: s.color }}>{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Net-assets-by-cycle line. Degrades to a single marker when only one cycle exists. */
export function WealthLine({ points }: { points: { label: string; value: number }[] }) {
  const W = 282;
  const H = 150;
  const pad = 8;
  const max = Math.max(...points.map((p) => p.value), 1);
  const xs = (i: number) => (points.length === 1 ? W / 2 : pad + (i * (W - 2 * pad)) / (points.length - 1));
  const ys = (v: number) => H - pad - (v / max) * (H - 2 * pad - 20);

  const line = points.map((p, i) => `${xs(i)},${ys(p.value)}`).join(" ");
  const area = `${xs(0)},${H} ${line} ${xs(points.length - 1)},${H}`;

  return (
    <div>
      <div style={{ position: "relative", height: H }}>
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
          {[0.33, 0.66].map((f) => (
            <line key={f} x1="0" y1={H * f} x2={W} y2={H * f} stroke="var(--rule2)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          ))}
          <polygon points={area} fill="var(--accent)" opacity="0.12" />
          <polyline points={line} fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" style={{ strokeDasharray: 1400, animation: "nrDraw 1.2s ease both" }} />
        </svg>
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ position: "absolute", inset: 0, width: "100%", height: "100%", overflow: "visible" }}>
          {points.map((p, i) => (
            <circle key={i} cx={xs(i)} cy={ys(p.value)} r="3.5" fill="var(--card)" stroke="var(--accent)" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
          ))}
        </svg>
      </div>
      <div style={{ display: "flex", justifyContent: points.length === 1 ? "center" : "space-between", marginTop: 10 }} className="mono">
        {points.map((p, i) => (
          <span key={i} style={{ fontSize: 10.5, color: "var(--muted)" }}>{p.label}</span>
        ))}
      </div>
    </div>
  );
}
