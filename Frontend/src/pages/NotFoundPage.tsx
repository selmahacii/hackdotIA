import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, ArrowLeft } from 'lucide-react';
import { Button } from '../components/Common/Button';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-6">
      <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 text-brand-400 mb-4 shadow-xl">
        <ShieldAlert className="w-12 h-12" />
      </div>
      <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight mb-2">Page non trouvée (404)</h1>
      <p className="text-sm text-slate-400 max-w-md mb-6">
        La ressource demandée n'existe pas ou a été déplacée.
      </p>
      <Link to="/dashboard">
        <Button variant="primary" icon={<ArrowLeft className="w-4 h-4" />}>
          Retour au tableau de bord
        </Button>
      </Link>
    </div>
  );
};
