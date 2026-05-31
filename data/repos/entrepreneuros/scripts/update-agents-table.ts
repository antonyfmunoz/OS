import { db, client } from '../server/db';
import { sql } from 'drizzle-orm';

async function updateAgentsTable() {
  console.log('Starting agents table update...');
  
  try {
    // Add the missing columns to the agents table
    await db.execute(sql`
      DO $$
      BEGIN
        -- Check if knowledge_base column exists, if not add it
        IF NOT EXISTS (
          SELECT 1 FROM information_schema.columns 
          WHERE table_name = 'agents' AND column_name = 'knowledge_base'
        ) THEN
          ALTER TABLE agents ADD COLUMN knowledge_base text;
        END IF;

        -- Check if kpis column exists, if not add it
        IF NOT EXISTS (
          SELECT 1 FROM information_schema.columns 
          WHERE table_name = 'agents' AND column_name = 'kpis'
        ) THEN
          ALTER TABLE agents ADD COLUMN kpis text;
        END IF;

        -- Check if behavioral_style column exists, if not add it
        IF NOT EXISTS (
          SELECT 1 FROM information_schema.columns 
          WHERE table_name = 'agents' AND column_name = 'behavioral_style'
        ) THEN
          ALTER TABLE agents ADD COLUMN behavioral_style text;
        END IF;
        
        -- Check if is_active column exists, if not add it
        IF NOT EXISTS (
          SELECT 1 FROM information_schema.columns 
          WHERE table_name = 'agents' AND column_name = 'is_active'
        ) THEN
          ALTER TABLE agents ADD COLUMN is_active boolean DEFAULT true;
        END IF;
        
        -- Check if simulation_mode column exists, if not add it
        IF NOT EXISTS (
          SELECT 1 FROM information_schema.columns 
          WHERE table_name = 'agents' AND column_name = 'simulation_mode'
        ) THEN
          ALTER TABLE agents ADD COLUMN simulation_mode boolean DEFAULT false;
        END IF;
        
        -- Check if parent_agent_id column exists, if not add it
        IF NOT EXISTS (
          SELECT 1 FROM information_schema.columns 
          WHERE table_name = 'agents' AND column_name = 'parent_agent_id'
        ) THEN
          ALTER TABLE agents ADD COLUMN parent_agent_id text;
        END IF;
      END
      $$;
    `);
    
    console.log('✓ Updated agents table with missing columns');

    console.log('Agents table update completed successfully!');
  } catch (error) {
    console.error('Error updating agents table:', error);
  } finally {
    // Close the connection
    await client.end();
  }
}

// Run the script
updateAgentsTable()
  .then(() => {
    console.log('Agents table update completed successfully!');
    process.exit(0);
  })
  .catch(error => {
    console.error('Agents table update failed:', error);
    process.exit(1);
  });