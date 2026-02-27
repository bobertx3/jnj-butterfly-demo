CREATE OR REFRESH MATERIALIZED VIEW bronze_account
AS
SELECT
  *,
  current_timestamp() AS _ingested_at
FROM read_files(
  '/Volumes/bx4/butterfly/raw_landing/account',
  format => 'csv',
  header => 'true',
  inferSchema => 'true'
);

CREATE OR REFRESH MATERIALIZED VIEW bronze_contact
AS
SELECT
  *,
  current_timestamp() AS _ingested_at
FROM read_files(
  '/Volumes/bx4/butterfly/raw_landing/contact',
  format => 'csv',
  header => 'true',
  inferSchema => 'true'
);

CREATE OR REFRESH MATERIALIZED VIEW bronze_consent
AS
SELECT
  *,
  current_timestamp() AS _ingested_at
FROM read_files(
  '/Volumes/bx4/butterfly/raw_landing/consent',
  format => 'csv',
  header => 'true',
  inferSchema => 'true'
);

CREATE OR REFRESH MATERIALIZED VIEW bronze_product
AS
SELECT
  *,
  current_timestamp() AS _ingested_at
FROM read_files(
  '/Volumes/bx4/butterfly/raw_landing/product',
  format => 'csv',
  header => 'true',
  inferSchema => 'true'
);

CREATE OR REFRESH MATERIALIZED VIEW bronze_alignment
AS
SELECT
  *,
  current_timestamp() AS _ingested_at
FROM read_files(
  '/Volumes/bx4/butterfly/raw_landing/alignment',
  format => 'csv',
  header => 'true',
  inferSchema => 'true'
);

CREATE OR REFRESH MATERIALIZED VIEW bronze_employee
AS
SELECT
  *,
  current_timestamp() AS _ingested_at
FROM read_files(
  '/Volumes/bx4/butterfly/raw_landing/employee',
  format => 'csv',
  header => 'true',
  inferSchema => 'true'
);

CREATE OR REFRESH MATERIALIZED VIEW bronze_transactions
AS
SELECT
  *,
  current_timestamp() AS _ingested_at
FROM read_files(
  '/Volumes/bx4/butterfly/raw_landing/transactions',
  format => 'csv',
  header => 'true',
  inferSchema => 'true'
);

CREATE OR REFRESH MATERIALIZED VIEW bronze_activities
AS
SELECT
  *,
  current_timestamp() AS _ingested_at
FROM read_files(
  '/Volumes/bx4/butterfly/raw_landing/activities',
  format => 'csv',
  header => 'true',
  inferSchema => 'true'
);

CREATE OR REFRESH MATERIALIZED VIEW bronze_opportunities
AS
SELECT
  *,
  current_timestamp() AS _ingested_at
FROM read_files(
  '/Volumes/bx4/butterfly/raw_landing/opportunities',
  format => 'csv',
  header => 'true',
  inferSchema => 'true'
);

CREATE OR REFRESH MATERIALIZED VIEW bronze_cases
AS
SELECT
  *,
  current_timestamp() AS _ingested_at
FROM read_files(
  '/Volumes/bx4/butterfly/raw_landing/cases',
  format => 'csv',
  header => 'true',
  inferSchema => 'true'
);
