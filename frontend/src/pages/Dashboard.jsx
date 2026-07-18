import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { Truck, IdentificationCard, BellRinging, Coins, Drop } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

const COLORS = ["#2563eb", "#16a34a", "#f59e0b", "#8b5cf6", "#ef4444", "#0891b2"];

const fmtCurrency = (v) =>
  (v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2 });
const fmtLiters = (v) => `${(v || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} L`;

const KpiCard = ({ label, value, sub, icon: Icon, tid, accent }) => (
  <Card className="rise" data-testid={tid}>
    <CardContent className="p-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-500 font-medium">{label}</div>
          <div className="mt-2 text-3xl font-bold tabular-nums text-slate-900">{value}</div>
          {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
        </div>
        <div className={`h-10 w-10 rounded-md grid place-items-center ${accent || "bg-slate-100 text-slate-700"}`}>
          <Icon size={20} weight="bold" />
        </div>
      </div>
    </CardContent>
  </Card>
);

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get("/dashboard/summary")
      .then((r) => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-28 rounded-lg bg-white border border-slate-200 animate-pulse" />
        ))}
      </div>
    );
  }

  const secData = (data?.per_secretaria || []).slice(0, 6).map((s) => ({
    name: s.secretaria,
    litros: s.litros,
    valor: s.valor,
  }));

  const top = data?.top_vehicles || [];
  const series = data?.series || [];

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">Visão executiva da frota municipal — mês corrente.</p>
        </div>
        <Link to="/refuel">
          <Button className="bg-slate-900 hover:bg-slate-800" data-testid="dashboard-new-refuel">
            Novo abastecimento
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Litros no mês"
          value={fmtLiters(data?.month?.litros)}
          sub={`${data?.month?.count || 0} abastecimentos`}
          icon={Drop}
          tid="kpi-litros"
          accent="bg-blue-50 text-blue-600"
        />
        <KpiCard
          label="Valor gasto"
          value={fmtCurrency(data?.month?.valor)}
          sub="Mês corrente"
          icon={Coins}
          tid="kpi-valor"
          accent="bg-green-50 text-green-600"
        />
        <KpiCard
          label="Veículos ativos"
          value={data?.active_vehicles || 0}
          sub={`${data?.active_drivers || 0} motoristas ativos`}
          icon={Truck}
          tid="kpi-vehicles"
        />
        <KpiCard
          label="Alertas abertos"
          value={data?.open_alerts || 0}
          sub="Fraude e limites"
          icon={BellRinging}
          tid="kpi-alerts"
          accent={data?.open_alerts > 0 ? "bg-red-50 text-red-600" : "bg-slate-100 text-slate-700"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Consumo (últimos 30 dias)</CardTitle>
          </CardHeader>
          <CardContent>
            {series.length === 0 ? (
              <EmptyChart label="Sem abastecimentos registrados ainda." />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={series}>
                  <defs>
                    <linearGradient id="cGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563eb" stopOpacity={0.28} />
                      <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v, k) => (k === "valor" ? fmtCurrency(v) : fmtLiters(v))} />
                  <Area type="monotone" dataKey="litros" stroke="#2563eb" strokeWidth={2} fill="url(#cGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Consumo por secretaria</CardTitle>
          </CardHeader>
          <CardContent>
            {secData.length === 0 ? (
              <EmptyChart label="Nenhuma secretaria com consumo neste mês." />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie data={secData} dataKey="litros" nameKey="name" innerRadius={45} outerRadius={80}>
                    {secData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => fmtLiters(v)} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ranking — top veículos</CardTitle>
          </CardHeader>
          <CardContent>
            {top.length === 0 ? (
              <EmptyChart label="Sem dados suficientes." />
            ) : (
              <div className="space-y-2">
                {top.map((v, i) => (
                  <div
                    key={v.vehicle_id}
                    className="flex items-center gap-3 py-2 border-b border-slate-100 last:border-0"
                    data-testid={`top-vehicle-${i}`}
                  >
                    <div className="h-8 w-8 rounded-md bg-slate-100 grid place-items-center font-bold text-slate-700 text-sm">
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-mono font-semibold text-slate-900">{v.placa}</div>
                      <div className="text-xs text-slate-500">{v.count} abastecimentos</div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-semibold tabular-nums">{fmtLiters(v.litros)}</div>
                      <div className="text-xs text-slate-500 tabular-nums">{fmtCurrency(v.valor)}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ranking — secretarias</CardTitle>
          </CardHeader>
          <CardContent>
            {data?.per_secretaria?.length ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={secData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => fmtCurrency(v)} />
                  <Bar dataKey="valor" fill="#2563eb" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyChart label="Sem dados de consumo por secretaria." />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

const EmptyChart = ({ label }) => (
  <div className="h-[260px] grid place-items-center text-sm text-slate-500 border border-dashed border-slate-200 rounded-md">
    {label}
  </div>
);
