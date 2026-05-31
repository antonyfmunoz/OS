import { db, client } from '../server/db';
import { sql } from 'drizzle-orm';

async function setupTables() {
  console.log('Starting database tables setup...');
  
  try {
    // First create the users table
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "users" (
        "id" text PRIMARY KEY,
        "username" text UNIQUE NOT NULL,
        "password" text NOT NULL,
        "email" text NOT NULL,
        "full_name" text,
        "avatar" text,
        "company" text,
        "role" text,
        "firebase_uid" text UNIQUE,
        "preferences" text,
        "metadata" jsonb,
        "created_at" timestamp DEFAULT now(),
        "updated_at" timestamp DEFAULT now()
      );
    `);
    console.log('✓ Users table created/verified');

    // Then create the agents table
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "agents" (
        "id" text PRIMARY KEY,
        "name" text NOT NULL,
        "role" text NOT NULL,
        "role_level" text DEFAULT 'laborer',
        "department" text DEFAULT 'general',
        "icon" text DEFAULT 'ri-robot-line',
        "instructions" text,
        "brain_content" text,
        "knowledge_base" text,
        "kpis" text,
        "behavioral_style" text,
        "latest_activity" text,
        "is_active" boolean DEFAULT true,
        "simulation_mode" boolean DEFAULT false,
        "parent_agent_id" text,
        "created_at" timestamp DEFAULT now(),
        "updated_at" timestamp DEFAULT now()
      );
    `);
    console.log('✓ Agents table created/verified');

    // Create tasks table
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "tasks" (
        "id" text PRIMARY KEY,
        "title" text NOT NULL,
        "description" text,
        "status" text NOT NULL,
        "start_date" text,
        "due_date" text,
        "agent_id" text REFERENCES "agents"("id"),
        "priority" text DEFAULT 'medium',
        "task_type" text DEFAULT 'standard',
        "parent_task_id" text REFERENCES "tasks"("id"),
        "collaborator_ids" text[],
        "assigned_by_id" text REFERENCES "agents"("id"),
        "instructions" text,
        "metadata" text,
        "created_at" timestamp DEFAULT now(),
        "updated_at" timestamp DEFAULT now()
      );
    `);
    console.log('✓ Tasks table created/verified');

    // Create messages table
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "messages" (
        "id" text PRIMARY KEY,
        "content" text NOT NULL,
        "agent_id" text REFERENCES "agents"("id"),
        "task_id" text REFERENCES "tasks"("id"),
        "conversation_id" text,
        "sender_type" text NOT NULL,
        "timestamp" timestamp DEFAULT now()
      );
    `);
    console.log('✓ Messages table created/verified');

    // Create integrations table
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "integrations" (
        "id" text PRIMARY KEY,
        "name" text NOT NULL,
        "type" text NOT NULL,
        "status" text NOT NULL,
        "details" text,
        "icon" text
      );
    `);
    console.log('✓ Integrations table created/verified');

    // Create notifications table
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
      );
    `);
    console.log('✓ Notifications table created/verified');

    // Create AI messages table
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "ai_messages" (
        "id" text PRIMARY KEY,
        "user_id" text REFERENCES "users"("id"),
        "content" text NOT NULL,
        "role" text NOT NULL,
        "timestamp" timestamp DEFAULT now()
      );
    `);
    console.log('✓ AI messages table created/verified');

    console.log('All core tables have been successfully created/verified!');
  } catch (error) {
    console.error('Error creating tables:', error);
  } finally {
    // Close the connection
    await client.end();
  }
}

// Run the script
setupTables()
  .then(() => {
    console.log('Database setup completed successfully!');
    process.exit(0);
  })
  .catch(error => {
    console.error('Database setup failed:', error);
    process.exit(1);
  });