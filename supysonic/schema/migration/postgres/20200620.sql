ALTER TABLE user ADD podcast BOOLEAN DEFAULT false NOT NULL;

CREATE TABLE IF NOT EXISTS podcast_channel (
    id UUID PRIMARY KEY,
    url VARCHAR(256) NOT NULL,
    title VARCHAR(256),
    description VARCHAR(256),
    cover_art VARCHAR(256),
    original_image_url VARCHAR(256),
    status VARCHAR(16),
    error_message VARCHAR(256),
    created TIMESTAMP NOT NULL,
    last_fetched TIMESTAMP
);

CREATE TABLE IF NOT EXISTS podcast_episode (
    id UUID PRIMARY KEY,
    stream_url VARCHAR(256),
    file_path VARCHAR(256),
    channel_id CHAR(36) NOT NULL REFERENCES podcast_channel(id),
    title VARCHAR(256),
    description VARCHAR(256),
    duration VARCHAR(8),
    status VARCHAR(16) NOT NULL,
    publish_date TIMESTAMP,
    created TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS index_episode_channel_id_fk ON podcast_channel(id);
