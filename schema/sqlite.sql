CREATE TABLE folder (
	id CHAR(36) PRIMARY KEY,
	root BOOLEAN NOT NULL,
	name VARCHAR(256) NOT NULL,
	path VARCHAR(4096) NOT NULL,
	created DATETIME NOT NULL,
	has_cover_art BOOLEAN NOT NULL,
	last_scan INTEGER NOT NULL,
	parent_id CHAR(36) REFERENCES folder
);

CREATE TABLE artist (
	id CHAR(36) PRIMARY KEY,
	name VARCHAR(256) NOT NULL COLLATE NOCASE
);

CREATE TABLE album (
	id CHAR(36) PRIMARY KEY,
	name VARCHAR(256) NOT NULL COLLATE NOCASE,
	artist_id CHAR(36) NOT NULL REFERENCES artist
);

CREATE TABLE track (
	id CHAR(36) PRIMARY KEY,
	disc INTEGER NOT NULL,
	number INTEGER NOT NULL,
	title VARCHAR(256) NOT NULL,
	year INTEGER,
	genre VARCHAR(256),
	duration INTEGER NOT NULL,
	album_id CHAR(36) NOT NULL REFERENCES album,
	artist_id CHAR(36) NOT NULL REFERENCES artist,
	bitrate INTEGER NOT NULL,
	path VARCHAR(4096) NOT NULL,
	content_type VARCHAR(32) NOT NULL,
	created DATETIME NOT NULL,
	last_modification INTEGER NOT NULL,
	play_count INTEGER NOT NULL,
	last_play DATETIME,
	root_folder_id CHAR(36) NOT NULL REFERENCES folder,
	folder_id CHAR(36) NOT NULL REFERENCES folder
);

CREATE TABLE user (
	id CHAR(36) PRIMARY KEY,
	name VARCHAR(64) NOT NULL,
	mail VARCHAR(256),
	password CHAR(40) NOT NULL,
	salt CHAR(6) NOT NULL,
	admin BOOLEAN NOT NULL,
	lastfm_session CHAR(32),
	lastfm_status BOOLEAN NOT NULL,
	last_play_id CHAR(36) REFERENCES track,
	last_play_date DATETIME
);

CREATE TABLE client_prefs (
	user_id CHAR(36) NOT NULL,
	client_name VARCHAR(32) NOT NULL,
	format VARCHAR(8),
	bitrate INTEGER,
	PRIMARY KEY (user_id, client_name)
);

CREATE TABLE starred_folder (
	user_id CHAR(36) NOT NULL REFERENCES user,
	starred_id CHAR(36) NOT NULL REFERENCES folder,
	date DATETIME NOT NULL,
	PRIMARY KEY (user_id, starred_id)
);

CREATE TABLE starred_artist (
	user_id CHAR(36) NOT NULL REFERENCES user,
	starred_id CHAR(36) NOT NULL REFERENCES artist,
	date DATETIME NOT NULL,
	PRIMARY KEY (user_id, starred_id)
);

CREATE TABLE starred_album (
	user_id CHAR(36) NOT NULL REFERENCES user,
	starred_id CHAR(36) NOT NULL REFERENCES album,
	date DATETIME NOT NULL,
	PRIMARY KEY (user_id, starred_id)
);

CREATE TABLE starred_track (
	user_id CHAR(36) NOT NULL REFERENCES user,
	starred_id CHAR(36) NOT NULL REFERENCES track,
	date DATETIME NOT NULL,
	PRIMARY KEY (user_id, starred_id)
);

CREATE TABLE rating_folder (
	user_id CHAR(36) NOT NULL REFERENCES user,
	rated_id CHAR(36) NOT NULL REFERENCES folder,
	rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
	PRIMARY KEY (user_id, rated_id)
);

CREATE TABLE rating_track (
	user_id CHAR(36) NOT NULL REFERENCES user,
	rated_id CHAR(36) NOT NULL REFERENCES track,
	rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
	PRIMARY KEY (user_id, rated_id)
);

CREATE TABLE chat_message (
	id CHAR(36) PRIMARY KEY,
	user_id CHAR(36) NOT NULL REFERENCES user,
	time INTEGER NOT NULL,
	message VARCHAR(512) NOT NULL
);

CREATE TABLE playlist (
	id CHAR(36) PRIMARY KEY,
	user_id CHAR(36) NOT NULL REFERENCES user,
	name VARCHAR(256) NOT NULL COLLATE NOCASE,
	comment VARCHAR(256),
	public BOOLEAN NOT NULL,
	created DATETIME NOT NULL
);

CREATE TABLE playlist_track (
	playlist_id CHAR(36) NOT NULL REFERENCES playlist,
	track_id CHAR(36) NOT NULL REFERENCES track,
	PRIMARY KEY(playlist_id, track_id)
);

