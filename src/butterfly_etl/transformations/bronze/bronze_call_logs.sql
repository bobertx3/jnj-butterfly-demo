CREATE OR REFRESH MATERIALIZED VIEW bronze_call_log_files
AS
SELECT
  path AS source_path,
  modificationTime AS source_modified_at,
  length(content) AS source_bytes,
  content AS pdf_binary,
  current_timestamp() AS _ingested_at
FROM read_files(
  '/Volumes/bx4/butterfly/raw_landing/call_logs',
  format => 'binaryFile'
);
