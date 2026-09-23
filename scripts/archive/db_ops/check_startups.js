const fs = require('fs');
const env = fs.readFileSync('.env', 'utf8');
const dbUrl = env.split('=')[1].trim().replace(/'/g, '');
const { Client } = require('pg');

async function run() {
  const client = new Client({ connectionString: dbUrl, ssl: { rejectUnauthorized: false } });
  await client.connect();
  const res = await client.query(`SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'startup_extractions';`);
  console.log(res.rows);
  await client.end();
}
run();
