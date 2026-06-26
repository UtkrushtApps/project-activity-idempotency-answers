CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE tenants (
    id uuid PRIMARY KEY,
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    email text NOT NULL,
    display_name text NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, email)
);

CREATE TABLE projects (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    name text NOT NULL,
    status text NOT NULL CHECK (status IN ('active', 'archived')),
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE project_members (
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role text NOT NULL CHECK (role IN ('owner', 'maintainer', 'member', 'viewer')),
    unread_count integer NOT NULL DEFAULT 0 CHECK (unread_count >= 0),
    joined_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, user_id)
);

CREATE TABLE project_activity_totals (
    project_id uuid PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    total_events bigint NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE activities (
    id bigserial PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenants(id),
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    actor_user_id uuid NOT NULL REFERENCES users(id),
    event_type text NOT NULL,
    message text NOT NULL,
    client_event_id text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE activity_receipts (
    activity_id bigint NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    delivered_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (activity_id, user_id)
);

CREATE INDEX idx_projects_tenant_status ON projects (tenant_id, status);
CREATE INDEX idx_project_members_user ON project_members (user_id);
CREATE INDEX idx_activities_project_created ON activities (project_id, created_at DESC);

-- Database-level idempotency guarantee for client supplied logical event ids.
-- NULL client_event_id values are intentionally excluded so legacy callers that do
-- not provide an idempotency key keep their previous append-only behavior.
CREATE UNIQUE INDEX ux_activities_idempotency_key
ON activities (tenant_id, project_id, actor_user_id, client_event_id)
WHERE client_event_id IS NOT NULL;

INSERT INTO tenants (id, name) VALUES
('00000000-0000-0000-0000-000000000001', 'Northstar Product Group'),
('00000000-0000-0000-0000-000000000002', 'Acme Delivery Labs');

INSERT INTO users (id, tenant_id, email, display_name) VALUES
('00000000-0000-0000-0000-000000000101', '00000000-0000-0000-0000-000000000001', 'maya@northstar.example', 'Maya Rao'),
('00000000-0000-0000-0000-000000000102', '00000000-0000-0000-0000-000000000001', 'eli@northstar.example', 'Eli Morgan'),
('00000000-0000-0000-0000-000000000103', '00000000-0000-0000-0000-000000000001', 'sofia@northstar.example', 'Sofia Chen'),
('00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000002', 'ravi@acme.example', 'Ravi Kapoor');

INSERT INTO projects (id, tenant_id, name, status) VALUES
('11111111-1111-1111-1111-111111111111', '00000000-0000-0000-0000-000000000001', 'Phoenix Mobile Launch', 'active'),
('22222222-2222-2222-2222-222222222222', '00000000-0000-0000-0000-000000000001', 'Atlas Platform Migration', 'active'),
('33333333-3333-3333-3333-333333333333', '00000000-0000-0000-0000-000000000002', 'Acme Client Rollout', 'active');

INSERT INTO project_members (project_id, user_id, role, unread_count) VALUES
('11111111-1111-1111-1111-111111111111', '00000000-0000-0000-0000-000000000101', 'owner', 0),
('11111111-1111-1111-1111-111111111111', '00000000-0000-0000-0000-000000000102', 'maintainer', 7),
('11111111-1111-1111-1111-111111111111', '00000000-0000-0000-0000-000000000103', 'member', 4),
('22222222-2222-2222-2222-222222222222', '00000000-0000-0000-0000-000000000101', 'owner', 1),
('22222222-2222-2222-2222-222222222222', '00000000-0000-0000-0000-000000000102', 'member', 2),
('33333333-3333-3333-3333-333333333333', '00000000-0000-0000-0000-000000000201', 'owner', 0);

INSERT INTO project_activity_totals (project_id, total_events) VALUES
('11111111-1111-1111-1111-111111111111', 0),
('22222222-2222-2222-2222-222222222222', 0),
('33333333-3333-3333-3333-333333333333', 0);

INSERT INTO activities (tenant_id, project_id, actor_user_id, event_type, message, client_event_id, metadata, created_at)
SELECT
'00000000-0000-0000-0000-000000000001'::uuid,
'11111111-1111-1111-1111-111111111111'::uuid,
CASE WHEN g % 3 = 0 THEN '00000000-0000-0000-0000-000000000101'::uuid WHEN g % 3 = 1 THEN '00000000-0000-0000-0000-000000000102'::uuid ELSE '00000000-0000-0000-0000-000000000103'::uuid END,
CASE WHEN g % 4 = 0 THEN 'comment.created' WHEN g % 4 = 1 THEN 'task.updated' WHEN g % 4 = 2 THEN 'file.uploaded' ELSE 'status.changed' END,
'Historical activity event #' || g,
'seed-phoenix-' || g,
jsonb_build_object('seed', true, 'sequence', g),
now() - (g || ' minutes')::interval
FROM generate_series(1, 300) AS g;

INSERT INTO activities (tenant_id, project_id, actor_user_id, event_type, message, client_event_id, metadata, created_at)
SELECT
'00000000-0000-0000-0000-000000000001'::uuid,
'22222222-2222-2222-2222-222222222222'::uuid,
'00000000-0000-0000-0000-000000000101'::uuid,
'planning.note',
'Atlas planning note #' || g,
'seed-atlas-' || g,
jsonb_build_object('seed', true, 'sequence', g),
now() - (g || ' minutes')::interval
FROM generate_series(1, 80) AS g;

UPDATE project_activity_totals pat
SET total_events = sub.cnt, updated_at = now()
FROM (
    SELECT project_id, count(*) AS cnt FROM activities GROUP BY project_id
) sub
WHERE pat.project_id = sub.project_id;

INSERT INTO activity_receipts (activity_id, user_id)
SELECT a.id, pm.user_id
FROM activities a
JOIN project_members pm ON pm.project_id = a.project_id AND pm.user_id <> a.actor_user_id
WHERE a.project_id IN ('11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222')
AND a.id % 20 = 0;
