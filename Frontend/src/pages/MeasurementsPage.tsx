import React, { useEffect, useState } from 'react';
import { Activity, Heart, Thermometer, Battery, MapPin, RefreshCw } from 'lucide-react';
import { measurementsApi } from '../api/measurements';
import { elderlyApi } from '../api/elderly';
import { Measurement, ElderlyPerson } from '../types';
import { Card } from '../components/Common/Card';
import { Button } from '../components/Common/Button';
import { Spinner } from '../components/Common/Spinner';
import { EmptyState } from '../components/Common/EmptyState';

export const MeasurementsPage: React.FC = () => {
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [residents, setResidents] = useState<ElderlyPerson[]>([]);
  const [selectedElderlyId, setSelectedElderlyId] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [measList, resList] = await Promise.all([
        measurementsApi.list({
          elderlyId: selectedElderlyId || undefined,
          limit: 100,
        }),
        elderlyApi.list(),
      ]);
      setMeasurements(measList);
      setResidents(resList);
    } catch (err: any) {
      alert(err.message || 'Erreur lors du chargement des mesures');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedElderlyId]);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
            Registre Télémétrique des Capteurs
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Données physiologiques, cinématiques et environnementales collectées par les dispositifs ESP32
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Resident Filter */}
          <select
            value={selectedElderlyId}
            onChange={(e) => setSelectedElderlyId(e.target.value)}
            className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none"
          >
            <option value="">Tous les résidents</option>
            {residents.map((r) => (
              <option key={r.id} value={r.id}>
                {r.first_name} {r.last_name}
              </option>
            ))}
          </select>

          <Button
            size="sm"
            variant="secondary"
            icon={<RefreshCw className="w-3.5 h-3.5" />}
            onClick={loadData}
          >
            Actualiser
          </Button>
        </div>
      </div>

      {/* Telemetry Table */}
      {isLoading ? (
        <Spinner size="lg" className="py-20" />
      ) : measurements.length === 0 ? (
        <EmptyState
          title="Aucune mesure enregistrée"
          description="Aucune télémétrie n'a encore été reçue des capteurs pour la sélection actuelle."
          icon={<Activity className="w-10 h-10 text-slate-500" />}
        />
      ) : (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-700/60 font-semibold uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-3.5 px-4">Date / Heure</th>
                  <th className="py-3.5 px-4">Fréquence (BPM)</th>
                  <th className="py-3.5 px-4">SpO2 (%)</th>
                  <th className="py-3.5 px-4">Contact Doigt</th>
                  <th className="py-3.5 px-4">Température (°C)</th>
                  <th className="py-3.5 px-4">Accélération (g)</th>
                  <th className="py-3.5 px-4">GPS</th>
                  <th className="py-3.5 px-4">Batterie</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {measurements.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                      {new Date(m.measured_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-100">
                      <span className="flex items-center gap-1.5">
                        <Heart className="w-3.5 h-3.5 text-rose-500" />
                        {m.bpm ? `${m.bpm} bpm` : '--'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-semibold text-slate-100">
                      <span className="flex items-center gap-1.5">
                        <Activity className="w-3.5 h-3.5 text-sky-400" />
                        {m.spo2 ? `${m.spo2} %` : '--'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {m.finger_detected ? (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-500/40">
                          Détecté
                        </span>
                      ) : (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-500">
                          Non détecté
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-200">
                      <span className="flex items-center gap-1.5">
                        <Thermometer className="w-3.5 h-3.5 text-amber-400" />
                        {m.temperature_c ? `${m.temperature_c} °C` : '--'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono">
                      {m.accel_magnitude_g ? `${m.accel_magnitude_g.toFixed(2)} g` : '--'}
                    </td>
                    <td className="py-3 px-4">
                      {m.gps_fix_valid && m.gps_latitude && m.gps_longitude ? (
                        <span className="flex items-center gap-1 text-[11px] text-emerald-400">
                          <MapPin className="w-3.5 h-3.5" />
                          {m.gps_latitude.toFixed(4)}, {m.gps_longitude.toFixed(4)}
                        </span>
                      ) : (
                        <span className="text-[11px] text-slate-500">Pas de fix</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span className="flex items-center gap-1 text-slate-300">
                        <Battery className="w-3.5 h-3.5 text-slate-400" />
                        {m.battery_level ? `${m.battery_level.toFixed(0)}%` : '--'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
};
