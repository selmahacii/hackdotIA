import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Radio, Volume2, VolumeX, Sparkles, RefreshCw, Eye } from 'lucide-react';
import { useWebSocket } from '../context/WebSocketContext';
import { useAuth } from '../context/AuthContext';
import { Card } from '../components/Common/Card';
import { Badge } from '../components/Common/Badge';
import { Button } from '../components/Common/Button';
import { alertsApi } from '../api/alerts';
import { Alert } from '../types';

export const MonitoringPage: React.FC = () => {
  const { isConnected, isConnecting, reconnect, liveAlerts } = useWebSocket();
  const { canMutate } = useAuth();
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Play synthetic audio chime for alerts
  const playAlertSound = (severity: string) => {
    if (!soundEnabled) return;
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);

      if (severity === 'CRITICAL') {
        osc.frequency.setValueAtTime(880, audioCtx.currentTime); // High pitch
        gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.4);
      } else {
        osc.frequency.setValueAtTime(440, audioCtx.currentTime);
        gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.2);
      }
    } catch {
      // AudioContext could be blocked by browser policy until interaction
    }
  };

  // Initial fetch of active alerts
  const fetchActiveAlerts = async () => {
    setIsLoading(true);
    try {
      const res = await alertsApi.list({ limit: 50 });
      setAlerts(res.items);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchActiveAlerts();
  }, []);

  // When a live alert arrives via WebSocket
  useEffect(() => {
    if (liveAlerts.length > 0) {
      const latest = liveAlerts[0];
      setAlerts((prev) => {
        // If already in list, update it
        const exists = prev.some((a) => a.id === latest.id);
        if (exists) {
          return prev.map((a) => (a.id === latest.id ? { ...a, ...latest } : a));
        }
        return [latest, ...prev];
      });
      playAlertSound(latest.severity);
    }
  }, [liveAlerts]);

  const handleAck = async (id: string) => {
    try {
      await alertsApi.ack(id);
      setAlerts((prev) =>
        prev.map((a) => (a.id === id ? { ...a, status: 'ACKNOWLEDGED' } : a))
      );
    } catch (err: any) {
      alert(err.message || "Impossible d'acquitter l'alerte");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
              Surveillance Médicale en Direct
            </h1>
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 text-xs font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              FLUX WEBSOCKET ACTIF
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Réception instantanée des alertes et anomalies physiques transmises par les capteurs
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Sound toggle */}
          <Button
            size="sm"
            variant="secondary"
            icon={soundEnabled ? <Volume2 className="w-4 h-4 text-emerald-400" /> : <VolumeX className="w-4 h-4 text-slate-400" />}
            onClick={() => setSoundEnabled(!soundEnabled)}
          >
            {soundEnabled ? 'Son activé' : 'Son coupé'}
          </Button>

          {/* Reconnect button */}
          <Button
            size="sm"
            variant="secondary"
            icon={<RefreshCw className={`w-3.5 h-3.5 ${isConnecting ? 'animate-spin' : ''}`} />}
            onClick={reconnect}
          >
            Reconnecter WebSocket
          </Button>
        </div>
      </div>

      {/* Connection banner if disconnected */}
      {!isConnected && (
        <div className="p-4 rounded-xl bg-amber-950/60 border border-amber-500/40 text-amber-200 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-amber-400 animate-pulse" />
            <span>
              Connexion WebSocket interrompue. Tentative de reconnexion automatique en cours...
            </span>
          </div>
          <Button size="sm" variant="warning" onClick={reconnect}>
            Forcer la reconnexion
          </Button>
        </div>
      )}

      {/* Live Stream Panel */}
      <Card
        title="Flux d'événements et alertes physiques"
        subtitle="Mise à jour en temps réel via broker MQTT et WebSocket"
      >
        {alerts.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-sm">
            Aucun incident en cours. Les résidents sont sous surveillance normale.
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-4 rounded-xl border transition-all ${
                  alert.severity === 'CRITICAL'
                    ? 'bg-red-950/30 border-red-500/50 shadow-md shadow-red-950/30'
                    : alert.severity === 'HIGH'
                    ? 'bg-orange-950/20 border-orange-500/40'
                    : 'bg-slate-900/60 border-slate-800'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <Badge label={alert.severity} variant="severity" />
                    <Badge label={alert.status} variant="status" />
                    <span className="text-xs font-bold text-slate-200">
                      {alert.elderly_name || 'Résident'}
                    </span>
                    {alert.device_name && (
                      <span className="text-[11px] text-slate-500">&bull; {alert.device_name}</span>
                    )}
                  </div>

                  <span className="text-xs text-slate-400">
                    {new Date(alert.occurred_at).toLocaleString()}
                  </span>
                </div>

                <div className="text-sm font-semibold text-slate-100 mb-1">{alert.title}</div>
                <p className="text-xs text-slate-400 mb-3">{alert.description}</p>

                {/* AI Summary Banner if enriched */}
                {alert.ai_summary && (
                  <div className="mb-3 p-2.5 rounded-lg bg-indigo-950/40 border border-indigo-500/30 text-xs text-indigo-200 flex items-start gap-2">
                    <Sparkles className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold text-indigo-300 block text-[11px]">
                        Enrichissement Groq AI :
                      </span>
                      <span>{alert.ai_summary}</span>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                  <Link
                    to={`/alerts/${alert.id}`}
                    className="text-xs text-brand-400 hover:text-brand-300 font-medium flex items-center gap-1"
                  >
                    <Eye className="w-3.5 h-3.5" /> Voir l'analyse complète
                  </Link>

                  <div className="flex items-center gap-2">
                    {canMutate && alert.status === 'OPEN' && (
                      <Button size="sm" variant="secondary" onClick={() => handleAck(alert.id)}>
                        Acquitter
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};
