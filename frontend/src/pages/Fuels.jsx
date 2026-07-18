import React, { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { PageHeader, EmptyState } from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { Plus, Trash } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";

const FUELS = [
  { v: "gasolina", l: "Gasolina" },
  { v: "etanol", l: "Etanol" },
  { v: "diesel_s10", l: "Diesel S10" },
  { v: "diesel_comum", l: "Diesel Comum" },
  { v: "arla_32", l: "Arla 32" },
];

export default function Fuels() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ tipo: "gasolina", preco_litro: "" });
  const { hasRole } = useAuth();
  const canEdit = hasRole("gestor");

  const load = () => api.get("/fuels").then((r) => setItems(r.data)).catch(() => {});
  useEffect(load, []);

  const save = async () => {
    try {
      await api.post("/fuels", { tipo: form.tipo, preco_litro: Number(form.preco_litro) });
      toast.success("Preço registrado");
      setOpen(false); setForm({ tipo: "gasolina", preco_litro: "" });
      load();
    } catch (e) { toast.error("Erro", { description: formatApiError(e) }); }
  };

  const remove = async (f) => {
    if (!window.confirm("Excluir preço?")) return;
    try { await api.delete(`/fuels/${f.id}`); load(); }
    catch (e) { toast.error("Erro", { description: formatApiError(e) }); }
  };

  return (
    <div className="space-y-6" data-testid="fuels-page">
      <PageHeader
        title="Combustíveis"
        description="Preços por litro (o mais recente por tipo é utilizado nas sugestões)."
        actions={canEdit && (
          <Button onClick={() => setOpen(true)} className="bg-slate-900" data-testid="new-fuel-btn">
            <Plus size={16} className="mr-2" /> Novo preço
          </Button>
        )}
      />
      {items.length === 0 ? (
        <EmptyState title="Sem preços cadastrados" description="Adicione o primeiro preço." />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Combustível</TableHead>
                  <TableHead className="text-right">Preço/Litro</TableHead>
                  <TableHead>Registrado em</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((f) => (
                  <TableRow key={f.id}>
                    <TableCell className="capitalize">{FUELS.find((x) => x.v === f.tipo)?.l || f.tipo}</TableCell>
                    <TableCell className="text-right tabular-nums font-semibold">
                      {Number(f.preco_litro).toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 3 })}
                    </TableCell>
                    <TableCell className="text-sm text-slate-500">{new Date(f.created_at).toLocaleString("pt-BR")}</TableCell>
                    <TableCell className="text-right">
                      {canEdit && <Button size="icon" variant="ghost" onClick={() => remove(f)}><Trash size={16} className="text-red-600" /></Button>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Novo preço</DialogTitle></DialogHeader>
          <div className="grid gap-4 py-2">
            <div className="space-y-1"><Label className="text-xs">Combustível</Label>
              <Select value={form.tipo} onValueChange={(v) => setForm({ ...form, tipo: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{FUELS.map((f) => <SelectItem key={f.v} value={f.v}>{f.l}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label className="text-xs">Preço por litro</Label>
              <Input type="number" step="0.001" value={form.preco_litro} onChange={(e) => setForm({ ...form, preco_litro: e.target.value })} data-testid="f-preco" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={save} className="bg-slate-900" data-testid="save-fuel-btn">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
