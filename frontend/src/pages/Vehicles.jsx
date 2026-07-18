import React, { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { PageHeader, EmptyState } from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { Plus, Truck, Pencil, Trash, CreditCard } from "@phosphor-icons/react";
import { useAuth } from "@/context/AuthContext";

const FUELS = [
  { v: "gasolina", l: "Gasolina" },
  { v: "etanol", l: "Etanol" },
  { v: "diesel_s10", l: "Diesel S10" },
  { v: "diesel_comum", l: "Diesel Comum" },
  { v: "arla_32", l: "Arla 32" },
];

const empty = {
  placa: "",
  renavam: "",
  modelo: "",
  marca: "",
  ano: "",
  secretaria: "",
  departamento: "",
  centro_custo: "",
  tipo_combustivel: "gasolina",
  capacidade_tanque: "",
  media_km_l: "",
  km_atual: "0",
  status: "ativo",
  foto: "",
  limite_diario_litros: "",
  limite_semanal_litros: "",
  limite_mensal_litros: "",
};

export default function Vehicles() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);
  const [saving, setSaving] = useState(false);
  const { hasRole } = useAuth();
  const canEdit = hasRole("gestor");

  const load = () => {
    setLoading(true);
    api
      .get("/vehicles")
      .then((r) => setItems(r.data))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const openNew = () => {
    setEditing(null);
    setForm(empty);
    setOpen(true);
  };
  const openEdit = (v) => {
    setEditing(v);
    setForm({
      ...empty,
      ...v,
      ano: v.ano ?? "",
      media_km_l: v.media_km_l ?? "",
      limite_diario_litros: v.limite_diario_litros ?? "",
      limite_semanal_litros: v.limite_semanal_litros ?? "",
      limite_mensal_litros: v.limite_mensal_litros ?? "",
    });
    setOpen(true);
  };

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        ...form,
        ano: form.ano ? Number(form.ano) : null,
        capacidade_tanque: Number(form.capacidade_tanque),
        media_km_l: form.media_km_l ? Number(form.media_km_l) : null,
        km_atual: Number(form.km_atual || 0),
        limite_diario_litros: form.limite_diario_litros ? Number(form.limite_diario_litros) : null,
        limite_semanal_litros: form.limite_semanal_litros ? Number(form.limite_semanal_litros) : null,
        limite_mensal_litros: form.limite_mensal_litros ? Number(form.limite_mensal_litros) : null,
      };
      if (editing) {
        await api.put(`/vehicles/${editing.id}`, payload);
        toast.success("Veículo atualizado");
      } else {
        await api.post("/vehicles", payload);
        toast.success("Veículo criado com cartão NFC gerado");
      }
      setOpen(false);
      load();
    } catch (e) {
      toast.error("Erro ao salvar", { description: formatApiError(e) });
    } finally {
      setSaving(false);
    }
  };

  const remove = async (v) => {
    if (!window.confirm(`Excluir veículo ${v.placa}?`)) return;
    try {
      await api.delete(`/vehicles/${v.id}`);
      toast.success("Veículo excluído");
      load();
    } catch (e) {
      toast.error("Erro ao excluir", { description: formatApiError(e) });
    }
  };

  return (
    <div className="space-y-6" data-testid="vehicles-page">
      <PageHeader
        title="Veículos"
        description="Cadastro da frota municipal. Cada veículo recebe um cartão NFC único."
        actions={
          canEdit && (
            <Button onClick={openNew} className="bg-slate-900 hover:bg-slate-800" data-testid="new-vehicle-btn">
              <Plus size={16} className="mr-2" /> Novo veículo
            </Button>
          )
        }
      />

      {loading ? (
        <div className="h-64 rounded-lg bg-white border border-slate-200 animate-pulse" />
      ) : items.length === 0 ? (
        <EmptyState
          title="Nenhum veículo cadastrado"
          description="Comece cadastrando o primeiro veículo. O cartão NFC será gerado automaticamente."
          action={
            canEdit && (
              <Button onClick={openNew} className="bg-slate-900 hover:bg-slate-800">
                <Plus size={16} className="mr-2" /> Cadastrar
              </Button>
            )
          }
        />
      ) : (
        <Card>
          <CardContent className="p-0 overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Placa</TableHead>
                  <TableHead>Veículo</TableHead>
                  <TableHead>Secretaria</TableHead>
                  <TableHead>Combustível</TableHead>
                  <TableHead className="text-right">Tanque</TableHead>
                  <TableHead className="text-right">Km</TableHead>
                  <TableHead>Cartão NFC</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((v) => (
                  <TableRow key={v.id} data-testid={`vehicle-row-${v.placa}`}>
                    <TableCell className="font-mono font-semibold">{v.placa}</TableCell>
                    <TableCell>
                      <div className="font-medium">{v.marca} {v.modelo}</div>
                      <div className="text-xs text-slate-500">{v.ano || "—"}</div>
                    </TableCell>
                    <TableCell>{v.secretaria}</TableCell>
                    <TableCell className="capitalize">{v.tipo_combustivel.replace("_", " ")}</TableCell>
                    <TableCell className="text-right tabular-nums">{v.capacidade_tanque} L</TableCell>
                    <TableCell className="text-right tabular-nums">{v.km_atual?.toLocaleString("pt-BR")}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1 font-mono text-xs bg-slate-100 px-2 py-1 rounded">
                        <CreditCard size={12} /> {v.nfc_card_id}
                      </span>
                    </TableCell>
                    <TableCell>
                      <Badge variant={v.status === "ativo" ? "default" : "secondary"} className="capitalize">
                        {v.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right space-x-1">
                      {canEdit && (
                        <>
                          <Button size="icon" variant="ghost" onClick={() => openEdit(v)} data-testid={`edit-${v.placa}`}>
                            <Pencil size={16} />
                          </Button>
                          <Button size="icon" variant="ghost" onClick={() => remove(v)} data-testid={`delete-${v.placa}`}>
                            <Trash size={16} className="text-red-600" />
                          </Button>
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editing ? "Editar veículo" : "Novo veículo"}</DialogTitle>
            <DialogDescription>
              {editing ? "Altere os dados do veículo." : "O cartão NFC será gerado automaticamente."}
            </DialogDescription>
          </DialogHeader>
          <div className="grid md:grid-cols-2 gap-4 py-2">
            <F label="Placa *"><Input value={form.placa} onChange={(e) => setForm({ ...form, placa: e.target.value.toUpperCase() })} data-testid="v-placa" /></F>
            <F label="Renavam"><Input value={form.renavam} onChange={(e) => setForm({ ...form, renavam: e.target.value })} /></F>
            <F label="Marca *"><Input value={form.marca} onChange={(e) => setForm({ ...form, marca: e.target.value })} data-testid="v-marca" /></F>
            <F label="Modelo *"><Input value={form.modelo} onChange={(e) => setForm({ ...form, modelo: e.target.value })} data-testid="v-modelo" /></F>
            <F label="Ano"><Input type="number" value={form.ano} onChange={(e) => setForm({ ...form, ano: e.target.value })} /></F>
            <F label="Secretaria *"><Input value={form.secretaria} onChange={(e) => setForm({ ...form, secretaria: e.target.value })} data-testid="v-secretaria" /></F>
            <F label="Departamento"><Input value={form.departamento} onChange={(e) => setForm({ ...form, departamento: e.target.value })} /></F>
            <F label="Centro de custo"><Input value={form.centro_custo} onChange={(e) => setForm({ ...form, centro_custo: e.target.value })} /></F>
            <F label="Combustível *">
              <Select value={form.tipo_combustivel} onValueChange={(v) => setForm({ ...form, tipo_combustivel: v })}>
                <SelectTrigger data-testid="v-combustivel"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {FUELS.map((f) => <SelectItem key={f.v} value={f.v}>{f.l}</SelectItem>)}
                </SelectContent>
              </Select>
            </F>
            <F label="Capacidade tanque (L) *"><Input type="number" step="0.1" value={form.capacidade_tanque} onChange={(e) => setForm({ ...form, capacidade_tanque: e.target.value })} data-testid="v-tanque" /></F>
            <F label="Média km/L"><Input type="number" step="0.1" value={form.media_km_l} onChange={(e) => setForm({ ...form, media_km_l: e.target.value })} /></F>
            <F label="Km atual"><Input type="number" value={form.km_atual} onChange={(e) => setForm({ ...form, km_atual: e.target.value })} /></F>
            <F label="Status">
              <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ativo">Ativo</SelectItem>
                  <SelectItem value="inativo">Inativo</SelectItem>
                  <SelectItem value="manutencao">Manutenção</SelectItem>
                </SelectContent>
              </Select>
            </F>
            <F label="URL Foto"><Input value={form.foto} onChange={(e) => setForm({ ...form, foto: e.target.value })} placeholder="https://..." /></F>
            <F label="Limite diário (L)"><Input type="number" value={form.limite_diario_litros} onChange={(e) => setForm({ ...form, limite_diario_litros: e.target.value })} /></F>
            <F label="Limite semanal (L)"><Input type="number" value={form.limite_semanal_litros} onChange={(e) => setForm({ ...form, limite_semanal_litros: e.target.value })} /></F>
            <F label="Limite mensal (L)"><Input type="number" value={form.limite_mensal_litros} onChange={(e) => setForm({ ...form, limite_mensal_litros: e.target.value })} /></F>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={save} disabled={saving} className="bg-slate-900" data-testid="save-vehicle-btn">
              {saving ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const F = ({ label, children }) => (
  <div className="space-y-1">
    <Label className="text-xs">{label}</Label>
    {children}
  </div>
);
