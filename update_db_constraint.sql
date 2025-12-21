-- Update the analyses_method_check constraint to include similarity_comparison
-- Run this SQL on your Render PostgreSQL database

-- Drop the old constraint
ALTER TABLE analyses DROP CONSTRAINT IF EXISTS analyses_method_check;

-- Add the updated constraint with similarity_comparison included
ALTER TABLE analyses ADD CONSTRAINT analyses_method_check 
CHECK (method IN (
    'chromaprint',
    'hpcp',
    'dtw',
    'lyrics',
    'music_identification',
    'similarity_detection',
    'melody_similarity',
    'cover_detection',
    'similarity_comparison',
    'other'
));

-- Verify the constraint was added
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conname = 'analyses_method_check';
