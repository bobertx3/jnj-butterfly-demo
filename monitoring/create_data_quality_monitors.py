"""Create or refresh Databricks Data Quality monitors for Butterfly tables."""

from __future__ import annotations

import argparse
import json
import time
from typing import Any, Dict, Iterable, List

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import DatabricksError
from databricks.sdk.service.dataquality import (
    DataProfilingConfig,
    Monitor,
    Refresh,
    SnapshotConfig,
)


DEFAULT_TABLES = [
    "bx4.butterfly.silver_account",
    "bx4.butterfly.silver_contact",
    "bx4.butterfly.silver_transactions",
    "bx4.butterfly.gold_customer_360",
    "bx4.butterfly.gold_region_performance",
]


def to_dict(value: Any) -> Any:
    if hasattr(value, "as_dict"):
        return value.as_dict()
    if isinstance(value, list):
        return [to_dict(v) for v in value]
    if isinstance(value, dict):
        return {k: to_dict(v) for k, v in value.items()}
    return value


def iter_metric_tables(monitor_dict: Dict[str, Any]) -> Iterable[str]:
    stack: List[Any] = [monitor_dict]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                if isinstance(value, str) and "table" in key.lower() and "." in value:
                    yield value
                else:
                    stack.append(value)
        elif isinstance(current, list):
            stack.extend(current)


def delete_monitor_for_table(w: WorkspaceClient, table_name: str) -> bool:
    """Delete the data quality monitor for a table if it exists. Returns True if deleted."""
    try:
        table = w.tables.get(full_name=table_name)
        w.data_quality.delete_monitor(object_type="table", object_id=table.table_id)
        print(f"[DQ] deleted monitor for {table_name}")
        return True
    except DatabricksError as e:
        if "NOT_FOUND" in str(e) or "does not exist" in str(e).lower():
            print(f"[DQ] no monitor to delete for {table_name}")
            return False
        raise


def create_or_refresh_monitor(
    w: WorkspaceClient,
    table_name: str,
    output_schema_name: str,
    assets_root: str,
    wait_refresh: bool = False,
) -> Dict[str, Any]:
    table = w.tables.get(full_name=table_name)
    schema_info = w.schemas.get(full_name=output_schema_name)

    try:
        monitor_info = w.data_quality.get_monitor(object_type="table", object_id=table.table_id)
    except DatabricksError:
        monitor_info = w.data_quality.create_monitor(
            monitor=Monitor(
                object_type="table",
                object_id=table.table_id,
                data_profiling_config=DataProfilingConfig(
                    output_schema_id=schema_info.schema_id,
                    assets_dir=f"{assets_root}/{table_name.replace('.', '_')}",
                    snapshot=SnapshotConfig(),
                    slicing_exprs=["region"] if table_name.endswith("gold_customer_360") else None,
                ),
            )
        )
        # No wait: API requires monitor to be ready before create_refresh; if still PENDING we skip refresh this run.

    try:
        refresh_info = w.data_quality.create_refresh(
            object_type="table",
            object_id=table.table_id,
            refresh=Refresh(object_type="table", object_id=table.table_id),
        )
    except DatabricksError as e:
        err_msg = str(e).lower()
        if "cannot find monitor" in err_msg or "resourcedoesnotexist" in err_msg:
            print(f"[DQ] monitor missing or orphaned for {table_name}, recreating...")
            try:
                w.data_quality.delete_monitor(object_type="table", object_id=table.table_id)
            except DatabricksError:
                pass
            monitor_info = w.data_quality.create_monitor(
                monitor=Monitor(
                    object_type="table",
                    object_id=table.table_id,
                    data_profiling_config=DataProfilingConfig(
                        output_schema_id=schema_info.schema_id,
                        assets_dir=f"{assets_root}/{table_name.replace('.', '_')}",
                        snapshot=SnapshotConfig(),
                        slicing_exprs=["region"] if table_name.endswith("gold_customer_360") else None,
                    ),
                )
            )
            try:
                refresh_info = w.data_quality.create_refresh(
                    object_type="table",
                    object_id=table.table_id,
                    refresh=Refresh(object_type="table", object_id=table.table_id),
                )
            except DatabricksError as re:
                if "pending" in str(re).lower():
                    print(f"[DQ] monitor for {table_name} still provisioning; refresh on next run.")
                    refresh_info = None
                else:
                    raise
        elif "pending" in err_msg:
            print(f"[DQ] monitor for {table_name} still provisioning; refresh on next run.")
            refresh_info = None
        else:
            raise

    refresh_id = getattr(refresh_info, "refresh_id", None) if refresh_info else None
    if refresh_id is not None and wait_refresh:
        for _ in range(40):
            status = w.data_quality.get_refresh(
                object_type="table",
                object_id=table.table_id,
                refresh_id=refresh_id,
            )
            state = str(getattr(status, "state", ""))
            if "SUCCESS" in state or "FAILED" in state or "TIMEOUT" in state:
                break
            time.sleep(15)

    monitor_dict = to_dict(monitor_info)
    return {
        "table_name": table_name,
        "object_id": table.table_id,
        "refresh_id": refresh_id,
        "monitor": monitor_dict,
        "metric_tables": sorted(set(iter_metric_tables(monitor_dict))),
    }


