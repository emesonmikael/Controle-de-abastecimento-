import React, { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { PageHeader, EmptyState } from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "sonner";
import { WarningCircle, CheckCircle, Sparkle } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";

const SEV = {
  info: "bg-blue-100 text-blue-800",
  warning: "bg-yellow-100 text-yellow-800",
  critical: "bg-red-100 text-red-800",
};

export default function Alerts() {
  const [items, setItems] = useState([]);
  const [tab, setTab] = useState("open");
  const [loading, setLoading] = useState(true);
  const { hasRole } = useAuth();
  const canResolve = hasRole("gestor");

  const load = () => {
    setLoading(true);
    api.get("/alerts", { params: { resolvido: tab === "resolved" } })
      .then((r) => setItems(r.data)).catch(() => setItems([]))
      .finally(() => setLoading(false));
  };
  useEffect(load, [tab]);

  const resolve = async (a) => {
    try {
      await api.post(`/alerts/${a.id}/resolve`);
      toast.success("Alerta resolvido");
      load();
    } catch (e) { toast.error("Erro", { description: formatApiError(e) }); }
  };

  return (
    <div className="space-y-6" data-testid="alerts-page">
      <PageHeader
        title="Alertas & Fraudes"
        description="Alertas gerados por regras e pela IA de detecção de anomalias."
      />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="open" data-testid="tab-open">Abertos</TabsTrigger>
          <TabsTrigger value="resolved" data-testid="tab-resolved">Resolvidos</TabsTrigger>
        </TabsList>
        <TabsContent value={tab} className="mt-4">
          {loading ? (
            <div className="h-40 bg-white rounded-lg border border-slate-200 animate-pulse" />
          ) : items.length === 0 ? (
            <EmptyState title="Nenhum alerta" description="Nenhum alerta neste estado no momento." />
          ) : (
            <div className="grid gap-3">
              {items.map((a) => (
                <Card key={a.id} className="rise" data-testid={`alert-${a.id}`}>
                  <CardContent className="p-5 flex items-start gap-4">
                    <div className={`h-9 w-9 rounded-md grid place-items-center shrink-0 ${SEV[a.severidade] || SEV.info}`}>
                      {a.ia_gerado ? <Sparkle size={18} weight="fill" /> : <WarningCircle size={18} weight="fill" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-slate-900">{a.tipo.replace(/_/g, " ")}</span>
                        <Badge className={SEV[a.severidade] || SEV.info}>{a.severidade}</Badge>
                        {a.ia_gerado && <Badge className="bg-purple-100 text-purple-800">IA</Badge>}
                      </div>
                      <div className="text-sm text-slate-700 mt-1">{a.mensagem}</div>
                      {a.contexto?.reasons?.length > 0 && (
                        <ul className="mt-2 text-xs text-slate-600 list-disc pl-4 space-y-0.5">
                          {a.contexto.reasons.map((r, i) => <li key={i}>{r}</li>)}
                        </ul>
                      )}
                      <div className="text-xs text-slate-400 mt-2">{new Date(a.created_at).toLocaleString("pt-BR")}</div>
                    </div>
                    {tab === "open" && canResolve && (
                      <Button variant="outline" size="sm" onClick={() => resolve(a)} data-testid={`resolve-${a.id}`}>
                        <CheckCircle size={16} className="mr-1" /> Resolver
                      </Button>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
