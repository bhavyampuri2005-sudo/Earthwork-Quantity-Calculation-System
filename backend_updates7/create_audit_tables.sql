
CREATE TABLE ProjectFiles (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(project_id),
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'uploaded',
    chainage_start NUMERIC(10,3),
    chainage_step NUMERIC(10,3),
    rows_extracted INTEGER,
    error_message TEXT
);

-- actor has no real user system to reference yet (no auth built) - it's
-- a free-text placeholder for now. Once login/RBAC exists, pass the
-- real username/user_id through log_action() instead.
CREATE TABLE AuditLog (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(project_id),
    action VARCHAR(100) NOT NULL,
    details TEXT,
    actor VARCHAR(100) DEFAULT 'unknown (no auth system yet)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Verify:
-- SELECT * FROM projectfiles;
-- SELECT * FROM auditlog;
