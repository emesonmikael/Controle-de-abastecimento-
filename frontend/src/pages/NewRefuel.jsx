import React, { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { CreditCard, Lightning, CheckCircle, WarningCircle, ArrowRight, ArrowClockwise } from "@phosphor-icons/react";

/** Steps: 1 read vehicle NFC, 2 details form, 3 result */
export default function NewRefuel() {
  const [step, setStep] = useState(1);
  const [cardId, setCardId] = useState("");
  const [scanning, setScanning] = useState(false);
  const [vehicle, setVehicle] = useState(null);
  const [precoSugerido, setPrecoSugerido] = useState(null);

  const [driverCard, setDriverCard] = useState("");
  const [driver, setDriver] = useState(null);

  const [km, setKm] = useState("");
  const [litros, setLitros] = useState("");
  const [preco, setPreco] = useState("");
  const [postoId, setPostoId] = useState("");
  const [postos, setPostos] = useState([]);
  const [gps, setGps] = useState(null);
  const [obs, setObs] = useState("");

  const [validation, setValidation] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    api.get("/stations").then((r) => setPostos(r.data)).catch(() => {});
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (p) => setGps({ latitude: p.coords.latitude, longitude: p.coords.longitude }),
        () => {},
        { enableHighAccuracy: true, timeout: 5000 }
      );
    }
  }, []);

  const readCard = async (numero) => {
    setScanning(true);
    try {
      const { data } = await api.post("/refuels/start", { nfc_card_id: numero });
      setVehicle(data.vehicle);
      setPrecoSugerido(data.preco_sugerido);
      if (data.preco_sugerido) setPreco(String(data.preco_sugerido));
      setStep(2);
      toast.success("Cartão lido", { description: `Veículo: ${data.vehicle.placa}` });
    } catch (e) {
      toast.error("Falha na leitura NFC", { description: formatApiError(e) });
    } finally {
      setScanning(false);
    }
  };

  const scanWebNFC = async () => {
    if (!("NDEFReader" in window)) {
      toast.info("Web NFC indisponível", {
        description: "Use um Android/Chrome ou digite o número do cartão manualmente.",
      });
      return;
    }
    try {
      setScanning(true);
      const reader = new window.NDEFReader();
      await reader.scan();
      reader.onreading = ({ message }) => {
        try {
          for (const rec of message.records) {
            const txt = new TextDecoder().decode(rec.data);
            if (txt) {
              setCardId(txt.trim());
              readCard(txt.trim());
              return;
            }
          }
        } catch (e) {
          toast.error("Erro decodificando NFC");
        }
      };
    } catch (e) {
      setScanning(false);
      toast.error("Permissão NFC negada");
    }
  };

  const readDriverCard = async (numero) => {
    try {
      const { data } = await api.get(`/nfc/lookup/${numero}`);
      if (data.driver) {
        setDriver(data.driver);
        toast.success("Motorista identificado", { description: data.driver.nome });
      } else {
        toast.error("Cartão não pertence a um motorista");
      }
    } catch (e) {
      toast.error("Cartão de motorista inválido", { description: formatApiError(e) });
    }
  };

  const validate = async () => {
    setValidation(null);
    try {
      const payload = {
        vehicle_id: vehicle.id,
        driver_id: driver?.id || null,
        km_atual: Number(km),
        litros: Number(litros),
        preco_litro: Number(preco),
        tipo_combustivel: vehicle.tipo_combustivel,
        posto_id: postoId || null,
      };
      const { data } = await api.post("/refuels/validate", payload);
      setValidation(data);
      if (data.ok) toast.success("Validação passou — pronto para autorizar");
      else toast.error("Validação falhou", { description: data.errors?.join(" · ") });
    } catch (e) {
      toast.error("Erro na validação", { description: formatApiError(e) });
    }
  };

  const authorize = async () => {
    setSubmitting(true);
    try {
      const payload = {
        vehicle_id: vehicle.id,
        driver_id: driver?.id || null,
        km_atual: Number(km),
        litros: Number(litros),
        preco_litro: Number(preco),
        tipo_combustivel: vehicle.tipo_combustivel,
        posto_id: postoId || null,
        latitude: gps?.latitude,
        longitude: gps?.longitude,
        observacoes: obs || null,
      };
      const { data } = await api.post("/refuels", payload);
      setResult(data);
      setStep(3);
      toast.success("Abastecimento autorizado e registrado");
    } catch (e) {
      toast.error("Falha ao autorizar", { description: formatApiError(e) });
    } finally {
      setSubmitting(false);
    }
  };

  const reset = () => {
    setStep(1);
    setCardId("");
    setVehicle(null);
    setDriver(null);
    setDriverCard("");
    setKm("");
    setLitros("");
    setPreco("");
    setPostoId("");
    setObs("");
    setValidation(null);
    setResult(null);
  };

  return (
    <div className="space-y-6" data-testid="new-refuel-page">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Novo abastecimento</h1>
        <p className="text-sm text-slate-500 mt-1">Fluxo NFC — leia o cartão do veículo para iniciar.</p>
      </div>

      <Stepper current={step} />

      {step === 1 && (
        <div className="grid lg:grid-cols-5 gap-6">
          <Card className="lg:col-span-3">
            <CardHeader>
              <CardTitle className="text-base">Leitura NFC do veículo</CardTitle>
              <CardDescription>Aproxime o cartão NFC ou informe o número do cartão.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col items-center justify-center py-8 relative">
                <div className="relative">
                  {scanning && (
                    <>
                      <span className="absolute inset-0 rounded-full border-2 border-blue-500 nfc-ring" />
                      <span className="absolute inset-0 rounded-full border-2 border-blue-500 nfc-ring" style={{ animationDelay: "0.6s" }} />
                    </>
                  )}
                  <div
                    className={`h-32 w-32 rounded-full grid place-items-center ${
                      scanning ? "bg-blue-600 nfc-pulse" : "bg-slate-900"
                    } text-white shadow-lg`}
                    data-testid="nfc-target"
                  >
                    <CreditCard size={54} weight="fill" />
                  </div>
                </div>
                <div className="mt-6 text-sm text-slate-600">
                  {scanning ? "Aguardando cartão..." : "Pronto para leitura"}
                </div>
                <Button
                  onClick={scanWebNFC}
                  className="mt-4 bg-blue-600 hover:bg-blue-700"
                  disabled={scanning}
                  data-testid="scan-nfc-btn"
                >
                  <Lightning size={16} className="mr-2" weight="fill" /> Iniciar leitura NFC
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">Entrada manual</CardTitle>
              <CardDescription>Digite o número do cartão impresso.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <Label htmlFor="card">Número do cartão</Label>
                <Input
                  id="card"
                  value={cardId}
                  onChange={(e) => setCardId(e.target.value.toUpperCase())}
                  placeholder="Ex.: A1B2C3D4E5F6"
                  className="mt-1 font-mono"
                  data-testid="card-number-input"
                />
              </div>
              <Button
                onClick={() => cardId && readCard(cardId)}
                disabled={!cardId || scanning}
                className="w-full bg-slate-900 hover:bg-slate-800"
                data-testid="submit-card-btn"
              >
                Ler cartão <ArrowRight size={16} className="ml-2" />
              </Button>
              <div className="text-xs text-slate-500 pt-2">
                Dica: Cadastre um veículo primeiro para obter um número de cartão válido.
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {step === 2 && vehicle && (
        <div className="grid lg:grid-cols-3 gap-6">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-base">Dados do abastecimento</CardTitle>
              <CardDescription>Informe quilometragem, litros e preço.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <Field label="Quilometragem atual" required>
                  <Input
                    type="number"
                    value={km}
                    onChange={(e) => setKm(e.target.value)}
                    placeholder={`Anterior: ${vehicle.km_atual}`}
                    data-testid="km-input"
                  />
                </Field>
                <Field label="Litros" required>
                  <Input
                    type="number"
                    step="0.01"
                    value={litros}
                    onChange={(e) => setLitros(e.target.value)}
                    placeholder="0,00"
                    data-testid="liters-input"
                  />
                </Field>
                <Field label="Preço por litro" required>
                  <Input
                    type="number"
                    step="0.001"
                    value={preco}
                    onChange={(e) => setPreco(e.target.value)}
                    data-testid="price-input"
                  />
                </Field>
                <Field label="Posto">
                  <Select value={postoId} onValueChange={setPostoId}>
                    <SelectTrigger data-testid="station-select">
                      <SelectValue placeholder="Selecione (opcional)" />
                    </SelectTrigger>
                    <SelectContent>
                      {postos.map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.nome}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
              </div>

              <div className="border-t border-slate-200 pt-4">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="text-sm font-semibold">Motorista (opcional)</div>
                    <div className="text-xs text-slate-500">Leia o cartão NFC ou digite o número.</div>
                  </div>
                  {driver && (
                    <Badge className="bg-green-100 text-green-800 hover:bg-green-100">{driver.nome}</Badge>
                  )}
                </div>
                <div className="flex gap-2">
                  <Input
                    value={driverCard}
                    onChange={(e) => setDriverCard(e.target.value.toUpperCase())}
                    placeholder="Cartão do motorista"
                    className="font-mono"
                    data-testid="driver-card-input"
                  />
                  <Button
                    variant="outline"
                    onClick={() => driverCard && readDriverCard(driverCard)}
                    disabled={!driverCard}
                    data-testid="driver-card-btn"
                  >
                    Vincular
                  </Button>
                </div>
              </div>

              <Field label="Observações">
                <Input value={obs} onChange={(e) => setObs(e.target.value)} placeholder="Opcional" data-testid="obs-input" />
              </Field>

              <div className="flex flex-wrap gap-2 pt-2">
                <Button variant="outline" onClick={reset} data-testid="cancel-btn">
                  Cancelar
                </Button>
                <Button variant="outline" onClick={validate} disabled={!km || !litros || !preco} data-testid="validate-btn">
                  Validar
                </Button>
                <Button
                  onClick={authorize}
                  disabled={!validation?.ok || submitting}
                  className="bg-green-600 hover:bg-green-700 text-white"
                  data-testid="authorize-btn"
                >
                  {submitting ? "Autorizando..." : "Autorizar abastecimento"}
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Veículo identificado</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2" data-testid="vehicle-summary">
                <Row k="Placa" v={<span className="font-mono font-semibold">{vehicle.placa}</span>} />
                <Row k="Modelo" v={`${vehicle.marca} ${vehicle.modelo}`} />
                <Row k="Secretaria" v={vehicle.secretaria} />
                <Row k="Combustível" v={vehicle.tipo_combustivel.replace("_", " ")} />
                <Row k="Tanque" v={`${vehicle.capacidade_tanque} L`} />
                <Row k="Km atual" v={vehicle.km_atual?.toLocaleString("pt-BR")} />
                <Row k="Status" v={<Badge variant={vehicle.status === "ativo" ? "default" : "destructive"}>{vehicle.status}</Badge>} />
              </CardContent>
            </Card>

            {validation && (
              <Card className={validation.ok ? "border-green-200" : "border-red-200"}>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    {validation.ok ? (
                      <>
                        <CheckCircle size={20} weight="fill" className="text-green-600" />
                        <span className="text-green-700">Validação OK</span>
                      </>
                    ) : (
                      <>
                        <WarningCircle size={20} weight="fill" className="text-red-600" />
                        <span className="text-red-700">Bloqueado</span>
                      </>
                    )}
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm space-y-2" data-testid="validation-panel">
                  {validation.errors?.map((e, i) => (
                    <div key={i} className="flex gap-2 text-red-700 bg-red-50 px-3 py-2 rounded">
                      <WarningCircle size={16} className="mt-0.5 shrink-0" />
                      <span>{e}</span>
                    </div>
                  ))}
                  {validation.warnings?.map((w, i) => (
                    <div key={i} className="flex gap-2 text-yellow-800 bg-yellow-50 px-3 py-2 rounded">
                      <WarningCircle size={16} className="mt-0.5 shrink-0" />
                      <span>{w}</span>
                    </div>
                  ))}
                  {validation.ok && (
                    <div className="text-green-700 bg-green-50 px-3 py-2 rounded">Tudo em ordem para autorizar.</div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}

      {step === 3 && result && (
        <Card data-testid="refuel-success">
          <CardContent className="p-8 text-center">
            <div className="h-16 w-16 rounded-full bg-green-100 text-green-600 grid place-items-center mx-auto">
              <CheckCircle size={40} weight="fill" />
            </div>
            <h2 className="text-2xl font-bold mt-4">Abastecimento autorizado</h2>
            <p className="text-slate-500 mt-1">Registro criado com sucesso.</p>

            <div className="mt-6 grid md:grid-cols-3 gap-4 text-left">
              <SummaryTile label="Veículo" value={<span className="font-mono">{result.vehicle_placa}</span>} />
              <SummaryTile label="Litros" value={`${result.litros.toFixed(2)} L`} />
              <SummaryTile
                label="Valor total"
                value={result.valor_total.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
              />
              <SummaryTile label="Km atual" value={result.km_atual.toLocaleString("pt-BR")} />
              <SummaryTile label="Km rodados" value={result.km_rodados.toFixed(0)} />
              <SummaryTile label="Autonomia" value={result.autonomia ? `${result.autonomia.toFixed(2)} km/L` : "—"} />
            </div>

            <div className="mt-8 flex justify-center gap-3">
              <Button variant="outline" onClick={reset} data-testid="new-refuel-btn">
                <ArrowClockwise size={16} className="mr-2" /> Novo abastecimento
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

const Stepper = ({ current }) => {
  const steps = ["Leitura NFC", "Dados & validação", "Confirmação"];
  return (
    <div className="flex items-center gap-2 text-sm">
      {steps.map((s, i) => (
        <React.Fragment key={s}>
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md ${
              current === i + 1
                ? "bg-slate-900 text-white"
                : current > i + 1
                ? "bg-green-100 text-green-800"
                : "bg-slate-100 text-slate-500"
            }`}
            data-testid={`step-${i + 1}`}
          >
            <span className="h-5 w-5 rounded-full grid place-items-center text-xs bg-white/20">
              {current > i + 1 ? "✓" : i + 1}
            </span>
            {s}
          </div>
          {i < steps.length - 1 && <div className="h-px flex-1 bg-slate-200" />}
        </React.Fragment>
      ))}
    </div>
  );
};

const Field = ({ label, required, children }) => (
  <div className="space-y-1">
    <Label className="text-xs">
      {label} {required && <span className="text-red-500">*</span>}
    </Label>
    {children}
  </div>
);

const Row = ({ k, v }) => (
  <div className="flex items-center justify-between border-b border-slate-100 last:border-0 py-1.5">
    <span className="text-slate-500">{k}</span>
    <span className="text-slate-900">{v}</span>
  </div>
);

const SummaryTile = ({ label, value }) => (
  <div className="border border-slate-200 rounded-md p-4">
    <div className="text-xs uppercase text-slate-500">{label}</div>
    <div className="mt-1 text-lg font-bold tabular-nums">{value}</div>
  </div>
);
