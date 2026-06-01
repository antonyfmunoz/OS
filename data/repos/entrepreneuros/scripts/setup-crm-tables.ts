import { db, client } from '../server/db';
import { 
  crmContacts, 
  crmDeals, 
  crmActivities 
} from '../shared/schema';
import { sql } from 'drizzle-orm';

async function createCrmTables() {
  console.log('Creating CRM tables if they do not exist...');
  
  try {
    // Ensure contacts table exists
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "crm_contacts" (
        "id" text PRIMARY KEY,
        "name" text NOT NULL,
        "email" text NOT NULL,
        "phone" text,
        "company" text,
        "title" text,
        "status" text DEFAULT 'lead',
        "last_contact" timestamp,
        "notes" text,
        "avatar" text,
        "user_id" text REFERENCES "users"("id"),
        "created_at" timestamp DEFAULT now(),
        "updated_at" timestamp DEFAULT now()
      );
    `);
    console.log('✓ crm_contacts table created/verified');
    
    // Ensure deals table exists
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "crm_deals" (
        "id" text PRIMARY KEY,
        "title" text NOT NULL,
        "company" text NOT NULL,
        "value" text NOT NULL,
        "stage" text DEFAULT 'discovery',
        "probability" integer DEFAULT 50,
        "expected_close_date" timestamp,
        "contact_id" text REFERENCES "crm_contacts"("id"),
        "assigned_agent_id" text REFERENCES "agents"("id"),
        "notes" text,
        "user_id" text REFERENCES "users"("id"),
        "created_at" timestamp DEFAULT now(),
        "updated_at" timestamp DEFAULT now()
      );
    `);
    console.log('✓ crm_deals table created/verified');
    
    // Ensure activities table exists
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS "crm_activities" (
        "id" text PRIMARY KEY,
        "type" text NOT NULL,
        "subject" text NOT NULL,
        "date" timestamp NOT NULL,
        "related_to_type" text NOT NULL,
        "related_to_id" text NOT NULL,
        "completed" boolean DEFAULT false,
        "notes" text,
        "created_by_agent_id" text REFERENCES "agents"("id"),
        "user_id" text REFERENCES "users"("id"),
        "created_at" timestamp DEFAULT now(),
        "updated_at" timestamp DEFAULT now()
      );
    `);
    console.log('✓ crm_activities table created/verified');
    
    console.log('All CRM tables have been successfully created/verified!');
  } catch (error) {
    console.error('Error creating CRM tables:', error);
  } finally {
    await client.end();
  }
}

createCrmTables();