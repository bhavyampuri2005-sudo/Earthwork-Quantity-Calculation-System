-- Adds separate cut/fill side-slope columns (reviewer confirmed these
-- must differ: cut 1.5, fill 2.0). Renames the existing side_slope
-- column to side_slope_cut (your existing 1.5 placeholder row becomes
-- the cut value automatically, since it happens to match), then adds
-- side_slope_fill and sets it for that same row.

ALTER TABLE slopemaster RENAME COLUMN side_slope TO side_slope_cut;
ALTER TABLE slopemaster ADD COLUMN side_slope_fill NUMERIC(5,2);

UPDATE slopemaster
SET side_slope_cut = 1.5, side_slope_fill = 2.0
WHERE project_id = 1;

-- Verify:
-- SELECT * FROM slopemaster WHERE project_id = 1;
