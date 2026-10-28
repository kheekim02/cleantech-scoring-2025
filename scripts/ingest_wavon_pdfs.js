/**
 * Ingestion script to load Wavon Ceramics deliverable PDFs into PostgreSQL table startup_deliverable_files.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { Client } = require('pg');

const RAW_DIR = '/Users/geoffrey/Global_Key_Advisors/Migrating_Automated_Startup_Scraper/data/raw/Wavon_Ceramics_—_Accelerating_Manufacturing/2025_CTO_Accelerator/Application_Phase';
const STARTUP_ID = 'Wavon_Ceramics_—_Accelerating_Manufacturing';

async function main() {
  if (!fs.existsSync(RAW_DIR)) {
    throw new Error(`Directory not found: ${RAW_DIR}`);
  }

  // Load DATABASE_URL from .env if not in process.env
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

  if (!dbUrl) {
    throw new Error('DATABASE_URL is required');
  }

  const client = new Client({ connectionString: dbUrl, ssl: { rejectUnauthorized: false } });
  await client.connect();

  const files = fs.readdirSync(RAW_DIR).filter(f => f.endsWith('.pdf')).sort();
  console.log(`Found ${files.length} PDF files for ${STARTUP_ID} in ${RAW_DIR}`);

  let totalBytes = 0;
  for (const file of files) {
    const fullPath = path.join(RAW_DIR, file);
    const buffer = fs.readFileSync(fullPath);
    const size = buffer.length;
    totalBytes += size;

    // Validate PDF magic bytes (%PDF-)
    const magic = buffer.slice(0, 5).toString('ascii');
    if (!magic.startsWith('%PDF')) {
      throw new Error(`File ${file} does not appear to be a valid PDF (magic bytes: ${magic})`);
    }

    const sha256 = crypto.createHash('sha256').update(buffer).digest('hex');

    await client.query(
      `
      INSERT INTO startup_deliverable_files (startup_id, filename, file_bytes, mime_type, file_size_bytes, sha256, updated_at)
      VALUES ($1, $2, $3, $4, $5, $6, NOW())
      ON CONFLICT (startup_id, filename)
      DO UPDATE SET
        file_bytes = EXCLUDED.file_bytes,
        mime_type = EXCLUDED.mime_type,
        file_size_bytes = EXCLUDED.file_size_bytes,
        sha256 = EXCLUDED.sha256,
        updated_at = NOW();
      `,
      [STARTUP_ID, file, buffer, 'application/pdf', size, sha256]
    );

    console.log(`  ✓ Ingested: ${file} (${Math.round(size / 1024)} KB, sha256: ${sha256.slice(0, 12)}...)`);
  }

  const verify = await client.query(
    'SELECT COUNT(*)::int as count, SUM(file_size_bytes)::bigint as total_bytes FROM startup_deliverable_files WHERE startup_id = $1',
    [STARTUP_ID]
  );

  console.log(`\nIngestion complete!`);
  console.log(`Total rows in startup_deliverable_files for ${STARTUP_ID}: ${verify.rows[0].count}`);
  console.log(`Total stored bytes: ${verify.rows[0].total_bytes} bytes (${(verify.rows[0].total_bytes / 1024 / 1024).toFixed(2)} MB)`);

  await client.end();
}

main().catch(err => {
  console.error('Fatal ingestion error:', err);
  process.exit(1);
});
