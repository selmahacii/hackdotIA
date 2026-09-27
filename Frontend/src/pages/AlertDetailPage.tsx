import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  User,
  Smartphone,
  CheckCircle,
  Layers,
  Sparkles,
  MessageSquare,
} from 'lucide-react';
import { alertsApi } from '../api/alerts';
import { Alert } from '../types';
import { useAuth } from '../context/AuthContext';
import { Card } from '../components/Common/Card';
import { Badge } from '../components/Common/Badge';
import { Button } from '../components/Common/Button';
import { Spinner } from '../components/Common/Spinner';
import { AIEnrichmentCard } from '../components/AI/AIEnrichmentCard';

export const AlertDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { canMutate } = useAuth();

  const [alert, setAlert] = useState<Alert | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const loadAlert = async () => {
    if (!id) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await alertsApi.getById(id);
      setAlert(data);
    } catch (err: any) {
      setErrorMsg(
        err.status === 403
          ? "Accès non autorisé : cette alerte concerne un résident qui ne vous est pas assigné."
          : err.message || "Erreur lors du chargement de l'alerte"
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAlert();
  }, [id]);

  const handleAck = async () => {
    if (!alert) return;
    setActionLoading(true);
    try {
      const res = await alertsApi.ack(alert.id);
      setAlert({
        ...alert,
        status: res.status,
        acknowledged_at: res.acknowledged_at,
        acknowledged_by: res.acknowledged_by,
      });
    } catch (err: any) {
      window.alert(err.message || "Échec de l'acquittement");
    } finally {
      setActionLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!alert) return;
    setActionLoading(true);
    try {
      const res = await alertsApi.resolve(alert.id);
      setAlert({
        ...alert,
        status: res.status,
        resolved_at: res.resolved_at,
      });
    } catch (err: any) {
      window.alert(err.message || 'Échec de la résolution');
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenAIChat = () => {
    if (!alert) return;
    window.dispatchEvent(
      new CustomEvent('open-ai-chat', {
        detail: {
          elderly_id: alert.elderly_id,
          alert_id: alert.id,
          context_label: `${alert.title} (${alert.elderly_name || 'Résident'})`,
          initial_prompt: `Peux-tu m'expliquer en détail les anomalies physiques et cinématiques de cette alerte (${alert.title}) et les vérifications recommandées ?`,
        },
      })
    );
  };

  if (isLoading) {
    return <Spinner size="lg" className="py-20" />;
  }

  if (errorMsg || !alert) {
    return (
      <div className="space-y-4">
        <Link to="/alerts" className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> Retour à la liste des alertes
        </Link>
        <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-500/40 text-rose-300 text-sm">
          {errorMsg || 'Alerte non trouvée.'}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Back button */}
      <div>
        <Link
          to="/alerts"
          className="text-xs text-slate-400 hover:text-slate-200 inline-flex items-center gap-1 mb-3 transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Retour aux alertes
        </Link>

        {/* Title banner */}
        <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Badge label={alert.severity} variant="severity" />
              <Badge label={alert.status} variant="status" />
              <span className="text-xs font-mono text-slate-500 uppercase tracking-wider">
                ID: {alert.id.slice(0, 8)}
              </span>
            </div>
            <h1 className="text-xl font-bold text-slate-100">{alert.title}</h1>
            <p className="text-xs text-slate-400 mt-1">{alert.description}</p>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Button
              variant="secondary"
              icon={<Sparkles className="w-4 h-4 text-indigo-400" />}
              onClick={handleOpenAIChat}
              className="border-indigo-500/40 text-indigo-300 hover:bg-indigo-950/40"
            >
              Interroger l'IA (Chat)
            </Button>

            {canMutate && alert.status === 'OPEN' && (
              <Button variant="secondary" onClick={handleAck} isLoading={actionLoading}>
                Acquitter l'alerte
              </Button>
            )}
            {canMutate && alert.status !== 'RESOLVED' && (
              <Button
                variant="success"
                icon={<CheckCircle className="w-4 h-4" />}
                onClick={handleResolve}
                isLoading={actionLoading}
              >
                Marquer comme Résolue
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Primary Detection Details (Strictly deterministic) */}
      <Card
        title="Détails de la Détection Primaire (Règles Déterministes)"
        subtitle="Origine de l'événement et contexte physique mesuré par les capteurs embarqués"
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-500 block mb-1">Résident concerné</span>
            <Link
              to={`/elderly/${alert.elderly_id}`}
              className="text-brand-400 hover:text-brand-300 font-semibold flex items-center gap-1.5"
            >
              <User className="w-3.5 h-3.5" />
              {alert.elderly_name || 'Fiche résident'}
            </Link>
          </div>

          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-500 block mb-1">Capteur / Appareil</span>
            <span className="text-slate-200 font-medium flex items-center gap-1.5">
              <Smartphone className="w-3.5 h-3.5 text-slate-400" />
              {alert.device_name || alert.device_uid || 'Bracelet ESP32'}
            </span>
          </div>

          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-500 block mb-1">Date et heure</span>
            <span className="text-slate-200 font-medium flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              {new Date(alert.occurred_at).toLocaleString()}
            </span>
          </div>

          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
            <span className="text-slate-500 block mb-1">Source de détection</span>
            <span className="text-slate-200 font-medium flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-slate-400" />
              {alert.source}
            </span>
          </div>
        </div>

        {/* Operational Context payload if present */}
        {alert.context && Object.keys(alert.context).length > 0 && (
          <div className="mt-4 pt-3 border-t border-slate-800 text-xs">
            <span className="text-slate-400 font-medium block mb-2">Données contextuelles capteurs :</span>
            <pre className="p-3 rounded-xl bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300 overflow-x-auto">
              {JSON.stringify(alert.context, null, 2)}
            </pre>
          </div>
        )}

        {/* Acknowledgment history */}
        {(alert.acknowledged_at || alert.resolved_at) && (
          <div className="mt-4 pt-3 border-t border-slate-800 text-xs flex flex-wrap gap-4 text-slate-400">
            {alert.acknowledged_at && (
              <span>
                Acquittée le {new Date(alert.acknowledged_at).toLocaleString()}
                {alert.acknowledged_by ? ` par ${alert.acknowledged_by}` : ''}
              </span>
            )}
            {alert.resolved_at && (
              <span>Résolue le {new Date(alert.resolved_at).toLocaleString()}</span>
            )}
          </div>
        )}
      </Card>

      {/* Secondary AI Enrichment Layer (Groq AI) */}
      <AIEnrichmentCard
        alertId={alert.id}
        analyses={alert.ai_analyses}
        canTrigger={canMutate}
      />
    </div>
  );
};
