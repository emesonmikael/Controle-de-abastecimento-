import React, { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { PageHeader, EmptyState } from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { Plus, Pencil, Trash, CreditCard } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";

const empty = {
  nome: "", cpf: "", cnh: "", categoria_cnh: "B",
  validade_cnh: "", secretaria: "", telefone: "", foto: "", status: "ativo",
};

export default function Drivers() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);
  const { hasRole } = useAuth();
  const canEdit = hasRole("gestor");

  const load = () => {
    setLoading(true);
    api.get("/drivers").then((r) => setItems(r.data)).catch(() => setItems([])).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const save = async () => {
    try {
      if (editing) await api.put(`/drivers/${editing.id}`, form);
      else await api.post("/drivers", form);
      toast.success(editing ? "Motorista atualizado" : "Motorista criado com cartão NFC");
      setOpen(false);
      load();
    } catch (e) {
      toast.error("Erro", { description: formatApiError(e) });
    }
  };
  const remove = async (d) => {
    if (!window.confirm(`Excluir motorista ${d.nome}?`)) return;
    try { await api.delete(`/drivers/${d.id}`); toast.success("Excluído"); load(); }
    catch (e) { toast.error("Erro", { description: formatApiError(e) }); }
  };

  const isExpired = (v) => {
    if (!v) return false;
    try { return new Date(v) < new Date(); } catch { return false; }
  };

  return (
    <div className="space-y-6" data-testid="drivers-page">
      <PageHeader
        title="Motoristas"
        description="Cadastro de motoristas municipais. Cada motorista recebe um cartão NFC."
        actions={canEdit && (
          <Button onClick={() => { setEditing(null); setForm(empty); setOpen(true); }} className="bg-slate-900" data-testid="new-driver-btn">
            <Plus size={16} className="mr-2" /> Novo motorista
          </Button>
        )}
      />
      {loading ? (
        <div className="h-64 bg-white border border-slate-200 rounded-lg animate-pulse" />
      ) : items.length === 0 ? (
        <EmptyState title="Nenhum motorista cadastrado" description="Comece cadastrando o primeiro motorista." />
      ) : (
        <Card>
          <CardContent className="p-0 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nome</TableHead>
                  <TableHead>CPF</TableHead>
                  <TableHead>CNH</TableHead>
                  <TableHead>Validade</TableHead>
                  <TableHead>Secretaria</TableHead>
                  <TableHead>Cartão NFC</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((d) => (
                  <TableRow key={d.id}>
                    <TableCell className="font-medium">{d.nome}</TableCell>
                    <TableCell className="font-mono text-sm">{d.cpf}</TableCell>
                    <TableCell className="font-mono text-sm">{d.cnh} <span className="text-xs text-slate-500">({d.categoria_cnh})</span></TableCell>
                    <TableCell className={isExpired(d.validade_cnh) ? "text-red-600 font-medium" : ""}>{d.validade_cnh}</TableCell>
                    <TableCell>{d.secretaria}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1 font-mono text-xs bg-slate-100 px-2 py-1 rounded">
                        <CreditCard size={12} /> {d.nfc_card_id}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge variant={d.status === "ativo" ? "default" : "secondary"} className="capitalize">{d.status}</Badge>
                    </TableCell>
                    <TableCell className="text-right space-x-1">
                      {canEdit && <>
                        <Button size="icon" variant="ghost" onClick={() => { setEditing(d); setForm({ ...empty, ...d }); setOpen(true); }}><Pencil size={16} /></Button>
                        <Button size="icon" variant="ghost" onClick={() => remove(d)}><Trash size={16} className="text-red-600" /></Button>
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
          <DialogHeader><DialogTitle>{editing ? "Editar motorista" : "Novo motorista"}</DialogTitle></DialogHeader>
          <div className="grid md:grid-cols-2 gap-4 py-2">
            <F label="Nome *"><Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} data-testid="d-nome" /></F>
            <F label="CPF *"><Input value={form.cpf} onChange={(e) => setForm({ ...form, cpf: e.target.value })} data-testid="d-cpf" /></F>
            <F label="CNH *"><Input value={form.cnh} onChange={(e) => setForm({ ...form, cnh: e.target.value })} /></F>
            <F label="Categoria *">
              <Select value={form.categoria_cnh} onValueChange={(v) => setForm({ ...form, categoria_cnh: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {["A","B","C","D","E","AB","AC","AD","AE"].map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </F>
            <F label="Validade CNH *"><Input type="date" value={form.validade_cnh} onChange={(e) => setForm({ ...form, validade_cnh: e.target.value })} /></F>
            <F label="Secretaria *"><Input value={form.secretaria} onChange={(e) => setForm({ ...form, secretaria: e.target.value })} /></F>
            <F label="Telefone"><Input value={form.telefone} onChange={(e) => setForm({ ...form, telefone: e.target.value })} /></F>
            <F label="Foto URL"><Input value={form.foto} onChange={(e) => setForm({ ...form, foto: e.target.value })} /></F>
            <F label="Status">
              <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ativo">Ativo</SelectItem>
                  <SelectItem value="inativo">Inativo</SelectItem>
                  <SelectItem value="suspenso">Suspenso</SelectItem>
                </SelectContent>
              </Select>
            </F>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={save} className="bg-slate-900" data-testid="save-driver-btn">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const F = ({ label, children }) => (
  <div className="space-y-1"><Label className="text-xs">{label}</Label>{children}</div>
);
