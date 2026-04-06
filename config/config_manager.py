"""
SurAI Runtime Configuration Manager
=====================================
Manages a persistent surai_config.json so that settings from the UI
survive server restarts. Thread-safe — safe to call from the detection
background thread and the FastAPI request thread simultaneously.

Usage
-----
    from config.config_manager import config_manager

    # Read a value
    threshold = config_manager.get().confidence_threshold

    # Update values (also writes JSON to disk)
    config_manager.update(db_dedup_seconds=300, low_memory_mode=True)
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from loguru import logger

# ── Location of the persisted JSON file ──────────────────────────────────────
# Stored next to this file (config/surai_config.json) so it's always
# found regardless of the CWD on Windows (no backslash issues with pathlib).
_CONFIG_FILE: Path = Path(__file__).parent / "surai_config.json"


# ── Typed config dataclass ────────────────────────────────────────────────────

@dataclass
class SurAIConfig:
    """Live runtime configuration for SurAI.

    All values have safe defaults so the system runs correctly
    even before the user ever opens the Settings page.
    """

    # ── Alerts & Deduplication ─────────────────────────────────────────────
    # How long (seconds) to wait before saving the SAME detection type to DB again.
    # Default = 60 s  (Demo / Presentation Mode).
    db_dedup_seconds: int = 60

    # ── AI & Model Tuning ────────────────────────────────────────────────────
    # Minimum InsightFace det_score for a face to be accepted.
    confidence_threshold: float = 0.60

    # Post-inference IoU NMS threshold. Faces with overlap > this are suppressed.
    iou_threshold: float = 0.45

    # ── Hardware & Performance ───────────────────────────────────────────────
    # 0 = process every frame; 1 = skip 1 of every 2; 3 = skip 3 of every 4.
    frame_skip: int = 0

    # Enable aggressive memory-saving measures (~5.8 GB RAM systems).
    low_memory_mode: bool = False


# ── Singleton manager ─────────────────────────────────────────────────────────

class ConfigManager:
    """Thread-safe singleton that owns the live SurAIConfig."""

    _instance: Optional["ConfigManager"] = None
    _class_lock = threading.Lock()

    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._lock = threading.RLock()  # Re-entrant — safe for same-thread nested calls
        self._config: SurAIConfig = self._load()
        self._initialized = True
        logger.info(
            f"[ConfigManager] Loaded from {_CONFIG_FILE}: "
            f"dedup={self._config.db_dedup_seconds}s, "
            f"conf={self._config.confidence_threshold:.2f}, "
            f"iou={self._config.iou_threshold:.2f}, "
            f"frame_skip={self._config.frame_skip}, "
            f"low_mem={self._config.low_memory_mode}"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self) -> SurAIConfig:
        """Return the current in-memory config snapshot (thread-safe)."""
        with self._lock:
            return self._config

    def update(self, **kwargs) -> SurAIConfig:
        """Apply partial updates, persist to disk, and return the new config.

        Unknown keys are silently ignored so future frontend additions
        don't crash the backend before the server is updated.

        Example::

            config_manager.update(db_dedup_seconds=3600, low_memory_mode=True)
        """
        with self._lock:
            current = asdict(self._config)

            # Validate and coerce each known field
            field_validators = {
                "db_dedup_seconds": (int, 0, 86400 * 7),   # 0 s → 7 days
                "confidence_threshold": (float, 0.0, 1.0),
                "iou_threshold": (float, 0.0, 1.0),
                "frame_skip": (int, 0, 10),
                "low_memory_mode": (bool, None, None),
            }

            for key, value in kwargs.items():
                if key not in field_validators:
                    logger.debug(f"[ConfigManager] Ignoring unknown key: {key!r}")
                    continue
                cast_fn, lo, hi = field_validators[key]
                try:
                    coerced = cast_fn(value)
                    if lo is not None and hi is not None:
                        coerced = max(lo, min(hi, coerced))
                    current[key] = coerced
                except (TypeError, ValueError) as exc:
                    logger.warning(f"[ConfigManager] Invalid value for {key!r}: {value!r} — {exc}")

            self._config = SurAIConfig(**current)
            self._save(self._config)
            logger.info(f"[ConfigManager] Settings updated: {asdict(self._config)}")
            return self._config

    def as_dict(self) -> dict:
        """Return the current config as a plain dict (for JSON serialisation)."""
        with self._lock:
            return asdict(self._config)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _load(self) -> SurAIConfig:
        """Load config from JSON file, falling back to defaults on any error."""
        if not _CONFIG_FILE.exists():
            logger.info(f"[ConfigManager] {_CONFIG_FILE} not found — using defaults")
            defaults = SurAIConfig()
            self._save(defaults)
            return defaults

        try:
            data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            # Only load keys that exist in the dataclass; ignore extras
            valid_keys = SurAIConfig.__dataclass_fields__.keys()
            filtered = {k: v for k, v in data.items() if k in valid_keys}
            return SurAIConfig(**{**asdict(SurAIConfig()), **filtered})
        except Exception as exc:
            logger.warning(
                f"[ConfigManager] Failed to parse {_CONFIG_FILE} ({exc}) — using defaults"
            )
            return SurAIConfig()

    def _save(self, cfg: SurAIConfig) -> None:
        """Atomically write the config to disk using a temp file + rename."""
        try:
            tmp = _CONFIG_FILE.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(asdict(cfg), indent=2),
                encoding="utf-8"
            )
            tmp.replace(_CONFIG_FILE)
        except Exception as exc:
            logger.error(f"[ConfigManager] Failed to write {_CONFIG_FILE}: {exc}")


# ── Module-level singleton ────────────────────────────────────────────────────
config_manager = ConfigManager()
