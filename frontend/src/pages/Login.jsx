import React, { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Lightning, ShieldCheck, GasPump } from "@phosphor-icons/react";
import { toast } from "sonner";

const DEMO = [
  { role: "Admin", email: "admin@frotanfc.gov.br", pw: "admin123" },
  { role: "Gestor", email: "gestor@frotanfc.gov.br", pw: "senha123" },
  { role: "Frentista", email: "frentista@frotanfc.gov.br", pw: "senha123" },
  { role: "Auditor", email: "auditor@frotanfc.gov.br", pw: "senha123" },
];

export default function LoginPage() {
  const { login, user, loading } = useAuth();
  const [email, setEmail] = useState("admin@frotanfc.gov.br");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  if (loading) return null;
  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    const res = await login(email, password);
    setBusy(false);
    if (!res.ok) {
      setError(res.error);
      toast.error("Falha no login", { description: res.error });
      return;
    }
    toast.success("Autenticado com sucesso");
    navigate("/");
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-slate-50" data-testid="login-page">
      {/* Left: brand panel */}
      <div className="hidden lg:flex flex-col justify-between bg-slate-900 text-white p-12 relative overflow-hidden">
        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 rounded-xl bg-blue-600 grid place-items-center">
              <Lightning weight="fill" size={24} />
            </div>
            <div>
              <div className="text-lg font-bold">Frota NFC</div>
              <div className="text-xs text-slate-400">Controle Municipal de Abastecimento</div>
            </div>
          </div>
        </div>

        <div className="relative z-10 space-y-8">
          <h1 className="text-4xl lg:text-5xl font-bold leading-tight">
            Abastecimento auditável
            <br />
            com <span className="text-blue-400">NFC</span>.
          </h1>
          <p className="text-slate-300 max-w-md text-base">
            Controle total da frota municipal — cadastro de veículos, cartões NFC criptografados,
            validações em tempo real e regras automáticas anti-fraude.
          </p>
          <div className="grid grid-cols-2 gap-3 max-w-md">
            <div className="border border-slate-700 rounded-lg p-4">
              <ShieldCheck size={22} className="text-blue-400 mb-2" />
              <div className="text-sm font-semibold">AES + JWT</div>
              <div className="text-xs text-slate-400">Criptografia ponta a ponta</div>
            </div>
            <div className="border border-slate-700 rounded-lg p-4">
              <GasPump size={22} className="text-blue-400 mb-2" />
              <div className="text-sm font-semibold">5 combustíveis</div>
              <div className="text-xs text-slate-400">Gasolina · Etanol · Diesel · Arla</div>
            </div>
          </div>
        </div>

        <div className="relative z-10 text-xs text-slate-500">
          © {new Date().getFullYear()} Frota NFC — Solução para prefeituras e frotas privadas
        </div>

        {/* subtle grid */}
        <div
          className="absolute inset-0 opacity-[0.05]"
          style={{
            backgroundImage:
              "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)",
            backgroundSize: "42px 42px",
          }}
        />
      </div>

      {/* Right: form */}
      <div className="flex items-center justify-center p-6 lg:p-12">
        <Card className="w-full max-w-md border-slate-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-2xl">Acessar plataforma</CardTitle>
            <CardDescription>Entre com suas credenciais municipais.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={submit} className="space-y-4" data-testid="login-form">
              <div className="space-y-2">
                <Label htmlFor="email">E-mail</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  data-testid="login-email"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Senha</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  data-testid="login-password"
                  required
                />
              </div>
              {error && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-md px-3 py-2" data-testid="login-error">
                  {error}
                </div>
              )}
              <Button
                type="submit"
                className="w-full bg-slate-900 hover:bg-slate-800 text-white"
                disabled={busy}
                data-testid="login-submit"
              >
                {busy ? "Autenticando..." : "Entrar"}
              </Button>
            </form>

            <div className="mt-6 pt-6 border-t border-slate-200">
              <div className="text-xs font-semibold text-slate-500 mb-2">Contas de demonstração</div>
              <div className="grid grid-cols-2 gap-2">
                {DEMO.map((d) => (
                  <button
                    key={d.email}
                    onClick={() => {
                      setEmail(d.email);
                      setPassword(d.pw);
                    }}
                    className="text-left border border-slate-200 rounded-md px-3 py-2 hover:border-slate-900 transition-colors text-xs"
                    data-testid={`demo-${d.role.toLowerCase()}`}
                  >
                    <div className="font-semibold text-slate-900">{d.role}</div>
                    <div className="text-slate-500 truncate">{d.email}</div>
                  </button>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
