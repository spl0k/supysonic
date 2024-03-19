ALTER TABLE user ADD COLUMN listenbrainz_session CHAR(36);
ALTER TABLE user ADD COLUMN listenbrainz_status BOOLEAN NOT NULL DEFAULT TRUE;
