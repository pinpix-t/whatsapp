-- Add is_archived column to conversations table
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;

-- Create index for filtering archived conversations
CREATE INDEX IF NOT EXISTS idx_conversations_is_archived ON conversations(is_archived);

