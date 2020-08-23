ALTER TABLE user ADD podcast BOOLEAN DEFAULT false NOT NULL;

CREATE TABLE IF NOT EXISTS podcast_channel (
    id CHAR(36) PRIMARY KEY,
    url VARCHAR(256) UNIQUE NOT NULL,
    title VARCHAR(256),
    description VARCHAR(256),
    cover_art VARCHAR(256),
    original_image_url VARCHAR(256),
    status TINYINT NOT NULL,
    error_message VARCHAR(256),
    created DATETIME NOT NULL,
    last_fetched DATETIME
);
CREATE INDEX IF NOT EXISTS index_channel_status_id_fk ON podcast_channel(status);

CREATE TABLE IF NOT EXISTS podcast_episode (
    id CHAR(36) PRIMARY KEY,
    stream_url VARCHAR(256) NOT NULL,
    file_path VARCHAR(256),
    channel_id CHAR(36) NOT NULL REFERENCES podcast_channel,
    title VARCHAR(256),
    description VARCHAR(256),
    duration VARCHAR(8),
    status TINYINT NOT NULL,
    publish_date DATETIME,
    error_message VARCHAR(256),
    created DATETIME NOT NULL,
    size INT,
    suffix VARCHAR(8),
    bitrate INT,
    content_type VARCHAR(64),
    cover_art VARCHAR(256),
    genre VARCHAR(16),
    year SMALLINT
);
CREATE INDEX IF NOT EXISTS index_episode_channel_id_fk ON podcast_episode(channel_id);
CREATE INDEX IF NOT EXISTS index_episode_status ON podcast_episode(status);
