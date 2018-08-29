START TRANSACTION;

ALTER TABLE folder ADD COLUMN path_hash BINARY(20) NOT NULL AFTER path;
ALTER TABLE track ADD COLUMN path_hash BINARY(20) NOT NULL AFTER path;

UPDATE folder SET path_hash=UNHEX(SHA1(path));
UPDATE track SET path_hash=UNHEX(SHA1(path));

CREATE UNIQUE INDEX index_folder_path ON folder(path_hash);
CREATE UNIQUE INDEX index_track_path ON track(path_hash);

COMMIT;

