# Frota NFC — PRD

**Data:** 18/07/2026
**Status:** MVP 1 concluído

## Problema
Sistema web profissional para controle total do abastecimento da frota municipal com tecnologia NFC. Substitui planilhas e controles manuais por processo auditável, com validações automáticas e detecção de fraudes por IA.

## Personas
- **Administrador** — controle total (usuários, configurações, exclusões).
- **Gestor** — cadastros, aprovações, resolução de alertas, relatórios.
- **Frentista** — realiza abastecimentos via cartão NFC.
- **Motorista** — se autentica opcionalmente no abastecimento via NFC.
- **Auditor** — consulta auditoria e logs (read-only).

## Arquitetura
- **Frontend**: React 19 + Tailwind + shadcn/ui + Recharts + Phosphor Icons + Sonner + PWA (manifest + SW).
- **Backend**: FastAPI + Motor (async Mongo) + PyJWT + bcrypt + cryptography (AES-GCM 256).
- **Banco**: MongoDB (`frota_nfc`).
- **IA anti-fraude**: heurísticas + Gemini 3 Flash via `emergentintegrations` (EMERGENT_LLM_KEY).
- **NFC**: Web NFC API (Chrome Android) + entrada manual do número do cartão.

## Requisitos essenciais (estáticos)
- Autenticação JWT com 5 papéis (RBAC).
- Cadastros: veículos, motoristas, postos, combustíveis, usuários.
- Cada veículo/motorista tem cartão NFC único (número + token AES cifrado).
- Fluxo NFC de abastecimento com validações (veículo ativo, combustível compatível, km coerente, limites diário/semanal/mensal, duplicado 10 min, CNH válida).
- Dashboard executivo (KPIs, séries, ranking, secretaria).
- Alertas automáticos + IA anti-fraude.
- Auditoria de todas as ações.

## MVP 1 — Implementado (18/07/2026)
- ✅ Login + 5 papéis (admin/gestor/frentista/motorista/auditor) — 4 usuários seed.
- ✅ CRUD veículos, motoristas, postos, combustíveis, usuários.
- ✅ Cartões NFC gerados automaticamente (AES-GCM 256 no token).
- ✅ Fluxo NFC de novo abastecimento: leitura (Web NFC + manual), validação, autorização.
- ✅ Cálculo automático de valor total, km rodados e autonomia.
- ✅ Regras de fraude: consumo acima da média, horário incomum, abastecimentos frequentes, aumento súbito.
- ✅ IA (Gemini 3 Flash) para análise de padrão suspeito com score de risco.
- ✅ Dashboard com KPIs, gráfico de área, pie por secretaria, ranking top veículos.
- ✅ Central de alertas com resolução.
- ✅ Auditoria com busca por usuário/ação/recurso.
- ✅ PWA base (manifest.json + service worker de shell).
- ✅ Testes backend: **37/37 passando (100%)**.

## Backlog priorizado
### P0
- Relatórios PDF/Excel/CSV com filtros (data, secretaria, veículo, motorista, posto, combustível).
- Mapa GPS de abastecimentos (Leaflet ou Google Maps).

### P1
- Upload real de fotos (hodômetro/bomba) via object storage.
- Configuração de limites e horários por secretaria/veículo.
- Rate-limit e bloqueio por brute-force em `/auth/login` (5 tentativas).
- Split de `server.py` em routers/ subpacote.
- Aggregation `$sum` para totais de limites (performance).
- CORS restrito por env em produção.

### P2
- Módulo motorista (self-service).
- Backup manual do banco pelo painel admin.
- Sincronização offline PWA completa (fila de refuels).
- Autorização em tempo real sem intervenção (integração bomba).

## Endpoints principais
Ver `/app/memory/test_credentials.md`.
