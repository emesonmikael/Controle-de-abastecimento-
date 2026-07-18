import React, { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  Gauge,
  Truck,
  IdentificationCard,
  GasPump,
  Buildings,
  CreditCard,
  BellRinging,
  ClipboardText,
  Users,
  SignOut,
  List,
  X,
  Lightning,
} from "@phosphor-icons/react";
import { Toaster } from "@/components/ui/sonner";
import { Button } from "@/components/ui/button";

const NAV = [
  { to: "/", label: "Dashboard", icon: Gauge, tid: "nav-dashboard", roles: null, hideFor: ["frentista"] },
  { to: "/refuel", label: "Novo Abastecimento", icon: Lightning, tid: "nav-refuel", roles: ["frentista", "gestor"] },
  { to: "/refuels", label: "Abastecimentos", icon: GasPump, tid: "nav-refuels", roles: null, hideFor: ["frentista"] },
  { to: "/vehicles", label: "Veículos", icon: Truck, tid: "nav-vehicles", roles: null, hideFor: ["frentista"] },
  { to: "/drivers", label: "Motoristas", icon: IdentificationCard, tid: "nav-drivers", roles: null, hideFor: ["frentista"] },
  { to: "/stations", label: "Postos", icon: Buildings, tid: "nav-stations", roles: null, hideFor: ["frentista"] },
  { to: "/fuels", label: "Combustíveis", icon: GasPump, tid: "nav-fuels", roles: null, hideFor: ["frentista"] },
  { to: "/cards", label: "Cartões NFC", icon: CreditCard, tid: "nav-cards", roles: ["gestor", "auditor"] },
  { to: "/alerts", label: "Alertas", icon: BellRinging, tid: "nav-alerts", roles: null, hideFor: ["frentista"] },
  { to: "/users", label: "Usuários", icon: Users, tid: "nav-users", roles: ["gestor"] },
  { to: "/audit", label: "Auditoria", icon: ClipboardText, tid: "nav-audit", roles: ["gestor", "auditor"] },
];

export default function Layout() {
  const { user, logout, hasRole } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const visible = NAV.filter((n) => {
    if (n.hideFor && user && n.hideFor.includes(user.role)) return false;
    return !n.roles || hasRole(...n.roles);
  });

  return (
    <div className="min-h-screen bg-slate-50 flex" data-testid="app-layout">
      {/* Sidebar */}
      <aside
        className={`${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        } lg:translate-x-0 fixed lg:sticky top-0 z-40 h-screen w-72 bg-white border-r border-slate-200 flex flex-col transition-transform`}
        data-testid="sidebar"
      >
        <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-200">
          <div className="h-9 w-9 rounded-lg bg-slate-900 text-white grid place-items-center">
            <Lightning weight="fill" size={20} />
          </div>
          <div>
            <div className="font-bold text-slate-900 leading-tight">Frota NFC</div>
            <div className="text-xs text-slate-500">Controle Municipal</div>
          </div>
          <button
            className="ml-auto lg:hidden p-1 text-slate-500"
            onClick={() => setMobileOpen(false)}
            data-testid="sidebar-close"
          >
            <X size={22} />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
          {visible.map(({ to, label, icon: Icon, tid }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setMobileOpen(false)}
              data-testid={tid}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm transition-colors ${
                  isActive
                    ? "bg-slate-900 text-white"
                    : "text-slate-700 hover:bg-slate-100"
                }`
              }
            >
              <Icon size={18} weight="regular" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-200">
          <div className="flex items-center gap-3 mb-3">
            <div className="h-9 w-9 rounded-full bg-blue-600 text-white grid place-items-center font-semibold">
              {user?.name?.[0]?.toUpperCase() || "?"}
            </div>
            <div className="min-w-0">
              <div className="text-sm font-medium text-slate-900 truncate" data-testid="user-name">
                {user?.name}
              </div>
              <div className="text-xs text-slate-500 capitalize">{user?.role}</div>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-center"
            onClick={handleLogout}
            data-testid="logout-btn"
          >
            <SignOut size={16} className="mr-2" />
            Sair
          </Button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-30 h-14 bg-white border-b border-slate-200 flex items-center px-4">
        <button onClick={() => setMobileOpen(true)} data-testid="sidebar-open">
          <List size={22} />
        </button>
        <div className="ml-3 font-bold">Frota NFC</div>
      </div>

      <main className="flex-1 min-w-0 pt-14 lg:pt-0">
        <div className="max-w-[1400px] mx-auto p-6 lg:p-8">
          <Outlet />
        </div>
      </main>

      <Toaster richColors position="top-right" />
    </div>
  );
}
