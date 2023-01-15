ALTER TABLE client_prefs ADD FOREIGN KEY (user_id) REFERENCES "user";
CREATE INDEX IF NOT EXISTS index_client_prefs_user_id_fk ON client_prefs(user_id);
