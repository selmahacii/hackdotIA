import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Users, UserPlus, Phone, ChevronRight, Search } from 'lucide-react';
import { elderlyApi } from '../api/elderly';
import { ElderlyPerson } from '../types';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/Common/Button';
import { Modal } from '../components/Common/Modal';
import { Spinner } from '../components/Common/Spinner';
import { EmptyState } from '../components/Common/EmptyState';

export const ElderlyListPage: React.FC = () => {
  const { isAdmin } = useAuth();
  const [residents, setResidents] = useState<ElderlyPerson[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Form state for creating resident
  const [newResident, setNewResident] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    emergency_contact_name: '',
    emergency_contact_phone: '',
    date_of_birth: '',
  });

  const loadResidents = async () => {
    setIsLoading(true);
    try {
      const data = await elderlyApi.list();
      setResidents(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Erreur lors du chargement des résidents');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadResidents();
  }, []);

  const handleCreateResident = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await elderlyApi.create({
        first_name: newResident.first_name,
        last_name: newResident.last_name,
        phone: newResident.phone || null,
        emergency_contact_name: newResident.emergency_contact_name || null,
        emergency_contact_phone: newResident.emergency_contact_phone || null,
        date_of_birth: newResident.date_of_birth || null,
        is_active: true,
      });
      setIsModalOpen(false);
      setNewResident({
        first_name: '',
        last_name: '',
        phone: '',
        emergency_contact_name: '',
        emergency_contact_phone: '',
        date_of_birth: '',
      });
      loadResidents();
    } catch (err: any) {
      alert(err.message || "Échec de l'enregistrement du résident");
    } finally {
      setIsSubmitting(false);
    }
  };

  const filteredResidents = residents.filter(
    (r) =>
      r.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (r.phone && r.phone.includes(searchTerm))
  );

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
            Résidents Sous Surveillance
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Fiches médicales, contacts d'urgence et suivi télémétrique individualisé
          </p>
        </div>

        {isAdmin && (
          <Button
            variant="primary"
            icon={<UserPlus className="w-4 h-4" />}
            onClick={() => setIsModalOpen(true)}
          >
            Nouveau Résident
          </Button>
        )}
      </div>

      {/* Search Bar */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-500" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Rechercher par nom, prénom ou téléphone..."
          className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-brand-500 transition"
        />
      </div>

      {/* List */}
      {isLoading ? (
        <Spinner size="lg" className="py-20" />
      ) : filteredResidents.length === 0 ? (
        <EmptyState
          title="Aucun résident trouvé"
          description={
            searchTerm
              ? "Aucun résultat ne correspond à votre recherche."
              : "Aucun résident n'est encore enregistré ou assigné à votre compte."
          }
          icon={<Users className="w-10 h-10 text-slate-500" />}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredResidents.map((r) => (
            <Link
              key={r.id}
              to={`/elderly/${r.id}`}
              className="group block p-5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-brand-500/40 hover:bg-slate-800/40 transition shadow-lg relative overflow-hidden"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center font-bold text-sm">
                    {r.first_name[0]}
                    {r.last_name[0]}
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-slate-100 group-hover:text-brand-300 transition">
                      {r.first_name} {r.last_name}
                    </h3>
                    <p className="text-xs text-slate-500">
                      Né(e) le {r.date_of_birth ? new Date(r.date_of_birth).toLocaleDateString() : 'Non renseigné'}
                    </p>
                  </div>
                </div>

                <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-brand-400 transition" />
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/80 space-y-1.5 text-xs text-slate-400">
                <div className="flex items-center gap-2">
                  <Phone className="w-3.5 h-3.5 text-slate-500" />
                  <span>{r.phone || 'Pas de numéro'}</span>
                </div>
                {r.emergency_contact_name && (
                  <div className="flex items-center gap-2 text-slate-300">
                    <span className="text-slate-500">Urgence :</span>
                    <span className="truncate">{r.emergency_contact_name}</span>
                  </div>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Modal create resident */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Ajouter un nouveau résident">
        <form onSubmit={handleCreateResident} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Prénom *</label>
              <input
                type="text"
                required
                value={newResident.first_name}
                onChange={(e) => setNewResident({ ...newResident, first_name: e.target.value })}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Nom *</label>
              <input
                type="text"
                required
                value={newResident.last_name}
                onChange={(e) => setNewResident({ ...newResident, last_name: e.target.value })}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Date de naissance</label>
            <input
              type="date"
              value={newResident.date_of_birth}
              onChange={(e) => setNewResident({ ...newResident, date_of_birth: e.target.value })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Téléphone</label>
            <input
              type="text"
              value={newResident.phone}
              onChange={(e) => setNewResident({ ...newResident, phone: e.target.value })}
              placeholder="+33 6 ..."
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Contact d'urgence (Nom)</label>
            <input
              type="text"
              value={newResident.emergency_contact_name}
              onChange={(e) => setNewResident({ ...newResident, emergency_contact_name: e.target.value })}
              placeholder="ex: Jean Dupont (Fils)"
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">Contact d'urgence (Téléphone)</label>
            <input
              type="text"
              value={newResident.emergency_contact_phone}
              onChange={(e) => setNewResident({ ...newResident, emergency_contact_phone: e.target.value })}
              placeholder="+33 6 ..."
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
            />
          </div>

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-800">
            <Button variant="secondary" onClick={() => setIsModalOpen(false)}>
              Annuler
            </Button>
            <Button type="submit" variant="primary" isLoading={isSubmitting}>
              Enregistrer
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
