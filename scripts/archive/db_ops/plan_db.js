const fs = require('fs');
const env = fs.readFileSync('.env', 'utf8');
const dbUrl = env.split('=')[1].trim().replace(/'/g, '');
const { Client } = require('pg');

async function run() {
  const client = new Client({ connectionString: dbUrl, ssl: { rejectUnauthorized: false } });
  await client.connect();
  
  try {
    await client.query(`
      CREATE TABLE IF NOT EXISTS admins (
        username text PRIMARY KEY,
        passcode text NOT NULL
      );
      INSERT INTO admins (username, passcode) VALUES ('admin', 'admin2025') ON CONFLICT DO NOTHING;
      
      CREATE TABLE IF NOT EXISTS judge_assignments (
        judge_id text NOT NULL,
        startup_id text NOT NULL,
        PRIMARY KEY (judge_id, startup_id)
      );
    `);
    console.log("Admin and assignment tables ready.");
  } catch(e) {
    console.log(e);
  }
  await client.end();
}
run();
