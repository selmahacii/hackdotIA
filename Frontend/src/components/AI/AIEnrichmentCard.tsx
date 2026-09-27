import React, { useState } from 'react';
import { Sparkles, Brain, Clock, ShieldCheck, RefreshCw, AlertCircle } from 'lucide-react';
import { AIAnalysis } from '../../types';
import { Button } from '../Common/Button';
import { alertsApi } from '../../api/alerts';

interface AIEnrichmentCardProps {
  alertId: string;
  analyses?: AIAnalysis[];
  canTrigger?: boolean;
}

export const AIEnrichmentCard: React.FC<AIEnrichmentCardProps> = ({
  alertId,
  analyses = [],
  canTrigger = true,
}) => {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [currentAnalyses, setCurrentAnalyses] = useState<AIAnalysis[]>(analyses);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const latestAnalysis = currentAnalyses.length > 0 ? currentAnalyses[currentAnalyses.length - 1] : null;

  const handleTrigger = async () => {
    setIsRefreshing(true);
    setErrorMsg(null);
    try {
      const result = await alertsApi.triggerAi(alertId, true);
      setCurrentAnalyses((prev) => [...prev, result]);
    } catch (err: any) {
      setErrorMsg(err.message || "Échec de l'enrichissement IA");
    } finally {
      setIsRefreshing(false);
    }
  };

  if (!latestAnalysis && !canTrigger) {
    return null;
  }

  return (
    <div className="border border-indigo-500/40 bg-gradient-to-br from-slate-900/90 via-indigo-950/20 to-slate-900/90 rounded-2xl p-5 shadow-xl relative overflow-hidden">
      {/* Decorative ambient gradient */}
      <div className="absolute top-0 right-0 -mt-4 -mr-4 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-indigo-500/20 pb-4 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-base font-semibold text-slate-100">
                Enrichissement IA — Analyse Cinématique
              </h4>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Groq AI
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Couche secondaire d'aide à la décision — Analyse des capteurs sans diagnostic médical
            </p>
          </div>
        </div>

        {canTrigger && (
          <Button
            size="sm"
            variant="secondary"
            icon={<RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />}
            onClick={handleTrigger}
            isLoading={isRefreshing}
          >
            Réanalyser (Groq)
          </Button>
        )}
      </div>

      {errorMsg && (
        <div className="mb-4 p-3 rounded-lg bg-red-950/60 border border-red-500/40 text-red-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {!latestAnalysis ? (
        <div className="py-6 text-center">
          <Brain className="w-10 h-10 text-indigo-400/40 mx-auto mb-2" />
          <p className="text-sm text-slate-300 font-medium">Aucune analyse IA disponible</p>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto mb-4">
            L'alerte a été créée par les règles déterministes. Cliquez pour générer un enrichissement contextuel via Groq.
          </p>
          {canTrigger && (
            <Button size="sm" variant="primary" onClick={handleTrigger} isLoading={isRefreshing}>
              Lancer l'analyse Groq
            </Button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {/* Metadata chips */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
            <div className="bg-slate-800/80 border border-slate-700/50 rounded-lg p-2.5">
              <span className="text-slate-400 block text-[11px]">Fournisseur</span>
              <span className="font-semibold text-slate-200 uppercase">{latestAnalysis.provider}</span>
            </div>
            <div className="bg-slate-800/80 border border-slate-700/50 rounded-lg p-2.5">
              <span className="text-slate-400 block text-[11px]">Modèle</span>
              <span className="font-medium text-slate-200 truncate block" title={latestAnalysis.model_name || 'N/A'}>
                {latestAnalysis.model_name || 'openai/gpt-oss-20b'}
              </span>
            </div>
            <div className="bg-slate-800/80 border border-slate-700/50 rounded-lg p-2.5">
              <span className="text-slate-400 block text-[11px]">Temps d'inférence</span>
              <span className="font-medium text-slate-200 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                {latestAnalysis.latency_ms ? `${latestAnalysis.latency_ms} ms` : '< 1s'}
              </span>
            </div>
            <div className="bg-slate-800/80 border border-slate-700/50 rounded-lg p-2.5">
              <span className="text-slate-400 block text-[11px]">Confiance estimée</span>
              <div className="flex items-center gap-2 mt-0.5">
                <div className="flex-1 bg-slate-700 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-400 h-full rounded-full transition-all"
                    style={{ width: `${Math.round(latestAnalysis.confidence * 100)}%` }}
                  />
                </div>
                <span className="font-semibold text-indigo-300">
                  {Math.round(latestAnalysis.confidence * 100)}%
                </span>
              </div>
            </div>
          </div>

          {/* Event Hypothesis */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3.5">
            <span className="text-xs font-semibold text-indigo-300 uppercase tracking-wider block mb-1">
              Événement physique suspecté
            </span>
            <p className="text-sm text-slate-100 font-medium">
              {latestAnalysis.possible_event || "Mouvement anormal détecté par les capteurs"}
            </p>
          </div>

          {/* Explanation */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3.5">
            <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block mb-1">
              Explication objective des signaux
            </span>
            <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
              {latestAnalysis.explanation}
            </p>
          </div>

          {/* Recommended actions */}
          <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3.5">
            <div className="flex items-center gap-1.5 mb-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-semibold text-emerald-300 uppercase tracking-wider">
                Vérifications opérationnelles recommandées
              </span>
            </div>
            <p className="text-sm text-slate-200 leading-relaxed">
              {latestAnalysis.recommended_action}
            </p>
          </div>

          {/* Regulatory & Safety Disclaimer */}
          <div className="flex items-start gap-2 p-2.5 rounded-lg bg-indigo-950/40 border border-indigo-500/20 text-[11px] text-slate-400">
            <Sparkles className="w-3.5 h-3.5 text-indigo-400 mt-0.5 shrink-0" />
            <p>
              <strong className="text-indigo-300">Règle de sécurité :</strong> Cet enrichissement est fourni à titre indicatif par le modèle d'IA et ne constitue pas un diagnostic médical. L'alerte primaire reste strictement régie par les règles déterministes.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
