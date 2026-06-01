import { db, client } from '../server/db';
import { sql } from 'drizzle-orm';

async function updateNotificationsTable() {
  console.log('Starting notifications table update...');
  
  try {
    let tableExists = false;
    let count = 0;
    
    try {
      const checkTable = await db.execute(sql`SELECT to_regclass('notifications') IS NOT NULL as exists`);
      tableExists = checkTable.rows[0].exists;
      
      if (tableExists) {
        const countResult = await db.execute(sql`SELECT COUNT(*) as count FROM notifications`);
        count = parseInt(countResult.rows[0].count);
        console.log(`Table exists with ${count} rows`);
      }
    } catch (err) {
      console.log('Table check failed, assuming table does not exist:', err.message);
      tableExists = false;
    }
    
    if (tableExists && count > 0) {
      console.log(`Found ${count} notifications. Creating backup before modifying the table.`);
      try {
        await db.execute(sql`CREATE TABLE IF NOT EXISTS notifications_backup AS SELECT * FROM notifications`);
        console.log('✓ Created notifications_backup table');
      } catch (err) {
        console.error('Failed to create backup:', err.message);
      }
    }
    
    if (tableExists) {
      await db.execute(sql`DROP TABLE IF EXISTS notifications CASCADE`);
      console.log('✓ Dropped old notifications table');
    }
    
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "notifications" (
        "id" text PRIMARY KEY,
        "user_id" text REFERENCES "users"("id"),
        "title" text NOT NULL,
        "content" text NOT NULL,
        "type" text NOT NULL,
        "read" boolean DEFAULT false,
        "href" text,
        "related_id" text,
        "metadata" jsonb,
        "created_at" timestamp DEFAULT now()
      )
    `);
    console.log('✓ Created notifications table with correct structure');
    
    if (tableExists && count > 0) {
      try {
        await db.execute(sql`
          INSERT INTO notifications (id, user_id, title, content, type, read, href, created_at)
          SELECT id, user_id, title, message, COALESCE(type, 'general'), read, link, created_at 
          FROM notifications_backup
        `);
        console.log('✓ Restored notification data with updated structure');
      } catch (error) {
        console.error('Failed to restore notifications data:', error.message);
      }
    }
    
    console.log('Notifications table update completed successfully!');
  } catch (error) {
    console.error('Error updating notifications table:', error.message);
  } finally {
    await client.end();
  }
}

updateNotificationsTable()
  .then(() => {
    console.log('Notifications table update completed');
    process.exit(0);
  })
  .catch(error => {
    console.error('Notifications table update failed:', error);
    process.exit(1);
  });
