"""Frota NFC - main FastAPI application.

Fleet fuel management system with NFC card control, JWT auth (RBAC), and AI fraud detection.
"""
from __future__ import annotations
import os
import logging
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorDatabase

from models import (
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserUpdate,
    UserOut,
    VehicleCreate,
    VehicleUpdate,
    VehicleOut,
    DriverCreate,
    DriverUpdate,
    DriverOut,
    StationCreate,
    StationUpdate,
    StationOut,
    FuelPriceCreate,
    FuelPriceOut,
    NFCCardOut,
    RefuelStart,
    RefuelValidate,
    RefuelCreate,
    RefuelOut,
    ValidationResult,
    AlertOut,
    AuditLogOut,
)
from security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_nfc_card_number,
    generate_nfc_token,
)
from deps import get_db, get_current_user, require_roles, log_audit
from fraud_ai import heuristic_fraud_checks

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("frota_nfc")

app = FastAPI(title="Frota NFC", version="1.0.0")
api = APIRouter(prefix="/api")


# ============================================================================
# STARTUP: indexes + seed admin
# ============================================================================
@app.on_event("startup")
async def startup() -> None:
    db = get_db()
    await db.users.create_index("email", unique=True)
    await db.vehicles.create_index("placa", unique=True)
    await db.drivers.create_index("cpf", unique=True)
    await db.nfc_cards.create_index("numero_cartao", unique=True)
    await db.refuels.create_index("vehicle_id")
    await db.refuels.create_index("created_at")
    await db.alerts.create_index("created_at")
    await db.audit_logs.create_index("created_at")

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@frotanfc.gov.br")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one(
            {
                "id": str(uuid.uuid4()),
                "email": admin_email,
                "name": "Administrador",
                "role": "admin",
                "phone": None,
                "active": True,
                "password_hash": hash_password(admin_password),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info("Admin seeded: %s", admin_email)
    else:
        if not verify_password(admin_password, existing.get("password_hash", "")):
            await db.users.update_one(
                {"email": admin_email},
                {"$set": {"password_hash": hash_password(admin_password)}},
            )
            logger.info("Admin password re-synced")

    # Seed some sample users if none besides admin
    users_count = await db.users.count_documents({})
    if users_count == 1:
        samples = [
            ("gestor@frotanfc.gov.br", "Gestor Municipal", "gestor"),
            ("frentista@frotanfc.gov.br", "João Frentista", "frentista"),
            ("auditor@frotanfc.gov.br", "Ana Auditora", "auditor"),
        ]
        for em, nm, rl in samples:
            await db.users.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "email": em,
                    "name": nm,
                    "role": rl,
                    "phone": None,
                    "active": True,
                    "password_hash": hash_password("senha123"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        logger.info("Sample users seeded")

    # Seed default fuel prices
    if await db.fuel_prices.count_documents({}) == 0:
        defaults = [
            ("gasolina", 5.89),
            ("etanol", 3.99),
            ("diesel_s10", 6.39),
            ("diesel_comum", 6.09),
            ("arla_32", 4.50),
        ]
        for t, p in defaults:
            await db.fuel_prices.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "tipo": t,
                    "preco_litro": p,
                    "posto_id": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        logger.info("Default fuel prices seeded")


# ============================================================================
# HELPERS
# ============================================================================
def _clean(doc: dict) -> dict:
    if not doc:
        return doc
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if isinstance(dt, str):
        return dt
    return dt.isoformat()


# ============================================================================
# AUTH
# ============================================================================
@api.post("/auth/login", response_model=LoginResponse)
async def login(payload: LoginRequest, request: Request):
    db = get_db()
    email = payload.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    if not user.get("active", True):
        raise HTTPException(status_code=403, detail="Usuário inativo")
    token = create_access_token(user["id"], user["email"], user["role"])
    await log_audit(
        db, user, "login", "auth", user["id"], {"email": email}, request.client.host if request.client else None
    )
    return LoginResponse(access_token=token, user=UserOut(**_clean(user)))


@api.get("/auth/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return UserOut(**user)


@api.post("/auth/logout")
async def logout(request: Request, user: dict = Depends(get_current_user)):
    db = get_db()
    await log_audit(db, user, "logout", "auth", user["id"], {}, request.client.host if request.client else None)
    return {"ok": True}


# ============================================================================
# USERS
# ============================================================================
@api.get("/users", response_model=List[UserOut])
async def list_users(user: dict = Depends(require_roles("admin", "gestor"))):
    db = get_db()
    docs = await db.users.find({}, {"password_hash": 0, "_id": 0}).sort("created_at", -1).to_list(500)
    return [UserOut(**d) for d in docs]


@api.post("/users", response_model=UserOut)
async def create_user(payload: UserCreate, request: Request, user: dict = Depends(require_roles("admin"))):
    db = get_db()
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    doc = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": payload.name,
        "role": payload.role,
        "phone": payload.phone,
        "active": payload.active,
        "password_hash": hash_password(payload.password),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    await log_audit(db, user, "create", "user", doc["id"], {"email": email})
    return UserOut(**_clean({**doc}))


@api.put("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: str, payload: UserUpdate, user: dict = Depends(require_roles("admin"))):
    db = get_db()
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if "password" in updates:
        updates["password_hash"] = hash_password(updates.pop("password"))
    if not updates:
        raise HTTPException(status_code=400, detail="Nada para atualizar")
    r = await db.users.update_one({"id": user_id}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    doc = await db.users.find_one({"id": user_id}, {"password_hash": 0, "_id": 0})
    await log_audit(db, user, "update", "user", user_id, {"fields": list(updates.keys())})
    return UserOut(**doc)


@api.delete("/users/{user_id}")
async def delete_user(user_id: str, user: dict = Depends(require_roles("admin"))):
    db = get_db()
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Não é possível remover a si mesmo")
    r = await db.users.delete_one({"id": user_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    await log_audit(db, user, "delete", "user", user_id)
    return {"ok": True}


# ============================================================================
# VEHICLES
# ============================================================================
@api.get("/vehicles", response_model=List[VehicleOut])
async def list_vehicles(user: dict = Depends(get_current_user)):
    db = get_db()
    docs = await db.vehicles.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [VehicleOut(**d) for d in docs]


@api.get("/vehicles/{vehicle_id}", response_model=VehicleOut)
async def get_vehicle(vehicle_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    doc = await db.vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    return VehicleOut(**doc)


@api.post("/vehicles", response_model=VehicleOut)
async def create_vehicle(payload: VehicleCreate, user: dict = Depends(require_roles("admin", "gestor"))):
    db = get_db()
    placa = payload.placa.upper().replace("-", "")
    if await db.vehicles.find_one({"placa": placa}):
        raise HTTPException(status_code=400, detail="Placa já cadastrada")
    # Generate NFC card for this vehicle
    numero_cartao = generate_nfc_card_number()
    vehicle_id = str(uuid.uuid4())
    token_enc = generate_nfc_token(vehicle_id, numero_cartao)

    doc = payload.model_dump()
    doc["placa"] = placa
    doc["id"] = vehicle_id
    doc["nfc_card_id"] = numero_cartao
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.vehicles.insert_one(doc)

    await db.nfc_cards.insert_one(
        {
            "id": str(uuid.uuid4()),
            "numero_cartao": numero_cartao,
            "tipo": "veiculo",
            "target_id": vehicle_id,
            "token_encrypted": token_enc,
            "ativo": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    await log_audit(db, user, "create", "vehicle", vehicle_id, {"placa": placa, "nfc": numero_cartao})
    return VehicleOut(**{k: v for k, v in doc.items() if k != "_id"})


@api.put("/vehicles/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(
    vehicle_id: str, payload: VehicleUpdate, user: dict = Depends(require_roles("admin", "gestor"))
):
    db = get_db()
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if "placa" in updates:
        updates["placa"] = updates["placa"].upper().replace("-", "")
    if not updates:
        raise HTTPException(status_code=400, detail="Nada para atualizar")
    r = await db.vehicles.update_one({"id": vehicle_id}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    doc = await db.vehicles.find_one({"id": vehicle_id}, {"_id": 0})
    await log_audit(db, user, "update", "vehicle", vehicle_id, {"fields": list(updates.keys())})
    return VehicleOut(**doc)


@api.delete("/vehicles/{vehicle_id}")
async def delete_vehicle(vehicle_id: str, user: dict = Depends(require_roles("admin"))):
    db = get_db()
    r = await db.vehicles.delete_one({"id": vehicle_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    await db.nfc_cards.delete_many({"tipo": "veiculo", "target_id": vehicle_id})
    await log_audit(db, user, "delete", "vehicle", vehicle_id)
    return {"ok": True}


# ============================================================================
# DRIVERS
# ============================================================================
@api.get("/drivers", response_model=List[DriverOut])
async def list_drivers(user: dict = Depends(get_current_user)):
    db = get_db()
    docs = await db.drivers.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return [DriverOut(**d) for d in docs]


@api.post("/drivers", response_model=DriverOut)
async def create_driver(payload: DriverCreate, user: dict = Depends(require_roles("admin", "gestor"))):
    db = get_db()
    if await db.drivers.find_one({"cpf": payload.cpf}):
        raise HTTPException(status_code=400, detail="CPF já cadastrado")
    driver_id = str(uuid.uuid4())
    numero_cartao = generate_nfc_card_number()
    token_enc = generate_nfc_token(driver_id, numero_cartao)
    doc = payload.model_dump()
    doc["id"] = driver_id
    doc["nfc_card_id"] = numero_cartao
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.drivers.insert_one(doc)
    await db.nfc_cards.insert_one(
        {
            "id": str(uuid.uuid4()),
            "numero_cartao": numero_cartao,
            "tipo": "motorista",
            "target_id": driver_id,
            "token_encrypted": token_enc,
            "ativo": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    await log_audit(db, user, "create", "driver", driver_id, {"cpf": payload.cpf, "nfc": numero_cartao})
    return DriverOut(**{k: v for k, v in doc.items() if k != "_id"})


@api.put("/drivers/{driver_id}", response_model=DriverOut)
async def update_driver(driver_id: str, payload: DriverUpdate, user: dict = Depends(require_roles("admin", "gestor"))):
    db = get_db()
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="Nada para atualizar")
    r = await db.drivers.update_one({"id": driver_id}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Motorista não encontrado")
    doc = await db.drivers.find_one({"id": driver_id}, {"_id": 0})
    await log_audit(db, user, "update", "driver", driver_id, {"fields": list(updates.keys())})
    return DriverOut(**doc)


@api.delete("/drivers/{driver_id}")
async def delete_driver(driver_id: str, user: dict = Depends(require_roles("admin"))):
    db = get_db()
    r = await db.drivers.delete_one({"id": driver_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Motorista não encontrado")
    await db.nfc_cards.delete_many({"tipo": "motorista", "target_id": driver_id})
    await log_audit(db, user, "delete", "driver", driver_id)
    return {"ok": True}


# ============================================================================
# STATIONS
# ============================================================================
@api.get("/stations", response_model=List[StationOut])
async def list_stations(user: dict = Depends(get_current_user)):
    db = get_db()
    docs = await db.stations.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [StationOut(**d) for d in docs]


@api.post("/stations", response_model=StationOut)
async def create_station(payload: StationCreate, user: dict = Depends(require_roles("admin", "gestor"))):
    db = get_db()
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.stations.insert_one(doc)
    await log_audit(db, user, "create", "station", doc["id"], {"nome": payload.nome})
    return StationOut(**{k: v for k, v in doc.items() if k != "_id"})


@api.put("/stations/{station_id}", response_model=StationOut)
async def update_station(station_id: str, payload: StationUpdate, user: dict = Depends(require_roles("admin", "gestor"))):
    db = get_db()
    updates = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    r = await db.stations.update_one({"id": station_id}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Posto não encontrado")
    doc = await db.stations.find_one({"id": station_id}, {"_id": 0})
    return StationOut(**doc)


@api.delete("/stations/{station_id}")
async def delete_station(station_id: str, user: dict = Depends(require_roles("admin"))):
    db = get_db()
    r = await db.stations.delete_one({"id": station_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Posto não encontrado")
    return {"ok": True}


# ============================================================================
# FUEL PRICES
# ============================================================================
@api.get("/fuels", response_model=List[FuelPriceOut])
async def list_fuels(user: dict = Depends(get_current_user)):
    db = get_db()
    docs = await db.fuel_prices.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [FuelPriceOut(**d) for d in docs]


@api.post("/fuels", response_model=FuelPriceOut)
async def create_fuel(payload: FuelPriceCreate, user: dict = Depends(require_roles("admin", "gestor"))):
    db = get_db()
    doc = payload.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.fuel_prices.insert_one(doc)
    return FuelPriceOut(**{k: v for k, v in doc.items() if k != "_id"})


@api.delete("/fuels/{fuel_id}")
async def delete_fuel(fuel_id: str, user: dict = Depends(require_roles("admin"))):
    db = get_db()
    r = await db.fuel_prices.delete_one({"id": fuel_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Combustível não encontrado")
    return {"ok": True}


# ============================================================================
# NFC CARDS
# ============================================================================
@api.get("/nfc/cards")
async def list_cards(user: dict = Depends(require_roles("admin", "gestor", "auditor"))):
    db = get_db()
    docs = await db.nfc_cards.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return docs


@api.get("/nfc/lookup/{numero_cartao}")
async def lookup_card(numero_cartao: str, user: dict = Depends(get_current_user)):
    """Lookup a card by number and return the associated vehicle or driver."""
    db = get_db()
    card = await db.nfc_cards.find_one({"numero_cartao": numero_cartao.upper(), "ativo": True}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="Cartão NFC não reconhecido")
    result = {"card": card}
    if card["tipo"] == "veiculo":
        v = await db.vehicles.find_one({"id": card["target_id"]}, {"_id": 0})
        result["vehicle"] = v
    else:
        d = await db.drivers.find_one({"id": card["target_id"]}, {"_id": 0})
        result["driver"] = d
    return result


# ============================================================================
# REFUEL FLOW
# ============================================================================
async def _validate_refuel(db: AsyncIOMotorDatabase, payload: RefuelValidate) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    vehicle = await db.vehicles.find_one({"id": payload.vehicle_id}, {"_id": 0})
    if not vehicle:
        return ValidationResult(ok=False, errors=["Veículo não encontrado"])
    if vehicle.get("status") != "ativo":
        errors.append(f"Veículo inativo (status: {vehicle.get('status')})")

    if vehicle.get("tipo_combustivel") != payload.tipo_combustivel:
        errors.append(
            f"Combustível não permitido para este veículo (esperado: {vehicle.get('tipo_combustivel')})"
        )

    if payload.litros <= 0:
        errors.append("Litros deve ser maior que zero")
    if payload.litros > vehicle.get("capacidade_tanque", 999):
        errors.append(
            f"Volume ({payload.litros}L) excede capacidade do tanque ({vehicle.get('capacidade_tanque')}L)"
        )

    km_anterior = vehicle.get("km_atual", 0)
    if payload.km_atual < km_anterior:
        errors.append(f"Quilometragem ({payload.km_atual}) menor que a última registrada ({km_anterior})")
    if payload.km_atual > km_anterior + 5000:
        warnings.append("Quilometragem muito acima do último registro (>5000 km)")

    # Driver validation (optional)
    driver = None
    if payload.driver_id:
        driver = await db.drivers.find_one({"id": payload.driver_id}, {"_id": 0})
        if not driver:
            errors.append("Motorista não encontrado")
        else:
            if driver.get("status") != "ativo":
                errors.append(f"Motorista inativo (status: {driver.get('status')})")
            validade = driver.get("validade_cnh")
            if validade:
                try:
                    dt = datetime.fromisoformat(validade)
                    if dt.date() < datetime.now(timezone.utc).date():
                        errors.append("CNH vencida")
                except Exception:
                    pass

    # Limits check (daily/weekly/monthly)
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = day_start - timedelta(days=day_start.weekday())
    month_start = day_start.replace(day=1)

    async def _sum_since(since_iso: str) -> float:
        cursor = db.refuels.find(
            {"vehicle_id": payload.vehicle_id, "created_at": {"$gte": since_iso}},
            {"litros": 1, "_id": 0},
        )
        total = 0.0
        async for r in cursor:
            total += r.get("litros", 0) or 0
        return total

    if vehicle.get("limite_diario_litros"):
        used = await _sum_since(day_start.isoformat())
        if used + payload.litros > vehicle["limite_diario_litros"]:
            errors.append(f"Limite diário excedido ({used + payload.litros:.1f}L / {vehicle['limite_diario_litros']}L)")

    if vehicle.get("limite_semanal_litros"):
        used = await _sum_since(week_start.isoformat())
        if used + payload.litros > vehicle["limite_semanal_litros"]:
            errors.append(
                f"Limite semanal excedido ({used + payload.litros:.1f}L / {vehicle['limite_semanal_litros']}L)"
            )

    if vehicle.get("limite_mensal_litros"):
        used = await _sum_since(month_start.isoformat())
        if used + payload.litros > vehicle["limite_mensal_litros"]:
            errors.append(
                f"Limite mensal excedido ({used + payload.litros:.1f}L / {vehicle['limite_mensal_litros']}L)"
            )

    # Duplicate check (last 10 min same vehicle same liters)
    dup_since = (now - timedelta(minutes=10)).isoformat()
    dup = await db.refuels.find_one(
        {
            "vehicle_id": payload.vehicle_id,
            "created_at": {"$gte": dup_since},
            "litros": payload.litros,
        }
    )
    if dup:
        errors.append("Abastecimento duplicado detectado nos últimos 10 minutos")

    ok = len(errors) == 0
    return ValidationResult(
        ok=ok,
        errors=errors,
        warnings=warnings,
        vehicle=VehicleOut(**vehicle) if vehicle else None,
        driver=DriverOut(**driver) if driver else None,
    )


@api.post("/refuels/start")
async def refuel_start(payload: RefuelStart, user: dict = Depends(get_current_user)):
    """Read vehicle NFC card and return vehicle info."""
    db = get_db()
    card = await db.nfc_cards.find_one({"numero_cartao": payload.nfc_card_id.upper(), "ativo": True}, {"_id": 0})
    if not card:
        await log_audit(db, user, "nfc_read_failed", "nfc", None, {"numero_cartao": payload.nfc_card_id})
        raise HTTPException(status_code=404, detail="Cartão NFC inválido")
    if card["tipo"] != "veiculo":
        raise HTTPException(status_code=400, detail="Este cartão pertence a um motorista, não a um veículo")
    vehicle = await db.vehicles.find_one({"id": card["target_id"]}, {"_id": 0})
    if not vehicle:
        raise HTTPException(status_code=404, detail="Veículo associado ao cartão não encontrado")
    await log_audit(db, user, "nfc_read", "vehicle", vehicle["id"], {"numero_cartao": payload.nfc_card_id})

    # Get latest price for this fuel type
    price_doc = await db.fuel_prices.find_one({"tipo": vehicle["tipo_combustivel"]}, sort=[("created_at", -1)])
    preco = price_doc.get("preco_litro") if price_doc else None
    return {"vehicle": vehicle, "preco_sugerido": preco}


@api.post("/refuels/validate", response_model=ValidationResult)
async def refuel_validate(payload: RefuelValidate, user: dict = Depends(get_current_user)):
    db = get_db()
    # If driver NFC provided, resolve to driver_id
    if payload.driver_nfc_card_id and not payload.driver_id:
        card = await db.nfc_cards.find_one({"numero_cartao": payload.driver_nfc_card_id.upper(), "ativo": True})
        if card and card["tipo"] == "motorista":
            payload.driver_id = card["target_id"]
    return await _validate_refuel(db, payload)


@api.post("/refuels", response_model=RefuelOut)
async def create_refuel(payload: RefuelCreate, request: Request, user: dict = Depends(get_current_user)):
    db = get_db()

    # Resolve driver NFC if provided
    if payload.driver_nfc_card_id and not payload.driver_id:
        card = await db.nfc_cards.find_one({"numero_cartao": payload.driver_nfc_card_id.upper(), "ativo": True})
        if card and card["tipo"] == "motorista":
            payload.driver_id = card["target_id"]

    validation = await _validate_refuel(db, payload)
    if not validation.ok:
        raise HTTPException(status_code=400, detail={"errors": validation.errors})

    vehicle = await db.vehicles.find_one({"id": payload.vehicle_id}, {"_id": 0})
    driver = None
    if payload.driver_id:
        driver = await db.drivers.find_one({"id": payload.driver_id}, {"_id": 0})

    posto = None
    if payload.posto_id:
        posto = await db.stations.find_one({"id": payload.posto_id}, {"_id": 0})

    km_anterior = vehicle.get("km_atual", 0)
    km_rodados = max(payload.km_atual - km_anterior, 0)
    autonomia = km_rodados / payload.litros if payload.litros > 0 else None

    refuel_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    doc = {
        "id": refuel_id,
        "vehicle_id": payload.vehicle_id,
        "vehicle_placa": vehicle["placa"],
        "driver_id": payload.driver_id,
        "driver_nome": driver["nome"] if driver else None,
        "frentista_id": user["id"],
        "frentista_nome": user["name"],
        "posto_id": payload.posto_id,
        "posto_nome": posto["nome"] if posto else None,
        "tipo_combustivel": payload.tipo_combustivel,
        "litros": payload.litros,
        "preco_litro": payload.preco_litro,
        "valor_total": round(payload.litros * payload.preco_litro, 2),
        "km_atual": payload.km_atual,
        "km_anterior": km_anterior,
        "km_rodados": km_rodados,
        "autonomia": autonomia,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "foto_hodometro": payload.foto_hodometro,
        "foto_bomba": payload.foto_bomba,
        "observacoes": payload.observacoes,
        "secretaria": vehicle.get("secretaria"),
        "hora": now.hour,
        "created_at": now.isoformat(),
    }
    await db.refuels.insert_one(doc)
    await db.vehicles.update_one({"id": payload.vehicle_id}, {"$set": {"km_atual": payload.km_atual}})

    # Fraud checks (heuristics + AI)
    history_cursor = db.refuels.find({"vehicle_id": payload.vehicle_id, "id": {"$ne": refuel_id}}).sort("created_at", -1)
    history = [h async for h in history_cursor]
    for h in history:
        h.pop("_id", None)

    alerts = heuristic_fraud_checks(doc, history, vehicle)

    for a in alerts:
        await db.alerts.insert_one(
            {
                "id": str(uuid.uuid4()),
                "tipo": a["tipo"],
                "severidade": a["severidade"],
                "mensagem": a["mensagem"],
                "contexto": a.get("contexto", {}),
                "vehicle_id": payload.vehicle_id,
                "driver_id": payload.driver_id,
                "refuel_id": refuel_id,
                "resolvido": False,
                "ia_gerado": a.get("ia_gerado", False),
                "created_at": now.isoformat(),
            }
        )

    await log_audit(
        db, user, "create", "refuel", refuel_id,
        {"placa": vehicle["placa"], "litros": payload.litros, "valor": doc["valor_total"]},
        request.client.host if request.client else None,
    )
    return RefuelOut(**doc)


@api.get("/refuels", response_model=List[RefuelOut])
async def list_refuels(
    user: dict = Depends(get_current_user),
    vehicle_id: Optional[str] = None,
    driver_id: Optional[str] = None,
    secretaria: Optional[str] = None,
    limit: int = Query(100, le=1000),
):
    db = get_db()
    q: dict = {}
    if vehicle_id:
        q["vehicle_id"] = vehicle_id
    if driver_id:
        q["driver_id"] = driver_id
    if secretaria:
        q["secretaria"] = secretaria
    docs = await db.refuels.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return [RefuelOut(**d) for d in docs]


# ============================================================================
# DASHBOARD
# ============================================================================
@api.get("/dashboard/summary")
async def dashboard_summary(user: dict = Depends(get_current_user)):
    db = get_db()
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()

    total_refuels = await db.refuels.count_documents({})
    total_vehicles = await db.vehicles.count_documents({"status": "ativo"})
    total_drivers = await db.drivers.count_documents({"status": "ativo"})
    open_alerts = await db.alerts.count_documents({"resolvido": False})

    # Month aggregations
    pipeline = [
        {"$match": {"created_at": {"$gte": month_start}}},
        {
            "$group": {
                "_id": None,
                "litros": {"$sum": "$litros"},
                "valor": {"$sum": "$valor_total"},
                "count": {"$sum": 1},
            }
        },
    ]
    agg = await db.refuels.aggregate(pipeline).to_list(1)
    month = agg[0] if agg else {"litros": 0, "valor": 0, "count": 0}

    # Consumption per secretaria (month)
    per_sec = await db.refuels.aggregate(
        [
            {"$match": {"created_at": {"$gte": month_start}}},
            {
                "$group": {
                    "_id": "$secretaria",
                    "litros": {"$sum": "$litros"},
                    "valor": {"$sum": "$valor_total"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"valor": -1}},
        ]
    ).to_list(50)

    # Top vehicles (month)
    top_vehicles = await db.refuels.aggregate(
        [
            {"$match": {"created_at": {"$gte": month_start}}},
            {
                "$group": {
                    "_id": {"vehicle_id": "$vehicle_id", "placa": "$vehicle_placa"},
                    "litros": {"$sum": "$litros"},
                    "valor": {"$sum": "$valor_total"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"litros": -1}},
            {"$limit": 10},
        ]
    ).to_list(10)

    # Time series (last 30 days) - group by day
    thirty = (now - timedelta(days=30)).isoformat()
    daily_docs = await db.refuels.find(
        {"created_at": {"$gte": thirty}}, {"_id": 0, "created_at": 1, "litros": 1, "valor_total": 1}
    ).to_list(5000)
    from collections import defaultdict

    buckets: dict[str, dict] = defaultdict(lambda: {"litros": 0.0, "valor": 0.0, "count": 0})
    for r in daily_docs:
        try:
            day = r["created_at"][:10]
        except Exception:
            continue
        buckets[day]["litros"] += r.get("litros", 0) or 0
        buckets[day]["valor"] += r.get("valor_total", 0) or 0
        buckets[day]["count"] += 1
    series = [{"date": k, **v} for k, v in sorted(buckets.items())]

    return {
        "total_refuels": total_refuels,
        "active_vehicles": total_vehicles,
        "active_drivers": total_drivers,
        "open_alerts": open_alerts,
        "month": {
            "litros": round(month.get("litros", 0) or 0, 2),
            "valor": round(month.get("valor", 0) or 0, 2),
            "count": month.get("count", 0),
        },
        "per_secretaria": [
            {"secretaria": p["_id"] or "N/A", "litros": round(p["litros"], 2), "valor": round(p["valor"], 2), "count": p["count"]}
            for p in per_sec
        ],
        "top_vehicles": [
            {
                "vehicle_id": p["_id"]["vehicle_id"],
                "placa": p["_id"]["placa"],
                "litros": round(p["litros"], 2),
                "valor": round(p["valor"], 2),
                "count": p["count"],
            }
            for p in top_vehicles
        ],
        "series": series,
    }


@api.get("/dashboard/map")
async def dashboard_map(user: dict = Depends(get_current_user)):
    db = get_db()
    docs = await db.refuels.find(
        {"latitude": {"$ne": None}, "longitude": {"$ne": None}},
        {"_id": 0, "latitude": 1, "longitude": 1, "vehicle_placa": 1, "litros": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(500)
    return docs


# ============================================================================
# ALERTS
# ============================================================================
@api.get("/alerts", response_model=List[AlertOut])
async def list_alerts(
    user: dict = Depends(get_current_user),
    resolvido: Optional[bool] = None,
    limit: int = Query(200, le=1000),
):
    db = get_db()
    q: dict = {}
    if resolvido is not None:
        q["resolvido"] = resolvido
    docs = await db.alerts.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return [AlertOut(**d) for d in docs]


@api.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, user: dict = Depends(require_roles("admin", "gestor"))):
    db = get_db()
    r = await db.alerts.update_one({"id": alert_id}, {"$set": {"resolvido": True}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    await log_audit(db, user, "resolve", "alert", alert_id)
    return {"ok": True}


# ============================================================================
# AUDIT
# ============================================================================
@api.get("/audit", response_model=List[AuditLogOut])
async def list_audit(
    user: dict = Depends(require_roles("admin", "auditor", "gestor")),
    action: Optional[str] = None,
    resource: Optional[str] = None,
    limit: int = Query(200, le=1000),
):
    db = get_db()
    q: dict = {}
    if action:
        q["action"] = action
    if resource:
        q["resource"] = resource
    docs = await db.audit_logs.find(q, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return [AuditLogOut(**d) for d in docs]


# ============================================================================
# HEALTH
# ============================================================================
@api.get("/")
async def root():
    return {"app": "Frota NFC", "version": "1.0.0", "status": "ok"}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
