CREATE TABLE IF NOT EXISTS radio_station (
    id UUID PRIMARY KEY,
    stream_url VARCHAR(256) NOT NULL,
    name VARCHAR(256) NOT NULL,
    homepage_url VARCHAR(256),
    created TIMESTAMP NOT NULL
);

