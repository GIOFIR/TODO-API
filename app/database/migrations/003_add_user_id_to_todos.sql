-- Add user_id column to todos table

-- First add the column without constraint
ALTER TABLE todos 
ADD COLUMN IF NOT EXISTS user_id INTEGER;

-- Then add the foreign key constraint
DO $$
BEGIN
    -- Check if the foreign key constraint doesn't already exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'todos_user_id_fkey' 
        AND table_name = 'todos'
    ) THEN
        ALTER TABLE todos 
        ADD CONSTRAINT todos_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    END IF;
END;
$$;

-- Create index for user_id
CREATE INDEX IF NOT EXISTS idx_todos_user_id ON todos(user_id);
