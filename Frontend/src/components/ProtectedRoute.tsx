import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';
import { Spinner } from './Common/Spinner';
import { ShieldAlert } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: UserRole[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles }) => {
  const { isAuthenticated, isLoading, hasRole, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center">
        <Spinner size="lg" />
        <p className="text-sm text-slate-400 mt-4">Vérification de la session sécurisée...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !hasRole(allowedRoles)) {
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center text-center p-6">
        <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-500/40 text-rose-400 mb-4 shadow-xl">
          <ShieldAlert className="w-12 h-12" />
        </div>
        <h2 className="text-xl font-bold text-slate-100 mb-2">Accès Restreint (403)</h2>
        <p className="text-sm text-slate-400 max-w-md mb-6">
          Votre rôle actuel (<strong>{user?.role}</strong>) ne possède pas les permissions nécessaires pour accéder à cette page.
        </p>
        <button
          onClick={() => window.history.back()}
          className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 hover:bg-slate-700 text-sm font-medium transition"
        >
          &larr; Retour
        </button>
      </div>
    );
  }

  return <>{children}</>;
};
