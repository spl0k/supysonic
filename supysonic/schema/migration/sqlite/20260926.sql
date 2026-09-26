CREATE TABLE IF NOT EXISTS lastfm_link (
    user_id CHAR(36) PRIMARY KEY REFERENCES user,
    session_key CHAR(32) NOT NULL,
    session_valid BOOLEAN NOT NULL
);
INSERT INTO lastfm_link (user_id, session_key, session_valid) SELECT id, lastfm_session, lastfm_status FROM user WHERE lastfm_session IS NOT NULL;
ALTER TABLE user DROP COLUMN lastfm_session;
ALTER TABLE user DROP COLUMN lastfm_status;
