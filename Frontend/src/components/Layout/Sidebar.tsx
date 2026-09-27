import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Radio,
  Users,
  AlertTriangle,
  Activity,
  Cpu,
  Smartphone,
  Shield,
  UserCheck,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export const Sidebar: React.FC = () => {
  const { isAdmin, isSuperAdmin } = useAuth();

  const navItems = [
    { to: '/dashboard', label: 'Tableau de bord', icon: LayoutDashboard },
    { to: '/monitoring', label: 'Surveillance Live', icon: Radio, highlight: true },
    { to: '/elderly', label: 'Résidents', icon: Users },
    { to: '/alerts', label: 'Alertes', icon: AlertTriangle },
    { to: '/measurements', label: 'Mesures', icon: Activity },
    { to: '/sensors', label: 'Intégrité Capteurs', icon: Cpu },
    { to: '/devices', label: 'Appareils IoT', icon: Smartphone },
  ];

  const adminItems = [
    { to: '/admin', label: 'Métriques Système', icon: Shield },
    { to: '/admin/users', label: 'Gestion Utilisateurs', icon: UserCheck },
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="p-4 space-y-1 flex-1">
        <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Supervision
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-brand-600/15 text-brand-400 border border-brand-500/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.label}</span>
              {item.highlight && (
                <span className="ml-auto w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              )}
            </NavLink>
          );
        })}

        {isAdmin && (
          <>
            <div className="pt-6 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Administration {isSuperAdmin ? '(Superadmin)' : ''}
            </div>
            {adminItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/admin'}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-purple-600/15 text-purple-300 border border-purple-500/30'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`
                  }
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </>
        )}
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-slate-800/60 text-center">
        <p className="text-[11px] text-slate-500">
          Guardia v1.2 &bull; Groq AI Engine
        </p>
      </div>
    </aside>
  );
};
