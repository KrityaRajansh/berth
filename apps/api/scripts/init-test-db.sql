-- Runs once when the local Docker database is first created.
-- A separate database keeps integration tests away from development data.
CREATE DATABASE berth_test OWNER berth;
