import React, { useEffect, useState } from 'react';
import { UserPlus, Edit2, Trash2 } from 'lucide-react';
import { adminApi } from '../api/admin';
import { elderlyApi } from '../api/elderly';
import { User, UserRole, ElderlyPerson } from '../types';
import { useAuth } from '../context/AuthContext';
import { Card } from '../components/Common/Card';
import { Badge } from '../components/Common/Badge';
import { Button } from '../components/Common/Button';
import { Modal } from '../components/Common/Modal';
import { Spinner } from '../components/Common/Spinner';

export const AdminUsersPage: React.FC = () => {
  const { isSuperAdmin } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [residents, setResidents] = useState<ElderlyPerson[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  // Form state create
  const [createForm, setCreateForm] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
    role: 'CAREGIVER' as UserRole,
    assigned_elderly_ids: [] as string[],
  });

  // Form state edit
  const [editForm, setEditForm] = useState({
    full_name: '',
    email: '',
    role: 'CAREGIVER' as UserRole,
    is_active: true,
    password: '',
    assigned_elderly_ids: [] as string[],
  });

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [uRes, resList] = await Promise.all([adminApi.getUsers(0, 100), elderlyApi.list()]);
      setUsers(uRes.items);
      setResidents(resList);
    } catch (err: any) {
      alert(err.message || 'Erreur lors du chargement des utilisateurs');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await adminApi.createUser(createForm);
      setIsCreateOpen(false);
      setCreateForm({
        username: '',
        email: '',
        password: '',
        full_name: '',
        role: 'CAREGIVER',
        assigned_elderly_ids: [],
      });
      loadData();
    } catch (err: any) {
      alert(err.message || 'Échec de la création');
    }
  };

  const handleEditClick = (u: User) => {
    setEditingUser(u);
    setEditForm({
      full_name: u.full_name || '',
      email: u.email,
      role: u.role,
      is_active: u.is_active,
      password: '',
      assigned_elderly_ids: u.assigned_elderly_ids || [],
    });
    setIsEditOpen(true);
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    try {
      await adminApi.updateUser(editingUser.id, {
        full_name: editForm.full_name,
        email: editForm.email,
        role: editForm.role,
        is_active: editForm.is_active,
        password: editForm.password ? editForm.password : undefined,
        assigned_elderly_ids: editForm.assigned_elderly_ids,
      });
      setIsEditOpen(false);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Échec de la mise à jour');
    }
  };

  const handleDelete = async (u: User) => {
    if (!window.confirm(`Supprimer définitivement le compte de ${u.username} ?`)) return;
    try {
      await adminApi.deleteUser(u.id);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Échec de la suppression');
    }
  };

  const toggleElderlyAssignment = (
    elderlyId: string,
    currentList: string[],
    setList: (newList: string[]) => void
  ) => {
    if (currentList.includes(elderlyId)) {
      setList(currentList.filter((id) => id !== elderlyId));
    } else {
      setList([...currentList, elderlyId]);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
            Gestion des Utilisateurs & RBAC
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Contrôle des accès, rôles opérationnels et affectation des soignants aux résidents
          </p>
        </div>

        <Button
          variant="primary"
          icon={<UserPlus className="w-4 h-4" />}
          onClick={() => setIsCreateOpen(true)}
        >
          Créer un Utilisateur
        </Button>
      </div>

      {isLoading ? (
        <Spinner size="lg" className="py-20" />
      ) : (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-700/60 font-semibold uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="py-3.5 px-4">Utilisateur</th>
                  <th className="py-3.5 px-4">Email</th>
                  <th className="py-3.5 px-4">Rôle RBAC</th>
                  <th className="py-3.5 px-4">Statut</th>
                  <th className="py-3.5 px-4">Résidents Affectés</th>
                  <th className="py-3.5 px-4">Dernière Connexion</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-800/30 transition">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-100">{u.username}</div>
                      {u.full_name && <div className="text-[11px] text-slate-400">{u.full_name}</div>}
                    </td>
                    <td className="py-3 px-4 text-slate-300">{u.email}</td>
                    <td className="py-3 px-4">
                      <Badge label={u.role} variant="role" />
                    </td>
                    <td className="py-3 px-4">
                      {u.is_active ? (
                        <span className="text-[11px] text-emerald-400 font-medium">Actif</span>
                      ) : (
                        <span className="text-[11px] text-rose-400 font-medium">Désactivé</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {u.role === 'CAREGIVER' ? (
                        u.assigned_elderly_ids && u.assigned_elderly_ids.length > 0 ? (
                          <span className="text-xs text-slate-200">
                            {u.assigned_elderly_ids.length} résident(s)
                          </span>
                        ) : (
                          <span className="text-[11px] text-amber-400">Aucun (accès restreint)</span>
                        )
                      ) : (
                        <span className="text-slate-500">Tous (Rôle global)</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px]">
                      {u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'Jamais'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleEditClick(u)}
                          title="Modifier"
                        >
                          <Edit2 className="w-3.5 h-3.5 text-slate-400" />
                        </Button>
                        {isSuperAdmin && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDelete(u)}
                            title="Supprimer (Superadmin)"
                          >
                            <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Modal Create User */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Créer un compte utilisateur">
        <form onSubmit={handleCreate} className="space-y-4 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-300 mb-1 font-medium">Nom d'utilisateur *</label>
              <input
                type="text"
                required
                value={createForm.username}
                onChange={(e) => setCreateForm({ ...createForm, username: e.target.value })}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
              />
            </div>
            <div>
              <label className="block text-slate-300 mb-1 font-medium">Nom complet</label>
              <input
                type="text"
                value={createForm.full_name}
                onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
              />
            </div>
          </div>

          <div>
            <label className="block text-slate-300 mb-1 font-medium">Email *</label>
            <input
              type="email"
              required
              value={createForm.email}
              onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
            />
          </div>

          <div>
            <label className="block text-slate-300 mb-1 font-medium">Mot de passe temporaire *</label>
            <input
              type="password"
              required
              minLength={6}
              value={createForm.password}
              onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
            />
          </div>

          <div>
            <label className="block text-slate-300 mb-1 font-medium">Rôle attribué *</label>
            <select
              value={createForm.role}
              onChange={(e) => setCreateForm({ ...createForm, role: e.target.value as UserRole })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
            >
              {isSuperAdmin && <option value="SUPERADMIN">SUPERADMIN (Super administrateur)</option>}
              <option value="ADMIN">ADMIN (Administrateur établissement)</option>
              <option value="CAREGIVER">CAREGIVER (Soignant - Isolation résidents)</option>
              <option value="OPERATOR">OPERATOR (Opérateur de surveillance)</option>
              <option value="READ_ONLY">READ_ONLY (Auditeur / Lecture seule)</option>
            </select>
          </div>

          {/* If CAREGIVER, assign residents */}
          {createForm.role === 'CAREGIVER' && (
            <div className="pt-2 border-t border-slate-800">
              <label className="block text-slate-300 mb-2 font-medium">
                Résidents affectés à ce soignant (Isolation des données) :
              </label>
              <div className="space-y-1.5 max-h-40 overflow-y-auto p-2 bg-slate-950 rounded-lg border border-slate-800">
                {residents.map((r) => {
                  const checked = createForm.assigned_elderly_ids.includes(r.id);
                  return (
                    <label
                      key={r.id}
                      className="flex items-center gap-2 p-1.5 hover:bg-slate-900 rounded cursor-pointer text-slate-200"
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() =>
                          toggleElderlyAssignment(
                            r.id,
                            createForm.assigned_elderly_ids,
                            (newList) => setCreateForm({ ...createForm, assigned_elderly_ids: newList })
                          )
                        }
                        className="rounded border-slate-700 bg-slate-900 text-brand-600 focus:ring-0"
                      />
                      <span>
                        {r.first_name} {r.last_name}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-800">
            <Button variant="secondary" onClick={() => setIsCreateOpen(false)}>
              Annuler
            </Button>
            <Button type="submit" variant="primary">
              Créer le compte
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal Edit User */}
      <Modal isOpen={isEditOpen} onClose={() => setIsEditOpen(false)} title={`Modifier ${editingUser?.username}`}>
        <form onSubmit={handleUpdate} className="space-y-4 text-xs">
          <div>
            <label className="block text-slate-300 mb-1 font-medium">Nom complet</label>
            <input
              type="text"
              value={editForm.full_name}
              onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
            />
          </div>

          <div>
            <label className="block text-slate-300 mb-1 font-medium">Email</label>
            <input
              type="email"
              value={editForm.email}
              onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
            />
          </div>

          <div>
            <label className="block text-slate-300 mb-1 font-medium">Rôle attribué</label>
            <select
              value={editForm.role}
              onChange={(e) => setEditForm({ ...editForm, role: e.target.value as UserRole })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
            >
              {isSuperAdmin && <option value="SUPERADMIN">SUPERADMIN</option>}
              <option value="ADMIN">ADMIN</option>
              <option value="CAREGIVER">CAREGIVER</option>
              <option value="OPERATOR">OPERATOR</option>
              <option value="READ_ONLY">READ_ONLY</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-300 mb-1 font-medium">
              Changer le mot de passe (laisser vide pour ne pas modifier)
            </label>
            <input
              type="password"
              placeholder="Nouveau mot de passe"
              value={editForm.password}
              onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100"
            />
          </div>

          <div>
            <label className="flex items-center gap-2 text-slate-200 cursor-pointer">
              <input
                type="checkbox"
                checked={editForm.is_active}
                onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                className="rounded border-slate-700 bg-slate-900 text-brand-600 focus:ring-0"
              />
              <span className="font-medium">Compte actif</span>
            </label>
          </div>

          {/* Caregiver assignments */}
          {editForm.role === 'CAREGIVER' && (
            <div className="pt-2 border-t border-slate-800">
              <label className="block text-slate-300 mb-2 font-medium">
                Résidents affectés à ce soignant :
              </label>
              <div className="space-y-1.5 max-h-40 overflow-y-auto p-2 bg-slate-950 rounded-lg border border-slate-800">
                {residents.map((r) => {
                  const checked = editForm.assigned_elderly_ids.includes(r.id);
                  return (
                    <label
                      key={r.id}
                      className="flex items-center gap-2 p-1.5 hover:bg-slate-900 rounded cursor-pointer text-slate-200"
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() =>
                          toggleElderlyAssignment(
                            r.id,
                            editForm.assigned_elderly_ids,
                            (newList) => setEditForm({ ...editForm, assigned_elderly_ids: newList })
                          )
                        }
                        className="rounded border-slate-700 bg-slate-900 text-brand-600 focus:ring-0"
                      />
                      <span>
                        {r.first_name} {r.last_name}
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-800">
            <Button variant="secondary" onClick={() => setIsEditOpen(false)}>
              Annuler
            </Button>
            <Button type="submit" variant="primary">
              Mettre à jour
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
