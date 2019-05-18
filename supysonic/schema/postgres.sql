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
CREATE INDEX IF NOT EXISTS index_folder_parent_id_fk ON folder(parent_id);

CREATE TABLE IF NOT EXISTS artist (
    id UUID PRIMARY KEY,
    name CITEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS album (
    id UUID PRIMARY KEY,
    name CITEXT NOT NULL,
    artist_id UUID NOT NULL REFERENCES artist
);
CREATE INDEX IF NOT EXISTS index_album_artist_id_fk ON album(artist_id);

CREATE TABLE IF NOT EXISTS track (
    id UUID PRIMARY KEY,
    disc INTEGER NOT NULL,
    number INTEGER NOT NULL,
    title CITEXT NOT NULL,
    year INTEGER,
    genre VARCHAR(256),
    duration INTEGER NOT NULL,
    has_art BOOLEAN NOT NULL DEFAULT false,
    album_id UUID NOT NULL REFERENCES album,
    artist_id UUID NOT NULL REFERENCES artist,
    bitrate INTEGER NOT NULL,
    path VARCHAR(4096) NOT NULL,
    path_hash BYTEA UNIQUE NOT NULL,
    created TIMESTAMP NOT NULL,
    last_modification INTEGER NOT NULL,
    play_count INTEGER NOT NULL,
    last_play TIMESTAMP,
    root_folder_id UUID NOT NULL REFERENCES folder,
    folder_id UUID NOT NULL REFERENCES folder
);
CREATE INDEX IF NOT EXISTS index_track_album_id_fk ON track(album_id);
CREATE INDEX IF NOT EXISTS index_track_artist_id_fk ON track(artist_id);
CREATE INDEX IF NOT EXISTS index_track_folder_id_fk ON track(folder_id);
CREATE INDEX IF NOT EXISTS index_track_root_folder_id_fk ON track(root_folder_id);

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
CREATE INDEX IF NOT EXISTS index_user_last_play_id_fk ON "user"(last_play_id);

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
CREATE INDEX IF NOT EXISTS index_starred_folder_user_id_fk ON starred_folder(user_id);
CREATE INDEX IF NOT EXISTS index_starred_folder_starred_id_fk ON starred_folder(starred_id);

CREATE TABLE IF NOT EXISTS starred_artist (
    user_id UUID NOT NULL REFERENCES "user",
    starred_id UUID NOT NULL REFERENCES artist,
    date TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, starred_id)
);
CREATE INDEX IF NOT EXISTS index_starred_artist_user_id_fk ON starred_artist(user_id);
CREATE INDEX IF NOT EXISTS index_starred_artist_starred_id_fk ON starred_artist(starred_id);

CREATE TABLE IF NOT EXISTS starred_album (
    user_id UUID NOT NULL REFERENCES "user",
    starred_id UUID NOT NULL REFERENCES album,
    date TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, starred_id)
);
CREATE INDEX IF NOT EXISTS index_starred_album_user_id_fk ON starred_album(user_id);
CREATE INDEX IF NOT EXISTS index_starred_album_starred_id_fk ON starred_album(starred_id);

CREATE TABLE IF NOT EXISTS starred_track (
    user_id UUID NOT NULL REFERENCES "user",
    starred_id UUID NOT NULL REFERENCES track,
    date TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, starred_id)
);
CREATE INDEX IF NOT EXISTS index_starred_track_user_id_fk ON starred_track(user_id);
CREATE INDEX IF NOT EXISTS index_starred_track_starred_id_fk ON starred_track(starred_id);

CREATE TABLE IF NOT EXISTS rating_folder (
    user_id UUID NOT NULL REFERENCES "user",
    rated_id UUID NOT NULL REFERENCES folder,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    PRIMARY KEY (user_id, rated_id)
);
CREATE INDEX IF NOT EXISTS index_rating_folder_user_id_fk ON rating_folder(user_id);
CREATE INDEX IF NOT EXISTS index_rating_folder_rated_id_fk ON rating_folder(rated_id);

CREATE TABLE IF NOT EXISTS rating_track (
    user_id UUID NOT NULL REFERENCES "user",
    rated_id UUID NOT NULL REFERENCES track,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    PRIMARY KEY (user_id, rated_id)
);
CREATE INDEX IF NOT EXISTS index_rating_track_user_id_fk ON rating_track(user_id);
CREATE INDEX IF NOT EXISTS index_rating_track_rated_id_fk ON rating_track(rated_id);

CREATE TABLE IF NOT EXISTS chat_message (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES "user",
    time INTEGER NOT NULL,
    message VARCHAR(512) NOT NULL
);
CREATE INDEX IF NOT EXISTS index_chat_message_user_id_fk ON chat_message(user_id);

CREATE TABLE IF NOT EXISTS playlist (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES "user",
    name VARCHAR(256) NOT NULL,
    comment VARCHAR(256),
    public BOOLEAN NOT NULL,
    created TIMESTAMP NOT NULL,
    tracks TEXT
);
CREATE INDEX IF NOT EXISTS index_playlist_user_id_fk ON playlist(user_id);

CREATE TABLE meta (
    key VARCHAR(32) PRIMARY KEY,
    value VARCHAR(256) NOT NULL
);

