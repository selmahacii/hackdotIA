import React, { useEffect, useState, useMemo } from 'react';
import {
  UserPlus,
  Edit2,
  Trash2,
  Shield,
  ShieldCheck,
  ShieldAlert,
  Key,
  Check,
  X,
  Search,
  Users,
  RefreshCw,
  CheckCircle2,
  Lock,
  UserCheck,
  Eye,
  SlidersHorizontal,
  ChevronRight,
  Database,
  Fingerprint,
} from 'lucide-react';
import { adminApi } from '../api/admin';
import { elderlyApi } from '../api/elderly';
import {
  User,
  UserRole,
  ElderlyPerson,
  RbacMatrixResponse,
  AdminStats,
} from '../types';
import { useAuth } from '../context/AuthContext';
import { Card } from '../components/Common/Card';
import { Badge } from '../components/Common/Badge';
import { Button } from '../components/Common/Button';
import { Modal } from '../components/Common/Modal';
import { Spinner } from '../components/Common/Spinner';

export const AdminUsersPage: React.FC = () => {
  const { isSuperAdmin, user: currentUser } = useAuth();

  // Primary state
  const [users, setUsers] = useState<User[]>([]);
  const [residents, setResidents] = useState<ElderlyPerson[]>([]);
  const [rbacMatrix, setRbacMatrix] = useState<RbacMatrixResponse | null>(null);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);

  // Tabs
  const [activeTab, setActiveTab] = useState<'users' | 'matrix' | 'policies'>('users');

  // Filters & search
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<UserRole | 'ALL'>('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'INACTIVE'>('ALL');

  // Notification message
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  // Create form state
  const [createForm, setCreateForm] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
    role: 'CAREGIVER' as UserRole,
    assigned_elderly_ids: [] as string[],
  });

  // Edit form state
  const [editForm, setEditForm] = useState({
    full_name: '',
    email: '',
    role: 'CAREGIVER' as UserRole,
    is_active: true,
    password: '',
    assigned_elderly_ids: [] as string[],
  });

  // Synchronous feedback helper
  const showFeedback = (type: 'success' | 'error', message: string) => {
    setFeedback({ type, message });
    setTimeout(() => {
      setFeedback(null);
    }, 4000);
  };

  // Synchronous data loader across all APIs
  const loadData = async (silent = false) => {
    if (!silent) setIsLoading(true);
    else setIsSyncing(true);

    try {
      const [usersRes, residentsList, statsRes, matrixRes] = await Promise.all([
        adminApi.getUsers(0, 100),
        elderlyApi.list(),
        adminApi.getStats(),
        adminApi.getRbacMatrix().catch(() => null),
      ]);

      setUsers(usersRes.items);
      setResidents(residentsList);
      setStats(statsRes);
      if (matrixRes) {
        setRbacMatrix(matrixRes);
      }
    } catch (err: any) {
      showFeedback('error', err.message || 'Erreur de synchronisation avec les API Guardia');
    } finally {
      setIsLoading(false);
      setIsSyncing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Filtered users
  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      const matchesSearch =
        u.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (u.email && u.email.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (u.full_name && u.full_name.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesRole = roleFilter === 'ALL' || u.role === roleFilter;

      const matchesStatus =
        statusFilter === 'ALL' ||
        (statusFilter === 'ACTIVE' && u.is_active) ||
        (statusFilter === 'INACTIVE' && !u.is_active);

      return matchesSearch && matchesRole && matchesStatus;
    });
  }, [users, searchQuery, roleFilter, statusFilter]);

  // Synchronous Create
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSyncing(true);
    try {
      const newUser = await adminApi.createUser(createForm);
      showFeedback('success', `Compte ${newUser.username} créé avec succès (Rôle : ${newUser.role})`);
      setIsCreateOpen(false);
      setCreateForm({
        username: '',
        email: '',
        password: '',
        full_name: '',
        role: 'CAREGIVER',
        assigned_elderly_ids: [],
      });
      await loadData(true);
    } catch (err: any) {
      showFeedback('error', err.message || 'Échec de la création du compte');
    } finally {
      setIsSyncing(false);
    }
  };

  // Synchronous Edit Open
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

  // Synchronous Update
  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    setIsSyncing(true);
    try {
      await adminApi.updateUser(editingUser.id, {
        full_name: editForm.full_name,
        email: editForm.email,
        role: editForm.role,
        is_active: editForm.is_active,
        password: editForm.password ? editForm.password : undefined,
        assigned_elderly_ids: editForm.assigned_elderly_ids,
      });
      showFeedback('success', `Mise à jour synchronisée pour ${editingUser.username}`);
      setIsEditOpen(false);
      await loadData(true);
    } catch (err: any) {
      showFeedback('error', err.message || 'Échec de la mise à jour');
    } finally {
      setIsSyncing(false);
    }
  };

  // Synchronous Status Toggle
  const handleToggleActive = async (u: User) => {
    if (u.id === currentUser?.id) {
      showFeedback('error', 'Impossible de désactiver votre propre compte session');
      return;
    }

    const nextState = !u.is_active;
    setIsSyncing(true);
    try {
      await adminApi.updateUser(u.id, { is_active: nextState });
      showFeedback(
        'success',
        `Compte ${u.username} ${nextState ? 'activé' : 'désactivé'} en temps réel`
      );
      // Optimistic update + sync
      setUsers((prev) =>
        prev.map((item) => (item.id === u.id ? { ...item, is_active: nextState } : item))
      );
      await loadData(true);
    } catch (err: any) {
      showFeedback('error', err.message || 'Impossible de modifier le statut');
    } finally {
      setIsSyncing(false);
    }
  };

  // Synchronous Delete
  const handleDelete = async (u: User) => {
    if (u.id === currentUser?.id) {
      showFeedback('error', 'Vous ne pouvez pas supprimer votre propre compte');
      return;
    }
    if (!window.confirm(`Supprimer définitivement l'utilisateur '${u.username}' et révoquer ses accès ?`)) {
      return;
    }

    setIsSyncing(true);
    try {
      await adminApi.deleteUser(u.id);
      showFeedback('success', `Utilisateur ${u.username} supprimé définitivement`);
      await loadData(true);
    } catch (err: any) {
      showFeedback('error', err.message || 'Échec de la suppression');
    } finally {
      setIsSyncing(false);
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

  // Resident name resolver
  const getResidentNames = (ids: string[]) => {
    if (!ids || ids.length === 0) return [];
    return ids
      .map((id) => {
        const found = residents.find((r) => r.id === id);
        return found ? `${found.first_name} ${found.last_name}` : id.slice(0, 8);
      });
  };

  // Calculate Quick Metrics
  const activeCount = users.filter((u) => u.is_active).length;
  const caregiverWithScopeCount = users.filter(
    (u) => u.role === 'CAREGIVER' && u.assigned_elderly_ids && u.assigned_elderly_ids.length > 0
  ).length;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Banner / Feedback Alert */}
      {feedback && (
        <div
          className={`flex items-center justify-between px-4 py-3 rounded-xl border text-xs font-medium transition-all duration-300 animate-fadeIn ${
            feedback.type === 'success'
              ? 'bg-emerald-950/70 border-emerald-500/40 text-emerald-200'
              : 'bg-rose-950/70 border-rose-500/40 text-rose-200'
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>{feedback.message}</span>
          </div>
          <button
            onClick={() => setFeedback(null)}
            className="text-slate-400 hover:text-slate-200 p-1 rounded"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Header & Synchronous Status */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
              <Shield className="w-4 h-4" />
            </div>
            <h1 className="text-xl font-bold text-slate-100 tracking-tight">
              Gouvernance des Accès & Matrice RBAC
            </h1>
            {isSyncing && (
              <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-medium bg-brand-500/15 text-brand-400 border border-brand-500/30 animate-pulse">
                <RefreshCw className="w-3 h-3 animate-spin" /> Synchrone
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1 pl-10.5">
            Contrôle d'accès basé sur les rôles, isolation des données soignants et politique de sécurité en temps réel.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => loadData(true)}
            disabled={isSyncing}
            icon={<RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />}
          >
            Actualiser
          </Button>
          <Button
            variant="primary"
            size="sm"
            icon={<UserPlus className="w-4 h-4" />}
            onClick={() => setIsCreateOpen(true)}
          >
            Nouvel Utilisateur
          </Button>
        </div>
      </div>

      {/* Structured Minimalist KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
        <Card className="p-3.5 bg-slate-900/60 border-slate-800/90 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400">Comptes Utilisateurs</span>
            <Users className="w-3.5 h-3.5 text-brand-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-100">{users.length}</span>
            <span className="text-[11px] text-emerald-400 font-medium">
              {activeCount} actifs ({Math.round((activeCount / (users.length || 1)) * 100)}%)
            </span>
          </div>
          <div className="mt-1 text-[10px] text-slate-500 flex items-center gap-1">
            <Check className="w-3 h-3 text-emerald-400" /> API Synchrone v1
          </div>
        </Card>

        <Card className="p-3.5 bg-slate-900/60 border-slate-800/90">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400">Cloisonnement Soignants</span>
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-400">
              {caregiverWithScopeCount}
            </span>
            <span className="text-[11px] text-slate-400">
              / {users.filter((u) => u.role === 'CAREGIVER').length} soignants
            </span>
          </div>
          <div className="mt-1 text-[10px] text-slate-500">
            Isolation stricte par résident
          </div>
        </Card>

        <Card className="p-3.5 bg-slate-900/60 border-slate-800/90">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400">Résidents Pris en Charge</span>
            <UserCheck className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-purple-300">
              {residents.length}
            </span>
            <span className="text-[11px] text-slate-400">dossiers actifs</span>
          </div>
          <div className="mt-1 text-[10px] text-slate-500">
            Périmètres cliniques validés
          </div>
        </Card>

        <Card className="p-3.5 bg-slate-900/60 border-slate-800/90">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400">Politique de Sécurité</span>
            <Fingerprint className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-sm font-bold text-cyan-300">JWT HS256</span>
            <span className="text-[11px] text-slate-400">480 min</span>
          </div>
          <div className="mt-1 text-[10px] text-emerald-400 flex items-center gap-1">
            <Lock className="w-2.5 h-2.5" /> Moindre Privilège Actif
          </div>
        </Card>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800">
        <button
          onClick={() => setActiveTab('users')}
          className={`flex items-center gap-2 py-2.5 px-4 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'users'
              ? 'border-brand-500 text-brand-400 bg-brand-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          Annuaire des Utilisateurs ({filteredUsers.length})
        </button>

        <button
          onClick={() => setActiveTab('matrix')}
          className={`flex items-center gap-2 py-2.5 px-4 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'matrix'
              ? 'border-brand-500 text-brand-400 bg-brand-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
          }`}
        >
          <Shield className="w-3.5 h-3.5" />
          Matrice des Rôles & Privilèges (5 Rôles)
        </button>

        <button
          onClick={() => setActiveTab('policies')}
          className={`flex items-center gap-2 py-2.5 px-4 text-xs font-semibold border-b-2 transition-all ${
            activeTab === 'policies'
              ? 'border-brand-500 text-brand-400 bg-brand-500/5'
              : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
          }`}
        >
          <Key className="w-3.5 h-3.5" />
          Politique & Cloisonnement RLS
        </button>
      </div>

      {/* TAB 1: USERS DIRECTORY */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          {/* Controls Ribbon: Search + Filters */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800/80">
            {/* Search Input */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Rechercher par identifiant, nom, email..."
                className="w-full pl-9 pr-3 py-1.5 bg-slate-950/80 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500/50"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Quick Filters */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-1 bg-slate-950/60 p-1 rounded-lg border border-slate-800">
                {(['ALL', 'SUPERADMIN', 'ADMIN', 'CAREGIVER', 'OPERATOR', 'READ_ONLY'] as const).map(
                  (role) => (
                    <button
                      key={role}
                      onClick={() => setRoleFilter(role)}
                      className={`px-2 py-1 rounded text-[10px] font-medium transition ${
                        roleFilter === role
                          ? 'bg-slate-800 text-slate-100 shadow-sm'
                          : 'text-slate-400 hover:text-slate-300'
                      }`}
                    >
                      {role === 'ALL' ? 'Tous' : role}
                    </button>
                  )
                )}
              </div>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none"
              >
                <option value="ALL">Tous statuts</option>
                <option value="ACTIVE">Actifs uniquement</option>
                <option value="INACTIVE">Désactivés uniquement</option>
              </select>
            </div>
          </div>

          {/* Table */}
          {isLoading ? (
            <Spinner size="lg" className="py-20" />
          ) : filteredUsers.length === 0 ? (
            <Card className="py-14 text-center">
              <Users className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs font-medium text-slate-300">Aucun utilisateur ne correspond aux filtres</p>
              <p className="text-[11px] text-slate-500 mt-1">Modifiez vos critères de recherche ou réinitialisez les filtres.</p>
              <Button
                variant="ghost"
                size="sm"
                className="mt-3"
                onClick={() => {
                  setSearchQuery('');
                  setRoleFilter('ALL');
                  setStatusFilter('ALL');
                }}
              >
                Réinitialiser
              </Button>
            </Card>
          ) : (
            <Card className="overflow-hidden p-0 border-slate-800/90 shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 font-semibold uppercase text-[10px] tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Utilisateur</th>
                      <th className="py-3 px-4">Email</th>
                      <th className="py-3 px-4">Rôle & Privilège</th>
                      <th className="py-3 px-4">Statut</th>
                      <th className="py-3 px-4">Périmètre / Résidents</th>
                      <th className="py-3 px-4">Dernière Activité</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 bg-slate-900/30">
                    {filteredUsers.map((u) => {
                      const assignedNames = getResidentNames(u.assigned_elderly_ids || []);
                      return (
                        <tr
                          key={u.id}
                          className="hover:bg-slate-800/30 transition-colors group"
                        >
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2.5">
                              <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700/80 flex items-center justify-center font-bold text-[10px] text-slate-200 uppercase shrink-0">
                                {u.username.slice(0, 2)}
                              </div>
                              <div>
                                <div className="font-semibold text-slate-100 flex items-center gap-1.5">
                                  <span>{u.username}</span>
                                  {u.id === currentUser?.id && (
                                    <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-brand-500/20 text-brand-300 border border-brand-500/30">
                                      VOUS
                                    </span>
                                  )}
                                </div>
                                {u.full_name && (
                                  <div className="text-[11px] text-slate-400">{u.full_name}</div>
                                )}
                              </div>
                            </div>
                          </td>

                          <td className="py-3 px-4 text-slate-300 font-mono text-[11px]">
                            {u.email}
                          </td>

                          <td className="py-3 px-4">
                            <Badge label={u.role} variant="role" />
                          </td>

                          <td className="py-3 px-4">
                            <button
                              onClick={() => handleToggleActive(u)}
                              title="Cliquer pour basculer le statut en temps réel"
                              className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold border transition ${
                                u.is_active
                                  ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30 hover:bg-emerald-900/40'
                                  : 'bg-rose-950/40 text-rose-400 border-rose-500/30 hover:bg-rose-900/40'
                              }`}
                            >
                              <span
                                className={`w-1.5 h-1.5 rounded-full ${
                                  u.is_active ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
                                }`}
                              />
                              {u.is_active ? 'Actif' : 'Désactivé'}
                            </button>
                          </td>

                          <td className="py-3 px-4">
                            {u.role === 'CAREGIVER' ? (
                              assignedNames.length > 0 ? (
                                <div className="space-y-1">
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-brand-500/10 border border-brand-500/20 text-[10px] text-brand-300 font-medium">
                                    <ShieldCheck className="w-2.5 h-2.5 text-brand-400" />
                                    {assignedNames.length} résident(s)
                                  </span>
                                  <div className="text-[10px] text-slate-400 truncate max-w-xs" title={assignedNames.join(', ')}>
                                    {assignedNames.slice(0, 2).join(', ')}
                                    {assignedNames.length > 2 && ` +${assignedNames.length - 2}`}
                                  </div>
                                </div>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-[10px] text-amber-300">
                                  <ShieldAlert className="w-2.5 h-2.5" /> Aucun (Accès restreint)
                                </span>
                              )
                            ) : (
                              <span className="text-[11px] text-slate-500">Périmètre Global</span>
                            )}
                          </td>

                          <td className="py-3 px-4 text-slate-400 text-[11px]">
                            {u.last_login_at
                              ? new Date(u.last_login_at).toLocaleString('fr-FR', {
                                  day: '2-digit',
                                  month: '2-digit',
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })
                              : 'Jamais'}
                          </td>

                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end gap-1.5 opacity-90 group-hover:opacity-100">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleEditClick(u)}
                                title="Modifier les privilèges"
                              >
                                <Edit2 className="w-3.5 h-3.5 text-slate-300 hover:text-brand-400" />
                              </Button>

                              {isSuperAdmin && u.id !== currentUser?.id && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleDelete(u)}
                                  title="Supprimer définitivement (Superadmin)"
                                >
                                  <Trash2 className="w-3.5 h-3.5 text-rose-400/80 hover:text-rose-400" />
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* TAB 2: RBAC MATRIX & CAPABILITIES */}
      {activeTab === 'matrix' && (
        <div className="space-y-6">
          {/* Roles Cards Minimalist Grid */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {[
              {
                role: 'SUPERADMIN',
                name: 'Super Administrateur',
                level: 'Niveau 1',
                color: 'text-rose-400 border-rose-500/30 bg-rose-500/5',
                target: 'RSSI & Devs',
                desc: 'Accès sans restriction, audit système, suppression définitive.',
              },
              {
                role: 'ADMIN',
                name: 'Administrateur',
                level: 'Niveau 2',
                color: 'text-purple-400 border-purple-500/30 bg-purple-500/5',
                target: 'Cadre Médical',
                desc: 'Gestion des dossiers, création des comptes soignants, matériel IoT.',
              },
              {
                role: 'CAREGIVER',
                name: 'Soignant / Infirmier',
                level: 'Niveau 3',
                color: 'text-blue-400 border-blue-500/30 bg-blue-500/5',
                target: 'Personnel Soignant',
                desc: 'Soins cliniques, alertes, IA, scopé STRICTEMENT à ses résidents.',
              },
              {
                role: 'OPERATOR',
                name: 'Opérateur 24/7',
                level: 'Niveau 3',
                color: 'text-amber-400 border-amber-500/30 bg-amber-500/5',
                target: 'Poste de Garde',
                desc: 'Surveillance télémétrique en direct, levée de doute, acquittement ACK.',
              },
              {
                role: 'READ_ONLY',
                name: 'Auditeur / Famille',
                level: 'Niveau 4',
                color: 'text-slate-400 border-slate-700/60 bg-slate-800/20',
                target: 'Auditeurs & Tuteurs',
                desc: 'Consultation passive des indicateurs agrégés sans écriture.',
              },
            ].map((r) => (
              <Card key={r.role} className={`p-3.5 border ${r.color}`}>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    {r.level}
                  </span>
                  <span className="text-[10px] font-mono opacity-80">{r.role}</span>
                </div>
                <h3 className="font-bold text-slate-100 text-xs mt-1.5">{r.name}</h3>
                <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{r.desc}</p>
                <div className="mt-2.5 pt-2 border-t border-slate-800/80 text-[10px] text-slate-400 flex items-center justify-between">
                  <span>Cible :</span>
                  <span className="font-medium text-slate-300">{r.target}</span>
                </div>
              </Card>
            ))}
          </div>

          {/* Granular Permission Matrix */}
          <Card className="p-0 overflow-hidden border-slate-800/90">
            <div className="p-4 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-100">
                  Matrice des Droits & Privilèges Granulaires
                </h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Permissions effectives vérifiées par les dépendances FastAPI (<code className="text-brand-400">require_roles</code>)
                </p>
              </div>
              <span className="text-[10px] font-mono px-2 py-1 rounded bg-slate-800 text-slate-300">
                14 Permissions Granulaires
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 text-[10px] uppercase font-semibold">
                  <tr>
                    <th className="py-2.5 px-4 w-1/3">Capacité / Action API</th>
                    <th className="py-2.5 px-3 text-center">Superadmin</th>
                    <th className="py-2.5 px-3 text-center">Admin</th>
                    <th className="py-2.5 px-3 text-center">Soignant</th>
                    <th className="py-2.5 px-3 text-center">Opérateur</th>
                    <th className="py-2.5 px-3 text-center">Lecture Seule</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {(
                    rbacMatrix?.modules || [
                      {
                        category: 'Surveillance & Constantes Vitales',
                        permissions: [
                          {
                            code: 'DASHBOARD_VIEW',
                            label: 'Accès Tableau de Bord Global',
                            description: 'Visualisation des métriques globales et de l’EHPAD',
                            roles: ['SUPERADMIN', 'ADMIN', 'CAREGIVER', 'OPERATOR', 'READ_ONLY'],
                          },
                          {
                            code: 'TELEMETRY_REALTIME',
                            label: 'Flux Télémétrie Live (25 Hz / 1 Hz)',
                            description: 'Réception continue des signaux physiologiques via WebSocket',
                            roles: ['SUPERADMIN', 'ADMIN', 'CAREGIVER', 'OPERATOR'],
                          },
                          {
                            code: 'MEASUREMENTS_HISTORY',
                            label: 'Historique des Séries Temporelles',
                            description: 'Graphiques BPM, SpO2, accélération et exports',
                            roles: ['SUPERADMIN', 'ADMIN', 'CAREGIVER', 'OPERATOR', 'READ_ONLY'],
                          },
                        ],
                      },
                      {
                        category: 'Alertes & Urgences Médicales',
                        permissions: [
                          {
                            code: 'ALERTS_VIEW',
                            label: 'Consultation des Alertes Vitales',
                            description: 'Liste des alertes (filtrée selon affectation pour soignants)',
                            roles: ['SUPERADMIN', 'ADMIN', 'CAREGIVER', 'OPERATOR', 'READ_ONLY'],
                          },
                          {
                            code: 'ALERTS_ACKNOWLEDGE',
                            label: 'Acquittement & Prise en Charge (ACK)',
                            description: 'Prise en compte d’un incident critique',
                            roles: ['SUPERADMIN', 'ADMIN', 'CAREGIVER', 'OPERATOR'],
                          },
                          {
                            code: 'ALERTS_RESOLVE',
                            label: 'Résolution & Clôture d’Incidents',
                            description: 'Consignation des soins et clôture du ticket d’alerte',
                            roles: ['SUPERADMIN', 'ADMIN', 'CAREGIVER'],
                          },
                        ],
                      },
                      {
                        category: 'Intelligence Artificielle Clinique (Groq)',
                        permissions: [
                          {
                            code: 'AI_DIAGNOSTICS_VIEW',
                            label: 'Lecture Diagnostics IA Groq',
                            description: 'Accès aux analyses différentielles et scores de risque',
                            roles: ['SUPERADMIN', 'ADMIN', 'CAREGIVER', 'OPERATOR'],
                          },
                          {
                            code: 'AI_REEVALUATION_TRIGGER',
                            label: 'Déclenchement Manuel Ré-analyse IA',
                            description: 'Réévaluation contextuelle d’une série suspecte',
                            roles: ['SUPERADMIN', 'ADMIN', 'CAREGIVER'],
                          },
                        ],
                      },
                      {
                        category: 'Dossiers Résidents & IoT',
                        permissions: [
                          {
                            code: 'RESIDENTS_VIEW',
                            label: 'Consultation Fiche Résident',
                            description: 'Accès aux coordonnées et dossier (scopé pour soignant)',
                            roles: ['SUPERADMIN', 'ADMIN', 'CAREGIVER', 'OPERATOR', 'READ_ONLY'],
                          },
                          {
                            code: 'RESIDENTS_MANAGE',
                            label: 'Création & Édition Résidents',
                            description: 'Ajout de nouveaux résidents et antécédents médicaux',
                            roles: ['SUPERADMIN', 'ADMIN'],
                          },
                          {
                            code: 'DEVICES_PROVISION',
                            label: 'Appairage & Configuration Bracelets ESP32',
                            description: 'Association matériel-patient et calibration capteurs',
                            roles: ['SUPERADMIN', 'ADMIN'],
                          },
                        ],
                      },
                      {
                        category: 'Gouvernance & Sécurité Système',
                        permissions: [
                          {
                            code: 'USERS_MANAGE',
                            label: 'Gestion Utilisateurs & Rôles',
                            description: 'Création de comptes, réinitialisation mot de passe',
                            roles: ['SUPERADMIN', 'ADMIN'],
                          },
                          {
                            code: 'CAREGIVER_ASSIGNMENT',
                            label: 'Affectation Soignants-Patients',
                            description: 'Attribution du périmètre de confidentialité',
                            roles: ['SUPERADMIN', 'ADMIN'],
                          },
                          {
                            code: 'SUPERADMIN_DELETE',
                            label: 'Suppression Définitive & Root Access',
                            description: 'Suppression de compte et promotion superadmin',
                            roles: ['SUPERADMIN'],
                          },
                        ],
                      },
                    ]
                  ).map((group, gIdx) => (
                    <React.Fragment key={gIdx}>
                      <tr className="bg-slate-950/60 font-semibold text-[11px] text-brand-300">
                        <td colSpan={6} className="py-2 px-4 uppercase tracking-wider">
                          {group.category}
                        </td>
                      </tr>
                      {group.permissions.map((perm) => (
                        <tr key={perm.code} className="hover:bg-slate-800/30 transition">
                          <td className="py-2 px-4">
                            <div className="font-medium text-slate-200">{perm.label}</div>
                            <div className="text-[10px] text-slate-500">{perm.description}</div>
                          </td>
                          {(['SUPERADMIN', 'ADMIN', 'CAREGIVER', 'OPERATOR', 'READ_ONLY'] as UserRole[]).map(
                            (r) => {
                              const allowed = perm.roles.includes(r);
                              const isScopedCaregiver = r === 'CAREGIVER' && allowed && perm.code.includes('RESIDENTS');
                              return (
                                <td key={r} className="py-2 px-3 text-center">
                                  {allowed ? (
                                    <div className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-500/10 text-emerald-400">
                                      <Check className="w-3 h-3 stroke-[3]" />
                                    </div>
                                  ) : (
                                    <div className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-800/50 text-slate-600">
                                      <X className="w-3 h-3" />
                                    </div>
                                  )}
                                  {isScopedCaregiver && (
                                    <div className="text-[8px] text-amber-400 font-bold uppercase">
                                      Scopé
                                    </div>
                                  )}
                                </td>
                              );
                            }
                          )}
                        </tr>
                      ))}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {/* TAB 3: SECURITY POLICIES & COMPLIANCE */}
      {activeTab === 'policies' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="p-4 bg-slate-900/60 border-slate-800">
              <div className="flex items-center gap-2.5 text-brand-400 font-bold text-xs uppercase tracking-wider mb-2">
                <ShieldCheck className="w-4 h-4" /> Cloisonnement Soignants (RLS)
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Le rôle <strong>CAREGIVER</strong> applique une restriction au niveau de la ligne (Row-Level Security) : un soignant n'a accès qu'aux résidents et alertes déclarés dans son tableau <code>assigned_elderly_ids</code>.
              </p>
              <div className="mt-3 p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-[11px] text-slate-400">
                <span className="font-semibold text-slate-200">Garantie médicale :</span> Cloisonnement strict empêchant toute fuite de secret médical entre pavillons ou services.
              </div>
            </Card>

            <Card className="p-4 bg-slate-900/60 border-slate-800">
              <div className="flex items-center gap-2.5 text-purple-400 font-bold text-xs uppercase tracking-wider mb-2">
                <Key className="w-4 h-4" /> Spécifications d'Authentification
              </div>
              <ul className="space-y-2 text-xs text-slate-300">
                <li className="flex items-center justify-between border-b border-slate-800/60 pb-1">
                  <span className="text-slate-400">Algorithme de signature</span>
                  <span className="font-mono text-purple-300 font-bold">HMAC-SHA256 (HS256)</span>
                </li>
                <li className="flex items-center justify-between border-b border-slate-800/60 pb-1">
                  <span className="text-slate-400">Durée de validité Token</span>
                  <span className="font-mono text-purple-300 font-bold">480 minutes (8 heures)</span>
                </li>
                <li className="flex items-center justify-between border-b border-slate-800/60 pb-1">
                  <span className="text-slate-400">Claims de sécurité</span>
                  <span className="font-mono text-purple-300 text-[10px]">sub, role, user_id, assigned</span>
                </li>
              </ul>
            </Card>

            <Card className="p-4 bg-slate-900/60 border-slate-800">
              <div className="flex items-center gap-2.5 text-emerald-400 font-bold text-xs uppercase tracking-wider mb-2">
                <Database className="w-4 h-4" /> Traçabilité & Audit Trail
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Toutes les opérations d'acquittement d'alertes, modification de rôle et enregistrement de constante horodatent l'identifiant utilisateur (<code>user_id</code>) et le vecteur d'alerte avec identifiant idempotent unique (<code>event_id</code>).
              </p>
              <div className="mt-3 p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-[11px] text-emerald-400 font-medium flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> Conforme RGPD & Exigences HDS
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* MODAL: CREATE USER */}
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
                placeholder="ex: dr_martin"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-brand-500"
              />
            </div>
            <div>
              <label className="block text-slate-300 mb-1 font-medium">Nom complet</label>
              <input
                type="text"
                value={createForm.full_name}
                onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })}
                placeholder="ex: Dr. Julien Martin"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-brand-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-slate-300 mb-1 font-medium">Email professionnel *</label>
            <input
              type="email"
              required
              value={createForm.email}
              onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
              placeholder="ex: julien.martin@ehpad-guardia.fr"
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-brand-500"
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
              placeholder="Au moins 6 caractères"
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-brand-500"
            />
          </div>

          <div>
            <label className="block text-slate-300 mb-1 font-medium">Rôle & Privilèges attribués *</label>
            <select
              value={createForm.role}
              onChange={(e) => setCreateForm({ ...createForm, role: e.target.value as UserRole })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-brand-500"
            >
              {isSuperAdmin && <option value="SUPERADMIN">SUPERADMIN (Super Administrateur Technique)</option>}
              <option value="ADMIN">ADMIN (Administrateur Établissement)</option>
              <option value="CAREGIVER">CAREGIVER (Soignant / Infirmier - Isolation RLS)</option>
              <option value="OPERATOR">OPERATOR (Opérateur Surveillance 24/7)</option>
              <option value="READ_ONLY">READ_ONLY (Auditeur / Lecture Seule)</option>
            </select>
          </div>

          {/* Caregiver Resident Assignment */}
          {createForm.role === 'CAREGIVER' && (
            <div className="pt-2 border-t border-slate-800">
              <div className="flex items-center justify-between mb-2">
                <label className="block text-slate-300 font-medium">
                  Résidents affectés à ce soignant :
                </label>
                <span className="text-[10px] text-brand-400 font-semibold">
                  {createForm.assigned_elderly_ids.length} sélectionné(s)
                </span>
              </div>
              <div className="space-y-1.5 max-h-40 overflow-y-auto p-2 bg-slate-950 rounded-lg border border-slate-800">
                {residents.length === 0 ? (
                  <p className="text-slate-500 text-[11px] text-center py-2">Aucun résident enregistré dans le système</p>
                ) : (
                  residents.map((r) => {
                    const checked = createForm.assigned_elderly_ids.includes(r.id);
                    return (
                      <label
                        key={r.id}
                        className="flex items-center gap-2 p-1.5 hover:bg-slate-900 rounded cursor-pointer text-slate-200 text-xs"
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
                        <span className="font-medium">
                          {r.first_name} {r.last_name}
                        </span>
                      </label>
                    );
                  })
                )}
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4 border-t border-slate-800">
            <Button variant="secondary" onClick={() => setIsCreateOpen(false)} disabled={isSyncing}>
              Annuler
            </Button>
            <Button type="submit" variant="primary" disabled={isSyncing}>
              {isSyncing ? 'Création...' : 'Créer le compte'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* MODAL: EDIT USER */}
      <Modal isOpen={isEditOpen} onClose={() => setIsEditOpen(false)} title={`Modifier ${editingUser?.username}`}>
        <form onSubmit={handleUpdate} className="space-y-4 text-xs">
          <div>
            <label className="block text-slate-300 mb-1 font-medium">Nom complet</label>
            <input
              type="text"
              value={editForm.full_name}
              onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-100"
            />
          </div>

          <div>
            <label className="block text-slate-300 mb-1 font-medium">Email professionnel</label>
            <input
              type="email"
              value={editForm.email}
              onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-100"
            />
          </div>

          <div>
            <label className="block text-slate-300 mb-1 font-medium">Rôle attribué</label>
            <select
              value={editForm.role}
              onChange={(e) => setEditForm({ ...editForm, role: e.target.value as UserRole })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-100"
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
              Changer le mot de passe (laisser vide pour conserver l'actuel)
            </label>
            <input
              type="password"
              placeholder="Nouveau mot de passe (optionnel)"
              value={editForm.password}
              onChange={(e) => setEditForm({ ...editForm, password: e.target.value })}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-100"
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
              <span className="font-semibold text-slate-200">Compte actif</span>
            </label>
          </div>

          {/* Caregiver assignments */}
          {editForm.role === 'CAREGIVER' && (
            <div className="pt-2 border-t border-slate-800">
              <div className="flex items-center justify-between mb-2">
                <label className="block text-slate-300 font-medium">
                  Résidents affectés (Cloisonnement des données) :
                </label>
                <span className="text-[10px] text-brand-400 font-semibold">
                  {editForm.assigned_elderly_ids.length} sélectionné(s)
                </span>
              </div>
              <div className="space-y-1.5 max-h-40 overflow-y-auto p-2 bg-slate-950 rounded-lg border border-slate-800">
                {residents.map((r) => {
                  const checked = editForm.assigned_elderly_ids.includes(r.id);
                  return (
                    <label
                      key={r.id}
                      className="flex items-center gap-2 p-1.5 hover:bg-slate-900 rounded cursor-pointer text-slate-200 text-xs"
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
            <Button variant="secondary" onClick={() => setIsEditOpen(false)} disabled={isSyncing}>
              Annuler
            </Button>
            <Button type="submit" variant="primary" disabled={isSyncing}>
              {isSyncing ? 'Enregistrement...' : 'Mettre à jour'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
