"""Heuristic fraud detection rules for refuel operations."""
from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


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
