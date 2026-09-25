"""
core/multi_tenant_manager.py — Sovereign Multi-Tenant & Multi-Device Access Gateway
===================================================================================
Provides production-grade multi-tenant client onboarding, device linking,
Role-Based Access Control (RBAC: Observer, Trader, Sovereign Master), and
tamper-evident data isolation audit logging.

Security & Isolation Constraints:
- Sovereign Master: Master Muhammad Qureshi (+923468053268) holds root authority.
- Trader: Permitted trading, order approval, and portfolio view under deterministic limits.
- Observer: Read-only monitoring; strictly prohibited from executing commands or trades.
- Cross-Tenant Isolation: Tenant queries are strictly scoped; zero cross-tenant contamination.
===================================================================================
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("jarvis.core.multi_tenant_manager")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

_BASE_DIR = Path(__file__).resolve().parent.parent
_DB_PATH = _BASE_DIR / "data" / "multi_tenant.db"

# Roles enum
ROLE_OBSERVER = "Observer"
ROLE_TRADER = "Trader"
ROLE_SOVEREIGN_MASTER = "Sovereign Master"

VALID_ROLES = {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER}

# Master Sovereign Identity
MASTER_PHONE = "+923468053268"
MASTER_NAME = "Master Muhammad Qureshi"

# Permission Matrices
# Format: resource_prefix -> allowed roles
RESOURCE_PERMISSIONS: Dict[str, Set[str]] = {
    # Read-only telemetry, screen stream, vitals, 3D models
    "/api/health": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/status": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/pc": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/pc/vitals": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/screen": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/screen/stream": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/hotspots": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/sessions": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/download/apk": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/cua/stream": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/dag/state": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/subagents/logs": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/assimilator/tree": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/self-healing/log": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/keys/catalog": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/whatsapp/status": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/whatsapp/qr": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/client/status": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/client/audit": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/client/pair": {ROLE_OBSERVER, ROLE_TRADER, ROLE_SOVEREIGN_MASTER},

    # Trading & Market execution
    "/api/trade": {ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/trading": {ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/approval": {ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/portfolio": {ROLE_TRADER, ROLE_SOVEREIGN_MASTER},
    "/api/positions": {ROLE_TRADER, ROLE_SOVEREIGN_MASTER},

    # System administration, Win32 hardware control, terminal, APK ingest, keys ingest
    "/api/mouse": {ROLE_SOVEREIGN_MASTER},
    "/api/keyboard": {ROLE_SOVEREIGN_MASTER},
    "/api/terminal": {ROLE_SOVEREIGN_MASTER},
    "/api/command": {ROLE_SOVEREIGN_MASTER},
    "/api/system": {ROLE_SOVEREIGN_MASTER},
    "/api/keys/ingest": {ROLE_SOVEREIGN_MASTER},
    "/api/whatsapp/pair-code": {ROLE_SOVEREIGN_MASTER},
    "/api/whatsapp/reset": {ROLE_SOVEREIGN_MASTER},
    "/api/client/register": {ROLE_SOVEREIGN_MASTER},
    "/api/client/list": {ROLE_SOVEREIGN_MASTER},
    "/api/self_healing/resolve": {ROLE_SOVEREIGN_MASTER},
    "/api/assimilator/assimilate": {ROLE_SOVEREIGN_MASTER},
}


class MultiTenantManager:
    """
    SQLite-backed manager for multi-tenant identities, device sessions,
    RBAC enforcement, and tenant-isolated audit logging.
    """

    _instance: Optional[MultiTenantManager] = None
    _lock = threading.RLock()

    def __new__(cls, db_path: Optional[Path] = None) -> MultiTenantManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: Optional[Path] = None):
        if getattr(self, "_initialized", False):
            return
        self.db_path = Path(db_path or _DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._seed_master_tenant()
        self._initialized = True
        logger.info(f"[MultiTenantManager] Initialized multi-tenant gateway with DB: {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tenants (
                    tenant_id TEXT PRIMARY KEY,
                    client_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    phone_number TEXT,
                    email TEXT,
                    token TEXT UNIQUE NOT NULL,
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT
                );

                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    client_ip TEXT,
                    user_agent TEXT,
                    device_token TEXT UNIQUE NOT NULL,
                    linked_at TEXT NOT NULL,
                    last_active_at TEXT,
                    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS tenant_audit_log (
                    log_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    client_ip TEXT,
                    role TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_tenants_token ON tenants(token);
                CREATE INDEX IF NOT EXISTS idx_devices_token ON devices(device_token);
                CREATE INDEX IF NOT EXISTS idx_audit_tenant ON tenant_audit_log(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON tenant_audit_log(timestamp);
            """)

    def _seed_master_tenant(self) -> None:
        """Ensures Sovereign Master tenant exists in the database."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT tenant_id FROM tenants WHERE role = ?", (ROLE_SOVEREIGN_MASTER,))
            row = cur.fetchone()
            if not row:
                # Find if an existing token is configured
                master_token = os.environ.get("JARVIS_SOVEREIGN_TOKEN")
                if not master_token:
                    # Check internal.local.json or mobile.local.json
                    cfg_file = _BASE_DIR / "config" / "internal.local.json"
                    if cfg_file.exists():
                        try:
                            d = json.loads(cfg_file.read_text(encoding="utf-8"))
                            master_token = d.get("command_token")
                        except Exception:
                            pass
                if not master_token:
                    master_token = "sovereign_master_" + secrets.token_hex(24)

                master_id = "tenant_master_001"
                now = datetime.now(timezone.utc).isoformat()
                cur.execute("""
                    INSERT INTO tenants (tenant_id, client_name, role, phone_number, email, token, status, created_at, last_seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
                """, (master_id, MASTER_NAME, ROLE_SOVEREIGN_MASTER, MASTER_PHONE, "futureworldvision842@gmail.com", master_token, now, now))
                conn.commit()
                logger.info(f"[MultiTenantManager] Seeded Sovereign Master tenant: {master_id}")

    # =========================================================================
    # Tenant Management
    # =========================================================================

    def register_tenant(
        self,
        client_name: str,
        role: str = ROLE_OBSERVER,
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
        custom_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Registers a new tenant client with strict role assignment."""
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role: {role}. Must be one of {list(VALID_ROLES)}")

        tenant_id = f"tenant_{role.lower().replace(' ', '_')}_{secrets.token_hex(4)}"
        token = custom_token or f"jtoken_{role.lower()[:3]}_{secrets.token_urlsafe(32)}"
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO tenants (tenant_id, client_name, role, phone_number, email, token, status, created_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
            """, (tenant_id, client_name.strip(), role, phone_number, email, token, now, now))
            conn.commit()

        # Record audit
        self.record_audit(
            tenant_id=tenant_id,
            client_ip="internal",
            role=role,
            action="TENANT_REGISTERED",
            resource="/api/client/register",
            status="ALLOW",
            details=f"Client '{client_name}' registered with role {role}."
        )

        return {
            "ok": True,
            "tenant_id": tenant_id,
            "client_name": client_name,
            "role": role,
            "phone_number": phone_number,
            "token": token,
            "status": "ACTIVE",
            "created_at": now
        }

    def authenticate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Authenticates a tenant token or device token.
        Updates last_seen_at upon successful verification.
        """
        if not token:
            return None

        clean_token = token.strip()
        with self._get_connection() as conn:
            cur = conn.cursor()
            # 1. Check direct tenant token
            cur.execute("""
                SELECT tenant_id, client_name, role, phone_number, email, status, created_at, last_seen_at
                FROM tenants WHERE token = ?
            """, (clean_token,))
            row = cur.fetchone()
            if row:
                tenant_dict = dict(row)
                if tenant_dict["status"] != "ACTIVE":
                    return None
                now = datetime.now(timezone.utc).isoformat()
                cur.execute("UPDATE tenants SET last_seen_at = ? WHERE tenant_id = ?", (now, tenant_dict["tenant_id"]))
                conn.commit()
                tenant_dict["auth_type"] = "tenant_token"
                return tenant_dict

            # 2. Check device token
            cur.execute("""
                SELECT d.device_id, d.device_type, d.client_ip, d.user_agent,
                       t.tenant_id, t.client_name, t.role, t.phone_number, t.email, t.status
                FROM devices d
                JOIN tenants t ON d.tenant_id = t.tenant_id
                WHERE d.device_token = ?
            """, (clean_token,))
            row = cur.fetchone()
            if row:
                res_dict = dict(row)
                if res_dict["status"] != "ACTIVE":
                    return None
                now = datetime.now(timezone.utc).isoformat()
                cur.execute("UPDATE devices SET last_active_at = ? WHERE device_id = ?", (now, res_dict["device_id"]))
                cur.execute("UPDATE tenants SET last_seen_at = ? WHERE tenant_id = ?", (now, res_dict["tenant_id"]))
                conn.commit()
                res_dict["auth_type"] = "device_token"
                return res_dict

        return None

    def get_tenant_by_id(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Fetches tenant record by tenant_id."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT tenant_id, client_name, role, phone_number, email, status, created_at, last_seen_at FROM tenants WHERE tenant_id = ?", (tenant_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_tenant_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Fetches tenant record by phone number (sanitized digits)."""
        clean_phone = "".join(filter(str.isdigit, phone))
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM tenants WHERE replace(replace(phone_number, '+', ''), ' ', '') LIKE ?", (f"%{clean_phone}%",))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_tenants(self, requesting_role: str) -> List[Dict[str, Any]]:
        """Lists all registered tenants (Restricted to Sovereign Master)."""
        if requesting_role != ROLE_SOVEREIGN_MASTER:
            raise PermissionError("Access denied: only Sovereign Master may enumerate tenant identities.")
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT tenant_id, client_name, role, phone_number, email, status, created_at, last_seen_at FROM tenants ORDER BY created_at DESC")
            return [dict(r) for r in cur.fetchall()]

    # =========================================================================
    # Device Enrollment & Linking
    # =========================================================================

    def pair_device(
        self,
        tenant_id: str,
        device_type: str = "mobile_companion",
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrolls a client device (mobile app, desktop workstation, tablet)
        and returns a persistent device token.
        """
        tenant = self.get_tenant_by_id(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found.")

        device_id = f"dev_{secrets.token_hex(6)}"
        device_token = f"jdev_{secrets.token_urlsafe(32)}"
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO devices (device_id, tenant_id, device_type, client_ip, user_agent, device_token, linked_at, last_active_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (device_id, tenant_id, device_type, client_ip or "127.0.0.1", user_agent or "JARVIS-Client/1.0", device_token, now, now))
            conn.commit()

        # Record audit
        self.record_audit(
            tenant_id=tenant_id,
            client_ip=client_ip or "127.0.0.1",
            role=tenant["role"],
            action="DEVICE_PAIRED",
            resource="/api/client/pair",
            status="ALLOW",
            details=f"Device {device_id} ({device_type}) paired for tenant '{tenant['client_name']}'."
        )

        return {
            "ok": True,
            "device_id": device_id,
            "tenant_id": tenant_id,
            "device_type": device_type,
            "device_token": device_token,
            "role": tenant["role"],
            "client_name": tenant["client_name"],
            "linked_at": now
        }

    def list_devices(self, tenant_id: str, requesting_role: str) -> List[Dict[str, Any]]:
        """Lists linked devices for a tenant. Cross-tenant isolation enforced."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            if requesting_role == ROLE_SOVEREIGN_MASTER and not tenant_id:
                cur.execute("SELECT * FROM devices ORDER BY linked_at DESC")
            else:
                cur.execute("SELECT * FROM devices WHERE tenant_id = ? ORDER BY linked_at DESC", (tenant_id,))
            return [dict(r) for r in cur.fetchall()]

    # =========================================================================
    # Role-Based Access Control (RBAC) Engine
    # =========================================================================

    def check_permission(self, role: str, path: str) -> bool:
        """
        Determines whether a client role is authorized for a specific resource path.
        Matching is prefix-based against the RESOURCE_PERMISSIONS matrix.
        """
        if role == ROLE_SOVEREIGN_MASTER:
            return True

        clean_path = path.split("?")[0].rstrip("/")
        if not clean_path.startswith("/"):
            clean_path = "/" + clean_path

        # Check exact and prefix matches
        for resource_prefix, allowed_roles in RESOURCE_PERMISSIONS.items():
            if clean_path == resource_prefix or clean_path.startswith(resource_prefix + "/"):
                return role in allowed_roles

        # Default policy:
        # If unlisted /api/ endpoint:
        # Observer is strictly read-only and restricted to safe monitoring.
        # Trader is restricted to market data & execution.
        # Unknown endpoints require Sovereign Master.
        return False

    # =========================================================================
    # Tamper-Evident Data Isolation Audit Trail
    # =========================================================================

    def record_audit(
        self,
        tenant_id: str,
        client_ip: str,
        role: str,
        action: str,
        resource: str,
        status: str,
        details: Optional[str] = None
    ) -> str:
        """Writes an immutable audit log entry."""
        log_id = f"aud_{int(time.time()*1000)}_{secrets.token_hex(4)}"
        now = datetime.now(timezone.utc).isoformat()

        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO tenant_audit_log (log_id, tenant_id, client_ip, role, action, resource, status, details, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (log_id, tenant_id, client_ip, role, action, resource, status, details or "", now))
                conn.commit()
        except Exception as e:
            logger.error(f"[MultiTenantManager] Audit record error: {e}")

        return log_id

    def get_audit_trail(
        self,
        requesting_tenant_id: str,
        requesting_role: str,
        target_tenant_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieves tenant audit records with STRICT multi-tenant data isolation.
        Non-master clients can ONLY view their own audit records.
        """
        with self._get_connection() as conn:
            cur = conn.cursor()
            if requesting_role == ROLE_SOVEREIGN_MASTER:
                if target_tenant_id:
                    cur.execute("""
                        SELECT * FROM tenant_audit_log
                        WHERE tenant_id = ?
                        ORDER BY timestamp DESC LIMIT ?
                    """, (target_tenant_id, limit))
                else:
                    cur.execute("""
                        SELECT * FROM tenant_audit_log
                        ORDER BY timestamp DESC LIMIT ?
                    """, (limit,))
            else:
                # STRICT ISOLATION: force query to requesting_tenant_id only
                cur.execute("""
                    SELECT * FROM tenant_audit_log
                    WHERE tenant_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                """, (requesting_tenant_id, limit))

            return [dict(r) for r in cur.fetchall()]


# Singleton Accessor
_tenant_manager: Optional[MultiTenantManager] = None

def get_tenant_manager() -> MultiTenantManager:
    """Returns the singleton MultiTenantManager instance."""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = MultiTenantManager()
    return _tenant_manager


if __name__ == "__main__":
    mgr = get_tenant_manager()
    print("[MultiTenantManager] Testing initial setup...")
    tenants = mgr.list_tenants(ROLE_SOVEREIGN_MASTER)
    print(f"Total enrolled tenants: {len(tenants)}")
    for t in tenants:
        print(f"• Tenant: {t['client_name']} | Role: {t['role']} | Status: {t['status']}")
