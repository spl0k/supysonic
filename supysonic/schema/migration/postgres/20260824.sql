ALTER TABLE "user" ALTER COLUMN password TYPE VARCHAR(256);
UPDATE "user" SET password = password || '#' || salt;
ALTER TABLE "user" DROP COLUMN salt;
