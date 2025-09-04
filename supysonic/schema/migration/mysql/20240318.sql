ALTER TABLE user ADD listenbrainz_session CHAR(36);
ALTER TABLE user ADD listenbrainz_status BOOLEAN NOT NULL DEFAULT TRUE;
