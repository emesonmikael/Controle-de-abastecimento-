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
import { Plus, Pencil, Trash } from "@phosphor-icons/react";

const empty = { email: "", name: "", role: "frentista", phone: "", password: "", active: true };

const ROLES = [
  { v: "admin", l: "Administrador" },
  { v: "gestor", l: "Gestor" },
  { v: "frentista", l: "Frentista" },
  { v: "motorista", l: "Motorista" },
  { v: "auditor", l: "Auditor" },
];

export default function Users() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);

  const load = () => api.get("/users").then((r) => setItems(r.data)).catch(() => {});
  useEffect(load, []);

  const save = async () => {
    try {
      if (editing) {
        const payload = { ...form };
        if (!payload.password) delete payload.password;
        delete payload.email;
        await api.put(`/users/${editing.id}`, payload);
        toast.success("Usuário atualizado");
      } else {
        await api.post("/users", form);
        toast.success("Usuário criado");
      }
      setOpen(false); load();
    } catch (e) { toast.error("Erro", { description: formatApiError(e) }); }
  };

  const remove = async (u) => {
    if (!window.confirm(`Excluir ${u.email}?`)) return;
    try { await api.delete(`/users/${u.id}`); load(); }
    catch (e) { toast.error("Erro", { description: formatApiError(e) }); }
  };

  return (
    <div className="space-y-6" data-testid="users-page">
      <PageHeader
        title="Usuários"
        description="Gestão de usuários do sistema por nível de acesso."
        actions={
          <Button onClick={() => { setEditing(null); setForm(empty); setOpen(true); }} className="bg-slate-900" data-testid="new-user-btn">
            <Plus size={16} className="mr-2" /> Novo usuário
          </Button>
        }
      />
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>E-mail</TableHead>
                <TableHead>Papel</TableHead>
                <TableHead>Status</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="font-medium">{u.name}</TableCell>
                  <TableCell className="text-sm text-slate-600">{u.email}</TableCell>
                  <TableCell><Badge variant="secondary" className="capitalize">{u.role}</Badge></TableCell>
                  <TableCell>
                    <Badge variant={u.active ? "default" : "destructive"}>{u.active ? "Ativo" : "Inativo"}</Badge>
                  </TableCell>
                  <TableCell className="text-right space-x-1">
                    <Button size="icon" variant="ghost" onClick={() => { setEditing(u); setForm({ ...empty, ...u, password: "" }); setOpen(true); }}><Pencil size={16} /></Button>
                    <Button size="icon" variant="ghost" onClick={() => remove(u)}><Trash size={16} className="text-red-600" /></Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? "Editar usuário" : "Novo usuário"}</DialogTitle></DialogHeader>
          <div className="grid gap-4 py-2">
            <F label="Nome"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="u-name" /></F>
            {!editing && <F label="E-mail"><Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="u-email" /></F>}
            <F label="Papel">
              <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                <SelectTrigger data-testid="u-role"><SelectValue /></SelectTrigger>
                <SelectContent>{ROLES.map((r) => <SelectItem key={r.v} value={r.v}>{r.l}</SelectItem>)}</SelectContent>
              </Select>
            </F>
            <F label="Telefone"><Input value={form.phone || ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></F>
            <F label={editing ? "Nova senha (deixe vazio para manter)" : "Senha"}>
              <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} data-testid="u-password" />
            </F>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={save} className="bg-slate-900" data-testid="save-user-btn">Salvar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const F = ({ label, children }) => (<div className="space-y-1"><Label className="text-xs">{label}</Label>{children}</div>);
