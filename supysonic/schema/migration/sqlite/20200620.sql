ALTER TABLE user ADD podcast BOOLEAN DEFAULT false NOT NULL;

CREATE TABLE IF NOT EXISTS podcast_channel (
    id CHAR(36) PRIMARY KEY,
    url VARCHAR(256) NOT NULL,
    title VARCHAR(256),
    description VARCHAR(256),
    cover_art VARCHAR(256),
    original_image_url VARCHAR(256),
    status VARCHAR(16),
    error_message VARCHAR(256),
    created DATETIME NOT NULL,
    last_fetched DATETIME
);

CREATE TABLE IF NOT EXISTS podcast_episode (
    id CHAR(36) PRIMARY KEY,
    stream_url VARCHAR(256),
    file_path VARCHAR(256),
    channel_id CHAR(36) NOT NULL,
    title VARCHAR(256),
    description VARCHAR(256),
    duration VARCHAR(8),
    status VARCHAR(16) NOT NULL,
    publish_date DATETIME,
    created DATETIME NOT NULL
);
CREATE INDEX IF NOT EXISTS index_episode_channel_id_fk ON podcast_channel(id);
