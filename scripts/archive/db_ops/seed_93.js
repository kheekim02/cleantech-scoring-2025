const { Client } = require('pg');

const client = new Client({
  connectionString: 'postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres?pgbouncer=true',
  ssl: { rejectUnauthorized: false }
});

async function run() {
  await client.connect();
  
  const res = await client.query("SELECT payload FROM startup_extractions WHERE startup_id = 'spark_inc'");
  const basePayload = res.rows[0].payload;
  
  console.log("Seeding 91 additional startups...");
  
  for (let i = 1; i <= 91; i++) {
    const newId = `startup_test_${i}`;
    const newName = `Test Company ${i} (Scalability)`;
    
    const payload = JSON.parse(JSON.stringify(basePayload));
    payload.meta = payload.meta || {};
    payload.meta.name = newName;
    payload.startup_id = newId;
    
    await client.query(
      "INSERT INTO startup_extractions (startup_id, company_name, payload) VALUES ($1, $2, $3) ON CONFLICT (startup_id) DO UPDATE SET payload = EXCLUDED.payload, company_name = EXCLUDED.company_name",
      [newId, newName, JSON.stringify(payload)]
    );
  }
  
  const finalCount = await client.query('SELECT COUNT(*) FROM startup_extractions');
  console.log(`Done! Total companies in DB: ${finalCount.rows[0].count}`);
  
  process.exit(0);
}
run().catch(console.error);
