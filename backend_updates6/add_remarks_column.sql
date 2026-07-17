-- Adds the Remarks column Module 4 of the SRS specifies for Slope Master
-- (soil type / notes per chainage range), currently missing.
ALTER TABLE slopemaster ADD COLUMN remarks VARCHAR(255);
