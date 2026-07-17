CREATE TABLE IF NOT EXISTS Projects (
    project_id SERIAL PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ChainageProfile (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES Projects(project_id),
    chainage DECIMAL(10,3),
    gl DECIMAL(10,3),
    fl DECIMAL(10,3),
    fill DECIMAL(10,3) DEFAULT 0,
    cut DECIMAL(10,3) DEFAULT 0
);


CREATE TABLE IF NOT EXISTS SlopeMaster (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES Projects(project_id),
    from_chainage DECIMAL(10,3),
    to_chainage DECIMAL(10,3),
    side_slope DECIMAL(5,2)
);

CREATE TABLE IF NOT EXISTS EarthworkCalculation (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES Projects(project_id),
    chainage DECIMAL(10,3),
    area DECIMAL(12,4),
    volume DECIMAL(12,4),
    type VARCHAR(10)



);

CREATE TABLE IF NOT EXISTS SkippedRows (
    id SERIAL PRIMARY KEY,
    project_id INT REFERENCES Projects(project_id),
    raw_chainage TEXT,
    raw_gl TEXT,
    raw_fl TEXT,
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);