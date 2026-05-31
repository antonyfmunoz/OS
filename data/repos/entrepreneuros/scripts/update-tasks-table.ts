import { db, client } from '../server/db';
import { sql } from 'drizzle-orm';

async function updateTasksTable() {
  console.log('Starting tasks table update...');
  
  try {
    // Add the missing columns to the tasks table
    await db.execute(sql`
      DO $$
      BEGIN
        -- Check if start_date column exists, if not add it
        IF NOT EXISTS (
          SELECT 1 FROM information_schema.columns 
          WHERE table_name = 'tasks' AND column_name = 'start_date'
        ) THEN
          ALTER TABLE tasks ADD COLUMN start_date text;
        END IF;

        -- Check if instructions column exists, if not add it
        IF NOT EXISTS (
          SELECT 1 FROM information_schema.columns 
          WHERE table_name = 'tasks' AND column_name = 'instructions'
        ) THEN
          ALTER TABLE tasks ADD COLUMN instructions text;
        END IF;

        -- Check if assigned_by_id column exists, if not add it
        IF NOT EXISTS (
          SELECT 1 FROM information_schema.columns 
          WHERE table_name = 'tasks' AND column_name = 'assigned_by_id'
        ) THEN
          ALTER TABLE tasks ADD COLUMN assigned_by_id text REFERENCES agents(id);
        END IF;
        
        -- Check if metadata column exists, if not add it
        IF NOT EXISTS (
          SELECT 1 FROM information_schema.columns 
          WHERE table_name = 'tasks' AND column_name = 'metadata'
        ) THEN
          ALTER TABLE tasks ADD COLUMN metadata text;
        END IF;
      END
      $$;
    `);
    
    console.log('✓ Updated tasks table with missing columns');

    console.log('Tasks table update completed successfully!');
  } catch (error) {
    console.error('Error updating tasks table:', error);
  } finally {
    // Close the connection
    await client.end();
  }
}

// Run the script
updateTasksTable()
  .then(() => {
    console.log('Tasks table update completed successfully!');
    process.exit(0);
  })
  .catch(error => {
    console.error('Tasks table update failed:', error);
    process.exit(1);
  });