"""Pydantic models for Frota NFC."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict, EmailStr
import uuid


def _uid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


UserRole = Literal["admin", "gestor", "frentista", "motorista", "auditor"]
VehicleStatus = Literal["ativo", "inativo", "manutencao"]
DriverStatus = Literal["ativo", "inativo", "suspenso"]
FuelType = Literal["gasolina", "etanol", "diesel_s10", "diesel_comum", "arla_32"]


# ============================================================================
# USER
# ============================================================================
class UserBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: EmailStr
    name: str
    role: UserRole = "frentista"
    phone: Optional[str] = None
    active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None
    phone: Optional[str] = None
    active: Optional[bool] = None
    password: Optional[str] = None


class UserOut(UserBase):
    id: str
    created_at: datetime


# ============================================================================
# VEHICLE
# ============================================================================
class VehicleBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    placa: str
    renavam: Optional[str] = None
    modelo: str
    marca: str
    ano: Optional[int] = None
    secretaria: str
    departamento: Optional[str] = None
    centro_custo: Optional[str] = None
    tipo_combustivel: FuelType
    capacidade_tanque: float  # liters
    media_km_l: Optional[float] = None
    km_atual: float = 0
    status: VehicleStatus = "ativo"
    foto: Optional[str] = None
    limite_diario_litros: Optional[float] = None
    limite_semanal_litros: Optional[float] = None
    limite_mensal_litros: Optional[float] = None


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    placa: Optional[str] = None
    renavam: Optional[str] = None
    modelo: Optional[str] = None
    marca: Optional[str] = None
    ano: Optional[int] = None
    secretaria: Optional[str] = None
    departamento: Optional[str] = None
    centro_custo: Optional[str] = None
    tipo_combustivel: Optional[FuelType] = None
    capacidade_tanque: Optional[float] = None
    media_km_l: Optional[float] = None
    km_atual: Optional[float] = None
    status: Optional[VehicleStatus] = None
    foto: Optional[str] = None
    limite_diario_litros: Optional[float] = None
    limite_semanal_litros: Optional[float] = None
    limite_mensal_litros: Optional[float] = None


class VehicleOut(VehicleBase):
    id: str
    nfc_card_id: Optional[str] = None
    created_at: datetime


# ============================================================================
# DRIVER
# ============================================================================
class DriverBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    nome: str
    cpf: str
    cnh: str
    categoria_cnh: str
    validade_cnh: str  # ISO date string
    secretaria: str
    telefone: Optional[str] = None
    foto: Optional[str] = None
    status: DriverStatus = "ativo"


class DriverCreate(DriverBase):
    pass


class DriverUpdate(BaseModel):
    nome: Optional[str] = None
    cpf: Optional[str] = None
    cnh: Optional[str] = None
    categoria_cnh: Optional[str] = None
    validade_cnh: Optional[str] = None
    secretaria: Optional[str] = None
    telefone: Optional[str] = None
    foto: Optional[str] = None
    status: Optional[DriverStatus] = None


class DriverOut(DriverBase):
    id: str
    nfc_card_id: Optional[str] = None
    created_at: datetime


# ============================================================================
# STATION
# ============================================================================
class StationBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    nome: str
    endereco: str
    responsavel: Optional[str] = None
    bombas: int = 1
    combustiveis: List[FuelType] = []
    ativo: bool = True


class StationCreate(StationBase):
    pass


class StationUpdate(BaseModel):
    nome: Optional[str] = None
    endereco: Optional[str] = None
    responsavel: Optional[str] = None
    bombas: Optional[int] = None
    combustiveis: Optional[List[FuelType]] = None
    ativo: Optional[bool] = None


class StationOut(StationBase):
    id: str
    created_at: datetime


# ============================================================================
# FUEL PRICE
# ============================================================================
class FuelPriceBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tipo: FuelType
    preco_litro: float
    posto_id: Optional[str] = None


class FuelPriceCreate(FuelPriceBase):
    pass


class FuelPriceOut(FuelPriceBase):
    id: str
    created_at: datetime


# ============================================================================
# NFC CARD
# ============================================================================
class NFCCardBase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    numero_cartao: str
    tipo: Literal["veiculo", "motorista"]
    target_id: str  # vehicle_id or driver_id
    ativo: bool = True


class NFCCardOut(NFCCardBase):
    id: str
    token_encrypted: str
    created_at: datetime


# ============================================================================
# REFUEL
# ============================================================================
class RefuelStart(BaseModel):
    """Step 1: Frentista reads vehicle NFC card."""
    nfc_card_id: str  # numero do cartao


class RefuelValidate(BaseModel):
    """Step 2: Validate the refuel before authorization."""
    vehicle_id: str
    driver_id: Optional[str] = None
    driver_nfc_card_id: Optional[str] = None
    km_atual: float
    litros: float
    tipo_combustivel: FuelType
    preco_litro: float
    posto_id: Optional[str] = None


class RefuelCreate(RefuelValidate):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    foto_hodometro: Optional[str] = None
    foto_bomba: Optional[str] = None
    observacoes: Optional[str] = None


class RefuelOut(BaseModel):
    id: str
    vehicle_id: str
    vehicle_placa: str
    driver_id: Optional[str] = None
    driver_nome: Optional[str] = None
    frentista_id: str
    frentista_nome: str
    posto_id: Optional[str] = None
    posto_nome: Optional[str] = None
    tipo_combustivel: FuelType
    litros: float
    preco_litro: float
    valor_total: float
    km_atual: float
    km_anterior: float
    km_rodados: float
    autonomia: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    foto_hodometro: Optional[str] = None
    foto_bomba: Optional[str] = None
    observacoes: Optional[str] = None
    secretaria: str
    created_at: datetime


class ValidationResult(BaseModel):
    ok: bool
    errors: List[str] = []
    warnings: List[str] = []
    vehicle: Optional[VehicleOut] = None
    driver: Optional[DriverOut] = None


# ============================================================================
# ALERT
# ============================================================================
AlertSeverity = Literal["info", "warning", "critical"]


class AlertOut(BaseModel):
    id: str
    tipo: str
    severidade: AlertSeverity
    mensagem: str
    contexto: dict = {}
    vehicle_id: Optional[str] = None
    driver_id: Optional[str] = None
    refuel_id: Optional[str] = None
    resolvido: bool = False
    ia_gerado: bool = False
    created_at: datetime


# ============================================================================
# AUDIT
# ============================================================================
class AuditLogOut(BaseModel):
    id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: str
    resource: str
    resource_id: Optional[str] = None
    details: dict = {}
    ip: Optional[str] = None
    created_at: datetime


# ============================================================================
# AUTH
# ============================================================================
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
