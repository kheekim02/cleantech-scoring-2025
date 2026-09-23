const { Client } = require('pg');

// Map: category code → ordered list of PDF files for that category
const CAT_TO_PDFS = {
  BC:  [{ file: '03_SPARK_EBD1_Business_Model_Canvas.pdf', label: 'Business Model Canvas' }],
  ES:  [
    { file: '04_SPARK_M2ImpactSustainaiblityQuestions.pdf', label: 'Impact & Sustainability Questions' },
    { file: '05_SPARK_EBD2ImpactStatement.pdf', label: 'Impact Statement' },
    { file: '14_SPARK_InclusionAssigment.pdf', label: 'Inclusion Assignment' },
  ],
  F:   [{ file: '11_SPARK_Financial_Projection.pdf', label: 'Financial Projections' }],
  IP:  [{ file: '09_SPARK_EBD4TechnologyValidation_docx.pdf', label: 'Technology Validation' }],
  IS:  [
    { file: '15_SPARK_EBD6_Executive_Summary.pdf', label: 'Executive Summary' },
    { file: '16_SPARK_Making_Energy_Intelligent.pdf', label: 'Making Energy Intelligent' },
  ],
  L:   [{ file: '01_SPARK_Team_Targets.pdf', label: 'Team Targets' }],
  M:   [{ file: '08_SPARK_EBD3CustomerSegmentationCompetitiveMatrix.pdf', label: 'Customer Segmentation & Competitive Matrix' }],
  PMF: [
    { file: '02_SPARK_M1_Customer_Interview_Capture.pdf', label: 'Customer Interview Capture' },
    { file: '06_SPARK_M3AssignmentQuestion.pdf', label: 'M3 Assignment' },
  ],
  T:   [{ file: '09_SPARK_EBD4TechnologyValidation_docx.pdf', label: 'Technology Validation' }],
  TP:  [
    { file: '07_SPARK_M4Questions.pdf', label: 'M4 Questions' },
    { file: '10_SPARK_M6Questions.pdf', label: 'M6 Questions' },
    { file: '12_SPARK_M7Questions.pdf', label: 'M7 Questions' },
    { file: '13_SPARK_M8Questions.pdf', label: 'M8 Questions' },
  ],
};

const BASE_PDF_URL = '/pdfs/spark';

async function main() {
  const client = new Client({
    connectionString: 'postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres?pgbouncer=true',
    ssl: { rejectUnauthorized: false }
  });
  await client.connect();

  const res = await client.query("SELECT payload FROM startup_extractions WHERE startup_id = 'spark_inc'");
  const payload = res.rows[0].payload;

  // Replace the document.sections with PDF-based sections
  payload.document.sections = Object.entries(CAT_TO_PDFS).map(([cat_code, pdfs]) => ({
    cat_code,
    heading: pdfs[0].label,
    pdfs: pdfs.map(p => ({
      url: `${BASE_PDF_URL}/${p.file}`,
      filename: p.file,
      label: p.label
    }))
    // No more 'text' field — the left pane will render PDF iframes
  }));

  await client.query(
    "UPDATE startup_extractions SET payload = $1::jsonb WHERE startup_id = 'spark_inc'",
    [JSON.stringify(payload)]
  );

  console.log(`✅ Updated payload with PDF sections for ${payload.document.sections.length} categories`);
  payload.document.sections.forEach(s => {
    console.log(`  ${s.cat_code}: ${s.pdfs.length} PDF(s)`);
  });
  await client.end();
}

main().catch(console.error);
