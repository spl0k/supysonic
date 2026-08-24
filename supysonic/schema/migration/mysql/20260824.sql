ALTER TABLE user MODIFY password VARCHAR(256) NOT NULL;
UPDATE user SET password = CONCAT(password, '#', salt);
ALTER TABLE user DROP COLUMN salt;
