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

function guessCatCode(filename) {
    const f = filename.toLowerCase();
    
    // Explicit precedence to avoid generic words capturing specific docs
    if (f.includes('inclusion') || f.includes('m7')) return 'L';
    if (f.includes('impact') && !f.includes('statement')) return 'ES';
    if (f.includes('statement')) return 'IS'; 
    if (f.includes('ghg') || f.includes('erp') || f.includes('sustainab') || f.includes('ebd2') || f.includes('ebd9')) return 'ES';
    if (f.includes('canvas') || f.includes('bmc') || f.includes('ebd1') && !f.includes('ebd10')) return 'BC';
    if (f.includes('segment') || f.includes('matrix') || f.includes('ebd3')) return 'M';
    if (f.includes('technology') || f.includes('validation') || f.includes('ebd4') || f.includes('m4')) return 'TP';
    if (f.includes('financ') || f.includes('projection') || f.includes('pro_forma') || f.includes('proforma') || f.includes('profit') || f.includes('loss') || f.includes('ebd5') || f.includes('m6')) return 'F';
    if (f.includes('team') || f.includes('target') || f.includes('ebd10') || f.includes('m8')) return 'T';
    if (f.includes('pitch') || f.includes('deck') || f.includes('ebd8')) return 'IP';
    if (f.includes('discovery') || f.includes('interview') || f.includes('m1') || f.includes('m3') || f.includes('assignment')) return 'PMF';
    if (f.includes('executive') || f.includes('summary') || f.includes('1pager') || f.includes('one_page') || f.includes('ebd6')) return 'IS';
    return 'IS';
}

async function run() {
  await client.connect();
  const res = await client.query("SELECT startup_id, payload FROM startup_extractions WHERE startup_id NOT IN ('spark_inc', 'solarpure_inc') AND startup_id NOT LIKE 'startup_test_%'");
  for (let row of res.rows) {
      const payload = row.payload;
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
          const cat = guessCatCode(pdf.url.split('/').pop());
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
  process.exit(0);
}
run();
