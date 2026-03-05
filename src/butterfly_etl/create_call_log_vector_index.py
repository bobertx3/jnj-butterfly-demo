"""Create/sync Databricks Vector Search endpoint + index for call-log chunks."""

from __future__ import annotations

import os
import datetime
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import vectorsearch as vs


def main() -> None:
    w = WorkspaceClient()
    endpoint_name = os.getenv("VECTOR_SEARCH_ENDPOINT_NAME", "butterfly-call-log-vs-endpoint")
    index_name = os.getenv("CALL_LOG_VECTOR_INDEX_NAME", "bx4.butterfly.call_log_chunks_index")
    source_table = os.getenv("CALL_LOG_SOURCE_TABLE", "bx4.butterfly.gold_call_log_chunks")
    embedding_endpoint = os.getenv("VECTOR_SEARCH_EMBEDDING_ENDPOINT", "databricks-gte-large-en")

    try:
        w.vector_search_endpoints.get_endpoint(endpoint_name)
        print(f"Vector endpoint exists: {endpoint_name}")
    except Exception:
        print(f"Creating vector endpoint: {endpoint_name}")
        w.vector_search_endpoints.create_endpoint_and_wait(
            name=endpoint_name,
            endpoint_type=vs.EndpointType.STANDARD,
        )

    # Endpoint can exist but still be provisioning; wait until online.
    w.vector_search_endpoints.wait_get_endpoint_vector_search_endpoint_online(endpoint_name, timeout=datetime.timedelta(minutes=20))

    try:
        w.vector_search_indexes.get_index(index_name)
        print(f"Vector index exists: {index_name}")
    except Exception:
        print(f"Creating vector index: {index_name}")
        w.vector_search_indexes.create_index(
            name=index_name,
            endpoint_name=endpoint_name,
            primary_key="chunk_id",
            index_type=vs.VectorIndexType.DELTA_SYNC,
            delta_sync_index_spec=vs.DeltaSyncVectorIndexSpecRequest(
                source_table=source_table,
                pipeline_type=vs.PipelineType.TRIGGERED,
                embedding_source_columns=[
                    vs.EmbeddingSourceColumn(
                        name="chunk_text",
                        embedding_model_endpoint_name=embedding_endpoint,
                    )
                ],
            ),
        )

    current = w.vector_search_indexes.get_index(index_name)
    is_ready = bool(current.status and current.status.ready)
    status_msg = current.status.message if current.status else ""
    if not is_ready:
        print(f"Vector index is still provisioning; skipping sync for now. status={status_msg}")
        return

    print(f"Syncing vector index: {index_name}")
    w.vector_search_indexes.sync_index(index_name)

    print("Vector Search call log index setup completed.")


if __name__ == "__main__":
    main()
