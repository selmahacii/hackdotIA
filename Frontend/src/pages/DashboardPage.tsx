import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Users,
  Smartphone,
  AlertTriangle,
  Activity,
  Sparkles,
  ArrowRight,
  Heart,
  Thermometer,
  Zap,
} from 'lucide-react';
import { dashboardApi } from '../api/dashboard';
import { DashboardStats } from '../types';
import { Card } from '../components/Common/Card';
import { Badge } from '../components/Common/Badge';
import { Spinner } from '../components/Common/Spinner';

export const DashboardPage: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    try {
      const data = await dashboardApi.getStats();
      setStats(data);
    } catch (err: any) {
      setError(err?.message || 'Erreur lors du chargement des statistiques');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    // Auto-refresh every 30s
    const timer = setInterval(fetchStats, 30000);
    return () => clearInterval(timer);
  }, []);

  if (isLoading) {
    return <Spinner size="lg" className="py-20" />;
  }

  if (error || !stats) {
    return (
      <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-500/40 text-rose-300 text-sm">
        {error || 'Impossible de charger les données du tableau de bord.'}
      </div>
    );
  }

  const { kpi, recent_alerts, recent_measurements, ai_engine } = stats;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Tableau de bord</h1>
          <p className="text-xs text-slate-400 mt-1">
            Vue d'ensemble de la télésurveillance et état opérationnel en temps réel
          </p>
        </div>

        {/* AI Engine Status chip */}
        <div className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-indigo-950/40 border border-indigo-500/30">
          <Sparkles className="w-4 h-4 text-indigo-400" />
          <div className="text-xs">
            <span className="text-slate-400 block text-[10px]">Moteur IA</span>
            <span className="font-semibold text-indigo-300">
              Groq ({ai_engine.groq_model || 'openai/gpt-oss-20b'})
            </span>
          </div>
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse ml-1" />
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Residents under care */}
        <Card className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Résidents suivis</p>
            <p className="text-2xl font-bold text-slate-100 mt-0.5">{kpi.residents_count}</p>
          </div>
        </Card>

        {/* Connected devices */}
        <Card className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Smartphone className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Appareils en ligne</p>
            <div className="flex items-baseline gap-1 mt-0.5">
              <span className="text-2xl font-bold text-slate-100">{kpi.devices_online}</span>
              <span className="text-xs text-slate-500">/ {kpi.devices_total}</span>
            </div>
          </div>
        </Card>

        {/* Open Alerts */}
        <Card className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Alertes en cours</p>
            <p className="text-2xl font-bold text-slate-100 mt-0.5">{kpi.open_alerts_total}</p>
          </div>
        </Card>

        {/* Critical Alerts */}
        <Card className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <Zap className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Alertes critiques</p>
            <p className="text-2xl font-bold text-rose-400 mt-0.5">{kpi.critical_alerts}</p>
          </div>
        </Card>
      </div>

      {/* Main Section: Alerts + Telemetry */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Alerts Feed */}
        <Card
          title="Dernières alertes"
          subtitle="Détection déterministe avec enrichissement Groq"
          action={
            <Link
              to="/alerts"
              className="text-xs text-brand-400 hover:text-brand-300 font-medium flex items-center gap-1"
            >
              Toutes les alertes <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          }
        >
          {recent_alerts.length === 0 ? (
            <p className="text-xs text-slate-500 py-8 text-center">Aucune alerte active</p>
          ) : (
            <div className="divide-y divide-slate-800">
              {recent_alerts.map((alert) => (
                <Link
                  key={alert.id}
                  to={`/alerts/${alert.id}`}
                  className="py-3 flex items-center justify-between hover:bg-slate-800/40 px-2 rounded-lg transition"
                >
                  <div className="min-w-0 pr-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge label={alert.severity} variant="severity" />
                      <span className="text-xs font-semibold text-slate-200">
                        {alert.elderly_name}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 truncate">{alert.title}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-[10px] text-slate-500 block">
                      {new Date(alert.occurred_at).toLocaleTimeString()}
                    </span>
                    {alert.has_ai && (
                      <span className="text-[10px] text-indigo-400 font-medium inline-flex items-center gap-0.5">
                        <Sparkles className="w-2.5 h-2.5" /> IA
                      </span>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Card>

        {/* Recent Sensor Telemetry */}
        <Card
          title="Télémétrie récente"
          subtitle="Dernières mesures transmises par les bracelets"
          action={
            <Link
              to="/measurements"
              className="text-xs text-brand-400 hover:text-brand-300 font-medium flex items-center gap-1"
            >
              Historique complet <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          }
        >
          {recent_measurements.length === 0 ? (
            <p className="text-xs text-slate-500 py-8 text-center">Aucune mesure enregistrée</p>
          ) : (
            <div className="space-y-2.5">
              {recent_measurements.slice(0, 5).map((m) => (
                <div
                  key={m.id}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs"
                >
                  <span className="text-slate-400">
                    {new Date(m.measured_at).toLocaleTimeString()}
                  </span>
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1 text-slate-200">
                      <Heart className="w-3.5 h-3.5 text-rose-500" />
                      {m.bpm ? `${m.bpm} bpm` : '--'}
                    </span>
                    <span className="flex items-center gap-1 text-slate-200">
                      <Activity className="w-3.5 h-3.5 text-blue-400" />
                      {m.spo2 ? `${m.spo2} %` : '--'}
                    </span>
                    <span className="flex items-center gap-1 text-slate-200">
                      <Thermometer className="w-3.5 h-3.5 text-amber-400" />
                      {m.temperature_c ? `${m.temperature_c} °C` : '--'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
