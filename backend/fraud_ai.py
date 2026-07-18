"""AI-based fraud detection using Emergent LLM Key + Gemini.

Combines heuristic rules with an LLM analysis for suspicious refuels.
"""
from __future__ import annotations
import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


async def analyze_refuel_with_ai(refuel: dict, history: list[dict], vehicle: dict) -> Optional[dict]:
    """Call Gemini via emergentintegrations. Returns dict with risk_score/reasons or None on failure."""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except Exception as e:  # noqa: BLE001
        logger.warning("emergentintegrations not available: %s", e)
        return None

    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        logger.warning("EMERGENT_LLM_KEY not set")
        return None

    system = (
        "Você é um analista de fraudes em abastecimento de frota municipal. "
        "Analise o abastecimento atual comparando com o histórico e o veículo. "
        "Detecte padrões suspeitos: consumo fora do padrão, abastecimentos frequentes, "
        "quilometragem incompatível, horários incomuns, aumento repentino de consumo. "
        "Responda APENAS com JSON no formato: "
        '{"risk_score": 0-100, "suspicious": true/false, "reasons": ["motivo1","motivo2"], "summary": "resumo curto em pt-BR"}'
    )

    hist_summary = [
        {
            "data": h.get("created_at"),
            "litros": h.get("litros"),
            "km": h.get("km_atual"),
            "km_rodados": h.get("km_rodados"),
            "autonomia": h.get("autonomia"),
            "valor_total": h.get("valor_total"),
        }
        for h in history[:10]
    ]

    prompt = json.dumps(
        {
            "veiculo": {
                "placa": vehicle.get("placa"),
                "modelo": vehicle.get("modelo"),
                "tipo_combustivel": vehicle.get("tipo_combustivel"),
                "capacidade_tanque": vehicle.get("capacidade_tanque"),
                "media_km_l_esperada": vehicle.get("media_km_l"),
                "km_atual": vehicle.get("km_atual"),
            },
            "abastecimento_atual": {
                "data": refuel.get("created_at"),
                "litros": refuel.get("litros"),
                "km": refuel.get("km_atual"),
                "km_rodados": refuel.get("km_rodados"),
                "autonomia": refuel.get("autonomia"),
                "valor_total": refuel.get("valor_total"),
                "hora": refuel.get("hora"),
            },
            "historico_recente": hist_summary,
        },
        ensure_ascii=False,
    )

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"fraud-{refuel.get('id','x')}",
            system_message=system,
        ).with_model("gemini", "gemini-3-flash-preview")
        resp = await chat.send_message(UserMessage(text=prompt))
        text = (resp or "").strip()
        # Extract JSON block
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
        # Find braces
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]
        return json.loads(text)
    except Exception as e:  # noqa: BLE001
        logger.exception("AI fraud analysis failed: %s", e)
        return None


def heuristic_fraud_checks(refuel: dict, history: list[dict], vehicle: dict) -> list[dict]:
    """Return a list of alert dicts based on simple rules."""
    alerts: list[dict] = []
    now = datetime.now(timezone.utc)

    # 1. Consumption above expected
    autonomia = refuel.get("autonomia")
    expected = vehicle.get("media_km_l")
    if autonomia and expected and expected > 0:
        if autonomia < expected * 0.6:
            alerts.append(
                {
                    "tipo": "consumo_acima_media",
                    "severidade": "warning",
                    "mensagem": (
                        f"Consumo elevado: {autonomia:.2f} km/L vs esperado {expected:.2f} km/L "
                        f"para {vehicle.get('placa')}"
                    ),
                }
            )

    # 2. Refuel at unusual time (00:00-05:00)
    hour = refuel.get("hora")
    if isinstance(hour, int) and 0 <= hour < 5:
        alerts.append(
            {
                "tipo": "horario_incomum",
                "severidade": "warning",
                "mensagem": f"Abastecimento em horário incomum ({hour:02d}h) para {vehicle.get('placa')}",
            }
        )

    # 3. Frequent refuels (>=3 in last 24h)
    recent = [
        h
        for h in history
        if _parse_dt(h.get("created_at")) and (now - _parse_dt(h.get("created_at"))) < timedelta(hours=24)
    ]
    if len(recent) >= 3:
        alerts.append(
            {
                "tipo": "abastecimentos_frequentes",
                "severidade": "critical",
                "mensagem": f"{len(recent)} abastecimentos nas últimas 24h para {vehicle.get('placa')}",
            }
        )

    # 4. Sudden increase in liters (>50% above avg of last 5)
    last5 = [h.get("litros", 0) for h in history[:5] if h.get("litros")]
    if last5 and refuel.get("litros"):
        avg = sum(last5) / len(last5)
        if avg > 0 and refuel["litros"] > avg * 1.5:
            alerts.append(
                {
                    "tipo": "aumento_repentino_consumo",
                    "severidade": "warning",
                    "mensagem": (
                        f"Volume {refuel['litros']:.1f}L bem acima da média recente "
                        f"({avg:.1f}L) para {vehicle.get('placa')}"
                    ),
                }
            )

    return alerts


def _parse_dt(v):
    if not v:
        return None
    try:
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v
    except Exception:  # noqa: BLE001
        return None
