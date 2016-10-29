START TRANSACTION;

ALTER TABLE track ADD artist_id CHAR(36) AFTER album_id;
UPDATE track SET artist_id = (SELECT artist_id FROM album WHERE id = track.album_id);
ALTER TABLE track MODIFY artist_id CHAR(36) NOT NULL;
ALTER TABLE track ADD FOREIGN KEY (artist_id) REFERENCES artist;

COMMIT;

