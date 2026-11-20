export function PlasmaNucleus() {
  return (
    <g>
      {/* Core glow layer — visible breathing (CSS) */}
      <circle
        className="nucleus-core"
        cx="160" cy="160" r="28"
        fill="url(#nucleusGrad)"
        filter="url(#nucleusGlow)"
      />

      {/* Inner bright core */}
      <circle
        className="nucleus-inner"
        cx="160" cy="160" r="14"
        fill="url(#nucleusInner)"
      />

      {/* Hot center spot — wanders like a living light */}
      <circle
        className="hotspot"
        cx="0" cy="0" r="5.5"
        fill="#fff"
        opacity="0.7"
        filter="url(#nucleusGlow)"
      />

      {/* Surface shimmer — soft highlight sweeping the nucleus */}
      <ellipse
        className="nucleus-shimmer"
        cx="160" cy="160"
        rx="26" ry="10"
        fill="none"
        stroke="#D8E7FF"
        strokeWidth="0.6"
        opacity="0.25"
        filter="url(#nucleusGlow)"
      />
    </g>
  );
}
