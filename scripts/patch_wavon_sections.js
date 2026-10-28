/**
 * Update Wavon Ceramics document.sections in PostgreSQL table startup_extractions.
 * Maps all 18 ingested deliverables to the 10 rubric categories and OTHER.
 */
const { Client } = require('pg');
const fs = require('fs');

const STARTUP_ID = 'Wavon_Ceramics_—_Accelerating_Manufacturing';

const CATEGORY_MAPPINGS = [
  {
    cat_code: 'BC',
    heading: 'Business Canvas',
    files: ['04_WavonCeramics_BusinessModelCanvas.pdf']
  },
  {
    cat_code: 'ES',
    heading: 'Environmental & Social',
    files: [
      '05_WavonCeramics_M2ImpactSustainaiblityQuestions.pdf',
      '06_WavonCeramics_GHGERP.pdf',
      '07_WavonCeramics_EBD2ImpactStatement.pdf',
      '16_WavonCeramics_InclusionAssignment.pdf'
    ]
  },
  {
    cat_code: 'F',
    heading: 'Financials',
    files: [
      '12_WavonCeramics_M6Questions.pdf',
      '13_WavonCeramics_FinancialProjection.pdf'
    ]
  },
  {
    cat_code: 'IP',
    heading: 'Investor Pitch',
    files: ['18_WavonCeramics_InvestorPitch.pdf']
  },
  {
    cat_code: 'IS',
    heading: 'Impact Strategy',
    files: ['17_WavonCeramics_ExecutiveSummary.pdf']
  },
  {
    cat_code: 'L',
    heading: 'Legal',
    files: [
      '14_WavonCeramics_M7Questions.pdf',
      '16_WavonCeramics_InclusionAssignment.pdf'
    ]
  },
  {
    cat_code: 'M',
    heading: 'Marketing',
    files: [
      '09_WavonCeramics_M4Questions.pdf',
      '10_WavonCeramics_EBD3CustomerSegmentationCompetitiveMatrix.pdf'
    ]
  },
  {
    cat_code: 'PMF',
    heading: 'Product Market Fit',
    files: [
      '03_WavonCeramics_M1CustomerDiscoveryInterviews.pdf',
      '08_WavonCeramics_M3AssignmentQuestion.pdf'
    ]
  },
  {
    cat_code: 'T',
    heading: 'Team',
    files: [
      '02_WavonCeramics_TeamTargets.pdf',
      '15_WavonCeramics_M8Questions.pdf'
    ]
  },
  {
    cat_code: 'TP',
    heading: 'Tech / Product',
    files: ['11_WavonCeramics_EBD4TechnologyValidation.pdf']
  },
  {
    cat_code: 'OTHER',
    heading: 'Supporting Documents & Deliverables',
    files: ['01_Supplementary.pdf']
  }
];

function buildSections(startupId) {
  return CATEGORY_MAPPINGS.map(cat => ({
    cat_code: cat.cat_code,
    heading: cat.heading,
    pdfs: cat.files.map(filename => ({
      url: `/api/get-startup?id=${encodeURIComponent(startupId)}&file=${encodeURIComponent(filename)}`,
      label: filename.replace(/_/g, ' ').replace(/\.pdf$/i, '')
    }))
  }));
}

async function main() {
  let dbUrl = process.env.DATABASE_URL;
  if (!dbUrl && fs.existsSync('.env')) {
    const lines = fs.readFileSync('.env', 'utf8').split('\n');
    for (const line of lines) {
      if (line.startsWith('DATABASE_URL=')) {
        dbUrl = line.split('=', 2)[1].trim().replace(/^['"]|['"]$/g, '');
        break;
      }
    }
  }

  const client = new Client({ connectionString: dbUrl, ssl: { rejectUnauthorized: false } });
  await client.connect();

  console.log(`Fetching current record for ${STARTUP_ID}...`);
  const res = await client.query('SELECT payload FROM startup_extractions WHERE startup_id = $1', [STARTUP_ID]);
  if (res.rows.length === 0) {
    throw new Error(`Startup not found in startup_extractions: ${STARTUP_ID}`);
  }

  const payload = res.rows[0].payload;
  const sections = buildSections(STARTUP_ID);

  payload.document = payload.document || {};
  payload.document.sections = sections;

  console.log(`Generated ${sections.length} sections for ${STARTUP_ID}:`);
  sections.forEach(s => {
    console.log(`  [${s.cat_code}] ${s.heading}: ${s.pdfs.length} PDF(s)`);
    s.pdfs.forEach(p => console.log(`     - ${p.label} -> ${p.url}`));
  });

  await client.query(
    'UPDATE startup_extractions SET payload = $1::jsonb WHERE startup_id = $2',
    [JSON.stringify(payload), STARTUP_ID]
  );

  console.log(`\nSuccessfully updated startup_extractions for ${STARTUP_ID}!`);

  // Verify
  const verify = await client.query('SELECT payload->\'document\'->\'sections\' as sections FROM startup_extractions WHERE startup_id = $1', [STARTUP_ID]);
  const verifiedSections = verify.rows[0].sections;
  console.log(`Verified stored sections count: ${verifiedSections.length}`);

  let totalFiles = 0;
  verifiedSections.forEach(s => totalFiles += s.pdfs.length);
  console.log(`Total mapped file references: ${totalFiles}`);

  await client.end();
}

main().catch(err => {
  console.error('Update error:', err);
  process.exit(1);
});
