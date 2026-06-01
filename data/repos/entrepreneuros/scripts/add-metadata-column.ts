import { Pool, neonConfig } from '@neondatabase/serverless';
import ws from 'ws';
import { sql } from "drizzle-orm";

// Configure Neon to use WebSockets
neonConfig.webSocketConstructor = ws;

// Connect directly to the database
const pool = new Pool({ connectionString: process.env.DATABASE_URL });

/**
 * This script adds a metadata JSONB column to the users table
 * to track notification preferences and other user-specific settings.
 */
async function addMetadataColumn() {
  try {
    console.log("Starting migration: Adding metadata column to users table...");
    
    // Check if the column already exists to avoid errors
    const checkColumnResult = await pool.query(`
      SELECT column_name
      FROM information_schema.columns 
      WHERE table_name = 'users' AND column_name = 'metadata';
    `);
    
    if (checkColumnResult.rows.length > 0) {
      console.log("Column 'metadata' already exists in users table, skipping...");
      return;
    }
    
    // Add the metadata column
    await pool.query(`
      ALTER TABLE users
      ADD COLUMN metadata JSONB;
    `);
    
    console.log("Successfully added metadata column to users table!");
    
  } catch (error) {
    console.error("Error adding metadata column:", error);
    throw error;
  } finally {
    // Close the connection pool
    await pool.end();
  }
}

// Run the migration
addMetadataColumn()
  .then(() => {
    console.log("Migration completed successfully!");
    process.exit(0);
  })
  .catch(error => {
    console.error("Migration failed:", error);
    process.exit(1);
  });