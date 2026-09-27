import React, { useEffect, useState } from 'react';
import { Smartphone, Plus, Battery, Wifi, RefreshCw } from 'lucide-react';
import { devicesApi } from '../api/devices';
import { elderlyApi } from '../api/elderly';
import { Device, ElderlyPerson } from '../types';
import { useAuth } from '../context/AuthContext';
import { Card } from '../components/Common/Card';
import { Badge } from '../components/Common/Badge';
import { Button } from '../components/Common/Button';
import { Modal } from '../components/Common/Modal';
import { Spinner } from '../components/Common/Spinner';
import { EmptyState } from '../components/Common/EmptyState';

export const DevicesPage: React.FC = () => {
  const { isAdmin } = useAuth();
  const [devices, setDevices] = useState<Device[]>([]);
  const [residents, setResidents] = useState<ElderlyPerson[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // New device form
  const [newDevice, setNewDevice] = useState({
    device_uid: '',
    elderly_id: '',
    name: '',
    firmware_version: '1.2.0-esp6.1',
  });

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [devs, resList] = await Promise.all([devicesApi.list(), elderlyApi.list()]);
      setDevices(devs);
      setResidents(resList);
      if (resList.length > 0 && !newDevice.elderly_id) {
        setNewDevice((prev) => ({ ...prev, elderly_id: resList[0].id }));
      }
    } catch (err: any) {
      alert(err.message || 'Erreur lors du chargement des appareils');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDevice.device_uid || !newDevice.elderly_id) {
      alert('Veuillez remplir l’UID et sélectionner un résident');
      return;
    }

    setIsSubmitting(true);
    try {
      await devicesApi.create(newDevice);
      setIsModalOpen(false);
      setNewDevice({
        device_uid: '',
        elderly_id: residents[0]?.id || '',
        name: '',
        firmware_version: '1.2.0-esp6.1',
      });
      loadData();
    } catch (err: any) {
      alert(err.message || 'Erreur lors de l’enregistrement de l’appareil');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
            Parc des Dispositifs IoT Embarqués
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Bracelets et capteurs ESP32 connectés au système de télésurveillance
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isAdmin && (
            <Button
              variant="primary"
              icon={<Plus className="w-4 h-4" />}
              onClick={() => setIsModalOpen(true)}
            >
              Enregistrer un Appareil
            </Button>
          )}
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

      {isLoading ? (
        <Spinner size="lg" className="py-20" />
      ) : devices.length === 0 ? (
        <EmptyState
          title="Aucun appareil enregistré"
          description="Enregistrez un bracelet ESP32 pour démarrer la collecte télémétrique."
          icon={<Smartphone className="w-10 h-10 text-slate-500" />}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {devices.map((d) => {
            const resident = residents.find((r) => r.id === d.elderly_id);
            return (
              <Card
                key={d.id}
                title={d.name || d.device_uid}
                subtitle={`UID : ${d.device_uid}`}
                action={<Badge label={d.status} variant="device" />}
              >
                <div className="space-y-3 text-xs">
                  <div className="flex items-center justify-between text-slate-300">
                    <span className="text-slate-400">Résident assigné</span>
                    <span className="font-semibold text-slate-100">
                      {resident ? `${resident.first_name} ${resident.last_name}` : 'Non assigné'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-300">
                    <span className="text-slate-400">Version Firmware</span>
                    <span className="font-mono text-slate-200">
                      {d.firmware_version || '1.2.0'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-300">
                    <span className="text-slate-400 flex items-center gap-1.5">
                      <Battery className="w-3.5 h-3.5 text-slate-400" />
                      Batterie
                    </span>
                    <span className="font-semibold text-slate-100">
                      {d.battery_level ? `${d.battery_level.toFixed(0)}%` : '--'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-300">
                    <span className="text-slate-400 flex items-center gap-1.5">
                      <Wifi className="w-3.5 h-3.5 text-slate-400" />
                      Signal Wi-Fi (RSSI)
                    </span>
                    <span className="font-semibold text-slate-100">
                      {d.wifi_rssi ? `${d.wifi_rssi} dBm` : '--'}
                    </span>
                  </div>

                  <div className="pt-3 border-t border-slate-700/50 text-[11px] text-slate-500">
                    Dernière connexion :{' '}
                    {d.last_seen_at ? new Date(d.last_seen_at).toLocaleString() : 'Jamais'}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Modal register device */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Enregistrer un nouveau dispositif IoT">
        <form onSubmit={handleCreate} className="space-y-4 text-xs">
          <div>
            <label className="block text-slate-300 mb-1 font-medium">UID Dispositif (Identifiant MQTT) *</label>
            <input
              type="text"
              required
              value={newDevice.device_uid}
              onChange={(e) => setNewDevice({ ...newDevice, device_uid: e.target.value })}
              placeholder="ex: ESP32-BRACELET-003"
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100 font-mono"
            />
          </div>

          <div>
            <label className="block text-slate-300 mb-1 font-medium">Nom descriptif</label>
            <input
              type="text"
              value={newDevice.name}
              onChange={(e) => setNewDevice({ ...newDevice, name: e.target.value })}
              placeholder="ex: Bracelet Chambre 104"
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
            />
          </div>

          <div>
            <label className="block text-slate-300 mb-1 font-medium">Résident assigné *</label>
            <select
              required
              value={newDevice.elderly_id}
              onChange={(e) => setNewDevice({ ...newDevice, elderly_id: e.target.value })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
            >
              {residents.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.first_name} {r.last_name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-slate-300 mb-1 font-medium">Version du Firmware</label>
            <input
              type="text"
              value={newDevice.firmware_version}
              onChange={(e) => setNewDevice({ ...newDevice, firmware_version: e.target.value })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100 font-mono"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-800">
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              Annuler
            </Button>
            <Button type="submit" variant="primary" isLoading={isSubmitting}>
              Enregistrer l'Appareil
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
