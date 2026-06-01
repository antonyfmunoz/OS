import { db } from '../server/db';
import { sql } from 'drizzle-orm';

async function fixMessagesTable() {
  console.log('Starting messages table update...');
  
  try {
    // First check if the table exists by attempting to query it
    try {
      await db.execute(sql`SELECT 1 FROM messages LIMIT 1`);
      console.log('Messages table exists');
    } catch (error) {
      console.log('Messages table does not exist. No changes needed.');
      return;
    }

    // Check column structure directly with SQL
    const columnResult = await db.execute(sql`
      SELECT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'messages'
        AND column_name = 'role'
      ) as exists
    `);
    
    const roleExists = columnResult[0].exists;

    if (roleExists) {
      console.log('Role column already exists. No changes needed.');
    } else {
      // Check if sender_type column exists
      const senderTypeResult = await db.execute(sql`
        SELECT EXISTS (
          SELECT FROM information_schema.columns
          WHERE table_schema = 'public'
          AND table_name = 'messages'
          AND column_name = 'sender_type'
        ) as exists
      `);
      
      const senderTypeExists = senderTypeResult[0].exists;

      if (senderTypeExists) {
        console.log('Found sender_type column. Renaming to role...');
        
        // Create a backup of the current table
        await db.execute(sql`CREATE TABLE messages_backup AS SELECT * FROM messages`);
        console.log('✓ Created messages_backup table');

        // Rename the column
        await db.execute(sql`ALTER TABLE messages RENAME COLUMN sender_type TO role`);
        console.log('✓ Renamed sender_type column to role');
      } else {
        console.log('Neither role nor sender_type column found. Adding role column...');
        
        // Add role column with a default value
        await db.execute(sql`ALTER TABLE messages ADD COLUMN role text NOT NULL DEFAULT 'user'`);
        console.log('✓ Added role column with default value "user"');
      }
    }

    // Check for metadata column
    const metadataResult = await db.execute(sql`
      SELECT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'messages'
        AND column_name = 'metadata'
      ) as exists
    `);
    
    if (!metadataResult[0].exists) {
      await db.execute(sql`ALTER TABLE messages ADD COLUMN metadata text`);
      console.log('✓ Added metadata column');
    }

    // Check for referenced_agent_ids column
    const referencedAgentsResult = await db.execute(sql`
      SELECT EXISTS (
        SELECT FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'messages'
        AND column_name = 'referenced_agent_ids'
      ) as exists
    `);
    
    if (!referencedAgentsResult[0].exists) {
      await db.execute(sql`ALTER TABLE messages ADD COLUMN referenced_agent_ids text`);
      console.log('✓ Added referenced_agent_ids column');
    }

    console.log('Messages table update completed successfully!');
  } catch (error) {
    console.error('Error updating messages table:', error);
  }
}

// Run the script
fixMessagesTable()
  .then(() => {
    console.log('Messages table update completed');
    process.exit(0);
  })
  .catch(error => {
    console.error('Messages table update failed:', error);
    process.exit(1);
  });