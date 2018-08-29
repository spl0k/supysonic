CREATE TABLE IF NOT EXISTS folder (
    id UUID PRIMARY KEY,
    root BOOLEAN NOT NULL,
    name CITEXT NOT NULL,
    path VARCHAR(4096) NOT NULL,
    path_hash BYTEA UNIQUE NOT NULL,
    created TIMESTAMP NOT NULL,
    cover_art VARCHAR(256),
    last_scan INTEGER NOT NULL,
    parent_id UUID REFERENCES folder
);

CREATE TABLE IF NOT EXISTS artist (
    id UUID PRIMARY KEY,
    name CITEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS album (
    id UUID PRIMARY KEY,
    name CITEXT NOT NULL,
    artist_id UUID NOT NULL REFERENCES artist
);

CREATE TABLE IF NOT EXISTS track (
    id UUID PRIMARY KEY,
    disc INTEGER NOT NULL,
    number INTEGER NOT NULL,
    title CITEXT NOT NULL,
    year INTEGER,
    genre VARCHAR(256),
    duration INTEGER NOT NULL,
    album_id UUID NOT NULL REFERENCES album,
    artist_id UUID NOT NULL REFERENCES artist,
    bitrate INTEGER NOT NULL,
    path VARCHAR(4096) NOT NULL,
    path_hash BYTEA UNIQUE NOT NULL,
    content_type VARCHAR(32) NOT NULL,
    created TIMESTAMP NOT NULL,
    last_modification INTEGER NOT NULL,
    play_count INTEGER NOT NULL,
    last_play TIMESTAMP,
    root_folder_id UUID NOT NULL REFERENCES folder,
    folder_id UUID NOT NULL REFERENCES folder
);

CREATE TABLE IF NOT EXISTS "user" (
    id UUID PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    mail VARCHAR(256),
    password CHAR(40) NOT NULL,
    salt CHAR(6) NOT NULL,
    admin BOOLEAN NOT NULL,
    lastfm_session CHAR(32),
    lastfm_status BOOLEAN NOT NULL,
    last_play_id UUID REFERENCES track,
    last_play_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS client_prefs (
    user_id UUID NOT NULL,
    client_name VARCHAR(32) NOT NULL,
    format VARCHAR(8),
    bitrate INTEGER,
    PRIMARY KEY (user_id, client_name)
);

CREATE TABLE IF NOT EXISTS starred_folder (
    user_id UUID NOT NULL REFERENCES "user",
    starred_id UUID NOT NULL REFERENCES folder,
    date TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, starred_id)
);

CREATE TABLE IF NOT EXISTS starred_artist (
    user_id UUID NOT NULL REFERENCES "user",
    starred_id UUID NOT NULL REFERENCES artist,
    date TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, starred_id)
);

CREATE TABLE IF NOT EXISTS starred_album (
    user_id UUID NOT NULL REFERENCES "user",
    starred_id UUID NOT NULL REFERENCES album,
    date TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, starred_id)
);

CREATE TABLE IF NOT EXISTS starred_track (
    user_id UUID NOT NULL REFERENCES "user",
    starred_id UUID NOT NULL REFERENCES track,
    date TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, starred_id)
);

CREATE TABLE IF NOT EXISTS rating_folder (
    user_id UUID NOT NULL REFERENCES "user",
    rated_id UUID NOT NULL REFERENCES folder,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    PRIMARY KEY (user_id, rated_id)
);

CREATE TABLE IF NOT EXISTS rating_track (
    user_id UUID NOT NULL REFERENCES "user",
    rated_id UUID NOT NULL REFERENCES track,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    PRIMARY KEY (user_id, rated_id)
);

CREATE TABLE IF NOT EXISTS chat_message (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES "user",
    time INTEGER NOT NULL,
    message VARCHAR(512) NOT NULL
);

CREATE TABLE IF NOT EXISTS playlist (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES "user",
    name VARCHAR(256) NOT NULL,
    comment VARCHAR(256),
    public BOOLEAN NOT NULL,
    created TIMESTAMP NOT NULL,
    tracks TEXT
);

