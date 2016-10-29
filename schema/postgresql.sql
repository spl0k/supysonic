CREATE TABLE folder (
	id UUID PRIMARY KEY,
	root BOOLEAN NOT NULL,
	name VARCHAR(256) NOT NULL,
	path VARCHAR(4096) NOT NULL,
	created TIMESTAMP NOT NULL,
	has_cover_art BOOLEAN NOT NULL,
	last_scan INTEGER NOT NULL,
	parent_id UUID REFERENCES folder
);

CREATE TABLE artist (
	id UUID PRIMARY KEY,
	name VARCHAR(256) NOT NULL
);

CREATE TABLE album (
	id UUID PRIMARY KEY,
	name VARCHAR(256) NOT NULL,
	artist_id UUID NOT NULL REFERENCES artist
);

CREATE TABLE track (
	id UUID PRIMARY KEY,
	disc INTEGER NOT NULL,
	number INTEGER NOT NULL,
	title VARCHAR(256) NOT NULL,
	year INTEGER,
	genre VARCHAR(256),
	duration INTEGER NOT NULL,
	album_id UUID NOT NULL REFERENCES album,
	artist_id UUID NOT NULL REFERENCES artist,
	bitrate INTEGER NOT NULL,
	path VARCHAR(4096) NOT NULL,
	content_type VARCHAR(32) NOT NULL,
	created TIMESTAMP NOT NULL,
	last_modification INTEGER NOT NULL,
	play_count INTEGER NOT NULL,
	last_play TIMESTAMP,
	root_folder_id UUID NOT NULL REFERENCES folder,
	folder_id UUID NOT NULL REFERENCES folder
);

CREATE TABLE "user" (
	id UUID PRIMARY KEY,
	name VARCHAR(64) NOT NULL,
	mail VARCHAR(256),
	password CHAR(40) NOT NULL,
	salt CHAR(6) NOT NULL,
	admin BOOLEAN NOT NULL,
	lastfm_session CHAR(32),
	lastfm_status BOOLEAN NOT NULL,
	last_play_id UUID REFERENCES track,
	last_play_date TIMESTAMP
);

CREATE TABLE client_prefs (
	user_id UUID NOT NULL,
	client_name VARCHAR(32) NOT NULL,
	format VARCHAR(8),
	bitrate INTEGER,
	PRIMARY KEY (user_id, client_name)
);

CREATE TABLE starred_folder (
	user_id UUID NOT NULL REFERENCES "user",
	starred_id UUID NOT NULL REFERENCES folder,
	date TIMESTAMP NOT NULL,
	PRIMARY KEY (user_id, starred_id)
);

CREATE TABLE starred_artist (
	user_id UUID NOT NULL REFERENCES "user",
	starred_id UUID NOT NULL REFERENCES artist,
	date TIMESTAMP NOT NULL,
	PRIMARY KEY (user_id, starred_id)
);

CREATE TABLE starred_album (
	user_id UUID NOT NULL REFERENCES "user",
	starred_id UUID NOT NULL REFERENCES album,
	date TIMESTAMP NOT NULL,
	PRIMARY KEY (user_id, starred_id)
);

CREATE TABLE starred_track (
	user_id UUID NOT NULL REFERENCES "user",
	starred_id UUID NOT NULL REFERENCES track,
	date TIMESTAMP NOT NULL,
	PRIMARY KEY (user_id, starred_id)
);

CREATE TABLE rating_folder (
	user_id UUID NOT NULL REFERENCES "user",
	rated_id UUID NOT NULL REFERENCES folder,
	rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
	PRIMARY KEY (user_id, rated_id)
);

CREATE TABLE rating_track (
	user_id UUID NOT NULL REFERENCES "user",
	rated_id UUID NOT NULL REFERENCES track,
	rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
	PRIMARY KEY (user_id, rated_id)
);

CREATE TABLE chat_message (
	id UUID PRIMARY KEY,
	user_id UUID NOT NULL REFERENCES "user",
	time INTEGER NOT NULL,
	message VARCHAR(512) NOT NULL
);

CREATE TABLE playlist (
	id UUID PRIMARY KEY,
	user_id UUID NOT NULL REFERENCES "user",
	name VARCHAR(256) NOT NULL,
	comment VARCHAR(256),
	public BOOLEAN NOT NULL,
	created TIMESTAMP NOT NULL
);

CREATE TABLE playlist_track (
	playlist_id UUID NOT NULL REFERENCES playlist,
	track_id UUID NOT NULL REFERENCES track,
	PRIMARY KEY(playlist_id, track_id)
);

