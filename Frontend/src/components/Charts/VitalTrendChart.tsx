import React from 'react';
import { MeasurementHistoryPoint } from '../../types';

interface VitalTrendChartProps {
  data: MeasurementHistoryPoint[];
  metric: 'bpm' | 'spo2' | 'temperature_c' | 'accel_magnitude_g';
  label: string;
  unit: string;
  color?: string;
  height?: number;
}

export const VitalTrendChart: React.FC<VitalTrendChartProps> = ({
  data,
  metric,
  label,
  unit,
  color = '#2a87ff',
  height = 140,
}) => {
  if (!data || data.length === 0) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center bg-slate-900/60 rounded-xl border border-slate-800 text-xs text-slate-500"
      >
        Aucune donnée chronologique disponible
      </div>
    );
  }

  // Extract valid numerical points
  const points = data
    .map((d, index) => ({
      val: d[metric],
      time: d.timestamp,
      index,
    }))
    .filter((p) => p.val !== null && p.val !== undefined && !isNaN(p.val as number));

  if (points.length < 2) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center bg-slate-900/60 rounded-xl border border-slate-800 text-xs text-slate-500"
      >
        Données insuffisantes pour tracer la courbe (minimum 2 mesures requises)
      </div>
    );
  }

  const values = points.map((p) => p.val as number);
  const minVal = Math.floor(Math.min(...values) * 0.95);
  const maxVal = Math.ceil(Math.max(...values) * 1.05) || 1;
  const range = maxVal - minVal || 1;

  const width = 500;
  const padding = { top: 15, bottom: 25, left: 35, right: 15 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const getX = (i: number) => padding.left + (i / (points.length - 1)) * plotWidth;
  const getY = (v: number) => padding.top + plotHeight - ((v - minVal) / range) * plotHeight;

  const pathD = points.reduce((acc, p, i) => {
    const x = getX(i);
    const y = getY(p.val as number);
    return i === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
  }, '');

  const areaD = `${pathD} L ${getX(points.length - 1)} ${padding.top + plotHeight} L ${getX(0)} ${
    padding.top + plotHeight
  } Z`;

  const latestVal = points[points.length - 1].val;

  return (
    <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-3 shadow-inner">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-slate-400">{label}</span>
        <div className="flex items-baseline gap-1">
          <span className="text-sm font-bold text-slate-100">{latestVal}</span>
          <span className="text-[11px] text-slate-400">{unit}</span>
        </div>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="w-full overflow-visible">
        <defs>
          <linearGradient id={`grad-${metric}`} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0.0" />
          </linearGradient>
        </defs>

        {/* Grid lines */}
        <line
          x1={padding.left}
          y1={padding.top}
          x2={width - padding.right}
          y2={padding.top}
          stroke="#334155"
          strokeDasharray="3 3"
          strokeWidth="0.8"
        />
        <line
          x1={padding.left}
          y1={padding.top + plotHeight / 2}
          x2={width - padding.right}
          y2={padding.top + plotHeight / 2}
          stroke="#334155"
          strokeDasharray="3 3"
          strokeWidth="0.8"
        />
        <line
          x1={padding.left}
          y1={padding.top + plotHeight}
          x2={width - padding.right}
          y2={padding.top + plotHeight}
          stroke="#334155"
          strokeWidth="1"
        />

        {/* Y Axis Labels */}
        <text
          x={padding.left - 6}
          y={padding.top + 4}
          fill="#64748b"
          fontSize="9"
          textAnchor="end"
        >
          {maxVal}
        </text>
        <text
          x={padding.left - 6}
          y={padding.top + plotHeight}
          fill="#64748b"
          fontSize="9"
          textAnchor="end"
        >
          {minVal}
        </text>

        {/* Area fill */}
        <path d={areaD} fill={`url(#grad-${metric})`} />

        {/* Line */}
        <path d={pathD} fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" />

        {/* Points */}
        {points.map((p, i) => (
          <circle
            key={i}
            cx={getX(i)}
            cy={getY(p.val as number)}
            r={i === points.length - 1 ? 4 : 2}
            fill={i === points.length - 1 ? '#ffffff' : color}
            stroke={color}
            strokeWidth="1.5"
          />
        ))}
      </svg>
    </div>
  );
};
