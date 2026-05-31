import { db, client } from '../server/db';
import { sql } from 'drizzle-orm';
import crypto from 'crypto';
import { promisify } from 'util';

const scryptAsync = promisify(crypto.scrypt);

// Function to hash password, same as the one in auth.ts
async function hashPassword(password: string) {
  const salt = crypto.randomBytes(16).toString("hex");
  const buf = (await scryptAsync(password, salt, 64)) as Buffer;
  return `${buf.toString("hex")}.${salt}`;
}

async function createDemoUser() {
  console.log('Creating demo user...');
  
  try {
    // Check if the demo user already exists
    const existingUser = await db.execute(sql`
      SELECT * FROM users WHERE username = 'demo'
    `);
    
    if (existingUser.length > 0) {
      console.log('Demo user already exists');
      return;
    }
    
    // Hash the password
    const hashedPassword = await hashPassword('password');
    
    // Create the demo user
    await db.execute(sql`
      INSERT INTO users (
        id, username, password, email, full_name, role, created_at, updated_at
      ) VALUES (
        'user_demo', 'demo', ${hashedPassword}, 'demo@example.com', 'Demo User', 'admin', NOW(), NOW()
      )
    `);
    
    console.log('✓ Created demo user with username: demo, password: password');
  } catch (error) {
    console.error('Error creating demo user:', error);
  } finally {
    // Close the connection
    await client.end();
  }
}

// Run the script
createDemoUser()
  .then(() => {
    console.log('Demo user creation completed');
    process.exit(0);
  })
  .catch(error => {
    console.error('Demo user creation failed:', error);
    process.exit(1);
  });