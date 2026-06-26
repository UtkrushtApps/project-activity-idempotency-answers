# Solution Steps

1. Add a database-level uniqueness guarantee for logical activity events. Create a partial unique index on activities using tenant_id, project_id, actor_user_id, and client_event_id, excluding NULL client_event_id values so callers without an idempotency key keep the previous append behavior.

2. Keep the API contract unchanged: accept client_event_id in the request body and Idempotency-Key in the header, and continue storing the body client_event_id first with the header as a fallback.

3. Replace the plain INSERT with an atomic PostgreSQL upsert. Use INSERT ... ON CONFLICT against the partial unique index and return the activity row in both the insert and retry/conflict paths.

4. Return an inserted flag from the upsert using PostgreSQL system column behavior, so the service can distinguish the first successful durable insert from a retry that found the existing row.

5. Move unread-counter and project-total side effects into the same transaction as the activity insert/upsert, and execute them only when the upsert reports that a new activity row was inserted.

6. Commit once after the upsert and any first-insert side effects. This prevents the old failure mode where the activity insert could commit separately from side effects, and it ensures concurrent retries wait on the same database uniqueness guarantee.

7. Leave feed listing, unread listing, request context extraction, access checks, response schemas, and route shapes unchanged so existing clients continue to receive the same response structure.

8. Run the included tests or exercise the endpoint twice with the same client_event_id/Idempotency-Key and verify that activities contains one row and unread_count increases only once.

