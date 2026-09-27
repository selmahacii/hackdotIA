import React from 'react';
import { AlertSeverity, AlertStatus, DeviceStatus, SensorStatus } from '../../types';

interface BadgeProps {
  label: string;
  variant?: 'severity' | 'status' | 'device' | 'sensor' | 'role' | 'default';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ label, variant = 'default', className = '' }) => {
  const normalized = label?.toUpperCase() || '';

  let colorClasses = 'bg-slate-700/60 text-slate-300 border-slate-600/50';

  if (variant === 'severity' || variant === 'default') {
    switch (normalized as AlertSeverity) {
      case 'CRITICAL':
        colorClasses = 'bg-red-950/70 text-red-300 border-red-500/60 animate-pulse';
        break;
      case 'HIGH':
        colorClasses = 'bg-orange-950/70 text-orange-300 border-orange-500/60';
        break;
      case 'MEDIUM':
        colorClasses = 'bg-amber-950/60 text-amber-300 border-amber-500/50';
        break;
      case 'LOW':
        colorClasses = 'bg-blue-950/60 text-blue-300 border-blue-500/50';
        break;
      case 'INFO':
        colorClasses = 'bg-slate-800/80 text-slate-300 border-slate-600/40';
        break;
    }
  }

  if (variant === 'status') {
    switch (normalized as AlertStatus) {
      case 'OPEN':
        colorClasses = 'bg-rose-950/80 text-rose-300 border-rose-500/50';
        break;
      case 'ACKNOWLEDGED':
        colorClasses = 'bg-amber-950/80 text-amber-300 border-amber-500/50';
        break;
      case 'RESOLVED':
        colorClasses = 'bg-emerald-950/80 text-emerald-300 border-emerald-500/50';
        break;
    }
  }

  if (variant === 'device') {
    switch (normalized as DeviceStatus) {
      case 'ONLINE':
        colorClasses = 'bg-emerald-950/70 text-emerald-300 border-emerald-500/50';
        break;
      case 'OFFLINE':
        colorClasses = 'bg-rose-950/70 text-rose-300 border-rose-500/50';
        break;
      default:
        colorClasses = 'bg-slate-800 text-slate-400 border-slate-700';
    }
  }

  if (variant === 'sensor') {
    switch (normalized as SensorStatus) {
      case 'HEALTHY':
        colorClasses = 'bg-emerald-950/70 text-emerald-300 border-emerald-500/50';
        break;
      case 'SUSPECT':
        colorClasses = 'bg-amber-950/70 text-amber-300 border-amber-500/50';
        break;
      case 'NO_CONTACT':
      case 'UNAVAILABLE':
        colorClasses = 'bg-rose-950/70 text-rose-300 border-rose-500/50';
        break;
      default:
        colorClasses = 'bg-slate-800 text-slate-400 border-slate-700';
    }
  }

  if (variant === 'role') {
    switch (normalized) {
      case 'SUPERADMIN':
        colorClasses = 'bg-purple-950/80 text-purple-300 border-purple-500/60';
        break;
      case 'ADMIN':
        colorClasses = 'bg-indigo-950/80 text-indigo-300 border-indigo-500/60';
        break;
      case 'CAREGIVER':
        colorClasses = 'bg-teal-950/80 text-teal-300 border-teal-500/60';
        break;
      case 'OPERATOR':
        colorClasses = 'bg-sky-950/80 text-sky-300 border-sky-500/60';
        break;
      case 'READ_ONLY':
        colorClasses = 'bg-slate-800 text-slate-400 border-slate-600/40';
        break;
    }
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colorClasses} ${className}`}
    >
      {label}
    </span>
  );
};
