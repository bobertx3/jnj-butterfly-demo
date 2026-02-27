#!/usr/bin/env python3
"""
Create or update the Butterfly Analytics Genie space from src/genie/butterfly_genie_config.yaml.
Requires: databricks-sdk, PyYAML. Run from repo root with Databricks auth configured.
"""
from __future__ import annotations

import json
import os
import uuid
import yaml

from databricks.sdk import WorkspaceClient


def load_config(config_path: str | None = None) -> dict:
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "butterfly_genie_config.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def build_serialized_space(config: dict) -> str:
    tables = []
    for ident in config["table_identifiers"]:
        tables.append({"identifier": ident})
    sample_questions = []
    for q in config.get("sample_questions") or []:
        sample_questions.append({
            "id": str(uuid.uuid4()).replace("-", "")[:32],
            "question": [q],
        })
    payload = {
        "version": 2,
        "config": {"sample_questions": sample_questions},
        "data_sources": {"tables": tables},
    }
    return json.dumps(payload)


def main() -> None:
    config = load_config()
    w = WorkspaceClient()
    warehouse_id = os.environ.get("GENIE_WAREHOUSE_ID")
    if not warehouse_id:
        whs = list(w.warehouses.list())
        running = [wh for wh in whs if getattr(wh, "state", None) == "RUNNING"]
        whs = running if running else whs
        if not whs:
            raise RuntimeError("No SQL warehouse found; set GENIE_WAREHOUSE_ID or start a warehouse")
        warehouse_id = whs[0].id
    title = config["display_name"]
    description = (config.get("description") or "").strip()
    serialized_space = build_serialized_space(config)
    parent_path = os.environ.get("GENIE_PARENT_PATH", "/Genie")
    existing = None
    for space in w.genie.list_spaces():
        if getattr(space, "title", None) == title:
            existing = space
            break
    if existing:
        space_id = existing.space_id
        w.genie.update_space(
            space_id=space_id,
            warehouse_id=warehouse_id,
            serialized_space=serialized_space,
            title=title,
            description=description or None,
        )
        print(f"Updated Genie space: {title} (space_id={space_id})")
    else:
        out = w.genie.create_space(
            warehouse_id=warehouse_id,
            serialized_space=serialized_space,
            title=title,
            description=description or None,
            parent_path=parent_path,
        )
        print(f"Created Genie space: {title} (space_id={out.space_id})")


if __name__ == "__main__":
    main()
