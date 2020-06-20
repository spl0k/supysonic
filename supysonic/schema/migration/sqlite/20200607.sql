CREATE TABLE IF NOT EXISTS radio_station (
    id CHAR(36) PRIMARY KEY,
    stream_url VARCHAR(256) NOT NULL,
    name VARCHAR(256) NOT NULL,
    homepage_url VARCHAR(256),
    created DATETIME NOT NULL
);

