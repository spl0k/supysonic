COMMIT;
PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

CREATE TEMPORARY TABLE IF NOT EXISTS folder_id_to_int (
	id INTEGER NOT NULL PRIMARY KEY,
	uuid CHAR(36) NOT NULL
);

INSERT INTO folder_id_to_int(uuid) SELECT id FROM folder;

DROP INDEX index_folder_parent_id_fk;
DROP INDEX index_folder_path;

CREATE TABLE IF NOT EXISTS folder_new (
    id INTEGER NOT NULL PRIMARY KEY,
    root BOOLEAN NOT NULL,
    name VARCHAR(256) NOT NULL COLLATE NOCASE,
    path VARCHAR(4096) NOT NULL,
    path_hash BLOB NOT NULL,
    created DATETIME NOT NULL,
    cover_art VARCHAR(256),
    last_scan INTEGER NOT NULL,
    parent_id INTEGER REFERENCES folder
);
CREATE INDEX IF NOT EXISTS index_folder_parent_id_fk ON folder_new(parent_id);
CREATE UNIQUE INDEX IF NOT EXISTS index_folder_path ON folder_new(path_hash);

INSERT INTO folder_new(id, root, name, path, path_hash, created, cover_art, last_scan, parent_id)
SELECT id_int.id, root, name, path, path_hash, created, cover_art, last_scan, NULL
FROM folder
JOIN folder_id_to_int id_int ON folder.id == id_int.uuid
WHERE folder.parent_id IS NULL;

INSERT INTO folder_new(id, root, name, path, path_hash, created, cover_art, last_scan, parent_id)
SELECT id_int.id, root, name, path, path_hash, created, cover_art, last_scan, parent_id_int.id
FROM folder
JOIN folder_id_to_int id_int ON folder.id == id_int.uuid
JOIN folder_id_to_int parent_id_int ON folder.parent_id == parent_id_int.uuid
WHERE folder.parent_id IS NOT NULL;

DROP TABLE folder;
ALTER TABLE folder_new RENAME TO folder;


DROP INDEX index_track_album_id_fk;
DROP INDEX index_track_artist_id_fk;
DROP INDEX index_track_folder_id_fk;
DROP INDEX index_track_root_folder_id_fk;
DROP INDEX index_track_path;

CREATE TABLE IF NOT EXISTS track_new (
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
    root_folder_id INTEGER NOT NULL REFERENCES folder,
    folder_id INTEGER NOT NULL REFERENCES folder
);
CREATE INDEX IF NOT EXISTS index_track_album_id_fk ON track_new(album_id);
CREATE INDEX IF NOT EXISTS index_track_artist_id_fk ON track_new(artist_id);
CREATE INDEX IF NOT EXISTS index_track_folder_id_fk ON track_new(folder_id);
CREATE INDEX IF NOT EXISTS index_track_root_folder_id_fk ON track_new(root_folder_id);
CREATE UNIQUE INDEX IF NOT EXISTS index_track_path ON track_new(path_hash);

INSERT INTO track_new(id, disc, number, title, year, genre, duration, has_art, album_id, artist_id, bitrate, path, path_hash, created, last_modification, play_count, last_play, root_folder_id, folder_id)
SELECT track.id, disc, number, title, year, genre, duration, has_art, album_id, artist_id, bitrate, path, path_hash, created, last_modification, play_count, last_play, root_id_int.id, folder_id_int.id
FROM track
JOIN folder_id_to_int root_id_int ON track.root_folder_id == root_id_int.uuid
JOIN folder_id_to_int folder_id_int ON track.folder_id == folder_id_int.uuid;

DROP TABLE track;
ALTER TABLE track_new RENAME TO track;


DROP INDEX index_starred_folder_user_id_fk;
DROP INDEX index_starred_folder_starred_id_fk;

CREATE TABLE IF NOT EXISTS starred_folder_new (
    user_id CHAR(36) NOT NULL REFERENCES user,
    starred_id INTEGER NOT NULL REFERENCES folder,
    date DATETIME NOT NULL,
    PRIMARY KEY (user_id, starred_id)
);
CREATE INDEX IF NOT EXISTS index_starred_folder_user_id_fk ON starred_folder_new(user_id);
CREATE INDEX IF NOT EXISTS index_starred_folder_starred_id_fk ON starred_folder_new(starred_id);

INSERT INTO starred_folder_new(user_id, starred_id, date)
SELECT user_id, id_int.id, date
FROM starred_folder
JOIN folder_id_to_int id_int ON starred_folder.starred_id == id_int.uuid;

DROP TABLE starred_folder;
ALTER TABLE starred_folder_new RENAME TO starred_folder;


DROP INDEX index_rating_folder_user_id_fk;
DROP INDEX index_rating_folder_rated_id_fk;

CREATE TABLE IF NOT EXISTS rating_folder_new (
    user_id CHAR(36) NOT NULL REFERENCES user,
    rated_id INTEGER NOT NULL REFERENCES folder,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    PRIMARY KEY (user_id, rated_id)
);
CREATE INDEX IF NOT EXISTS index_rating_folder_user_id_fk ON rating_folder_new(user_id);
CREATE INDEX IF NOT EXISTS index_rating_folder_rated_id_fk ON rating_folder_new(rated_id);

INSERT INTO rating_folder_new(user_id, rated_id, rating)
SELECT user_id, id_int.id, rating
FROM rating_folder
JOIN folder_id_to_int id_int ON rating_folder.rated_id == id_int.uuid;

DROP TABLE rating_folder;
ALTER TABLE rating_folder_new RENAME TO rating_folder;


DROP TABLE folder_id_to_int;

COMMIT;
VACUUM;
PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;
