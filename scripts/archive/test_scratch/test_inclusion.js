const { Client } = require('pg');

const client = new Client({
  connectionString: 'postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres',
  ssl: { rejectUnauthorized: false }
});

async function run() {
  await client.connect();
  const res = await client.query("SELECT startup_id, payload FROM startup_extractions WHERE startup_id = 'Averra'");
  const payload = res.rows[0].payload;
  
  payload.document.sections.forEach(s => {
      s.pdfs.forEach(p => {
          if(p.filename.toLowerCase().includes('inclusion')) {
             console.log(`Found ${p.filename} mapped to ${s.cat_code}`);
          }
      });
  });
  
  process.exit(0);
}
run();
