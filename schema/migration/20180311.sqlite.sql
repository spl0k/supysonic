BEGIN TRANSACTION;

ALTER TABLE folder RENAME TO folder_old;
ALTER TABLE track RENAME TO track_old;

CREATE TABLE folder (
	id CHAR(36) PRIMARY KEY,
	root BOOLEAN NOT NULL,
	name VARCHAR(256) NOT NULL COLLATE NOCASE,
	path VARCHAR(4096) NOT NULL,
	created DATETIME NOT NULL,
	has_cover_art BOOLEAN NOT NULL,
	last_scan INTEGER NOT NULL,
	parent_id CHAR(36) REFERENCES folder
);

CREATE TABLE track (
	id CHAR(36) PRIMARY KEY,
	disc INTEGER NOT NULL,
	number INTEGER NOT NULL,
	title VARCHAR(256) NOT NULL COLLATE NOCASE,
	year INTEGER,
	genre VARCHAR(256),
	duration INTEGER NOT NULL,
	album_id CHAR(36) NOT NULL REFERENCES album,
	artist_id CHAR(36) NOT NULL REFERENCES artist,
	bitrate INTEGER NOT NULL,
	path VARCHAR(4096) NOT NULL,
	content_type VARCHAR(32) NOT NULL,
	created DATETIME NOT NULL,
	last_modification INTEGER NOT NULL,
	play_count INTEGER NOT NULL,
	last_play DATETIME,
	root_folder_id CHAR(36) NOT NULL REFERENCES folder,
	folder_id CHAR(36) NOT NULL REFERENCES folder
);

INSERT INTO folder (id, root, name, path, created, has_cover_art, last_scan, parent_id)
SELECT id, root, name, path, created, has_cover_art, last_scan, parent_id
FROM folder_old;

INSERT INTO track(id, disc, number, title, year, genre, duration, album_id, artist_id, bitrate, path, content_type, created, last_modification, play_count, last_play, root_folder_id, folder_id)
SELECT id, disc, number, title, year, genre, duration, album_id, artist_id, bitrate, path, content_type, created, last_modification, play_count, last_play, root_folder_id, folder_id
FROM track_old;

DROP TABLE folder_old;
DROP TABLE track_old;

COMMIT;

VACUUM;

