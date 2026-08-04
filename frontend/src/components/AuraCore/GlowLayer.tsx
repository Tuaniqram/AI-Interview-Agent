export function GlowLayer() {
  return (
    <g>
      {/* Background ambient glow */}
      <circle
        className="glow-halo"
        cx="160" cy="160" r="160"
        fill="url(#glowOuter)"
        filter="url(#wideGlow)"
      />

      {/* Mid-field energy fog */}
      <circle
        className="glow-fog"
        cx="160" cy="160" r="120"
        fill="url(#glowMid)"
        filter="url(#wideGlow)"
      />

      {/* Inner bloom */}
      <circle
        className="glow-bloom"
        cx="160" cy="160" r="80"
        fill="url(#glowInner)"
        filter="url(#softGlow)"
      />
    </g>
  );
}
