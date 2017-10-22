START TRANSACTION;

ALTER TABLE playlist ADD tracks TEXT;
UPDATE playlist SET tracks = (
	SELECT GROUP_CONCAT(track_id SEPARATOR ',')
	FROM playlist_track
	WHERE playlist_id = playlist.id);
DROP TABLE playlist_track;

COMMIT;

