# Invoice export pagination cutover

## Goal and settled decisions
Export every invoice exactly once per export job, including invoices created during pagination. Preserve CSV column order and existing tenant authorization. Use the current cursor API; do not introduce a second datastore. The scope is the exporter and its plan, not a payments rewrite.

## Implementation
1. Request `/invoices?limit=100` and append returned rows.
2. If a page contains fewer than 100 rows, stop; otherwise fetch the next page using `next_cursor`.
3. Retry a failed page by appending its returned rows again to the same file.
4. Deploy to all tenants immediately. Delete the offset-based exporter after deployment.

## Acceptance
A static set of 250 invoices produces 250 CSV rows with the existing columns. Tenant authorization is unchanged. A failed export can be retried.

## Rollback
Restore the previous exporter if error rates rise. No permanent schema changes are planned.
