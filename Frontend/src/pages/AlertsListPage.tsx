import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle,
  Eye,
  Sparkles,
  RefreshCw,
  Search,
} from 'lucide-react';
import { alertsApi } from '../api/alerts';
import { Alert, AlertSeverity, AlertStatus } from '../types';
import { useAuth } from '../context/AuthContext';
import { Badge } from '../components/Common/Badge';
import { Button } from '../components/Common/Button';
import { Spinner } from '../components/Common/Spinner';
import { EmptyState } from '../components/Common/EmptyState';

export const AlertsListPage: React.FC = () => {
  const { canMutate } = useAuth();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  const loadAlerts = async () => {
    setIsLoading(true);
    try {
      const res = await alertsApi.list({
        severity: severityFilter !== 'ALL' ? (severityFilter as AlertSeverity) : undefined,
        status: statusFilter !== 'ALL' ? (statusFilter as AlertStatus) : undefined,
        limit: 100,
      });
      setAlerts(res.items);
    } catch (err: any) {
      alert(err.message || 'Erreur lors du chargement des alertes');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, [severityFilter, statusFilter]);

  const handleAck = async (id: string) => {
    try {
      await alertsApi.ack(id);
      setAlerts((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: 'ACKNOWLEDGED' } : a))
      );
    } catch (err: any) {
      alert(err.message || "Échec de l'acquittement");
    }
  };

  const handleResolve = async (id: string) => {
    try {
      await alertsApi.resolve(id);
      setAlerts((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: 'RESOLVED' } : a))
      );
    } catch (err: any) {
      alert(err.message || 'Échec de la résolution');
    }
  };

  const filtered = alerts.filter(
    (a) =>
      a.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (a.elderly_name && a.elderly_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (a.description && a.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
            Registre des Alertes & Événements
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Détection déterministe, acquittement soignant et enrichissement cinématique Groq AI
          </p>
        </div>

        <Button
          size="sm"
          variant="secondary"
          icon={<RefreshCw className="w-3.5 h-3.5" />}
          onClick={loadAlerts}
        >
          Actualiser
        </Button>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center gap-3 bg-slate-900/80 p-3.5 rounded-2xl border border-slate-800">
        <div className="flex-1 min-w-[200px] relative">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filtrer par résident, titre..."
            className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-700/80 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>

        {/* Severity */}
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="px-3 py-1.5 bg-slate-950 border border-slate-700/80 rounded-lg text-xs text-slate-200 focus:outline-none"
        >
          <option value="ALL">Toutes sévérités</option>
          <option value="CRITICAL">Critique</option>
          <option value="HIGH">Haute</option>
          <option value="MEDIUM">Moyenne</option>
          <option value="LOW">Basse</option>
          <option value="INFO">Info</option>
        </select>

        {/* Status */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-1.5 bg-slate-950 border border-slate-700/80 rounded-lg text-xs text-slate-200 focus:outline-none"
        >
          <option value="ALL">Tous statuts</option>
          <option value="OPEN">Ouvert</option>
          <option value="ACKNOWLEDGED">Acquitté</option>
          <option value="RESOLVED">Résolu</option>
        </select>
      </div>

      {/* Alerts Table/List */}
      {isLoading ? (
        <Spinner size="lg" className="py-20" />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="Aucune alerte correspondante"
          description="Aucune alerte ne correspond aux filtres sélectionnés."
          icon={<AlertTriangle className="w-10 h-10 text-slate-500" />}
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((alert) => (
            <div
              key={alert.id}
              className={`p-4 rounded-xl border bg-slate-900/80 transition-all ${
                alert.status === 'RESOLVED'
                  ? 'border-slate-800 opacity-70'
                  : alert.severity === 'CRITICAL'
                  ? 'border-red-500/50 shadow-sm shadow-red-950/20'
                  : 'border-slate-800'
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <Badge label={alert.severity} variant="severity" />
                  <Badge label={alert.status} variant="status" />
                  <span className="text-xs font-semibold text-slate-200">
                    {alert.elderly_name || 'Résident'}
                  </span>
                  {alert.device_name && (
                    <span className="text-[11px] text-slate-500">&bull; {alert.device_name}</span>
                  )}
                </div>

                <div className="flex items-center gap-3 text-xs text-slate-400">
                  {alert.has_ai_analysis && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-400 bg-indigo-950/50 border border-indigo-500/30 px-2 py-0.5 rounded-md">
                      <Sparkles className="w-3 h-3" /> Groq IA
                    </span>
                  )}
                  <span>{new Date(alert.occurred_at).toLocaleString()}</span>
                </div>
              </div>

              <h3 className="text-sm font-semibold text-slate-100">{alert.title}</h3>
              <p className="text-xs text-slate-400 mt-0.5 mb-3">{alert.description}</p>

              {/* Actions Footer */}
              <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                <Link
                  to={`/alerts/${alert.id}`}
                  className="text-xs text-brand-400 hover:text-brand-300 font-medium flex items-center gap-1"
                >
                  <Eye className="w-3.5 h-3.5" /> Fiche d'alerte et enrichissement &rarr;
                </Link>

                <div className="flex items-center gap-2">
                  {canMutate && alert.status === 'OPEN' && (
                    <Button size="sm" variant="secondary" onClick={() => handleAck(alert.id)}>
                      Acquitter
                    </Button>
                  )}
                  {canMutate && alert.status !== 'RESOLVED' && (
                    <Button
                      size="sm"
                      variant="success"
                      icon={<CheckCircle className="w-3.5 h-3.5" />}
                      onClick={() => handleResolve(alert.id)}
                    >
                      Résoudre
                    </Button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
