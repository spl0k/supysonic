CREATE TABLE client_prefs_new (
    user_id CHAR(36) NOT NULL REFERENCES user,
    client_name VARCHAR(32) NOT NULL,
    format VARCHAR(8),
    bitrate INTEGER,
    PRIMARY KEY (user_id, client_name)
);

INSERT INTO client_prefs_new(user_id, client_name, format, bitrate)
SELECT user_id, client_name, format, bitrate
FROM client_prefs;

DROP TABLE client_prefs;
ALTER TABLE client_prefs_new RENAME TO client_prefs;

CREATE INDEX IF NOT EXISTS index_client_prefs_user_id_fk ON client_prefs(user_id);
