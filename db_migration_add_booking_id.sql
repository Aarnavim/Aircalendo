-- Migration script to add booking_id column to attendance table

ALTER TABLE attendance ADD COLUMN booking_id INTEGER;
