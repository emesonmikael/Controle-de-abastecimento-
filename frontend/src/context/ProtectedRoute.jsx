import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export const ProtectedRoute = ({ children, roles }) => {
  const { user, loading, hasRole } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50" data-testid="auth-loading">
        <div className="h-8 w-8 border-2 border-slate-300 border-t-slate-900 rounded-full animate-spin" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  if (roles && !hasRole(...roles)) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8" data-testid="forbidden">
        <div className="text-center">
          <h2 className="text-2xl font-bold">Acesso restrito</h2>
          <p className="text-slate-500 mt-2">Você não tem permissão para acessar esta página.</p>
        </div>
      </div>
    );
  }
  return children;
};
