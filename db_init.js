const { Client } = require('pg');
const fs = require('fs');
const path = require('path');

const connectionString = 'postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres?pgbouncer=true';

async function initDB() {
  const client = new Client({
    connectionString,
    ssl: { rejectUnauthorized: false }
  });

  try {
    console.log("Connecting to Supabase...");
    await client.connect();

    console.log("Creating startup_extractions table...");
    await client.query(`
      CREATE TABLE IF NOT EXISTS startup_extractions (
        startup_id    TEXT PRIMARY KEY,
        company_name  TEXT NOT NULL,
        payload       JSONB NOT NULL,
        ingested_at   TIMESTAMP WITH TIME ZONE DEFAULT NOW()
      );
      CREATE INDEX IF NOT EXISTS idx_extractions_name ON startup_extractions (company_name);
    `);
    console.log("Table created.");

    // Load mock data
    const mockDataPath = path.join(__dirname, 'site', 'data', 'startups', 'solarpure.json');
    const mockData = JSON.parse(fs.readFileSync(mockDataPath, 'utf8'));

    console.log("Seeding solarpure.json...");
    await client.query(`
      INSERT INTO startup_extractions (startup_id, company_name, payload)
      VALUES ($1, $2, $3::jsonb)
      ON CONFLICT (startup_id) DO UPDATE SET payload = EXCLUDED.payload, ingested_at = NOW();
    `, [mockData.meta.id, mockData.meta.name, JSON.stringify(mockData)]);
    console.log("Seed complete.");

  } catch (err) {
    console.error("Error initializing DB:", err);
  } finally {
    await client.end();
  }
}

initDB();
