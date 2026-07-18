"""BUG FIX 2 — verify AI fraud detection was removed.

- Creating a refuel must NEVER produce an alert with ia_gerado=true.
- GET /api/alerts must never return alerts with tipo='ia_deteccao_fraude'
  nor with ia_gerado=true.
- Heuristic rules still work:
    * 'aumento_repentino_consumo' when liters > 150% of avg of last 3
    * 'abastecimentos_frequentes' when 3+ refuels in the last 24h
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

load_dotenv(Path("/app/frontend/.env"))
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
TIMEOUT = 30

CREDS = {
    "admin": ("admin@frotanfc.gov.br", "admin123"),
    "frentista": ("frentista@frotanfc.gov.br", "senha123"),
}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_login(*CREDS['admin'])}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def frentista_headers():
    return {"Authorization": f"Bearer {_login(*CREDS['frentista'])}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def vehicle(admin_headers):
    placa = f"AI{uuid.uuid4().hex[:5].upper()}"
    r = requests.post(
        f"{API}/vehicles",
        json={
            "placa": placa,
            "marca": "Test",
            "modelo": "AI-Removed",
            "secretaria": "TEST_AI",
            "tipo_combustivel": "gasolina",
            "capacidade_tanque": 60.0,
            "km_atual": 20000.0,
            "media_km_l": 10.0,
        },
        headers=admin_headers,
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    v = r.json()
    yield v
    requests.delete(f"{API}/vehicles/{v['id']}", headers=admin_headers, timeout=TIMEOUT)


class TestNoIAAlerts:
    def test_existing_ia_alerts_are_only_historical(self, admin_headers):
        """Legacy IA alerts may exist from before the fix. Check they are all older
        than the fix-timestamp cutoff (i.e., no ia_gerado=true has been created
        recently). If any is recent, that means AI is still firing.
        """
        r = requests.get(f"{API}/alerts", headers=admin_headers, params={"limit": 1000}, timeout=TIMEOUT)
        assert r.status_code == 200
        alerts = r.json()
        ia_alerts = [a for a in alerts if a.get("ia_gerado") is True or a.get("tipo") == "ia_deteccao_fraude"]
        # Report count for visibility
        print(f"Legacy IA alerts count in DB: {len(ia_alerts)}")
        # All IA alerts must be older than 5 minutes ago (i.e. not just-created)
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent = []
        for a in ia_alerts:
            try:
                ts = datetime.fromisoformat(a["created_at"].replace("Z", "+00:00"))
                if ts > cutoff:
                    recent.append(a)
            except Exception:
                pass
        assert not recent, (
            f"Found {len(recent)} RECENT IA alerts (ia_gerado=true or tipo='ia_deteccao_fraude') "
            f"created in the last 5 minutes — AI removal not effective. First: {recent[0]}"
        )

    def test_refuel_create_does_not_generate_ia_alerts(self, admin_headers, frentista_headers, vehicle):
        """After creating a refuel, no new alert with ia_gerado=true / tipo='ia_deteccao_fraude'.

        We isolate by using this refuel's vehicle_id AND refuel_id AND created_at > now.
        """
        v_id = vehicle["id"]
        km = vehicle["km_atual"]
        t_before = datetime.now(timezone.utc)

        # Create a refuel
        r = requests.post(
            f"{API}/refuels",
            json={
                "vehicle_id": v_id,
                "km_atual": km + 50,
                "litros": 12.3,
                "tipo_combustivel": "gasolina",
                "preco_litro": 5.89,
            },
            headers=frentista_headers,
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        refuel_id = r.json()["id"]

        # Allow backend a moment
        time.sleep(1.0)
        r2 = requests.get(f"{API}/alerts", headers=admin_headers, params={"limit": 1000}, timeout=TIMEOUT)
        assert r2.status_code == 200
        alerts_after = r2.json()

        # (a) No alert directly referencing this refuel should be ia_gerado=true
        for a in alerts_after:
            if a.get("refuel_id") == refuel_id:
                assert a.get("ia_gerado") is not True, f"Refuel produced ia_gerado=True alert: {a}"
                assert a.get("tipo") != "ia_deteccao_fraude", f"Refuel produced ia_deteccao_fraude alert: {a}"

        # (b) No IA alerts created after t_before for this vehicle
        new_ia = []
        for a in alerts_after:
            if a.get("vehicle_id") != v_id:
                continue
            if not (a.get("ia_gerado") is True or a.get("tipo") == "ia_deteccao_fraude"):
                continue
            try:
                ts = datetime.fromisoformat(a["created_at"].replace("Z", "+00:00"))
            except Exception:
                continue
            if ts >= t_before:
                new_ia.append(a)
        assert not new_ia, f"New IA-tagged alerts appeared after refuel: {new_ia}"


class TestHeuristicRulesStillWork:
    def test_aumento_repentino_consumo_triggers(self, admin_headers, frentista_headers):
        """Seed history with small liters, then a >150% bigger refuel — should trigger heuristic alert."""
        # Dedicated vehicle
        placa = f"HR{uuid.uuid4().hex[:5].upper()}"
        r = requests.post(
            f"{API}/vehicles",
            json={
                "placa": placa,
                "marca": "T",
                "modelo": "Heur",
                "secretaria": "TEST_HR",
                "tipo_combustivel": "gasolina",
                "capacidade_tanque": 60.0,
                "km_atual": 10000.0,
                "media_km_l": 10.0,
            },
            headers=admin_headers,
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        v = r.json()
        try:
            km = v["km_atual"]
            # small refuels (avg ~5L) — must use unique liters to avoid dup-detection
            for lit in [4.5, 5.0, 5.2, 4.8]:
                km += 50
                rr = requests.post(
                    f"{API}/refuels",
                    json={
                        "vehicle_id": v["id"],
                        "km_atual": km,
                        "litros": lit,
                        "tipo_combustivel": "gasolina",
                        "preco_litro": 5.89,
                    },
                    headers=frentista_headers,
                    timeout=TIMEOUT,
                )
                assert rr.status_code == 200, rr.text
                time.sleep(0.15)

            # Big refuel — 15L (>>150% avg)
            km += 80
            rb = requests.post(
                f"{API}/refuels",
                json={
                    "vehicle_id": v["id"],
                    "km_atual": km,
                    "litros": 15.0,
                    "tipo_combustivel": "gasolina",
                    "preco_litro": 5.89,
                },
                headers=frentista_headers,
                timeout=TIMEOUT,
            )
            assert rb.status_code == 200, rb.text
            big_id = rb.json()["id"]

            time.sleep(0.5)
            ra = requests.get(f"{API}/alerts", headers=admin_headers, params={"limit": 1000}, timeout=TIMEOUT)
            assert ra.status_code == 200
            alerts = ra.json()
            matched = [a for a in alerts if a.get("refuel_id") == big_id and a.get("tipo") == "aumento_repentino_consumo"]
            assert matched, "Expected 'aumento_repentino_consumo' heuristic alert"
            # heuristic alerts must NOT be ia_gerado
            for a in matched:
                assert a.get("ia_gerado") is not True
        finally:
            requests.delete(f"{API}/vehicles/{v['id']}", headers=admin_headers, timeout=TIMEOUT)

    def test_abastecimentos_frequentes_triggers(self, admin_headers, frentista_headers):
        """3+ refuels in 24h on same vehicle → heuristic 'abastecimentos_frequentes'."""
        placa = f"FQ{uuid.uuid4().hex[:5].upper()}"
        r = requests.post(
            f"{API}/vehicles",
            json={
                "placa": placa,
                "marca": "T",
                "modelo": "Freq",
                "secretaria": "TEST_FQ",
                "tipo_combustivel": "gasolina",
                "capacidade_tanque": 60.0,
                "km_atual": 5000.0,
                "media_km_l": 10.0,
            },
            headers=admin_headers,
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        v = r.json()
        try:
            km = v["km_atual"]
            last_id = None
            # 4 refuels back-to-back (in the last 24h window)
            for lit in [3.1, 3.2, 3.3, 3.4]:
                km += 40
                rr = requests.post(
                    f"{API}/refuels",
                    json={
                        "vehicle_id": v["id"],
                        "km_atual": km,
                        "litros": lit,
                        "tipo_combustivel": "gasolina",
                        "preco_litro": 5.89,
                    },
                    headers=frentista_headers,
                    timeout=TIMEOUT,
                )
                assert rr.status_code == 200, rr.text
                last_id = rr.json()["id"]
                time.sleep(0.15)

            time.sleep(0.5)
            ra = requests.get(f"{API}/alerts", headers=admin_headers, params={"limit": 1000}, timeout=TIMEOUT)
            assert ra.status_code == 200
            alerts = ra.json()
            freq = [a for a in alerts if a.get("vehicle_id") == v["id"] and a.get("tipo") == "abastecimentos_frequentes"]
            assert freq, (
                "Expected 'abastecimentos_frequentes' heuristic alert after 4 refuels in 24h; "
                f"last refuel id={last_id}"
            )
            for a in freq:
                assert a.get("ia_gerado") is not True
        finally:
            requests.delete(f"{API}/vehicles/{v['id']}", headers=admin_headers, timeout=TIMEOUT)


class TestFrentistaRoleFromMe:
    def test_auth_me_returns_frentista_role(self, frentista_headers):
        r = requests.get(f"{API}/auth/me", headers=frentista_headers, timeout=TIMEOUT)
        assert r.status_code == 200
        u = r.json()
        assert u["role"] == "frentista"
        assert u["email"] == "frentista@frotanfc.gov.br"
