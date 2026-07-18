import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { PageHeader, EmptyState } from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function Audit() {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");

  useEffect(() => {
    api.get("/audit", { params: { limit: 500 } }).then((r) => setItems(r.data)).catch(() => {});
  }, []);

  const filtered = items.filter((a) =>
    !q ||
    a.action?.toLowerCase().includes(q.toLowerCase()) ||
    a.resource?.toLowerCase().includes(q.toLowerCase()) ||
    a.user_email?.toLowerCase().includes(q.toLowerCase())
  );

  return (
    <div className="space-y-6" data-testid="audit-page">
      <PageHeader title="Auditoria" description="Log completo de ações do sistema." />
      <Input placeholder="Buscar por ação, recurso ou usuário..." value={q} onChange={(e) => setQ(e.target.value)} className="max-w-md" />
      {filtered.length === 0 ? (
        <EmptyState title="Nenhum registro" description="Nada encontrado nos logs." />
      ) : (
        <Card>
          <CardContent className="p-0 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Quando</TableHead>
                  <TableHead>Usuário</TableHead>
                  <TableHead>Ação</TableHead>
                  <TableHead>Recurso</TableHead>
                  <TableHead>Detalhes</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((a) => (
                  <TableRow key={a.id}>
                    <TableCell className="text-xs text-slate-500">{new Date(a.created_at).toLocaleString("pt-BR")}</TableCell>
                    <TableCell className="text-sm">{a.user_email || "—"}</TableCell>
                    <TableCell><Badge variant="secondary" className="capitalize">{a.action}</Badge></TableCell>
                    <TableCell className="text-sm capitalize">{a.resource}</TableCell>
                    <TableCell className="text-xs text-slate-600 max-w-xs truncate">{JSON.stringify(a.details)}</TableCell>
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
