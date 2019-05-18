DROP INDEX index_track_album_id_fk;
DROP INDEX index_track_artist_id_fk;
DROP INDEX index_track_folder_id_fk;
DROP INDEX index_track_root_folder_id_fk;
DROP INDEX index_track_path;

ALTER TABLE track RENAME TO track_old;

CREATE TABLE IF NOT EXISTS track (
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
CREATE INDEX IF NOT EXISTS index_track_album_id_fk ON track(album_id);
CREATE INDEX IF NOT EXISTS index_track_artist_id_fk ON track(artist_id);
CREATE INDEX IF NOT EXISTS index_track_folder_id_fk ON track(folder_id);
CREATE INDEX IF NOT EXISTS index_track_root_folder_id_fk ON track(root_folder_id);
CREATE UNIQUE INDEX IF NOT EXISTS index_track_path ON track(path_hash);

INSERT INTO track(id, disc, number, title, year, genre, duration, has_art, album_id, artist_id, bitrate, path, path_hash, created, last_modification, play_count, last_play, root_folder_id, folder_id)
SELECT id, disc, number, title, year, genre, duration, has_art, album_id, artist_id, bitrate, path, path_hash, created, last_modification, play_count, last_play, root_folder_id, folder_id
FROM track_old;

DROP TABLE track_old;

COMMIT;
VACUUM;
