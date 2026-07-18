import React, { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { PageHeader, EmptyState } from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { Plus, Pencil, Trash } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";

const FUELS = [
  { v: "gasolina", l: "Gasolina" },
  { v: "etanol", l: "Etanol" },
  { v: "diesel_s10", l: "Diesel S10" },
  { v: "diesel_comum", l: "Diesel Comum" },
  { v: "arla_32", l: "Arla 32" },
];

const empty = { nome: "", endereco: "", responsavel: "", bombas: 1, combustiveis: [], ativo: true };

export default function Stations() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);
  const { hasRole } = useAuth();
  const canEdit = hasRole("gestor");

  const load = () => api.get("/stations").then((r) => setItems(r.data)).catch(() => {});
  useEffect(load, []);

  const save = async () => {
    try {
      const payload = { ...form, bombas: Number(form.bombas) };
      if (editing) await api.put(`/stations/${editing.id}`, payload);
      else await api.post("/stations", payload);
      toast.success(editing ? "Posto atualizado" : "Posto criado");
      setOpen(false); load();
    } catch (e) { toast.error("Erro", { description: formatApiError(e) }); }
  };

  const remove = async (s) => {
    if (!window.confirm(`Excluir posto ${s.nome}?`)) return;
    try { await api.delete(`/stations/${s.id}`); toast.success("Excluído"); load(); }
    catch (e) { toast.error("Erro", { description: formatApiError(e) }); }
  };

  const toggleFuel = (v) => {
    setForm((f) => ({
      ...f,
      combustiveis: f.combustiveis.includes(v) ? f.combustiveis.filter((x) => x !== v) : [...f.combustiveis, v],
    }));
  };

  return (
    <div className="space-y-6" data-testid="stations-page">
      <PageHeader
        title="Postos"
        description="Postos de abastecimento cadastrados."
        actions={canEdit && (
          <Button onClick={() => { setEditing(null); setForm(empty); setOpen(true); }} className="bg-slate-900" data-testid="new-station-btn">
            <Plus size={16} className="mr-2" /> Novo posto
          </Button>
        )}
      />
      {items.length === 0 ? (
        <EmptyState title="Nenhum posto cadastrado" description="Adicione o primeiro posto." />
      ) : (
        <Card>
          <CardContent className="p-0 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>Endereço</TableHead>
                  <TableHead>Responsável</TableHead>
                  <TableHead className="text-center">Bombas</TableHead>
                  <TableHead>Combustíveis</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium">{s.nome}</TableCell>
                    <TableCell className="text-sm text-slate-600">{s.endereco}</TableCell>
                    <TableCell>{s.responsavel || "—"}</TableCell>
                    <TableCell className="text-center tabular-nums">{s.bombas}</TableCell>
                    <TableCell className="text-xs">
                      {s.combustiveis?.length ? s.combustiveis.map((c) => (
                        <Badge key={c} variant="secondary" className="mr-1 capitalize">{c.replace("_"," ")}</Badge>
                      )) : "—"}
                    </TableCell>
                    <TableCell><Badge variant={s.ativo ? "default" : "secondary"}>{s.ativo ? "Ativo" : "Inativo"}</Badge></TableCell>
                    <TableCell className="text-right space-x-1">
                      {canEdit && <>
                        <Button size="icon" variant="ghost" onClick={() => { setEditing(s); setForm({ ...empty, ...s }); setOpen(true); }}><Pencil size={16} /></Button>
                        <Button size="icon" variant="ghost" onClick={() => remove(s)}><Trash size={16} className="text-red-600" /></Button>
                      </>}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>{editing ? "Editar posto" : "Novo posto"}</DialogTitle></DialogHeader>
          <div className="grid md:grid-cols-2 gap-4 py-2">
            <F label="Nome *"><Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} data-testid="s-nome" /></F>
            <F label="Endereço *"><Input value={form.endereco} onChange={(e) => setForm({ ...form, endereco: e.target.value })} data-testid="s-endereco" /></F>
            <F label="Responsável"><Input value={form.responsavel} onChange={(e) => setForm({ ...form, responsavel: e.target.value })} /></F>
            <F label="Bombas"><Input type="number" value={form.bombas} onChange={(e) => setForm({ ...form, bombas: e.target.value })} /></F>
            <div className="md:col-span-2 space-y-2">
              <Label className="text-xs">Combustíveis disponíveis</Label>
              <div className="flex flex-wrap gap-3">
                {FUELS.map((f) => (
                  <label key={f.v} className="flex items-center gap-2 text-sm border border-slate-200 rounded-md px-3 py-2 cursor-pointer">
                    <Checkbox checked={form.combustiveis.includes(f.v)} onCheckedChange={() => toggleFuel(f.v)} data-testid={`fuel-${f.v}`} />
                    {f.l}
                  </label>
                ))}
              </div>
            </div>
            <div className="md:col-span-2 flex items-center gap-2">
              <Checkbox checked={form.ativo} onCheckedChange={(v) => setForm({ ...form, ativo: !!v })} />
              <Label className="text-sm">Ativo</Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={save} className="bg-slate-900" data-testid="save-station-btn">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const F = ({ label, children }) => (<div className="space-y-1"><Label className="text-xs">{label}</Label>{children}</div>);
