"""Frota NFC — Backend integration tests.

Tests all critical /api/* endpoints against the deployed backend using the
public REACT_APP_BACKEND_URL. Follows the feature checklist in the review
request:
  - Auth (login, /auth/me, invalid creds, all seed users)
  - Vehicles / Drivers / Stations CRUD + RBAC
  - NFC lookup + refuel_start
  - Refuel validate + create (rules for status, km, tipo_combustivel)
  - Alerts (heuristic sudden-increase-in-liters), resolve
  - Audit list
  - Fuels seed (>=5)
  - Users create + RBAC
  - Dashboard summary

All tests share fixtures via module scope. Test-created data uses `TEST_` prefix
where possible.
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

# Load env from /app/frontend/.env to get REACT_APP_BACKEND_URL (public URL)
load_dotenv(Path("/app/frontend/.env"))

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

TIMEOUT = 30


# ============================================================================
# Session-scoped helpers
# ============================================================================
class ApiClient:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"Content-Type": "application/json"})

    def set_token(self, token: str | None):
        if token:
            self.s.headers["Authorization"] = f"Bearer {token}"
        else:
            self.s.headers.pop("Authorization", None)

    def get(self, path, **kw):
        return self.s.get(f"{API}{path}", timeout=TIMEOUT, **kw)

    def post(self, path, **kw):
        return self.s.post(f"{API}{path}", timeout=TIMEOUT, **kw)

    def put(self, path, **kw):
        return self.s.put(f"{API}{path}", timeout=TIMEOUT, **kw)

    def delete(self, path, **kw):
        return self.s.delete(f"{API}{path}", timeout=TIMEOUT, **kw)


CREDS = {
    "admin": ("admin@frotanfc.gov.br", "admin123"),
    "gestor": ("gestor@frotanfc.gov.br", "senha123"),
    "frentista": ("frentista@frotanfc.gov.br", "senha123"),
    "auditor": ("auditor@frotanfc.gov.br", "senha123"),
}


def _login(email: str, password: str) -> tuple[int, dict]:
    r = requests.post(
        f"{API}/auth/login",
        json={"email": email, "password": password},
        timeout=TIMEOUT,
    )
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text}


@pytest.fixture(scope="module")
def tokens() -> dict:
    out = {}
    for role, (em, pw) in CREDS.items():
        status, data = _login(em, pw)
        assert status == 200, f"Login failed for {role}: {status} {data}"
        assert "access_token" in data, f"No token for {role}: {data}"
        out[role] = data["access_token"]
    return out


def _client_for(token: str) -> ApiClient:
    c = ApiClient()
    c.set_token(token)
    return c


@pytest.fixture(scope="module")
def admin(tokens) -> ApiClient:
    return _client_for(tokens["admin"])


@pytest.fixture(scope="module")
def gestor(tokens) -> ApiClient:
    return _client_for(tokens["gestor"])


@pytest.fixture(scope="module")
def frentista(tokens) -> ApiClient:
    return _client_for(tokens["frentista"])


@pytest.fixture(scope="module")
def auditor(tokens) -> ApiClient:
    return _client_for(tokens["auditor"])


# ---------- Shared resources created during tests (module-scoped) ----------
@pytest.fixture(scope="module")
def shared(admin) -> dict:
    """Create a base vehicle, driver, station used across dependent tests."""
    state: dict = {}

    # Vehicle
    placa = f"TST{uuid.uuid4().hex[:4].upper()}"
    v_payload = {
        "placa": placa,
        "marca": "Fiat",
        "modelo": "Strada",
        "secretaria": "TEST_Secretaria",
        "tipo_combustivel": "gasolina",
        "capacidade_tanque": 55.0,
        "km_atual": 10000.0,
        "media_km_l": 10.0,
    }
    r = admin.post("/vehicles", json=v_payload)
    assert r.status_code == 200, f"Vehicle create failed {r.status_code} {r.text}"
    state["vehicle"] = r.json()

    # Driver (valid CNH in the future)
    future = (datetime.now(timezone.utc) + timedelta(days=365)).date().isoformat()
    cpf = f"TEST{uuid.uuid4().hex[:8]}"
    d_payload = {
        "nome": "TEST_Motorista",
        "cpf": cpf,
        "cnh": f"CNH{uuid.uuid4().hex[:8]}",
        "categoria_cnh": "B",
        "validade_cnh": future,
        "secretaria": "TEST_Secretaria",
    }
    r = admin.post("/drivers", json=d_payload)
    assert r.status_code == 200, f"Driver create failed {r.status_code} {r.text}"
    state["driver"] = r.json()

    # Station
    s_payload = {
        "nome": "TEST_Posto",
        "endereco": "Rua Teste, 123",
        "bombas": 2,
        "combustiveis": ["gasolina", "diesel_s10"],
    }
    r = admin.post("/stations", json=s_payload)
    assert r.status_code == 200, f"Station create failed {r.status_code} {r.text}"
    state["station"] = r.json()

    yield state

    # Best-effort cleanup
    try:
        admin.delete(f"/vehicles/{state['vehicle']['id']}")
        admin.delete(f"/drivers/{state['driver']['id']}")
        admin.delete(f"/stations/{state['station']['id']}")
    except Exception:
        pass


# ============================================================================
# AUTH
# ============================================================================
class TestAuth:
    def test_login_admin_returns_token_and_user(self):
        status, data = _login(*CREDS["admin"])
        assert status == 200
        assert isinstance(data.get("access_token"), str)
        assert len(data["access_token"]) > 20
        assert data.get("token_type", "bearer").lower() == "bearer"
        assert data["user"]["email"] == CREDS["admin"][0]
        assert data["user"]["role"] == "admin"
        assert data["user"]["active"] is True

    def test_login_invalid_returns_401(self):
        status, data = _login("admin@frotanfc.gov.br", "wrong_pw")
        assert status == 401

    def test_login_unknown_user_returns_401(self):
        status, _ = _login("nobody-xyz@example.com", "whatever")
        assert status == 401

    def test_all_seed_users_can_login(self):
        for role, (em, pw) in CREDS.items():
            status, data = _login(em, pw)
            assert status == 200, f"{role} could not login: {status} {data}"
            assert data["user"]["role"] == role

    def test_auth_me_returns_user(self, admin):
        r = admin.get("/auth/me")
        assert r.status_code == 200
        u = r.json()
        assert u["email"] == CREDS["admin"][0]
        assert u["role"] == "admin"

    def test_auth_me_without_token_401(self):
        r = requests.get(f"{API}/auth/me", timeout=TIMEOUT)
        assert r.status_code == 401

    def test_auth_me_invalid_token_401(self):
        r = requests.get(
            f"{API}/auth/me",
            headers={"Authorization": "Bearer garbage.token.here"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 401


# ============================================================================
# FUELS (seeded 5 defaults)
# ============================================================================
class TestFuels:
    def test_fuels_seeded(self, admin):
        r = admin.get("/fuels")
        assert r.status_code == 200
        docs = r.json()
        tipos = {d["tipo"] for d in docs}
        expected = {"gasolina", "etanol", "diesel_s10", "diesel_comum", "arla_32"}
        assert expected.issubset(tipos), f"Missing fuels: {expected - tipos}"


# ============================================================================
# VEHICLES + NFC
# ============================================================================
class TestVehicles:
    def test_admin_creates_vehicle_with_nfc(self, admin):
        placa = f"AV{uuid.uuid4().hex[:5].upper()}"
        payload = {
            "placa": placa,
            "marca": "VW",
            "modelo": "Gol",
            "secretaria": "TEST_Sec",
            "tipo_combustivel": "gasolina",
            "capacidade_tanque": 50.0,
            "km_atual": 5000.0,
        }
        r = admin.post("/vehicles", json=payload)
        assert r.status_code == 200, r.text
        v = r.json()
        assert v["id"]
        assert v["placa"] == placa
        assert v["nfc_card_id"], "nfc_card_id should be generated"

        # Card should appear in /nfc/cards
        r2 = admin.get("/nfc/cards")
        assert r2.status_code == 200
        cards = r2.json()
        assert any(
            c["numero_cartao"] == v["nfc_card_id"] and c["tipo"] == "veiculo"
            for c in cards
        ), "Vehicle NFC card not found in /nfc/cards"

        # Persisted: GET /vehicles/{id}
        r3 = admin.get(f"/vehicles/{v['id']}")
        assert r3.status_code == 200
        assert r3.json()["placa"] == placa

        # Cleanup
        admin.delete(f"/vehicles/{v['id']}")

    def test_frentista_cannot_create_vehicle(self, frentista):
        payload = {
            "placa": f"FR{uuid.uuid4().hex[:5].upper()}",
            "marca": "X",
            "modelo": "Y",
            "secretaria": "TEST",
            "tipo_combustivel": "gasolina",
            "capacidade_tanque": 40.0,
            "km_atual": 0.0,
        }
        r = frentista.post("/vehicles", json=payload)
        assert r.status_code == 403, f"Expected 403 for frentista, got {r.status_code}"

    def test_gestor_can_create_vehicle(self, gestor):
        placa = f"GE{uuid.uuid4().hex[:5].upper()}"
        payload = {
            "placa": placa,
            "marca": "X",
            "modelo": "Y",
            "secretaria": "TEST",
            "tipo_combustivel": "gasolina",
            "capacidade_tanque": 40.0,
            "km_atual": 0.0,
        }
        r = gestor.post("/vehicles", json=payload)
        assert r.status_code == 200, r.text
        vid = r.json()["id"]
        # cleanup via admin later; frentista/gestor can't delete
        gestor.delete(f"/vehicles/{vid}")  # will 403 — best effort


# ============================================================================
# DRIVERS
# ============================================================================
class TestDrivers:
    def test_admin_creates_driver_with_nfc(self, admin):
        future = (datetime.now(timezone.utc) + timedelta(days=200)).date().isoformat()
        payload = {
            "nome": "TEST_Driver_A",
            "cpf": f"TEST{uuid.uuid4().hex[:8]}",
            "cnh": f"CNH{uuid.uuid4().hex[:6]}",
            "categoria_cnh": "B",
            "validade_cnh": future,
            "secretaria": "TEST",
        }
        r = admin.post("/drivers", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["id"]
        assert d["nfc_card_id"]
        admin.delete(f"/drivers/{d['id']}")


# ============================================================================
# STATIONS
# ============================================================================
class TestStations:
    def test_admin_creates_station(self, admin):
        payload = {
            "nome": "TEST_Posto_X",
            "endereco": "Av Teste",
            "bombas": 3,
            "combustiveis": ["gasolina", "diesel_s10"],
        }
        r = admin.post("/stations", json=payload)
        assert r.status_code == 200, r.text
        s = r.json()
        assert s["id"]
        assert s["combustiveis"] == ["gasolina", "diesel_s10"]
        admin.delete(f"/stations/{s['id']}")


# ============================================================================
# NFC lookup & refuel start
# ============================================================================
class TestNFC:
    def test_nfc_lookup_returns_vehicle(self, admin, shared):
        card_id = shared["vehicle"]["nfc_card_id"]
        r = admin.get(f"/nfc/lookup/{card_id}")
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("card")
        assert j.get("vehicle")
        assert j["vehicle"]["id"] == shared["vehicle"]["id"]

    def test_nfc_lookup_lowercase_uppercased_by_backend(self, admin, shared):
        card_id = shared["vehicle"]["nfc_card_id"].lower()
        r = admin.get(f"/nfc/lookup/{card_id}")
        assert r.status_code == 200

    def test_nfc_lookup_invalid_404(self, admin):
        r = admin.get("/nfc/lookup/DOESNOTEXIST123")
        assert r.status_code == 404

    def test_refuel_start_returns_vehicle_and_price(self, frentista, shared):
        card_id = shared["vehicle"]["nfc_card_id"]
        r = frentista.post("/refuels/start", json={"nfc_card_id": card_id})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["vehicle"]["id"] == shared["vehicle"]["id"]
        assert j.get("preco_sugerido") is not None
        assert j["preco_sugerido"] > 0


# ============================================================================
# REFUEL VALIDATION
# ============================================================================
class TestRefuelValidate:
    def test_validate_inactive_vehicle_fails(self, admin, gestor):
        # Create vehicle then set to inativo
        placa = f"IN{uuid.uuid4().hex[:5].upper()}"
        r = admin.post(
            "/vehicles",
            json={
                "placa": placa,
                "marca": "X",
                "modelo": "Y",
                "secretaria": "TEST",
                "tipo_combustivel": "gasolina",
                "capacidade_tanque": 50.0,
                "km_atual": 1000.0,
            },
        )
        assert r.status_code == 200
        vid = r.json()["id"]
        admin.put(f"/vehicles/{vid}", json={"status": "inativo"})

        r2 = admin.post(
            "/refuels/validate",
            json={
                "vehicle_id": vid,
                "km_atual": 1010,
                "litros": 10,
                "tipo_combustivel": "gasolina",
                "preco_litro": 5.89,
            },
        )
        assert r2.status_code == 200
        j = r2.json()
        assert j["ok"] is False
        assert any("inativo" in e.lower() for e in j["errors"])
        admin.delete(f"/vehicles/{vid}")

    def test_validate_km_less_than_previous_fails(self, admin, shared):
        v = shared["vehicle"]
        r = admin.post(
            "/refuels/validate",
            json={
                "vehicle_id": v["id"],
                "km_atual": v["km_atual"] - 100,
                "litros": 10,
                "tipo_combustivel": v["tipo_combustivel"],
                "preco_litro": 5.89,
            },
        )
        assert r.status_code == 200
        j = r.json()
        assert j["ok"] is False
        assert any(
            "quilometragem" in e.lower() or "km" in e.lower() for e in j["errors"]
        )

    def test_validate_wrong_fuel_type_fails(self, admin, shared):
        v = shared["vehicle"]  # gasolina
        r = admin.post(
            "/refuels/validate",
            json={
                "vehicle_id": v["id"],
                "km_atual": v["km_atual"] + 10,
                "litros": 10,
                "tipo_combustivel": "diesel_s10",
                "preco_litro": 6.39,
            },
        )
        assert r.status_code == 200
        j = r.json()
        assert j["ok"] is False
        assert any("combustível" in e.lower() or "combustivel" in e.lower() for e in j["errors"])

    def test_validate_ok_true_for_valid_input(self, admin, shared):
        v = shared["vehicle"]
        r = admin.post(
            "/refuels/validate",
            json={
                "vehicle_id": v["id"],
                "km_atual": v["km_atual"] + 50,
                "litros": 10,
                "tipo_combustivel": v["tipo_combustivel"],
                "preco_litro": 5.89,
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True

    def test_validate_expired_cnh_fails(self, admin, shared):
        # Create driver with expired CNH
        past = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()
        r = admin.post(
            "/drivers",
            json={
                "nome": "TEST_ExpiredCNH",
                "cpf": f"EXP{uuid.uuid4().hex[:8]}",
                "cnh": f"E{uuid.uuid4().hex[:6]}",
                "categoria_cnh": "B",
                "validade_cnh": past,
                "secretaria": "TEST",
            },
        )
        assert r.status_code == 200
        did = r.json()["id"]
        v = shared["vehicle"]
        r2 = admin.post(
            "/refuels/validate",
            json={
                "vehicle_id": v["id"],
                "driver_id": did,
                "km_atual": v["km_atual"] + 60,
                "litros": 10,
                "tipo_combustivel": v["tipo_combustivel"],
                "preco_litro": 5.89,
            },
        )
        assert r2.status_code == 200
        j = r2.json()
        assert j["ok"] is False
        assert any("cnh" in e.lower() for e in j["errors"])
        admin.delete(f"/drivers/{did}")


# ============================================================================
# REFUEL CREATE + ALERTS
# ============================================================================
class TestRefuelCreate:
    def test_refuel_create_computes_totals_and_updates_km(self, frentista, admin, shared):
        v = shared["vehicle"]
        # Refresh km_atual (may have been updated by other tests using shared vehicle)
        v_curr = admin.get(f"/vehicles/{v['id']}").json()
        km_next = v_curr["km_atual"] + 100
        payload = {
            "vehicle_id": v["id"],
            "driver_id": shared["driver"]["id"],
            "km_atual": km_next,
            "litros": 20.0,
            "tipo_combustivel": v["tipo_combustivel"],
            "preco_litro": 5.89,
            "posto_id": shared["station"]["id"],
        }
        r = frentista.post("/refuels", json=payload)
        assert r.status_code == 200, r.text
        j = r.json()
        assert abs(j["valor_total"] - round(20.0 * 5.89, 2)) < 0.01
        assert j["km_anterior"] == v_curr["km_atual"]
        assert j["km_rodados"] == 100
        assert j["autonomia"] == pytest.approx(100 / 20.0, rel=1e-3)
        assert j["secretaria"] == v["secretaria"]

        # Vehicle km_atual updated
        v2 = admin.get(f"/vehicles/{v['id']}").json()
        assert v2["km_atual"] == km_next
        # store for downstream
        shared["last_refuel"] = j

    def test_refuel_create_km_less_than_previous_400(self, frentista, admin, shared):
        v = admin.get(f"/vehicles/{shared['vehicle']['id']}").json()
        payload = {
            "vehicle_id": v["id"],
            "km_atual": v["km_atual"] - 50,
            "litros": 10.0,
            "tipo_combustivel": v["tipo_combustivel"],
            "preco_litro": 5.89,
        }
        r = frentista.post("/refuels", json=payload)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"

    def test_refuel_list_filters(self, frentista, shared):
        r = frentista.get(
            "/refuels",
            params={"vehicle_id": shared["vehicle"]["id"]},
        )
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list)
        assert all(x["vehicle_id"] == shared["vehicle"]["id"] for x in arr)
        assert len(arr) >= 1

        r2 = frentista.get(
            "/refuels",
            params={"secretaria": shared["vehicle"]["secretaria"]},
        )
        assert r2.status_code == 200
        assert all(x["secretaria"] == shared["vehicle"]["secretaria"] for x in r2.json())

    def test_sudden_increase_generates_alert(self, frentista, admin, shared):
        """Create several small refuels then a big one — should trigger
        'aumento_repentino_consumo' heuristic alert."""
        v = admin.get(f"/vehicles/{shared['vehicle']['id']}").json()
        # 5 small refuels with unique liters (avoid duplicate-detection heuristic
        # that blocks same-liters within 10 minutes).
        km = v["km_atual"]
        small_liters = [4.5, 5.0, 5.2, 4.8, 5.1]  # avg ~= 4.92L
        for i, lit in enumerate(small_liters):
            km += 50
            r = frentista.post(
                "/refuels",
                json={
                    "vehicle_id": v["id"],
                    "km_atual": km,
                    "litros": lit,
                    "tipo_combustivel": v["tipo_combustivel"],
                    "preco_litro": 5.89,
                },
            )
            assert r.status_code == 200, f"small refuel {i} failed: {r.text}"
            time.sleep(0.2)
        # Now a big one (>50% above avg≈4.92L → e.g. 15L)
        km += 60
        r = frentista.post(
            "/refuels",
            json={
                "vehicle_id": v["id"],
                "km_atual": km,
                "litros": 15.0,
                "tipo_combustivel": v["tipo_combustivel"],
                "preco_litro": 5.89,
            },
        )
        assert r.status_code == 200, r.text
        big_refuel_id = r.json()["id"]

        # Check alerts
        time.sleep(0.5)
        r2 = admin.get("/alerts")
        assert r2.status_code == 200
        alerts = r2.json()
        matched = [
            a
            for a in alerts
            if a.get("refuel_id") == big_refuel_id
            and a.get("tipo") == "aumento_repentino_consumo"
        ]
        assert matched, (
            "Expected 'aumento_repentino_consumo' alert for the big refuel — "
            f"alerts snapshot (first 5): {alerts[:5]}"
        )
        shared["alert_id"] = matched[0]["id"]


# ============================================================================
# ALERTS
# ============================================================================
class TestAlerts:
    def test_alerts_list(self, admin):
        r = admin.get("/alerts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_resolve_alert_as_admin(self, admin, shared):
        aid = shared.get("alert_id")
        if not aid:
            # try any open alert
            r = admin.get("/alerts", params={"resolvido": False})
            arr = r.json()
            if not arr:
                pytest.skip("No open alert to resolve")
            aid = arr[0]["id"]
        r = admin.post(f"/alerts/{aid}/resolve")
        assert r.status_code == 200
        # Confirm resolved persisted
        r2 = admin.get("/alerts")
        found = [a for a in r2.json() if a["id"] == aid]
        assert found and found[0]["resolvido"] is True

    def test_resolve_alert_as_frentista_forbidden(self, frentista, admin):
        # Get some alert
        arr = admin.get("/alerts").json()
        if not arr:
            pytest.skip("No alert to test forbid on")
        aid = arr[0]["id"]
        r = frentista.post(f"/alerts/{aid}/resolve")
        assert r.status_code == 403


# ============================================================================
# AUDIT
# ============================================================================
class TestAudit:
    def test_audit_admin_can_list(self, admin):
        r = admin.get("/audit")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        # after all the login/create actions we've done, there should be entries
        assert len(r.json()) > 0

    def test_audit_auditor_can_list(self, auditor):
        r = auditor.get("/audit")
        assert r.status_code == 200

    def test_audit_gestor_can_list(self, gestor):
        r = gestor.get("/audit")
        assert r.status_code == 200

    def test_audit_frentista_forbidden(self, frentista):
        r = frentista.get("/audit")
        assert r.status_code == 403


# ============================================================================
# USERS
# ============================================================================
class TestUsers:
    def test_admin_creates_user(self, admin):
        email = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
        r = admin.post(
            "/users",
            json={
                "email": email,
                "name": "TEST_User",
                "role": "frentista",
                "password": "senha123",
            },
        )
        assert r.status_code == 200, r.text
        u = r.json()
        assert u["email"] == email
        # cleanup
        admin.delete(f"/users/{u['id']}")

    def test_frentista_cannot_create_user(self, frentista):
        email = f"nope_{uuid.uuid4().hex[:6]}@example.com"
        r = frentista.post(
            "/users",
            json={
                "email": email,
                "name": "no",
                "role": "frentista",
                "password": "senha123",
            },
        )
        assert r.status_code == 403


# ============================================================================
# DASHBOARD
# ============================================================================
class TestDashboard:
    def test_dashboard_summary_shape(self, admin):
        r = admin.get("/dashboard/summary")
        assert r.status_code == 200, r.text
        j = r.json()
        for k in [
            "total_refuels",
            "active_vehicles",
            "active_drivers",
            "open_alerts",
            "month",
            "per_secretaria",
            "top_vehicles",
            "series",
        ]:
            assert k in j, f"missing key {k}: {list(j.keys())}"
        assert isinstance(j["series"], list)
        assert isinstance(j["per_secretaria"], list)
        assert isinstance(j["top_vehicles"], list)
        assert "litros" in j["month"]
        assert "valor" in j["month"]
        assert "count" in j["month"]


# ============================================================================
# DELETE endpoints
# ============================================================================
class TestDeleteAsAdmin:
    def test_admin_can_delete_vehicle_driver_station_user(self, admin):
        # vehicle
        r = admin.post(
            "/vehicles",
            json={
                "placa": f"DL{uuid.uuid4().hex[:5].upper()}",
                "marca": "X",
                "modelo": "Y",
                "secretaria": "TEST",
                "tipo_combustivel": "gasolina",
                "capacidade_tanque": 40.0,
                "km_atual": 0,
            },
        )
        assert r.status_code == 200
        vid = r.json()["id"]
        r = admin.delete(f"/vehicles/{vid}")
        assert r.status_code == 200
        assert admin.get(f"/vehicles/{vid}").status_code == 404

        # driver
        future = (datetime.now(timezone.utc) + timedelta(days=100)).date().isoformat()
        r = admin.post(
            "/drivers",
            json={
                "nome": "TEST_Del",
                "cpf": f"D{uuid.uuid4().hex[:8]}",
                "cnh": f"C{uuid.uuid4().hex[:6]}",
                "categoria_cnh": "B",
                "validade_cnh": future,
                "secretaria": "TEST",
            },
        )
        assert r.status_code == 200
        did = r.json()["id"]
        assert admin.delete(f"/drivers/{did}").status_code == 200

        # station
        r = admin.post(
            "/stations",
            json={
                "nome": "TEST_Del_Posto",
                "endereco": "X",
                "bombas": 1,
                "combustiveis": ["gasolina"],
            },
        )
        assert r.status_code == 200
        sid = r.json()["id"]
        assert admin.delete(f"/stations/{sid}").status_code == 200

        # user
        email = f"del_{uuid.uuid4().hex[:6]}@example.com"
        r = admin.post(
            "/users",
            json={
                "email": email,
                "name": "TEST_Del",
                "role": "frentista",
                "password": "senha123",
            },
        )
        assert r.status_code == 200
        uid = r.json()["id"]
        assert admin.delete(f"/users/{uid}").status_code == 200
