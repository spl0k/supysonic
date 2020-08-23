ALTER TABLE user ADD podcast BOOLEAN DEFAULT false NOT NULL;

CREATE TABLE IF NOT EXISTS podcast_channel (
    id UUID PRIMARY KEY,
    url VARCHAR(256) NOT NULL,
    title VARCHAR(256),
    description VARCHAR(256),
    cover_art VARCHAR(256),
    original_image_url VARCHAR(256),
    status TINYINT NOT NULL,
    error_message VARCHAR(256),
    created TIMESTAMP NOT NULL,
    last_fetched TIMESTAMP
);
CREATE INDEX IF NOT EXISTS index_channel_status ON podcast_channel(status);

CREATE TABLE IF NOT EXISTS podcast_episode (
    id UUID PRIMARY KEY,
    stream_url VARCHAR(256) NOT NULL,
    file_path VARCHAR(256),
    channel_id UUID NOT NULL REFERENCES podcast_channel(id),
    title VARCHAR(256),
    description VARCHAR(256),
    duration VARCHAR(8),
    status TINYINT NOT NULL,
    publish_date TIMESTAMP,
    error_message VARCHAR(256),
    created TIMESTAMP NOT NULL,
    size INTEGER,
    suffix VARCHAR(8),
    bitrate INTEGER,
    content_type VARCHAR(64),
    cover_art VARCHAR(256),
    genre VARCHAR(16),
    year SMALLINT
);
CREATE INDEX IF NOT EXISTS index_episode_channel_id_fk ON podcast_episode(channel_id);
CREATE INDEX IF NOT EXISTS index_episode_status ON podcast_episode(status);
