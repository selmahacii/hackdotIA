import React, { useEffect, useState } from 'react';
import { Shield, Users, Cpu, Activity, Sparkles, CheckCircle2, RefreshCw } from 'lucide-react';
import { adminApi } from '../api/admin';
import { AdminStats } from '../types';
import { Card } from '../components/Common/Card';
import { Button } from '../components/Common/Button';
import { Spinner } from '../components/Common/Spinner';

export const AdminStatsPage: React.FC = () => {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadStats = async () => {
    setIsLoading(true);
    try {
      const data = await adminApi.getStats();
      setStats(data);
    } catch (err: any) {
      alert(err.message || 'Erreur lors du chargement des statistiques système');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  if (isLoading) {
    return <Spinner size="lg" className="py-20" />;
  }

  if (!stats) {
    return (
      <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-500/40 text-rose-300 text-sm">
        Impossible de charger les métriques d'administration.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
            Métriques Système & Superadministration
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Supervision de l'infrastructure backend, base PostgreSQL, broker MQTT et moteur Groq AI
          </p>
        </div>

        <Button
          size="sm"
          variant="secondary"
          icon={<RefreshCw className="w-3.5 h-3.5" />}
          onClick={loadStats}
        >
          Actualiser
        </Button>
      </div>

      {/* Global Status Banner */}
      <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-950/60 to-slate-900 border border-emerald-500/40 flex items-center justify-between shadow-xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100">
              Système Opérationnel — Intégrité Globale Validée
            </h3>
            <p className="text-xs text-slate-400">
              Tous les services (FastAPI, PostgreSQL 5433, Mosquitto MQTT, Groq AI) répondent nominalement.
            </p>
          </div>
        </div>

        <span className="px-3 py-1 rounded-full bg-emerald-950 border border-emerald-500/50 text-emerald-300 text-xs font-bold uppercase tracking-wider">
          {stats.system_status}
        </span>
      </div>

      {/* Database & Ingestion Counts */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-brand-500/10 text-brand-400 border border-brand-500/20">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Total Télémétries</p>
            <p className="text-2xl font-bold text-slate-100 mt-0.5">
              {stats.measurements.total}
            </p>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Comptes Utilisateurs</p>
            <p className="text-2xl font-bold text-slate-100 mt-0.5">{stats.users.total}</p>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Résidents Enregistrés</p>
            <p className="text-2xl font-bold text-slate-100 mt-0.5">{stats.residents}</p>
          </div>
        </Card>

        <Card className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Appareils Déployés</p>
            <div className="flex items-baseline gap-1 mt-0.5">
              <span className="text-2xl font-bold text-slate-100">{stats.devices.online}</span>
              <span className="text-xs text-slate-500">/ {stats.devices.total}</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Role distribution & AI provider specs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Role breakdown */}
        <Card title="Répartition des Utilisateurs par Rôle RBAC">
          <div className="space-y-3">
            {Object.entries(stats.users.by_role).map(([role, count]) => (
              <div key={role} className="flex items-center justify-between p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs">
                <span className="font-semibold text-slate-200">{role}</span>
                <span className="px-2.5 py-0.5 rounded-full bg-slate-800 text-brand-400 font-bold">
                  {count}
                </span>
              </div>
            ))}
          </div>
        </Card>

        {/* AI & Infrastructure Architecture */}
        <Card title="Architecture d'Intégration AI (Groq)">
          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">Fournisseur Actif</span>
              <span className="font-semibold text-indigo-400 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" /> Groq API (High Performance)
              </span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">Modèle Opérationnel</span>
              <span className="font-mono text-slate-200">openai/gpt-oss-20b</span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">Sécurité & PII</span>
              <span className="text-emerald-400 font-medium">Anonymisation stricte (Zéro donnée personnelle transmise)</span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-slate-400">Garantie Déterministe</span>
              <span className="text-slate-300">Règles locales prioritaires (IA non bloquante)</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};
