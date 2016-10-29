-- PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

ALTER TABLE track RENAME TO track_old;
CREATE TABLE track (
	id CHAR(36) PRIMARY KEY,
	disc INTEGER NOT NULL,
	number INTEGER NOT NULL,
	title VARCHAR(256) NOT NULL,
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

INSERT INTO track(id, disc, number, title, year, genre, duration, album_id, artist_id, bitrate, path, content_type, created, last_modification, play_count, last_play, root_folder_id, folder_id)
SELECT t.id, disc, number, title, year, genre, duration, album_id, artist_id, bitrate, path, content_type, created, last_modification, play_count, last_play, root_folder_id, folder_id
FROM track_old t, album a
WHERE album_id = a.id;

DROP TABLE track_old;

COMMIT;
-- PRAGMA foreign_keys = ON;

