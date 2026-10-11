import type { ReactNode } from "react";
import { SANS } from "../theme";

/** A plain browser window around real desktop captures (2880×1800, shown at their own shape). */
export function DesktopBrowser({ x, y, w, address, children }: { x: number; y: number; w: number; address: string; children: ReactNode }) {
  const bar = w * 0.034;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, borderRadius: w * 0.012, overflow: "hidden", background: "#e9e8e4",
                  boxShadow: `0 ${w * 0.03}px ${w * 0.07}px rgba(23, 24, 28, 0.2)` }}>
      <div style={{ height: bar, display: "flex", alignItems: "center", gap: bar * 0.22, padding: `0 ${bar * 0.45}px` }}>
        {[0, 1, 2].map((i) => <i key={i} style={{ width: bar * 0.3, height: bar * 0.3, borderRadius: "50%", background: "#c9c8c3" }} />)}
        <span style={{ marginLeft: bar * 0.5, padding: `${bar * 0.12}px ${bar * 0.5}px`, borderRadius: bar, background: "#f7f6f3", color: "#6d6f76", font: `500 ${bar * 0.36}px ${SANS}` }}>{address}</span>
      </div>
      <div style={{ position: "relative", width: "100%", aspectRatio: "1440 / 900" }}>{children}</div>
    </div>
  );
}
