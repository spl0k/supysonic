-- PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

ALTER TABLE playlist RENAME TO playlist_old;
CREATE TABLE playlist (
	id CHAR(36) PRIMARY KEY,
	user_id CHAR(36) NOT NULL REFERENCES user,
	name VARCHAR(256) NOT NULL COLLATE NOCASE,
	comment VARCHAR(256),
	public BOOLEAN NOT NULL,
	created DATETIME NOT NULL,
	tracks TEXT
);

CREATE TABLE TMP_playlist_tracks (
	id CHAR(36) PRIMARY KEY,
	tracks TEXT
);

INSERT INTO TMP_playlist_tracks(id, tracks)
SELECT id, GROUP_CONCAT(track_id, ',')
FROM playlist_old, playlist_track
WHERE id = playlist_id
GROUP BY id;

INSERT INTO playlist(id, user_id, name, comment, public, created, tracks)
SELECT p.id, user_id, name, comment, public, created, tracks
FROM playlist_old p, TMP_playlist_tracks pt
WHERE p.id = pt.id;

DROP TABLE TMP_playlist_tracks;
DROP TABLE playlist_track;
DROP TABLE playlist_old;

COMMIT;
-- PRAGMA foreign_keys = ON;

