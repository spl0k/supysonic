BEGIN TRANSACTION;

DROP INDEX index_folder_path;
ALTER TABLE folder RENAME TO folder_old;

CREATE TABLE folder (
    id CHAR(36) PRIMARY KEY,
    root BOOLEAN NOT NULL,
    name VARCHAR(256) NOT NULL COLLATE NOCASE,
    path VARCHAR(4096) NOT NULL,
    path_hash BLOB NOT NULL,
    created DATETIME NOT NULL,
    cover_art VARCHAR(256),
    last_scan INTEGER NOT NULL,
    parent_id CHAR(36) REFERENCES folder
);
CREATE UNIQUE INDEX index_folder_path ON folder(path_hash);

INSERT INTO folder(id, root, name, path, path_hash, created, cover_art, last_scan, parent_id)
SELECT id, root, name, path, path_hash, created, CASE WHEN has_cover_art THEN 'cover.jpg' ELSE NULL END, last_scan, parent_id
FROM folder_old;

DROP TABLE folder_old;

COMMIT;
VACUUM;

