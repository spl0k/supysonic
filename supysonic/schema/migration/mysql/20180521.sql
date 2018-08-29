START TRANSACTION;

ALTER TABLE folder ADD cover_art VARCHAR(256) AFTER has_cover_art;

UPDATE folder
SET cover_art = 'cover.jpg'
WHERE has_cover_art;

ALTER TABLE folder DROP COLUMN has_cover_art;

COMMIT;

