CREATE OR REFRESH MATERIALIZED VIEW silver_call_log_parsed
AS
SELECT
  source_path,
  source_modified_at,
  source_bytes,
  CAST(ai_parse_document(pdf_binary, 'text') AS STRING) AS transcript_text,
  _ingested_at
FROM bronze_call_log_files;

CREATE OR REFRESH MATERIALIZED VIEW gold_call_log_chunks (
  CONSTRAINT chunk_id_not_null EXPECT (chunk_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT chunk_text_not_null EXPECT (chunk_text IS NOT NULL AND length(trim(chunk_text)) > 0) ON VIOLATION DROP ROW
)
AS
WITH parsed AS (
  SELECT
    source_path,
    regexp_extract(source_path, '([^/]+)\\.pdf$', 1) AS document_name,
    regexp_extract(source_path, '([A-Za-z]+_[A-Za-z]+)', 1) AS customer_slug,
    transcript_text
  FROM silver_call_log_parsed
),
chunks AS (
  SELECT
    source_path,
    document_name,
    customer_slug,
    pos AS chunk_index,
    trim(chunk) AS chunk_text
  FROM parsed
  LATERAL VIEW posexplode(split(coalesce(transcript_text, ''), '\n\n')) exploded AS pos, chunk
)
SELECT
  concat(document_name, '_', lpad(cast(chunk_index AS STRING), 4, '0')) AS chunk_id,
  source_path,
  document_name,
  customer_slug,
  chunk_index,
  chunk_text,
  current_timestamp() AS _updated_at
FROM chunks
WHERE length(chunk_text) >= 80;
