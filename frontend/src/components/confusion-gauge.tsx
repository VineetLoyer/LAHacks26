"use client";

import { AnimatedCounter } from "@/components/animated-counter";

interface ConfusionGaugeProps {
  value: number;
  threshold: number;
}

function getColor(value: number): string {
  if (value <= 40) return "#22c55e";
  if (value <= 70) return "#eab308";
  return "#ef4444";
}

export function ConfusionGauge({ value, threshold }: ConfusionGaugeProps) {
  const size = 200;
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.min(Math.max(value, 0), 100) / 100;
  const dashOffset = circumference * (1 - progress);
  const color = getColor(value);
  const isSpike = value > threshold;

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <style>{`
        @keyframes gaugeGlow {
          0%, 100% { filter: drop-shadow(0 0 4px ${color}); }
          50% { filter: drop-shadow(0 0 12px ${color}); }
        }
      `}</style>
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
        style={isSpike ? { animation: "gaugeGlow 2s ease-in-out infinite" } : undefined}
      >
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          className="text-muted/30"
          strokeWidth={strokeWidth}
        />
        {/* Progress arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          style={{ transition: "stroke-dashoffset 0.8s ease, stroke 0.8s ease" }}
        />
      </svg>
      {/* Center text */}
      <div className="absolute inset-0 flex items-center justify-center">
        <AnimatedCounter
          value={value}
          suffix="%"
          className="text-4xl font-bold"
        />
      </div>
    </div>
  );
}
