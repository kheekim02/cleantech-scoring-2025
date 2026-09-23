const { Client } = require('pg');
const fs = require('fs');

const mappingFile = JSON.parse(fs.readFileSync('ai_pdf_mapping_hybrid.json', 'utf8'));
const mappings = mappingFile.mappings;
const meta = mappingFile.meta;

console.log("=== PRE-SYNC AUDIT ===");
console.log(`Total Documents in Mapping: ${meta.total_documents}`);
console.log(`High-Confidence Rules: ${meta.rule_hits} (${(meta.rule_hits/meta.total_documents*100).toFixed(1)}%)`);
console.log(`Dynamic AI Calls: ${meta.ai_calls} (${(meta.ai_calls/meta.total_documents*100).toFixed(1)}%)`);
console.log(`Agreement with Baseline Regex: ${(meta.hybrid_agreement*100).toFixed(1)}%`);

const client = new Client({
  connectionString: 'postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres',
  ssl: { rejectUnauthorized: false }
});

const catHeadings = {
  'BC': 'Business Canvas', 'ES': 'Environmental & Social', 'PMF': 'Product Market Fit',
  'M': 'Market & Customers', 'TP': 'Tech / Product', 'F': 'Financials',
  'L': 'Legal', 'T': 'Team', 'IS': 'Executive Summary', 'IP': 'Investor Pitch'
};

async function run() {
  await client.connect();
  console.log("Connected to Supabase.");

  const res = await client.query("SELECT startup_id, payload FROM startup_extractions WHERE startup_id NOT IN ('spark_inc', 'solarpure_inc') AND startup_id NOT LIKE 'startup_test_%'");
  
  let totalDbPdfs = 0;
  let totalMatchedPdfs = 0;
  const updates = [];

  for (const row of res.rows) {
    const payload = row.payload;
    const startupId = row.startup_id;
    const companyMap = mappings[startupId];

    if (!payload.document || !payload.document.sections) continue;

    let allPdfs = [];
    for (const sec of payload.document.sections) {
      if (sec.pdfs && Array.isArray(sec.pdfs)) {
        for (const pdf of sec.pdfs) {
          if (typeof pdf === 'string') {
            const filename = decodeURIComponent(pdf.split('/').pop());
            allPdfs.push({ url: pdf, label: filename.replace(/_/g, ' ').replace('.pdf', '') });
          } else if (pdf.url && pdf.label) {
            allPdfs.push(pdf);
          }
        }
      }
    }

    if (allPdfs.length === 0) continue;

    const grouped = {};
    for (const pdf of allPdfs) {
      totalDbPdfs++;
      const filename = decodeURIComponent(pdf.url.split('/').pop());

      let cat = null;
      let matchSource = null;

      if (companyMap && companyMap[filename] && companyMap[filename].cat_code) {
        cat = companyMap[filename].cat_code;
        matchSource = companyMap[filename].source;
        totalMatchedPdfs++;
      } else {
        // Log miss
        console.warn(`[MISS] ${startupId} -> ${filename}`);
      }

      // If missing from map, fallback to IS
      if (!cat) {
        cat = 'IS';
      }

      if (!grouped[cat]) grouped[cat] = [];
      if (!grouped[cat].some(p => p.url === pdf.url)) {
        grouped[cat].push(pdf);
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
    updates.push({ startup_id: startupId, payload });
  }

  const matchRate = (totalMatchedPdfs / totalDbPdfs) * 100;
  console.log(`\nDB Key Match Rate: ${totalMatchedPdfs} / ${totalDbPdfs} (${matchRate.toFixed(2)}%)`);

  if (matchRate < 90.0) {
    console.error(`[CRITICAL] Match rate (${matchRate.toFixed(2)}%) is below the 90% threshold gate! Aborting database write.`);
    process.exit(1);
  }

  console.log("Key match gate PASSED! Writing updates to Supabase...");

  for (const item of updates) {
    await client.query(
      "UPDATE startup_extractions SET payload = $1::jsonb WHERE startup_id = $2",
      [JSON.stringify(item.payload), item.startup_id]
    );
  }

  console.log(`Successfully updated ${updates.length} startups in Supabase!`);
  process.exit(0);
}

run();
