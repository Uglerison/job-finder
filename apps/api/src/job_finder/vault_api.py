"""A single process-local session for all encrypted credentials."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from job_finder.aggregated_search_api import _vault
from job_finder.ai_settings_api import VaultPasswordRequest
from job_finder.secret_store import SecretStoreError

router = APIRouter(prefix="/api/vault", tags=["vault"])


class VaultStatus(BaseModel):
    configured: bool
    unlocked: bool


@router.get("", response_model=VaultStatus)
def read_vault(request: Request) -> VaultStatus:
    vault = _vault(request)
    return VaultStatus(configured=vault.is_configured(), unlocked=vault.is_unlocked())


@router.post("/create", response_model=VaultStatus)
def create_vault(payload: VaultPasswordRequest, request: Request) -> VaultStatus:
    try:
        _vault(request).initialize(payload.vault_password.get_secret_value())
        return read_vault(request)
    except SecretStoreError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/unlock", response_model=VaultStatus)
def unlock_vault(payload: VaultPasswordRequest, request: Request) -> VaultStatus:
    try:
        _vault(request).unlock_all(payload.vault_password.get_secret_value())
        return read_vault(request)
    except SecretStoreError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/lock", response_model=VaultStatus)
def lock_vault(request: Request) -> VaultStatus:
    _vault(request).lock()
    return read_vault(request)
