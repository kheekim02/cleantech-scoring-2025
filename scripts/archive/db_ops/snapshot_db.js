const { Client } = require('pg');
const fs = require('fs');

const client = new Client({
  connectionString: 'postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres',
  ssl: { rejectUnauthorized: false }
});

async function run() {
  await client.connect();
  console.log("Connected to Supabase. Creating pre-AI snapshot...");
  const res = await client.query("SELECT startup_id, payload->'document'->'sections' as sections FROM startup_extractions WHERE startup_id NOT IN ('spark_inc', 'solarpure_inc') AND startup_id NOT LIKE 'startup_test_%'");
  
  const snapshot = {};
  res.rows.forEach(r => {
    snapshot[r.startup_id] = r.sections;
  });
  
  fs.writeFileSync('db_snapshot_pre_ai.json', JSON.stringify(snapshot, null, 2));
  console.log(`Snapshot saved successfully! Captured ${Object.keys(snapshot).length} startups into db_snapshot_pre_ai.json.`);
  process.exit(0);
}
run();
