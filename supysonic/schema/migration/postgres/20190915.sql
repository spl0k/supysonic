START TRANSACTION;

CREATE TEMPORARY TABLE IF NOT EXISTS folder_id_to_int (
	id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
	uid UUID NOT NULL
);

INSERT INTO folder_id_to_int(uid) SELECT id FROM folder;

ALTER TABLE folder DROP CONSTRAINT folder_parent_id_fkey;
ALTER TABLE rating_folder DROP CONSTRAINT rating_folder_rated_id_fkey;
ALTER TABLE starred_folder DROP CONSTRAINT starred_folder_starred_id_fkey;
ALTER TABLE track DROP CONSTRAINT track_folder_id_fkey;
ALTER TABLE track DROP CONSTRAINT track_root_folder_id_fkey;


ALTER TABLE folder
    ADD int_id INTEGER,
    ADD int_parent_id INTEGER;
UPDATE folder SET int_id = (SELECT id FROM folder_id_to_int WHERE uid = folder.id);
UPDATE folder SET int_parent_id = (SELECT id FROM folder_id_to_int WHERE uid = folder.parent_id);
CREATE SEQUENCE folder_id_seq AS INTEGER;
SELECT setval('folder_id_seq', coalesce(max(int_id), 0) + 1, false) FROM folder;
ALTER TABLE folder
    DROP CONSTRAINT folder_pkey,
    DROP COLUMN id,
    DROP COLUMN parent_id,
    ALTER COLUMN int_id SET DEFAULT nextval('folder_id_seq'),
    ADD PRIMARY KEY (int_id);
ALTER TABLE folder RENAME COLUMN int_id TO id;
ALTER TABLE folder RENAME COLUMN int_parent_id TO parent_id;
ALTER TABLE folder ADD CONSTRAINT folder_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES folder(id);


ALTER TABLE track
    ADD int_root_folder_id INTEGER,
    ADD int_folder_id INTEGER;
UPDATE track SET int_root_folder_id = (SELECT id FROM folder_id_to_int WHERE uid = track.root_folder_id);
UPDATE track SET int_folder_id = (SELECT id FROM folder_id_to_int WHERE uid = track.folder_id);
ALTER TABLE track
    DROP COLUMN root_folder_id,
    DROP COLUMN folder_id,
    ALTER COLUMN int_root_folder_id SET NOT NULL,
    ALTER COLUMN int_folder_id SET NOT NULL;
ALTER TABLE track RENAME COLUMN int_root_folder_id TO root_folder_id;
ALTER TABLE track RENAME COLUMN int_folder_id TO folder_id;
ALTER TABLE track ADD CONSTRAINT track_folder_id_fkey FOREIGN KEY (folder_id) REFERENCES folder(id);
ALTER TABLE track ADD CONSTRAINT track_root_folder_id_fkey FOREIGN KEY (root_folder_id) REFERENCES folder(id);


ALTER TABLE starred_folder ADD int_starred_id INTEGER;
UPDATE starred_folder SET int_starred_id = (SELECT id FROM folder_id_to_int WHERE uid = starred_folder.starred_id);
ALTER TABLE starred_folder
    DROP CONSTRAINT starred_folder_pkey,
    DROP COLUMN starred_id,
    ALTER COLUMN int_starred_id SET NOT NULL,
    ADD PRIMARY KEY (user_id, int_starred_id);
ALTER TABLE starred_folder RENAME COLUMN int_starred_id TO starred_id;
ALTER TABLE starred_folder ADD CONSTRAINT starred_folder_starred_id_fkey FOREIGN KEY (starred_id) REFERENCES folder(id);


ALTER TABLE rating_folder ADD int_rated_id INTEGER;
UPDATE rating_folder SET int_rated_id = (SELECT id FROM folder_id_to_int WHERE uid = rating_folder.rated_id);
ALTER TABLE rating_folder
    DROP CONSTRAINT rating_folder_pkey,
    DROP COLUMN rated_id,
	ALTER COLUMN int_rated_id SET NOT NULL,
    ADD PRIMARY KEY (user_id, int_rated_id);
ALTER TABLE rating_folder RENAME COLUMN int_rated_id TO rated_id;
ALTER TABLE rating_folder ADD CONSTRAINT rating_folder_rated_id_fkey FOREIGN KEY (rated_id) REFERENCES folder(id);


CREATE INDEX IF NOT EXISTS index_folder_parent_id_fk ON folder(parent_id);
CREATE INDEX IF NOT EXISTS index_track_folder_id_fk ON track(folder_id);
CREATE INDEX IF NOT EXISTS index_track_root_folder_id_fk ON track(root_folder_id);
CREATE INDEX IF NOT EXISTS index_starred_folder_starred_id_fk ON starred_folder(starred_id);
CREATE INDEX IF NOT EXISTS index_rating_folder_rated_id_fk ON rating_folder(rated_id);



DROP TABLE folder_id_to_int;

COMMIT;
