import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Activity,
  Lock,
  User,
  AlertCircle,
  Eye,
  EyeOff,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  KeyRound,
  Check,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const [username, setUsername] = useState('imad.ghobrini');
  const [password, setPassword] = useState('Imad2026!Pass');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedRole, setSelectedRole] = useState<string>('imad');

  const from = (location.state as any)?.from?.pathname || '/dashboard';

  const demoAccounts = [
    {
      id: 'imad',
      label: 'Imad Ghobrini',
      badge: 'Superadmin',
      badgeColor: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
      user: 'imad.ghobrini',
      pass: 'Imad2026!Pass',
      desc: 'Accès total & Superviseur IA',
    },
    {
      id: 'caregiver',
      label: 'Soignant Référent',
      badge: 'Caregiver',
      badgeColor: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
      user: 'caregiver',
      pass: 'Caregiver123!',
      desc: 'Suivi résidents & acquittement',
    },
    {
      id: 'admin',
      label: 'Administrateur',
      badge: 'Admin',
      badgeColor: 'bg-brand-500/15 text-brand-300 border-brand-500/30',
      user: 'admin',
      pass: 'Admin123!',
      desc: 'Gestion des profils & matériels',
    },
    {
      id: 'operator',
      label: 'Opérateur Télésurveillance',
      badge: 'Operator',
      badgeColor: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
      user: 'operator',
      pass: 'Operator123!',
      desc: 'Console temps réel & monitoring',
    },
  ];

  const handleSelectDemo = (acc: typeof demoAccounts[0]) => {
    setSelectedRole(acc.id);
    setUsername(acc.user);
    setPassword(acc.pass);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Veuillez renseigner votre identifiant et votre mot de passe.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err?.message || 'Identifiants invalides ou service indisponible.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col justify-between relative overflow-hidden select-none">
      {/* Delicate atmospheric ambient background glows */}
      <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[700px] h-[400px] bg-gradient-to-b from-brand-500/10 via-indigo-500/5 to-transparent rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-5%] w-[450px] h-[350px] bg-indigo-600/5 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute top-[30%] left-[-10%] w-[350px] h-[350px] bg-brand-600/5 rounded-full blur-[120px] pointer-events-none" />

      {/* Top minimal bar */}
      <header className="w-full max-w-6xl mx-auto px-6 py-6 flex items-center justify-between z-10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-brand-500/20 border border-brand-400/30">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
              SmartEldery
              <span className="text-[10px] font-semibold uppercase px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                v2.4
              </span>
            </span>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/60 border border-slate-800/80 text-xs text-slate-400 backdrop-blur-md">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[11px] font-medium text-slate-300">Réseau télémétrique & Groq IA opérationnels</span>
        </div>
      </header>

      {/* Main card section */}
      <main className="flex-1 flex items-center justify-center px-4 py-8 z-10">
        <div className="w-full max-w-md">
          {/* Card header */}
          <div className="text-center mb-8">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
              Espace Clinique
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-2 font-normal leading-relaxed max-w-sm mx-auto">
              Plateforme unifiée de télésurveillance, détection de chutes et assistance décisionnelle par IA
            </p>
          </div>

          {/* Minimalist Card container */}
          <div className="bg-slate-900/40 border border-slate-800/80 rounded-3xl p-7 sm:p-9 shadow-2xl backdrop-blur-xl relative overflow-hidden transition-all duration-300 hover:border-slate-700/80">
            {/* Subtle top inner light stroke */}
            <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-brand-500/30 to-transparent" />

            {/* Error banner */}
            {error && (
              <div className="mb-6 p-3.5 rounded-2xl bg-rose-950/50 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2.5 animate-fadeIn">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span className="leading-snug">{error}</span>
              </div>
            )}

            {/* Login form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-[11px] font-medium uppercase tracking-wider text-slate-400 mb-2">
                  Identifiant professionnel
                </label>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500 group-focus-within:text-brand-400 transition-colors">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => {
                      setUsername(e.target.value);
                      setSelectedRole('');
                    }}
                    placeholder="ex: imad.ghobrini"
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-950/60 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 transition-all font-normal"
                    required
                    autoComplete="username"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-[11px] font-medium uppercase tracking-wider text-slate-400">
                    Mot de passe
                  </label>
                  <span className="text-[11px] text-slate-500 hover:text-brand-400 transition cursor-pointer">
                    Sécurité renforcée
                  </span>
                </div>
                <div className="relative group">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500 group-focus-within:text-brand-400 transition-colors">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      setSelectedRole('');
                    }}
                    placeholder="••••••••••••"
                    className="w-full pl-10 pr-11 py-2.5 bg-slate-950/60 border border-slate-700/60 rounded-xl text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 transition-all font-normal"
                    required
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-500 hover:text-slate-300 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Submit button */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full mt-3 py-3 px-4 rounded-xl bg-gradient-to-r from-brand-600 via-indigo-600 to-brand-500 hover:from-brand-500 hover:to-indigo-500 text-white font-semibold text-xs tracking-wide shadow-lg shadow-brand-500/20 hover:shadow-indigo-500/30 transition-all duration-300 flex items-center justify-center gap-2 group disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Vérification sécurisée...</span>
                  </>
                ) : (
                  <>
                    <span>Accéder à la console</span>
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                  </>
                )}
              </button>
            </form>

            {/* Clean Segmented Demo Profiles */}
            <div className="mt-8 pt-6 border-t border-slate-800/60">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <KeyRound className="w-3 h-3 text-slate-400" />
                  Profils de Démonstration Rapide
                </span>
                <span className="text-[10px] text-slate-500 font-mono">1-Clic</span>
              </div>

              <div className="grid grid-cols-2 gap-2">
                {demoAccounts.map((acc) => {
                  const isSelected = selectedRole === acc.id;
                  return (
                    <button
                      key={acc.id}
                      type="button"
                      onClick={() => handleSelectDemo(acc)}
                      className={`p-2.5 rounded-xl text-left border transition-all duration-200 relative group ${
                        isSelected
                          ? 'bg-indigo-950/40 border-indigo-500/50 shadow-sm shadow-indigo-500/10'
                          : 'bg-slate-950/40 hover:bg-slate-800/40 border-slate-800/80 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-xs text-slate-200 truncate">
                          {acc.label}
                        </span>
                        {isSelected && (
                          <Check className="w-3 h-3 text-indigo-400 shrink-0" />
                        )}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className={`text-[9px] px-1.5 py-0.2 rounded font-medium border ${acc.badgeColor}`}>
                          {acc.badge}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Trust and compliance tags */}
          <div className="mt-6 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-[11px] text-slate-500">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400/80" />
              Chiffrement JWT & AES-256
            </span>
            <span className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400/80" />
              Groq Cloud Inférence Active
            </span>
            <span className="flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-sky-400/80" />
              Conforme Données de Santé
            </span>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-6xl mx-auto px-6 py-6 text-center text-xs text-slate-600 z-10">
        <p>© 2026 SmartEldery Health Platform — Télésurveillance Médicale Autonome & IA Embarquée.</p>
      </footer>
    </div>
  );
};
