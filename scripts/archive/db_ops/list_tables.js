const fs = require('fs');
const env = fs.readFileSync('.env', 'utf8');
const dbUrl = env.split('=')[1].trim().replace(/'/g, '');
const { Client } = require('pg');

async function run() {
  const client = new Client({ connectionString: dbUrl, ssl: { rejectUnauthorized: false } });
  await client.connect();
  const res = await client.query(`SELECT table_name FROM information_schema.tables WHERE table_schema='public';`);
  console.log(res.rows);
  await client.end();
}
run();
