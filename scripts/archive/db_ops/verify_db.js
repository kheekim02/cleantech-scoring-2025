const { Client } = require('pg');
const client = new Client({
  connectionString: 'postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres',
  ssl: { rejectUnauthorized: false }
});

async function verify() {
  await client.connect();
  const testComps = ['Averra', 'Bonhomme_&_Associates', 'Novagrid'];
  for (const comp of testComps) {
    const res = await client.query('SELECT payload->\'document\'->\'sections\' as sections FROM startup_extractions WHERE startup_id = $1', [comp]);
    console.log(`\n=== ${comp} ===`);
    res.rows[0].sections.forEach(s => {
      console.log(`  [${s.cat_code}] ${s.heading} (${s.pdfs.length} files):`);
      s.pdfs.forEach(p => console.log(`     - ${p.label}`));
    });
  }
  process.exit(0);
}
verify();
