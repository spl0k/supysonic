ALTER TABLE user ADD podcast BOOLEAN DEFAULT false NOT NULL;

CREATE TABLE IF NOT EXISTS podcast_channel (
    id BINARY(16) PRIMARY KEY,
    url VARCHAR(256) UNIQUE NOT NULL,
    title VARCHAR(256),
    description VARCHAR(256),
    cover_art VARCHAR(256),
    original_image_url VARCHAR(256),
    status TINYINT NOT NULL,
    error_message VARCHAR(256),
    created TIMESTAMP NOT NULL,
    last_fetched TIMESTAMP
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS podcast_episode (
    id BINARY(16) PRIMARY KEY,
    stream_url VARCHAR(256) NOT NULL,
    file_path VARCHAR(256),
    channel_id BINARY(16) NOT NULL,
    title VARCHAR(256),
    description VARCHAR(256),
    duration VARCHAR(8),
    status TINYINT NOT NULL,
    publish_date DATETIME,
    error_message VARCHAR(256),
    created DATETIME NOT NULL,
    size INTEGER,
    suffix VARCHAR(8),
    bitrate INTEGER,
    content_type VARCHAR(64),
    cover_art VARCHAR(256),
    genre VARCHAR(16),
    year SMALLINT,
    FOREIGN KEY(channel_id) REFERENCES podcast_channel(id),
    INDEX index_episode_channel_id_fk (channel_id),
    INDEX index_episode_status (status)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
