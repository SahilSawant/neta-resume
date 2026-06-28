// Server-only geo helpers: resolve an approximate IP lat/long to a Lok Sabha constituency, and map a
// Vercel region code to a state. Used by the homepage to feature a nearby MP.
//
// Parliamentary-constituency boundaries: "Parliamentary Constituencies 2019" by the DataMeet India
// community (https://github.com/datameet/maps), CC BY 4.0. Imported (not in /public) so it's bundled
// server-side and never shipped to the browser.
import pcData from "@/data/pc-boundaries.json";

type Ring = number[][];
type Polygon = Ring[];
interface PCFeature {
  properties: { pc_name: string; st_name: string };
  geometry: { type: "Polygon" | "MultiPolygon"; coordinates: number[][][] | number[][][][] };
}

const features = (pcData as unknown as { features: PCFeature[] }).features;

// Precompute a bbox per feature once, to skip the expensive ring test for far-away polygons.
const bboxes: [number, number, number, number][] = features.map((f) => {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  const polys = (f.geometry.type === "MultiPolygon"
    ? (f.geometry.coordinates as number[][][][])
    : [f.geometry.coordinates as number[][][]]);
  for (const poly of polys) for (const ring of poly) for (const [x, y] of ring) {
    if (x < minX) minX = x; if (x > maxX) maxX = x; if (y < minY) minY = y; if (y > maxY) maxY = y;
  }
  return [minX, minY, maxX, maxY];
});

function pointInRing(x: number, y: number, ring: Ring): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
    if (((yi > y) !== (yj > y)) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

function pointInPolygon(x: number, y: number, poly: Polygon): boolean {
  if (!pointInRing(x, y, poly[0])) return false; // outer ring
  for (let k = 1; k < poly.length; k++) if (pointInRing(x, y, poly[k])) return false; // holes
  return true;
}

/** Approximate (lat,lng) → Lok Sabha constituency name, or null if no polygon contains the point. */
export function pointToConstituency(lat: number, lng: number): string | null {
  const x = lng, y = lat;
  for (let i = 0; i < features.length; i++) {
    const b = bboxes[i];
    if (x < b[0] || x > b[2] || y < b[1] || y > b[3]) continue;
    const g = features[i].geometry;
    const polys = (g.type === "MultiPolygon"
      ? (g.coordinates as number[][][][])
      : [g.coordinates as number[][][]]);
    for (const poly of polys) if (pointInPolygon(x, y, poly as Polygon)) return features[i].properties.pc_name;
  }
  return null;
}

// Vercel `x-vercel-ip-country-region` → state name (ISO 3166-2:IN subdivision codes). The API filter
// normalizes spelling/case, so these standard names match our stored state values.
export const REGION_TO_STATE: Record<string, string> = {
  AN: "Andaman and Nicobar Islands", AP: "Andhra Pradesh", AR: "Arunachal Pradesh", AS: "Assam",
  BR: "Bihar", CH: "Chandigarh", CT: "Chhattisgarh", DN: "Dadra and Nagar Haveli", DD: "Daman and Diu",
  DH: "Dadra and Nagar Haveli and Daman and Diu", DL: "Delhi", GA: "Goa", GJ: "Gujarat", HR: "Haryana",
  HP: "Himachal Pradesh", JK: "Jammu and Kashmir", JH: "Jharkhand", KA: "Karnataka", KL: "Kerala",
  LA: "Ladakh", LD: "Lakshadweep", MP: "Madhya Pradesh", MH: "Maharashtra", MN: "Manipur", ML: "Meghalaya",
  MZ: "Mizoram", NL: "Nagaland", OR: "Odisha", PY: "Puducherry", PB: "Punjab", RJ: "Rajasthan",
  SK: "Sikkim", TN: "Tamil Nadu", TG: "Telangana", TR: "Tripura", UP: "Uttar Pradesh", UT: "Uttarakhand",
  WB: "West Bengal",
};
