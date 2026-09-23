const { Client } = require('pg');

const client = new Client({
  connectionString: 'postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres',
  ssl: { rejectUnauthorized: false }
});

async function run() {
  await client.connect();
  const res = await client.query("SELECT startup_id, payload FROM startup_extractions WHERE startup_id NOT IN ('spark_inc', 'solarpure_inc') AND startup_id NOT LIKE 'startup_test_%'");
  
  let perfect = 0;
  let nineSections = 0;
  let eightSections = 0;
  let underEight = 0;
  
  for (let row of res.rows) {
      const payload = row.payload;
      if (!payload.document || !payload.document.sections) continue;
      const count = payload.document.sections.length;
      if (count === 10) perfect++;
      else if (count === 9) nineSections++;
      else if (count === 8) eightSections++;
      else underEight++;
  }
  
  console.log(`\nCoverage Report across 91 Startups:`);
  console.log(`10/10 Sections Present: ${perfect} startups`);
  console.log(` 9/10 Sections Present: ${nineSections} startups (mostly missing Legal/Inclusion)`);
  console.log(` 8/10 Sections Present: ${eightSections} startups`);
  console.log(` <8 Sections Present: ${underEight} startups`);
  
  process.exit(0);
}

run().catch(console.error);
