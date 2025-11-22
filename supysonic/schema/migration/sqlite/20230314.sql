COMMIT;
PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;
DROP INDEX index_user_last_play_id_fk;
create TABLE user_new (
    id CHAR(36) PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    mail VARCHAR(256),
    password CHAR(40),
    salt CHAR(6),
    admin BOOLEAN NOT NULL,
    jukebox BOOLEAN NOT NULL,
    lastfm_session CHAR(32),
    lastfm_status BOOLEAN NOT NULL,
    last_play_id CHAR(36) REFERENCES track,
    last_play_date DATETIME
);
CREATE INDEX IF NOT EXISTS index_user_last_play_id_fk ON user_new(last_play_id);
INSERT INTO user_new(id, name, mail, password, salt, admin, jukebox, lastfm_session, lastfm_status, last_play_id, last_play_date)
SELECT id, name, mail, password, salt, admin, jukebox, lastfm_session, lastfm_status, last_play_id, last_play_date
FROM user;

DROP TABLE user;
ALTER TABLE user_new RENAME TO user;
COMMIT;
VACUUM;
PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;
