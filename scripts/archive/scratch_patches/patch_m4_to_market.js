const { Client } = require('pg');

const client = new Client({
  connectionString: 'postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres',
  ssl: { rejectUnauthorized: false }
});

const catHeadings = {
  'BC': 'Business Canvas', 'ES': 'Environmental & Social', 'PMF': 'Product Market Fit',
  'M': 'Market & Customers', 'TP': 'Tech / Product', 'F': 'Financials',
  'L': 'Legal', 'T': 'Team', 'IS': 'Executive Summary', 'IP': 'Investor Pitch'
};

function isM4File(filename) {
  const f = filename.toLowerCase();
  // Must NOT be EBD4 (which is Technology Validation)
  if (f.includes('ebd4') || f.includes('ebd_4') || f.includes('ebd-4')) {
    return false;
  }
  // Must match Module 4 / M4 patterns
  return (
    f.includes('m4questions') ||
    f.includes('m4_questions') ||
    f.includes('m4-questions') ||
    f.includes('m4_assignment') ||
    f.includes('module_4') ||
    f.includes('module-4') ||
    f.includes('module 4') ||
    (f.includes('m4') && !f.includes('ebd4') && !f.includes('m40') && !f.includes('m45'))
  );
}

async function run() {
  await client.connect();
  console.log("Connected to Supabase.");

  const res = await client.query("SELECT startup_id, payload FROM startup_extractions WHERE startup_id NOT IN ('spark_inc', 'solarpure_inc') AND startup_id NOT LIKE 'startup_test_%'");
  
  let totalMoved = 0;
  let companiesAffected = 0;

  for (const row of res.rows) {
    const payload = row.payload;
    const startupId = row.startup_id;

    if (!payload.document || !payload.document.sections) continue;

    let companyMoved = 0;
    // Flatten all PDFs with their current or updated category
    const allPdfsWithCat = [];

    for (const sec of payload.document.sections) {
      const currentCat = sec.cat_code;
      if (!sec.pdfs || !Array.isArray(sec.pdfs)) continue;

      for (const pdf of sec.pdfs) {
        const filename = decodeURIComponent(typeof pdf === 'string' ? pdf.split('/').pop() : pdf.url.split('/').pop());
        const label = typeof pdf === 'string' ? filename.replace(/_/g, ' ').replace('.pdf', '') : (pdf.label || filename);
        const url = typeof pdf === 'string' ? pdf : pdf.url;

        let targetCat = currentCat;
        if (isM4File(filename)) {
          if (currentCat !== 'M') {
            targetCat = 'M';
            companyMoved++;
            console.log(`[${startupId}] Moving M4 file: ${filename} (${currentCat} -> M)`);
          }
        }

        allPdfsWithCat.push({
          pdfObj: { url, label },
          cat: targetCat
        });
      }
    }

    if (companyMoved > 0) {
      companiesAffected++;
      totalMoved += companyMoved;

      // Regroup
      const grouped = {};
      for (const item of allPdfsWithCat) {
        if (!grouped[item.cat]) grouped[item.cat] = [];
        if (!grouped[item.cat].some(p => p.url === item.pdfObj.url)) {
          grouped[item.cat].push(item.pdfObj);
        }
      }

      const newSections = [];
      for (const [cat, pdfs] of Object.entries(grouped)) {
        newSections.push({
          heading: catHeadings[cat] || 'Application Documents',
          cat_code: cat,
          pdfs: pdfs
        });
      }

      payload.document.sections = newSections;
      await client.query("UPDATE startup_extractions SET payload = $1::jsonb WHERE startup_id = $2", [
        JSON.stringify(payload),
        startupId
      ]);
    }
  }

  console.log(`\n=== PATCH COMPLETE ===`);
  console.log(`Total M4 files moved to Market & Customers: ${totalMoved}`);
  console.log(`Total startups updated: ${companiesAffected}`);
  process.exit(0);
}

run();
