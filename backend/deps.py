"""Shared FastAPI dependencies."""
from __future__ import annotations
import os
from typing import Optional
from fastapi import Request, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from datetime import datetime, timezone

import jwt
from security import decode_token

_client: Optional[AsyncIOMotorClient] = None


def get_db() -> AsyncIOMotorDatabase:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    return _client[os.environ["DB_NAME"]]


async def get_current_user(request: Request) -> dict:
    token: Optional[str] = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Não autenticado")
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

    db = get_db()
    user = await db.users.find_one({"id": payload["sub"], "active": True})
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo")
    user.pop("password_hash", None)
    user.pop("_id", None)
    return user


def require_roles(*roles: str):
    async def _guard(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles and user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Permissão insuficiente")
        return user

    return _guard


async def log_audit(
    db: AsyncIOMotorDatabase,
    user: Optional[dict],
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip: Optional[str] = None,
) -> None:
    import uuid

    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user.get("id") if user else None,
        "user_email": user.get("email") if user else None,
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
        "details": details or {},
        "ip": ip,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.audit_logs.insert_one(doc)
