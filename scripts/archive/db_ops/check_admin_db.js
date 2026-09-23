const fs = require('fs');
const env = fs.readFileSync('.env', 'utf8');
const dbUrl = env.split('=')[1].trim().replace(/'/g, '');
const { Client } = require('pg');

async function run() {
  const client = new Client({ connectionString: dbUrl, ssl: { rejectUnauthorized: false } });
  await client.connect();
  
  const tables = ['judges', 'startups', 'human_reviews'];
  for (const t of tables) {
      console.log(`\n--- Table: ${t} ---`);
      try {
          const res = await client.query(`SELECT column_name, data_type FROM information_schema.columns WHERE table_name = $1;`, [t]);
          console.log(res.rows);
      } catch (e) {
          console.log("Error or missing table:", e.message);
      }
  }
  
  await client.end();
}
run();
