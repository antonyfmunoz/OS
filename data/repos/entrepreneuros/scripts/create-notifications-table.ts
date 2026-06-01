import { client } from '../server/db';

async function createNotificationsTable() {
  try {
    console.log('Creating notifications table...');
    
    // Create notifications table
    await client.unsafe(`
      CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        type TEXT NOT NULL,
        read BOOLEAN NOT NULL DEFAULT FALSE,
        href TEXT,
        related_id TEXT,
        metadata JSONB,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
      );
    `);
    
    console.log('Notifications table created successfully.');
  } catch (error) {
    console.error('Error creating notifications table:', error);
  } finally {
    await client.end();
  }
}

createNotificationsTable();