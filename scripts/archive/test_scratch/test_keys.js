const { Client } = require('pg');
const { execSync } = require('child_process');

const client = new Client({
  connectionString: 'postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres',
  ssl: { rejectUnauthorized: false }
});

async function run() {
  await client.connect();
  const dryCompanies = ['AmpTrans', 'Averra', 'Bonhomme_&_Associates', 'Condor_Calibration_Services', 'Novagrid'];
  
  for (const comp of dryCompanies) {
    const res = await client.query('SELECT payload->\'document\'->\'sections\' as sections FROM startup_extractions WHERE startup_id = $1', [comp]);
    const sections = res.rows[0]?.sections || [];
    const dbPdfs = new Set();
    sections.forEach(s => (s.pdfs || []).forEach(p => dbPdfs.add(decodeURIComponent(p.url.split('/').pop()))));
    
    const remoteFilesRaw = execSync(`ssh jkim@136.24.130.250 "ls '/data/scraping/datasets/cto_accelerator/parsed/${comp}/converted/'"`).toString();
    const diskPdfs = new Set(
      remoteFilesRaw.split('\n')
        .filter(f => f.endsWith('.pdf.md'))
        .map(f => f.slice(0, -3))
    );
    
    let matched = 0;
    dbPdfs.forEach(pdf => {
      if (diskPdfs.has(pdf)) matched++;
      else console.log(`[${comp}] Missing on disk:`, pdf);
    });
    console.log(`[${comp}] DB PDFs: ${dbPdfs.size}, Disk PDFs: ${diskPdfs.size}, Matched: ${matched}/${dbPdfs.size}`);
  }
  process.exit();
}
run();
