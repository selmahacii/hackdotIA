import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Phone, Calendar, Activity } from 'lucide-react';
import { elderlyApi } from '../api/elderly';
import { devicesApi } from '../api/devices';
import { measurementsApi } from '../api/measurements';
import { alertsApi } from '../api/alerts';
import { ElderlyPerson, Device, MeasurementHistoryPoint, Alert } from '../types';
import { Card } from '../components/Common/Card';
import { Badge } from '../components/Common/Badge';
import { Spinner } from '../components/Common/Spinner';
import { VitalTrendChart } from '../components/Charts/VitalTrendChart';

export const ElderlyDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const [resident, setResident] = useState<ElderlyPerson | null>(null);
  const [device, setDevice] = useState<Device | null>(null);
  const [history, setHistory] = useState<MeasurementHistoryPoint[]>([]);
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    const loadData = async () => {
      setIsLoading(true);
      setErrorMsg(null);
      try {
        const [resData, devList, histData, alertsRes] = await Promise.all([
          elderlyApi.getById(id),
          devicesApi.list(id),
          measurementsApi.getHistory(id, 60),
          alertsApi.list({ elderlyId: id, limit: 10 }),
        ]);

        setResident(resData);
        setDevice(devList.length > 0 ? devList[0] : null);
        setHistory(histData);
        setRecentAlerts(alertsRes.items);
      } catch (err: any) {
        setErrorMsg(
          err.status === 403
            ? "Accès non autorisé : ce résident ne fait pas partie de vos affectations soignantes."
            : err.message || 'Erreur lors du chargement des données'
        );
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [id]);

  if (isLoading) {
    return <Spinner size="lg" className="py-20" />;
  }

  if (errorMsg || !resident) {
    return (
      <div className="space-y-4">
        <Link to="/elderly" className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> Retour à la liste des résidents
        </Link>
        <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-500/40 text-rose-300 text-sm">
          {errorMsg || 'Résident non trouvé.'}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button & title */}
      <div>
        <Link
          to="/elderly"
          className="text-xs text-slate-400 hover:text-slate-200 inline-flex items-center gap-1 mb-2 transition"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Retour aux résidents
        </Link>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-brand-600/20 border border-brand-500/30 text-brand-400 flex items-center justify-center font-bold text-lg">
              {resident.first_name[0]}
              {resident.last_name[0]}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100">
                {resident.first_name} {resident.last_name}
              </h1>
              <p className="text-xs text-slate-400">
                Fiche de suivi télémétrique individualisée
              </p>
            </div>
          </div>

          <Badge label={resident.is_active ? 'SUIVI ACTIF' : 'INACTIF'} variant="sensor" />
        </div>
      </div>

      {/* Top info grid: Profile & IoT Device */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Profile Card */}
        <Card title="Informations Personnelles" className="md:col-span-2">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-slate-500 block mb-0.5">Date de naissance</span>
              <span className="text-slate-200 font-medium flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-slate-400" />
                {resident.date_of_birth ? new Date(resident.date_of_birth).toLocaleDateString() : 'Non renseigné'}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block mb-0.5">Téléphone résident</span>
              <span className="text-slate-200 font-medium flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5 text-slate-400" />
                {resident.phone || 'Non renseigné'}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block mb-0.5">Contact d'urgence</span>
              <span className="text-slate-200 font-medium">
                {resident.emergency_contact_name || 'Non renseigné'}
              </span>
            </div>
            <div>
              <span className="text-slate-500 block mb-0.5">Téléphone d'urgence</span>
              <span className="text-slate-200 font-medium flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5 text-slate-400" />
                {resident.emergency_contact_phone || 'Non renseigné'}
              </span>
            </div>
          </div>
        </Card>

        {/* Device Card */}
        <Card title="Appareil Connecté">
          {device ? (
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">{device.name || device.device_uid}</span>
                <Badge label={device.status} variant="device" />
              </div>
              <div className="flex items-center justify-between text-slate-300">
                <span>Batterie</span>
                <span className="font-semibold">{device.battery_level ? `${device.battery_level}%` : 'N/A'}</span>
              </div>
              <div className="flex items-center justify-between text-slate-300">
                <span>Signal Wi-Fi</span>
                <span className="font-semibold">{device.wifi_rssi ? `${device.wifi_rssi} dBm` : 'N/A'}</span>
              </div>
              <div className="flex items-center justify-between text-slate-400 pt-2 border-t border-slate-700/40 text-[11px]">
                <span>Dernier contact :</span>
                <span>{device.last_seen_at ? new Date(device.last_seen_at).toLocaleTimeString() : 'N/A'}</span>
              </div>
            </div>
          ) : (
            <div className="py-4 text-center text-xs text-slate-500">
              Aucun bracelet ou capteur n'est actuellement associé.
            </div>
          )}
        </Card>
      </div>

      {/* Vital Trends Section */}
      <div>
        <h3 className="text-base font-semibold text-slate-100 mb-3 flex items-center gap-2">
          <Activity className="w-4 h-4 text-brand-400" />
          Courbes des constantes vitales (Historique en temps réel)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <VitalTrendChart
            data={history}
            metric="bpm"
            label="Fréquence Cardiaque"
            unit="bpm"
            color="#ef4444"
          />
          <VitalTrendChart
            data={history}
            metric="spo2"
            label="Saturation Oxygène"
            unit="%"
            color="#38bdf8"
          />
          <VitalTrendChart
            data={history}
            metric="temperature_c"
            label="Température Cutanée"
            unit="°C"
            color="#f59e0b"
          />
        </div>
      </div>

      {/* Recent Alerts for this Resident */}
      <Card title={`Dernières alertes concernant ${resident.first_name} ${resident.last_name}`}>
        {recentAlerts.length === 0 ? (
          <p className="text-xs text-slate-500 py-6 text-center">Aucune alerte récente enregistrée.</p>
        ) : (
          <div className="divide-y divide-slate-800">
            {recentAlerts.map((a) => (
              <Link
                key={a.id}
                to={`/alerts/${a.id}`}
                className="py-3 flex items-center justify-between hover:bg-slate-800/40 px-2 rounded-lg transition"
              >
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Badge label={a.severity} variant="severity" />
                    <Badge label={a.status} variant="status" />
                    <span className="text-xs font-semibold text-slate-200">{a.title}</span>
                  </div>
                  <p className="text-xs text-slate-400">{a.description}</p>
                </div>
                <span className="text-xs text-slate-500 shrink-0">
                  {new Date(a.occurred_at).toLocaleString()}
                </span>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};
