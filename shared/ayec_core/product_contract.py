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
        )
    if not result:
        raise ValueError("Product catalog is empty")
    return result
