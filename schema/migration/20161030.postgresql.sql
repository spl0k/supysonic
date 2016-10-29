START TRANSACTION;

ALTER TABLE track ADD artist_id UUID;
UPDATE track SET artist_id = (SELECT artist_id FROM album WHERE id = track.album_id);
ALTER TABLE track ALTER artist_id SET NOT NULL;
ALTER TABLE track ADD FOREIGN KEY (artist_id) REFERENCES artist;

COMMIT;

