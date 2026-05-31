import { db, client } from '../server/db';
import { documents } from '../shared/schema';
import { sql } from 'drizzle-orm';

async function createDocumentsTable() {
  console.log('Creating documents table if it does not exist...');
  
  try {
    // Ensure documents table exists
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "documents" (
        "id" text PRIMARY KEY,
        "title" text NOT NULL,
        "content" text NOT NULL,
        "tags" text[],
        "user_id" text REFERENCES "users"("id"),
        "created_at" timestamp DEFAULT now(),
        "updated_at" timestamp DEFAULT now()
      );
    `);
    console.log('✓ documents table created/verified');
    
    console.log('Documents table has been successfully created/verified!');
  } catch (error) {
    console.error('Error creating documents table:', error);
  } finally {
    await client.end();
  }
}

createDocumentsTable();