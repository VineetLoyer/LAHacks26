"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

interface ConfusionChartProps {
  data: Array<{ slide: number; confusion_pct: number; responses: number }>;
  threshold: number;
}

interface DotProps {
  cx?: number;
  cy?: number;
  payload?: { confusion_pct: number };
}

function createDotRenderer(threshold: number) {
  return function ThresholdDot(props: DotProps) {
    const { cx, cy, payload } = props;
    if (cx == null || cy == null || !payload) return null;
    const exceeds = payload.confusion_pct > threshold;
    return (
      <circle
        cx={cx}
        cy={cy}
        r={exceeds ? 5 : 3}
        fill={exceeds ? "#ef4444" : "#22c55e"}
        stroke="#fff"
        strokeWidth={1.5}
      />
    );
  };
}

interface TooltipPayloadEntry {
  payload: { slide: number; confusion_pct: number; responses: number };
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
}) {
  if (!active || !payload || payload.length === 0) return null;
  const data = payload[0].payload;
  return (
    <div className="rounded-lg border bg-background p-3 shadow-md text-sm">
      <p className="font-medium">Slide {data.slide}</p>
      <p className="text-muted-foreground">
        Confusion: <span className="font-semibold text-foreground">{data.confusion_pct}%</span>
      </p>
      <p className="text-muted-foreground">
        Responses: <span className="font-semibold text-foreground">{data.responses}</span>
      </p>
    </div>
  );
}

export function ConfusionChart({ data, threshold }: ConfusionChartProps) {
  const DotRenderer = createDotRenderer(threshold);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="confusionGradient" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stopColor="#22c55e" stopOpacity={0.4} />
            <stop offset="100%" stopColor="#ef4444" stopOpacity={0.4} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
        <XAxis
          dataKey="slide"
          label={{ value: "Slide", position: "insideBottomRight", offset: -5 }}
          tick={{ fontSize: 12 }}
        />
        <YAxis
          domain={[0, 100]}
          label={{ value: "Confusion %", angle: -90, position: "insideLeft", offset: 10 }}
          tick={{ fontSize: 12 }}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine
          y={threshold}
          stroke="#ef4444"
          strokeDasharray="6 4"
          strokeWidth={2}
          label={{
            value: "Threshold",
            position: "right",
            fill: "#ef4444",
            fontSize: 12,
          }}
        />
        <Area
          type="monotone"
          dataKey="confusion_pct"
          stroke="#8b5cf6"
          strokeWidth={2}
          fill="url(#confusionGradient)"
          dot={<DotRenderer />}
          activeDot={{ r: 6, stroke: "#8b5cf6", strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
