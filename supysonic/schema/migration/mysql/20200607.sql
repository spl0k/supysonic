CREATE TABLE IF NOT EXISTS radio_station (
    id BINARY(16) PRIMARY KEY,
    stream_url VARCHAR(256) NOT NULL,
    name VARCHAR(256) NOT NULL,
    homepage_url VARCHAR(256),
    created DATETIME NOT NULL
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

