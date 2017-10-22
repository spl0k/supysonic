START TRANSACTION;

ALTER TABLE playlist ADD tracks TEXT;
UPDATE playlist SET tracks = (
	SELECT array_to_string(array_agg(track_id), ',')
	FROM playlist_track
	WHERE playlist_id = playlist.id);
DROP TABLE playlist_track;

COMMIT;

