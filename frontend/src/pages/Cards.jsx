import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { PageHeader, EmptyState } from "@/components/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CreditCard, Truck, IdentificationCard } from "@phosphor-icons/react";

export default function Cards() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    api.get("/nfc/cards").then((r) => setItems(r.data)).catch(() => {});
  }, []);

  return (
    <div className="space-y-6" data-testid="cards-page">
      <PageHeader title="Cartões NFC" description="Todos os cartões NFC gerados. O token AES fica cifrado no cartão." />
      {items.length === 0 ? (
        <EmptyState title="Nenhum cartão" description="Cadastre veículos e motoristas para gerar cartões." />
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((c) => (
            <Card key={c.id} className="rise">
              <CardContent className="p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className={`h-9 w-9 rounded-md grid place-items-center ${c.tipo === "veiculo" ? "bg-blue-100 text-blue-700" : "bg-purple-100 text-purple-700"}`}>
                    {c.tipo === "veiculo" ? <Truck size={18} weight="bold" /> : <IdentificationCard size={18} weight="bold" />}
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wider text-slate-500">{c.tipo}</div>
                    <div className="font-mono font-semibold text-slate-900">{c.numero_cartao}</div>
                  </div>
                  <Badge variant={c.ativo ? "default" : "secondary"} className="ml-auto">{c.ativo ? "Ativo" : "Inativo"}</Badge>
                </div>
                <div className="text-xs text-slate-500 font-mono truncate break-all">
                  <CreditCard size={12} className="inline mr-1" />
                  {c.token_encrypted.slice(0, 48)}...
                </div>
                <div className="text-xs text-slate-400 mt-2">Criado: {new Date(c.created_at).toLocaleString("pt-BR")}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
