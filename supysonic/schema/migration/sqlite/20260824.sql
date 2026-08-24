UPDATE user SET password = password || '#' || salt;
ALTER TABLE user DROP COLUMN salt;