def ensure_dq_reporting_views(spark: Any, schema_full: str) -> None:
    """Create or replace dq_rule_results, dq_monitor_assets, dq_summary so the DQ dashboard has data."""
    catalog, schema = schema_full.split(".", 1) if "." in schema_full else ("bx4", schema_full)
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")

    spark.sql(f"""
        CREATE OR REPLACE VIEW {catalog}.{schema}.dq_rule_results AS
        WITH checks AS (
          SELECT
            'silver_account' AS table_name,
            'null_account_id' AS rule_name,
            SUM(CASE WHEN account_id IS NULL THEN 1 ELSE 0 END) AS failed_records,
            COUNT(*) AS total_records
          FROM {catalog}.{schema}.silver_account
          UNION ALL
          SELECT
            'silver_contact' AS table_name,
            'null_email' AS rule_name,
            SUM(CASE WHEN email IS NULL THEN 1 ELSE 0 END) AS failed_records,
            COUNT(*) AS total_records
          FROM {catalog}.{schema}.silver_contact
          UNION ALL
          SELECT
            'silver_transactions' AS table_name,
            'negative_net_sales' AS rule_name,
            SUM(CASE WHEN net_sales < 0 THEN 1 ELSE 0 END) AS failed_records,
            COUNT(*) AS total_records
          FROM {catalog}.{schema}.silver_transactions
          UNION ALL
          SELECT
            'gold_customer_360' AS table_name,
            'null_region' AS rule_name,
            SUM(CASE WHEN region IS NULL THEN 1 ELSE 0 END) AS failed_records,
            COUNT(*) AS total_records
          FROM {catalog}.{schema}.gold_customer_360
          UNION ALL
          SELECT
            'gold_customer_360' AS table_name,
            'negative_open_pipeline' AS rule_name,
            SUM(CASE WHEN open_pipeline_amount < 0 THEN 1 ELSE 0 END) AS failed_records,
            COUNT(*) AS total_records
          FROM {catalog}.{schema}.gold_customer_360
        )
        SELECT
          table_name,
          rule_name,
          failed_records,
          total_records,
          CASE WHEN total_records = 0 THEN 0 ELSE failed_records / total_records END AS failure_ratio,
          current_timestamp() AS measured_at
        FROM checks
    """)
    spark.sql(f"""
        CREATE OR REPLACE VIEW {catalog}.{schema}.dq_monitor_assets AS
        SELECT
          table_name,
          object_id,
          refresh_id,
          metric_tables,
          monitor_json,
          from_unixtime(updated_at) AS updated_at
        FROM {catalog}.{schema}.dq_monitor_registry
    """)
    spark.sql(f"""
        CREATE OR REPLACE VIEW {catalog}.{schema}.dq_summary AS
        SELECT
          table_name,
          COUNT(*) AS rules_count,
          SUM(failed_records) AS failed_records,
          SUM(total_records) AS total_records,
          AVG(1 - failure_ratio) AS avg_pass_rate,
          MAX(measured_at) AS measured_at
        FROM {catalog}.{schema}.dq_rule_results
        GROUP BY table_name
    """)
    print(f"[DQ] reporting views ensured in {catalog}.{schema} (dq_rule_results, dq_monitor_assets, dq_summary)")


def maybe_persist_registry(rows: List[Dict[str, Any]], schema_full: str = "bx4.butterfly") -> None:
    try:
        from pyspark.sql import SparkSession
    except Exception:
        return

    spark = SparkSession.builder.getOrCreate()
    catalog, schema = schema_full.split(".", 1) if "." in schema_full else ("bx4", schema_full)
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
    payload = [
        {
            "table_name": r["table_name"],
            "object_id": r["object_id"],
            "refresh_id": str(r["refresh_id"]) if r["refresh_id"] is not None else None,
            "metric_tables": ",".join(r["metric_tables"]),
            "monitor_json": json.dumps(r["monitor"]),
            "updated_at": int(time.time()),
        }
        for r in rows
    ]
    spark.createDataFrame(payload).write.mode("overwrite").saveAsTable(f"{catalog}.{schema}.dq_monitor_registry")


def resolve_assets_root(w: WorkspaceClient, assets_root: str) -> str:
    """Replace ${workspace.current_user.userName} with actual username so DQ API can create paths."""
    placeholder = "${workspace.current_user.userName}"
    if placeholder not in assets_root:
        return assets_root
    me = w.current_user.me()
    username = getattr(me, "user_name", None) or getattr(me, "userName", None) or "unknown"
    return assets_root.replace(placeholder, username)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Databricks Data Quality monitors.")
    parser.add_argument(
        "--tables",
        nargs="*",
        default=DEFAULT_TABLES,
        help="Fully-qualified UC table names to monitor.",
    )
    parser.add_argument(
        "--output-schema",
        default="bx4.butterfly",
        help="Schema where monitor metric tables are materialized.",
    )
    parser.add_argument(
        "--assets-root",
        default="/Workspace/Users/${workspace.current_user.userName}/butterfly_dq_assets",
        help="Workspace directory used for generated monitor assets.",
    )
    parser.add_argument(
        "--delete-first",
        action="store_true",
        help="Delete existing monitors for the given tables before creating/refreshing.",
    )
    parser.add_argument(
        "--no-wait-refresh",
        action="store_true",
        help="Trigger refresh but do not wait for completion (keeps job task short).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    w = WorkspaceClient()
    assets_root = resolve_assets_root(w, args.assets_root)

    if args.delete_first:
        for table_name in args.tables:
            delete_monitor_for_table(w, table_name)

    results = []
    for table_name in args.tables:
        print(f"[DQ] ensuring monitor for {table_name}")
        result = create_or_refresh_monitor(
            w=w,
            table_name=table_name,
            output_schema_name=args.output_schema,
            assets_root=assets_root,
            wait_refresh=not args.no_wait_refresh,
        )
        print(f"[DQ] refresh queued/completed refresh_id={result['refresh_id']}")
        results.append(result)

    maybe_persist_registry(results, args.output_schema)
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        ensure_dq_reporting_views(spark, args.output_schema)
    except Exception as e:
        print(f"[DQ] could not ensure reporting views (dashboard may show no data): {e}")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
