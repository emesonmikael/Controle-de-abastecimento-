import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { PageHeader, EmptyState } from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const fmt = (v) => (v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export default function RefuelsList() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/refuels", { params: { limit: 300 } })
      .then((r) => setItems(r.data))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6" data-testid="refuels-page">
      <PageHeader title="Abastecimentos" description="Todos os abastecimentos registrados." />
      {loading ? (
        <div className="h-64 bg-white border border-slate-200 rounded-lg animate-pulse" />
      ) : items.length === 0 ? (
        <EmptyState title="Sem abastecimentos" description="Nenhum registro ainda." />
      ) : (
        <Card>
          <CardContent className="p-0 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data/Hora</TableHead>
                  <TableHead>Placa</TableHead>
                  <TableHead>Motorista</TableHead>
                  <TableHead>Secretaria</TableHead>
                  <TableHead>Combustível</TableHead>
                  <TableHead className="text-right">Litros</TableHead>
                  <TableHead className="text-right">R$/L</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                  <TableHead className="text-right">Km</TableHead>
                  <TableHead className="text-right">km/L</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="text-xs text-slate-500 whitespace-nowrap">{new Date(r.created_at).toLocaleString("pt-BR")}</TableCell>
                    <TableCell className="font-mono font-semibold">{r.vehicle_placa}</TableCell>
                    <TableCell className="text-sm">{r.driver_nome || "—"}</TableCell>
                    <TableCell className="text-sm">{r.secretaria}</TableCell>
                    <TableCell><Badge variant="secondary" className="capitalize">{r.tipo_combustivel.replace("_", " ")}</Badge></TableCell>
                    <TableCell className="text-right tabular-nums">{r.litros.toFixed(2)}</TableCell>
                    <TableCell className="text-right tabular-nums">{r.preco_litro.toFixed(3)}</TableCell>
                    <TableCell className="text-right tabular-nums font-semibold">{fmt(r.valor_total)}</TableCell>
                    <TableCell className="text-right tabular-nums">{r.km_atual.toLocaleString("pt-BR")}</TableCell>
                    <TableCell className="text-right tabular-nums">{r.autonomia ? r.autonomia.toFixed(2) : "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
