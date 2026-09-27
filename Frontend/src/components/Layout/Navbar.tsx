import React, { useState } from 'react';
import { Bell, LogOut, Shield, X } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useWebSocket } from '../../context/WebSocketContext';
import { Badge } from '../Common/Badge';
import { Link } from 'react-router-dom';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const { isConnected, isConnecting, unreadCount, clearUnread, liveAlerts } = useWebSocket();
  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <header className="sticky top-0 z-40 h-16 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between">
      {/* Brand title */}
      <div className="flex items-center gap-3">
        <Link to="/dashboard" className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center shadow-md shadow-brand-600/30">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-bold text-base text-slate-100 tracking-tight">Guardia</span>
            <span className="text-[10px] font-semibold text-brand-400 block -mt-1 tracking-wider uppercase">
              Télésurveillance & IA
            </span>
          </div>
        </Link>
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-4">
        {/* Live WebSocket Status indicator */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs">
          <span className="relative flex h-2 w-2">
            {isConnected && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            )}
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                isConnected ? 'bg-emerald-500' : isConnecting ? 'bg-amber-500' : 'bg-rose-500'
              }`}
            ></span>
          </span>
          <span className="font-medium text-slate-300">
            {isConnected ? 'LIVE' : isConnecting ? 'Connexion...' : 'Déconnecté'}
          </span>
        </div>

        {/* Notifications Popover */}
        <div className="relative">
          <button
            onClick={() => {
              setShowNotifications(!showNotifications);
              if (!showNotifications) clearUnread();
            }}
            className="relative p-2 rounded-xl bg-slate-800/80 border border-slate-700/60 text-slate-300 hover:text-white hover:bg-slate-700/60 transition"
            title="Notifications d'alertes en direct"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 flex h-4 min-w-4 px-1 items-center justify-center rounded-full bg-rose-600 text-[10px] font-bold text-white shadow-sm">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden z-50 animate-fadeIn">
              <div className="flex items-center justify-between p-3.5 border-b border-slate-800 bg-slate-800/50">
                <span className="text-xs font-semibold text-slate-200">Alertes Récentes (Live)</span>
                <button
                  onClick={() => setShowNotifications(false)}
                  className="text-slate-400 hover:text-slate-200"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/60">
                {liveAlerts.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500">
                    Aucune alerte reçue depuis l'ouverture de la session
                  </div>
                ) : (
                  liveAlerts.slice(0, 10).map((alert) => (
                    <Link
                      key={alert.id}
                      to={`/alerts/${alert.id}`}
                      onClick={() => setShowNotifications(false)}
                      className="block p-3 hover:bg-slate-800/60 transition"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <Badge label={alert.severity} variant="severity" />
                        <span className="text-[10px] text-slate-500">
                          {new Date(alert.occurred_at).toLocaleTimeString()}
                        </span>
                      </div>
                      <p className="text-xs font-medium text-slate-200 truncate">{alert.title}</p>
                      {alert.ai_summary && (
                        <p className="text-[11px] text-indigo-300 mt-1 truncate">
                          IA: {alert.ai_summary}
                        </p>
                      )}
                    </Link>
                  ))
                )}
              </div>

              <div className="p-2 border-t border-slate-800 bg-slate-800/30 text-center">
                <Link
                  to="/alerts"
                  onClick={() => setShowNotifications(false)}
                  className="text-xs text-brand-400 hover:text-brand-300 font-medium"
                >
                  Voir toutes les alertes &rarr;
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* User profile & Logout */}
        <div className="flex items-center gap-3 pl-2 border-l border-slate-800">
          <div className="text-right hidden sm:block">
            <div className="text-xs font-semibold text-slate-200">{user?.full_name || user?.username}</div>
            <div className="flex justify-end mt-0.5">
              <Badge label={user?.role || 'READ_ONLY'} variant="role" />
            </div>
          </div>

          <button
            onClick={logout}
            className="p-2 rounded-xl bg-slate-800/60 hover:bg-red-950/60 text-slate-400 hover:text-red-300 border border-slate-700/60 hover:border-red-500/40 transition"
            title="Se déconnecter"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
