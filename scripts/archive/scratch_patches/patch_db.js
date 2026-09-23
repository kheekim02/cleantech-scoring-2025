const fs = require('fs');
const env = fs.readFileSync('.env', 'utf8');
const dbUrl = env.split('=')[1].trim().replace(/'/g, '');
const { Client } = require('pg');

async function run() {
  const client = new Client({
    connectionString: dbUrl,
    ssl: { rejectUnauthorized: false }
  });
  await client.connect();
  try {
    await client.query(`ALTER TABLE human_reviews ADD COLUMN justification text;`);
    console.log("Column 'justification' added successfully.");
  } catch (err) {
    if (err.code === '42701') {
      console.log("Column already exists. Skipping.");
    } else {
      console.error("Error adding column:", err);
    }
  }
  await client.end();
}
run();
