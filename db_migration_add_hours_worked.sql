-- Migration script to add hours_worked column to attendance table

ALTER TABLE attendance ADD COLUMN hours_worked REAL DEFAULT 0;
