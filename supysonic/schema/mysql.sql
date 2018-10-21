CREATE TABLE IF NOT EXISTS folder (
    id BINARY(16) PRIMARY KEY,
    root BOOLEAN NOT NULL,
    name VARCHAR(256) NOT NULL,
    path VARCHAR(4096) NOT NULL,
    path_hash BINARY(20) UNIQUE NOT NULL,
    created DATETIME NOT NULL,
    cover_art VARCHAR(256),
    last_scan INTEGER NOT NULL,
    parent_id BINARY(16) REFERENCES folder
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS artist (
    id BINARY(16) PRIMARY KEY,
    name VARCHAR(256) NOT NULL
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS album (
    id BINARY(16) PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    artist_id BINARY(16) NOT NULL REFERENCES artist
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS track (
    id BINARY(16) PRIMARY KEY,
    disc INTEGER NOT NULL,
    number INTEGER NOT NULL,
    title VARCHAR(256) NOT NULL,
    year INTEGER,
    genre VARCHAR(256),
    duration INTEGER NOT NULL,
    has_art BOOLEAN NOT NULL DEFAULT false,
    album_id BINARY(16) NOT NULL REFERENCES album,
    artist_id BINARY(16) NOT NULL REFERENCES artist,
    bitrate INTEGER NOT NULL,
    path VARCHAR(4096) NOT NULL,
    path_hash BINARY(20) UNIQUE NOT NULL,
    content_type VARCHAR(32) NOT NULL,
    created DATETIME NOT NULL,
    last_modification INTEGER NOT NULL,
    play_count INTEGER NOT NULL,
    last_play DATETIME,
    root_folder_id BINARY(16) NOT NULL REFERENCES folder,
    folder_id BINARY(16) NOT NULL REFERENCES folder
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user (
    id BINARY(16) PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    mail VARCHAR(256),
    password CHAR(40) NOT NULL,
    salt CHAR(6) NOT NULL,
    admin BOOLEAN NOT NULL,
    lastfm_session CHAR(32),
    lastfm_status BOOLEAN NOT NULL,
    last_play_id BINARY(16) REFERENCES track,
    last_play_date DATETIME
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS client_prefs (
    user_id BINARY(16) NOT NULL,
    client_name VARCHAR(32) NOT NULL,
    format VARCHAR(8),
    bitrate INTEGER,
    PRIMARY KEY (user_id, client_name)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS starred_folder (
    user_id BINARY(16) NOT NULL REFERENCES user,
    starred_id BINARY(16) NOT NULL REFERENCES folder,
    date DATETIME NOT NULL,
    PRIMARY KEY (user_id, starred_id)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS starred_artist (
    user_id BINARY(16) NOT NULL REFERENCES user,
    starred_id BINARY(16) NOT NULL REFERENCES artist,
    date DATETIME NOT NULL,
    PRIMARY KEY (user_id, starred_id)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS starred_album (
    user_id BINARY(16) NOT NULL REFERENCES user,
    starred_id BINARY(16) NOT NULL REFERENCES album,
    date DATETIME NOT NULL,
    PRIMARY KEY (user_id, starred_id)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS starred_track (
    user_id BINARY(16) NOT NULL REFERENCES user,
    starred_id BINARY(16) NOT NULL REFERENCES track,
    date DATETIME NOT NULL,
    PRIMARY KEY (user_id, starred_id)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rating_folder (
    user_id BINARY(16) NOT NULL REFERENCES user,
    rated_id BINARY(16) NOT NULL REFERENCES folder,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    PRIMARY KEY (user_id, rated_id)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rating_track (
    user_id BINARY(16) NOT NULL REFERENCES user,
    rated_id BINARY(16) NOT NULL REFERENCES track,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    PRIMARY KEY (user_id, rated_id)
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_message (
    id BINARY(16) PRIMARY KEY,
    user_id BINARY(16) NOT NULL REFERENCES user,
    time INTEGER NOT NULL,
    message VARCHAR(512) NOT NULL
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS playlist (
    id BINARY(16) PRIMARY KEY,
    user_id BINARY(16) NOT NULL REFERENCES user,
    name VARCHAR(256) NOT NULL,
    comment VARCHAR(256),
    public BOOLEAN NOT NULL,
    created DATETIME NOT NULL,
    tracks TEXT
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE meta (
    `key` VARCHAR(32) PRIMARY KEY,
    value VARCHAR(256) NOT NULL
) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

