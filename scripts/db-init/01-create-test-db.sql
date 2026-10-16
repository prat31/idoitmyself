-- Runs once when the Postgres container initializes an empty data volume.
-- Creates the database used by the backend test suite (see tests/backend/conftest.py).
CREATE DATABASE idim_test;
