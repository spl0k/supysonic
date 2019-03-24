CREATE INDEX IF NOT EXISTS index_folder_parent_id_fk ON folder(parent_id);

CREATE INDEX IF NOT EXISTS index_album_artist_id_fk ON album(artist_id);

CREATE INDEX IF NOT EXISTS index_track_album_id_fk ON track(album_id);
CREATE INDEX IF NOT EXISTS index_track_artist_id_fk ON track(artist_id);
CREATE INDEX IF NOT EXISTS index_track_folder_id_fk ON track(folder_id);
CREATE INDEX IF NOT EXISTS index_track_root_folder_id_fk ON track(root_folder_id);

CREATE INDEX IF NOT EXISTS index_user_last_play_id_fk ON "user"(last_play_id);

CREATE INDEX IF NOT EXISTS index_starred_folder_user_id_fk ON starred_folder(user_id);
CREATE INDEX IF NOT EXISTS index_starred_folder_starred_id_fk ON starred_folder(starred_id);

CREATE INDEX IF NOT EXISTS index_starred_artist_user_id_fk ON starred_artist(user_id);
CREATE INDEX IF NOT EXISTS index_starred_artist_starred_id_fk ON starred_artist(starred_id);

CREATE INDEX IF NOT EXISTS index_starred_album_user_id_fk ON starred_album(user_id);
CREATE INDEX IF NOT EXISTS index_starred_album_starred_id_fk ON starred_album(starred_id);

CREATE INDEX IF NOT EXISTS index_starred_track_user_id_fk ON starred_track(user_id);
CREATE INDEX IF NOT EXISTS index_starred_track_starred_id_fk ON starred_track(starred_id);

CREATE INDEX IF NOT EXISTS index_rating_folder_user_id_fk ON rating_folder(user_id);
CREATE INDEX IF NOT EXISTS index_rating_folder_rated_id_fk ON rating_folder(rated_id);

CREATE INDEX IF NOT EXISTS index_rating_track_user_id_fk ON rating_track(user_id);
CREATE INDEX IF NOT EXISTS index_rating_track_rated_id_fk ON rating_track(rated_id);

CREATE INDEX IF NOT EXISTS index_chat_message_user_id_fk ON chat_message(user_id);

CREATE INDEX IF NOT EXISTS index_playlist_user_id_fk ON playlist(user_id);
