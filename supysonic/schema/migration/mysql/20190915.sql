START TRANSACTION;

CREATE TEMPORARY TABLE IF NOT EXISTS folder_id_to_int (
	id INTEGER PRIMARY KEY AUTO_INCREMENT,
	uuid BINARY(16) NOT NULL
);

INSERT INTO folder_id_to_int(uuid) SELECT id FROM folder;

DROP INDEX index_folder_parent_id_fk ON folder;
DROP INDEX index_track_folder_id_fk ON track;
DROP INDEX index_track_root_folder_id_fk ON track;
DROP INDEX index_starred_folder_starred_id_fk ON starred_folder;
DROP INDEX index_rating_folder_rated_id_fk ON rating_folder;


ALTER TABLE folder
    ADD int_id INTEGER AFTER id,
    ADD int_parent_id INTEGER REFERENCES folder(id) AFTER parent_id;
UPDATE folder SET int_id = (SELECT id FROM folder_id_to_int WHERE uuid = folder.id);
UPDATE folder SET int_parent_id = (SELECT id FROM folder_id_to_int WHERE uuid = folder.parent_id);
ALTER TABLE folder
    DROP PRIMARY KEY,
    DROP COLUMN id,
    DROP COLUMN parent_id,
    CHANGE COLUMN int_id id INTEGER AUTO_INCREMENT,
    CHANGE COLUMN int_parent_id parent_id INTEGER,
    ADD PRIMARY KEY (id);


ALTER TABLE track
    ADD int_root_folder_id INTEGER NOT NULL REFERENCES folder(id) AFTER root_folder_id,
    ADD int_folder_id INTEGER NOT NULL REFERENCES folder(id) AFTER folder_id;
UPDATE track SET int_root_folder_id = (SELECT id FROM folder_id_to_int WHERE uuid = track.root_folder_id);
UPDATE track SET int_folder_id = (SELECT id FROM folder_id_to_int WHERE uuid = track.folder_id);
ALTER TABLE track
    DROP COLUMN root_folder_id,
    DROP COLUMN folder_id,
    CHANGE COLUMN int_root_folder_id root_folder_id INTEGER NOT NULL,
    CHANGE COLUMN int_folder_id folder_id INTEGER NOT NULL;


ALTER TABLE starred_folder ADD int_starred_id INTEGER NOT NULL REFERENCES folder(id) AFTER starred_id;
UPDATE starred_folder SET int_starred_id = (SELECT id FROM folder_id_to_int WHERE uuid = starred_folder.starred_id);
ALTER TABLE starred_folder
    DROP PRIMARY KEY,
    DROP COLUMN starred_id,
    CHANGE COLUMN int_starred_id starred_id INTEGER NOT NULL,
    ADD PRIMARY KEY (user_id, starred_id);


ALTER TABLE rating_folder ADD int_rated_id INTEGER NOT NULL REFERENCES folder(id) AFTER rated_id;
UPDATE rating_folder SET int_rated_id = (SELECT id FROM folder_id_to_int WHERE uuid = rating_folder.rated_id);
ALTER TABLE rating_folder
    DROP PRIMARY KEY,
    DROP COLUMN rated_id,
    CHANGE COLUMN int_rated_id rated_id INTEGER NOT NULL,
    ADD PRIMARY KEY (user_id, rated_id);


CREATE INDEX index_folder_parent_id_fk ON folder(parent_id);
CREATE INDEX index_track_folder_id_fk ON track(folder_id);
CREATE INDEX index_track_root_folder_id_fk ON track(root_folder_id);
CREATE INDEX index_starred_folder_starred_id_fk ON starred_folder(starred_id);
CREATE INDEX index_rating_folder_rated_id_fk ON rating_folder(rated_id);

DROP TABLE folder_id_to_int;

COMMIT;
