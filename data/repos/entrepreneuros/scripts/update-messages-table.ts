import { db } from '../server/db';
import { sql } from 'drizzle-orm';

async function updateMessagesTable() {
  console.log('Starting messages table update...');
  
  try {
    const tableCheck = await db.execute(sql`SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'messages')`);
    const tableExists = tableCheck.rows[0].exists;

    if (!tableExists) {
      console.log('Messages table does not exist. No changes needed.');
      return;
    }

    const columnCheck = await db.execute(sql`
      SELECT column_name
      FROM information_schema.columns
      WHERE table_schema = 'public'
      AND table_name = 'messages'
      AND column_name = 'role'
    `);

    const roleColumnExists = columnCheck.rows.length > 0;

    if (roleColumnExists) {
      console.log('Role column already exists. No changes needed.');
      return;
    }

    const senderTypeCheck = await db.execute(sql`
      SELECT column_name
      FROM information_schema.columns
      WHERE table_schema = 'public'
      AND table_name = 'messages'
      AND column_name = 'sender_type'
    `);

    const senderTypeExists = senderTypeCheck.rows.length > 0;

    if (senderTypeExists) {
      console.log('Found sender_type column. Renaming to role...');
      
      await db.execute(sql`CREATE TABLE messages_backup AS SELECT * FROM messages`);
      console.log('✓ Created messages_backup table');

      await db.execute(sql`ALTER TABLE messages RENAME COLUMN sender_type TO role`);
      console.log('✓ Renamed sender_type column to role');
    } else {
      console.log('Neither role nor sender_type column found. Adding role column...');
      
      await db.execute(sql`
        ALTER TABLE messages 
        ADD COLUMN role text NOT NULL DEFAULT 'user'
      `);
      console.log('✓ Added role column with default value "user"');
    }

    const columnsCheck = await db.execute(sql`
      SELECT column_name
      FROM information_schema.columns
      WHERE table_schema = 'public'
      AND table_name = 'messages'
    `);

    const existingColumns = columnsCheck.rows.map((row: any) => row.column_name);

    if (!existingColumns.includes('metadata')) {
      await db.execute(sql`ALTER TABLE messages ADD COLUMN metadata text`);
      console.log('✓ Added metadata column');
    }

    if (!existingColumns.includes('referenced_agent_ids')) {
      await db.execute(sql`ALTER TABLE messages ADD COLUMN referenced_agent_ids text`);
      console.log('✓ Added referenced_agent_ids column');
    }

    console.log('Messages table update completed successfully!');
  } catch (error) {
    console.error('Error updating messages table:', error);
  }
}

// Run the script
updateMessagesTable()
  .then(() => {
    console.log('Messages table update completed');
    process.exit(0);
  })
  .catch(error => {
    console.error('Messages table update failed:', error);
    process.exit(1);
  });