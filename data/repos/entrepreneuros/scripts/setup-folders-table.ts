import { db } from "../server/db";
import { folders } from "../shared/schema";
import { sql } from "drizzle-orm";

/**
 * Creates the folder table if it doesn't exist
 */
async function createFoldersTable() {
  try {
    console.log("Setting up folders table...");

    // Create the folders table
    await db.execute(sql`
      CREATE TABLE IF NOT EXISTS folders (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        parent_id TEXT REFERENCES folders(id),
        user_id TEXT REFERENCES users(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);

    // Add the folder_id column to the documents table if it doesn't exist
    await db.execute(sql`
      ALTER TABLE documents 
      ADD COLUMN IF NOT EXISTS folder_id TEXT REFERENCES folders(id);
    `);

    console.log("Folders table setup complete!");
  } catch (error) {
    console.error("Error setting up folders table:", error);
  } finally {
    process.exit(0);
  }
}

createFoldersTable();