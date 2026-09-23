const { Client } = require('pg');
const fs = require('fs');
const { execSync } = require('child_process');

console.log("Downloading mapping from remote...");
execSync('scp jkim@136.24.130.250:/tmp/ai_pdf_mapping.json .');

const mappingFile = JSON.parse(fs.readFileSync('ai_pdf_mapping.json', 'utf8'));
const mappings = mappingFile.mappings;
const meta = mappingFile.meta;

console.log(`Loaded mappings. Processed ${meta.total_documents} documents in ${Math.round(meta.duration_seconds/60)} minutes.`);
console.log(`AI Success: ${meta.ai_classified}, Regex Fallback: ${meta.regex_fallback}`);

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
  
  for (let row of res.rows) {
      const payload = row.payload;
      const companyMap = mappings[row.startup_id];
      if (!companyMap) continue;
      
      if (!payload.document || !payload.document.sections) continue;
      const rawSections = payload.document.sections;
      let allPdfs = [];
      for (let sec of rawSections) {
          if (sec.pdfs && Array.isArray(sec.pdfs)) {
              for (let pdf of sec.pdfs) {
                  if (typeof pdf === 'string') {
                      const filename = decodeURIComponent(pdf.split('/').pop());
                      allPdfs.push({ url: pdf, label: filename.replace(/_/g, ' ').replace('.pdf', '') });
                  } else if (pdf.url && pdf.label) allPdfs.push(pdf);
              }
          }
      }
      
      if (allPdfs.length === 0) continue;
      
      const grouped = {};
      for (let pdf of allPdfs) {
          const filename = decodeURIComponent(pdf.url.split('/').pop());
          
          let cat = 'IS';
          if (companyMap[filename] && companyMap[filename].cat_code) {
              cat = companyMap[filename].cat_code;
          }
          
          if (!grouped[cat]) grouped[cat] = [];
          if (!grouped[cat].some(p => p.url === pdf.url)) grouped[cat].push(pdf);
      }
      
      const newSections = [];
      for (const [cat, pdfs] of Object.entries(grouped)) {
          newSections.push({ heading: catHeadings[cat] || 'Application Documents', cat_code: cat, pdfs: pdfs });
      }
      
      payload.document.sections = newSections;
      await client.query("UPDATE startup_extractions SET payload = $1::jsonb WHERE startup_id = $2", [JSON.stringify(payload), row.startup_id]);
  }
  
  console.log("Successfully synced AI mappings to Supabase!");
  process.exit(0);
}
run();
