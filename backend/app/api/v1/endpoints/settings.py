"""
Settings API Endpoints
========================
GET  /api/v1/settings        — returns current surai_config.json as JSON
POST /api/v1/settings/update — validates + saves new settings to disk,
                               updates the live in-memory config immediately.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional

from config.config_manager import config_manager

router = APIRouter()


# ── Request / Response schemas ────────────────────────────────────────────────

class SettingsResponse(BaseModel):
    """Full settings payload returned by GET /settings."""
    model_config = ConfigDict(extra='ignore')  # forward-compat: ignore extra fields

    db_dedup_seconds: int
    confidence_threshold: float
    iou_threshold: float
    frame_skip: int
    low_memory_mode: bool


class SettingsUpdateRequest(BaseModel):
    """Partial-update body for POST /settings/update.
    All fields are optional so the frontend can send only changed values.
    Unknown fields (e.g. active_yolo_model, data_retention_days) are silently
    ignored — the config_manager also ignores them, so they're safe to send.
    """
    model_config = ConfigDict(extra='ignore')  # CRITICAL: don't 422 on unknown fields
    db_dedup_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        le=604800,   # max 7 days
        description="Deduplication cooldown in seconds"
    )
    confidence_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum face detection confidence [0.0–1.0]"
    )
    iou_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="IoU NMS threshold [0.0–1.0]"
    )
    frame_skip: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Skip N frames between Tier-1 tracking runs (0 = every frame)"
    )
    low_memory_mode: Optional[bool] = Field(
        default=None,
        description="Enable aggressive memory-saving (for ~5.8 GB RAM systems)"
    )

    # ── Map frontend dropdown strings to seconds ────────────────────────────
    # The frontend stores cooldown as a string like "60s", "300s", "3600s".
    # Accept both plain int AND these string formats for flexibility.
    @field_validator("db_dedup_seconds", mode="before")
    @classmethod
    def coerce_dedup_seconds(cls, v):
        if isinstance(v, str):
            v = v.rstrip("s")  # "3600s" → "3600"
            try:
                return int(v)
            except ValueError:
                raise ValueError(f"Invalid db_dedup_seconds value: {v!r}")
        return v


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=SettingsResponse, summary="Get current system configuration")
async def get_settings():
    """Return the current surai_config.json values.

    Called by the frontend Settings page on load to pre-populate all controls.
    """
    return config_manager.as_dict()


@router.post(
    "/update",
    response_model=SettingsResponse,
    summary="Update system configuration"
)
async def update_settings(body: SettingsUpdateRequest):
    """Persist new settings to disk and apply them to the live pipeline.

    Only fields that are explicitly provided in the request body are updated;
    omitted fields keep their current values.
    """
    try:
        # Build dict of only the explicitly-set fields
        updates = body.model_dump(exclude_none=True)

        if not updates:
            raise HTTPException(
                status_code=422,
                detail="Request body is empty — no settings to update."
            )

        new_cfg = config_manager.update(**updates)
        return new_cfg

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save settings: {exc}"
        ) from exc
