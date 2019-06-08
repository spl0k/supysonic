COMMIT;
PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

DROP INDEX index_track_album_id_fk;
DROP INDEX index_track_artist_id_fk;
DROP INDEX index_track_folder_id_fk;
DROP INDEX index_track_root_folder_id_fk;
DROP INDEX index_track_path;

CREATE TABLE track_new (
    id CHAR(36) PRIMARY KEY,
    disc INTEGER NOT NULL,
    number INTEGER NOT NULL,
    title VARCHAR(256) NOT NULL COLLATE NOCASE,
    year INTEGER,
    genre VARCHAR(256),
    duration INTEGER NOT NULL,
    has_art BOOLEAN NOT NULL DEFAULT false,
    album_id CHAR(36) NOT NULL REFERENCES album,
    artist_id CHAR(36) NOT NULL REFERENCES artist,
    bitrate INTEGER NOT NULL,
    path VARCHAR(4096) NOT NULL,
    path_hash BLOB NOT NULL,
    created DATETIME NOT NULL,
    last_modification INTEGER NOT NULL,
    play_count INTEGER NOT NULL,
    last_play DATETIME,
    root_folder_id CHAR(36) NOT NULL REFERENCES folder,
    folder_id CHAR(36) NOT NULL REFERENCES folder
);
CREATE INDEX IF NOT EXISTS index_track_album_id_fk ON track_new(album_id);
CREATE INDEX IF NOT EXISTS index_track_artist_id_fk ON track_new(artist_id);
CREATE INDEX IF NOT EXISTS index_track_folder_id_fk ON track_new(folder_id);
CREATE INDEX IF NOT EXISTS index_track_root_folder_id_fk ON track_new(root_folder_id);
CREATE UNIQUE INDEX IF NOT EXISTS index_track_path ON track_new(path_hash);

INSERT INTO track_new(id, disc, number, title, year, genre, duration, has_art, album_id, artist_id, bitrate, path, path_hash, created, last_modification, play_count, last_play, root_folder_id, folder_id)
SELECT id, disc, number, title, year, genre, duration, has_art, album_id, artist_id, bitrate, path, path_hash, created, last_modification, play_count, last_play, root_folder_id, folder_id
FROM track;

DROP TABLE track;
ALTER TABLE track_new RENAME TO track;

COMMIT;
VACUUM;
PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;
