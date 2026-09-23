const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');

// Supabase project URL and anon key (from project settings > API)
const SUPABASE_URL = 'https://ubuqkdhajnnagropmatv.supabase.co';
// The anon key is safe for client-side use - get it from Supabase dashboard
// Project Settings > API > Project API keys > anon public
// For storage uploads we need service_role key OR public bucket with anon key

// Use pg-based approach: store PDFs as base64 in DB or use direct URL
// Better: use Supabase REST API with service role key
// OR: serve PDFs through a Netlify function that proxies from the DB/storage

// For now let's check if we can use the postgres connection to get the service key
const { Client } = require('pg');

async function main() {
  // Test - just list files
  const pdfDir = '/Users/geoffrey/Global_Key_Advisors/Migrating_Automated_Startup_Scraper/data/parsed/SPARK/pdfs';
  const files = fs.readdirSync(pdfDir).filter(f => f.endsWith('.pdf'));
  console.log(`Found ${files.length} PDFs:`);
  files.forEach(f => {
    const size = fs.statSync(path.join(pdfDir, f)).size;
    console.log(`  ${f} — ${Math.round(size/1024)}KB`);
  });
}

main();
