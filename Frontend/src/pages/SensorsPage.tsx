import React, { useEffect, useState } from 'react';
import { Cpu, RefreshCw, Heart, Activity, Thermometer, Navigation, ShieldCheck } from 'lucide-react';
import { sensorsApi } from '../api/sensors';
import { SensorHealthRecord } from '../types';
import { Card } from '../components/Common/Card';
import { Badge } from '../components/Common/Badge';
import { Button } from '../components/Common/Button';
import { Spinner } from '../components/Common/Spinner';
import { EmptyState } from '../components/Common/EmptyState';

export const SensorsPage: React.FC = () => {
  const [records, setRecords] = useState<SensorHealthRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadSensors = async () => {
    setIsLoading(true);
    try {
      const data = await sensorsApi.list();
      setRecords(data);
    } catch (err: any) {
      alert(err.message || 'Erreur lors du chargement de l’état des capteurs');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSensors();
  }, []);

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
            Intégrité et Diagnostics Matériels
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Supervision de l'état de fonctionnement des modules I²C, OneWire et UART (ESP32)
          </p>
        </div>

        <Button
          size="sm"
          variant="secondary"
          icon={<RefreshCw className="w-3.5 h-3.5" />}
          onClick={loadSensors}
        >
          Actualiser les diagnostics
        </Button>
      </div>

      {isLoading ? (
        <Spinner size="lg" className="py-20" />
      ) : records.length === 0 ? (
        <EmptyState
          title="Aucun diagnostic matériel"
          description="Aucun rapport d'intégrité capteur n'est actuellement disponible."
          icon={<Cpu className="w-10 h-10 text-slate-500" />}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {records.map((rec) => (
            <Card
              key={rec.device_id}
              title={rec.device_name || rec.device_uid}
              subtitle={`Résident : ${rec.elderly_name}`}
              action={<Badge label={rec.device_status} variant="device" />}
            >
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs mb-4">
                {/* MAX30102 */}
                <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700/60">
                  <div className="flex items-center gap-1.5 text-slate-400 mb-1">
                    <Heart className="w-3.5 h-3.5 text-rose-500" />
                    <span className="font-semibold text-[11px]">MAX30102</span>
                  </div>
                  <span className="text-[10px] text-slate-500 block mb-1.5">Cardio / SpO2</span>
                  <Badge label={rec.max30102_status} variant="sensor" />
                </div>

                {/* MPU6050 */}
                <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700/60">
                  <div className="flex items-center gap-1.5 text-slate-400 mb-1">
                    <Activity className="w-3.5 h-3.5 text-sky-400" />
                    <span className="font-semibold text-[11px]">MPU6050</span>
                  </div>
                  <span className="text-[10px] text-slate-500 block mb-1.5">Accéléromètre</span>
                  <Badge label={rec.mpu6050_status} variant="sensor" />
                </div>

                {/* DHT11 */}
                <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700/60">
                  <div className="flex items-center gap-1.5 text-slate-400 mb-1">
                    <Thermometer className="w-3.5 h-3.5 text-amber-400" />
                    <span className="font-semibold text-[11px]">DHT11</span>
                  </div>
                  <span className="text-[10px] text-slate-500 block mb-1.5">Temp / Humidité</span>
                  <Badge label={rec.dht11_status} variant="sensor" />
                </div>

                {/* GPS */}
                <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-700/60">
                  <div className="flex items-center gap-1.5 text-slate-400 mb-1">
                    <Navigation className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="font-semibold text-[11px]">GPS NEO-6M</span>
                  </div>
                  <span className="text-[10px] text-slate-500 block mb-1.5">Localisation</span>
                  <Badge label={rec.gps_status} variant="sensor" />
                </div>
              </div>

              <div className="pt-3 border-t border-slate-700/40 flex items-center justify-between text-[11px] text-slate-400">
                <span className="flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-slate-500" />
                  Dernier auto-test : {rec.last_checked_at ? new Date(rec.last_checked_at).toLocaleTimeString() : 'N/A'}
                </span>
                <span className="font-mono text-slate-500">UID: {rec.device_uid}</span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
