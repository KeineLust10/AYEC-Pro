"""Product identity and storage contract shared by AYEC applications."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProductContract:
    code: str
    name: str
    folder_name: str
    backup_folder: str
    database_name: str
    smart_import: bool = False
    trial_days: int = 15
    offline_allowance_days: int = 7
    restricted_safety_days: int = 3
    backup_interval_hours: int = 24
    local_retention_count: int = 10
    required_tables: tuple[str, ...] = ()
    supported_commands: tuple[str, ...] = ()
    minimum_core_version: str = "0.3.0"
    minimum_schema_version: int = 1

    def backup_root(self, program_root: str | Path) -> Path:
        return Path(program_root).expanduser().resolve() / self.folder_name / self.backup_folder

    def tenant_current_path(self, program_root: str | Path, tenant_id: str) -> Path:
        safe_tenant = Path(str(tenant_id or "")).name
        if not safe_tenant or safe_tenant in {".", ".."}:
            raise ValueError("tenant_id is required")
        return self.backup_root(program_root) / "tenants" / safe_tenant / "current" / self.database_name

    def tenant_versions_path(self, program_root: str | Path, tenant_id: str) -> Path:
        safe_tenant = Path(str(tenant_id or "")).name
        if not safe_tenant or safe_tenant in {".", ".."}:
            raise ValueError("tenant_id is required")
        return self.backup_root(program_root) / "tenants" / safe_tenant / "versions"


def load_catalog(path: str | Path) -> dict[str, ProductContract]:
    source = Path(path).expanduser().resolve()
    payload = json.loads(source.read_text(encoding="utf-8"))
    result: dict[str, ProductContract] = {}
    for item in payload.get("products", ()):
        if not item.get("active", True):
            continue
        code = str(item.get("code") or "").strip().lower()
        if not code or code in result:
            raise ValueError("Product catalog contains an invalid or duplicate code")
        result[code] = ProductContract(
            code=code,
            name=str(item.get("name") or code),
            folder_name=str(item.get("folder_name") or code),
            backup_folder=str(item.get("backup_folder") or (code + "-AYEC")),
            database_name=str(item.get("database_name") or (code + ".db")),
            smart_import=bool(item.get("smart_import", False)),
            trial_days=max(1, int(item.get("trial_days", 15))),
            offline_allowance_days=max(0, int(item.get("offline_allowance_days", 7))),
            restricted_safety_days=max(0, int(item.get("restricted_safety_days", 3))),
            backup_interval_hours=max(1, int(item.get("backup_interval_hours", 24))),
            local_retention_count=max(1, int(item.get("local_retention_count", 10))),
            required_tables=tuple(str(value) for value in item.get("required_tables", ()) if str(value).strip()),
            supported_commands=tuple(str(value) for value in item.get("supported_commands", ()) if str(value).strip()),
            minimum_core_version=str(item.get("minimum_core_version") or "0.3.0"),
            minimum_schema_version=max(1, int(item.get("minimum_schema_version", 1))),
        )
    if not result:
        raise ValueError("Product catalog is empty")
    return result
