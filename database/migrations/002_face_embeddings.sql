-- Biometric entries (Day 10). Embeddings only: no images are ever stored.

ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS embedding_model TEXT;
ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS embedding_dim INTEGER;
ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS embedding_count INTEGER NOT NULL DEFAULT 0;

-- Vehicles and plates never carry an embedding; FACE entries must; PERSON entries may.
ALTER TABLE watchlist DROP CONSTRAINT IF EXISTS watchlist_embedding_rules;
ALTER TABLE watchlist ADD CONSTRAINT watchlist_embedding_rules CHECK (
       (entity_type IN ('VEHICLE', 'PLATE') AND embedding IS NULL)
    OR (entity_type = 'PERSON')
    OR (entity_type = 'FACE' AND embedding IS NOT NULL
        AND embedding_model IS NOT NULL AND embedding_dim IS NOT NULL));

-- Hits can now come from a face match, not only from a plate.
ALTER TABLE watchlist_hits ALTER COLUMN plate DROP NOT NULL;
ALTER TABLE watchlist_hits ALTER COLUMN plate_confidence DROP NOT NULL;
ALTER TABLE watchlist_hits ADD COLUMN IF NOT EXISTS match_basis TEXT NOT NULL DEFAULT 'plate'
    CHECK (match_basis IN ('plate', 'face'));
ALTER TABLE watchlist_hits ADD COLUMN IF NOT EXISTS similarity REAL;
ALTER TABLE watchlist_hits DROP CONSTRAINT IF EXISTS watchlist_hits_match_type_check;
ALTER TABLE watchlist_hits ADD CONSTRAINT watchlist_hits_match_type_check
    CHECK (match_type IN ('exact', 'near', 'face'));
