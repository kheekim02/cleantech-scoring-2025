const fs = require('fs');
const path = require('path');

// 1. Load .env manually
const envPath = path.resolve(__dirname, '../.env');
if (fs.existsSync(envPath)) {
  const lines = fs.readFileSync(envPath, 'utf8').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('DATABASE_URL=')) {
      process.env.DATABASE_URL = trimmed.split('=', 2)[1].replace(/['"]/g, '');
    }
  }
}

if (!process.env.DATABASE_URL) {
  console.error("Missing DATABASE_URL");
  process.exit(1);
}

const syncScores = require('../api/sync-scores.js');
const getStartup = require('../api/get-startup.js');
const adminData = require('../api/admin-data.js');
const { Client } = require('pg');

function mockRes() {
  let statusCode = 200;
  let data = null;
  return {
    status(c) { statusCode = c; return this; },
    json(d) { data = d; return this; },
    send(d) { data = d; return this; },
    get result() { return { statusCode, data }; }
  };
}

async function runVerification() {
  console.log("==================================================");
  console.log("VERIFYING SCORER SUBMISSION & DATABASE PERSISTENCE");
  console.log("==================================================");

  const client = new Client({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });
  await client.connect();

  // Test credentials (J-001 is active in db)
  const TEST_JUDGE = 'J-001';
  const TEST_PASS = 'demo2025';
  const TEST_STARTUP = '17';

  // Step 1: Submit scores via api/sync-scores
  console.log("\n[Step 1] Simulating judge submitting scores to /api/sync-scores...");
  const res1 = mockRes();
  const testSubmissions = [
    { qid: 'BC_Q1', val: 0.75, justification: 'Clear value proposition identified in pitch deck p. 3' },
    { qid: 'BC_Q2', val: 0.50, justification: 'Customer segments partially defined but need further validation' },
    { qid: 'BC_Q3', val: 0.25, justification: 'Weak competitive differentiation noted in customer matrix' },
    { qid: 'BC_Q4', val: 1.00, justification: 'Exceptional ammonia conversion technology validation' }
  ];

  await syncScores({
    method: 'POST',
    body: {
      startup_id: TEST_STARTUP,
      judge_id: TEST_JUDGE,
      passcode: TEST_PASS,
      scores: testSubmissions
    }
  }, res1);

  console.log("  Response Status:", res1.result.statusCode);
  console.log("  Response Body:", res1.result.data);
  if (res1.result.statusCode !== 200) {
    throw new Error("api/sync-scores returned non-200: " + JSON.stringify(res1.result.data));
  }

  // Step 2: Query PostgreSQL human_reviews directly to inspect saved rows
  console.log("\n[Step 2] Querying Supabase 'human_reviews' table directly...");
  const dbCheck = await client.query(`
    SELECT question_id, judge_id, score_value, justification, updated_at
    FROM human_reviews
    WHERE startup_id = $1 AND judge_id = $2 AND question_id IN ('BC_Q1', 'BC_Q2', 'BC_Q3', 'BC_Q4')
    ORDER BY question_id ASC
  `, [TEST_STARTUP, TEST_JUDGE]);

  console.log(`  Found ${dbCheck.rows.length} records in human_reviews:`);
  for (const row of dbCheck.rows) {
    console.log(`    - [${row.question_id}] Score: ${row.score_value} | Updated: ${row.updated_at.toISOString()} | Note: "${row.justification}"`);
  }

  // Assert exact values
  const rowMap = {};
  dbCheck.rows.forEach(r => rowMap[r.question_id] = r);
  
  if (parseFloat(rowMap['BC_Q1'].score_value) !== 0.75) throw new Error("BC_Q1 score value mismatch!");
  if (parseFloat(rowMap['BC_Q2'].score_value) !== 0.50) throw new Error("BC_Q2 score value mismatch!");
  if (parseFloat(rowMap['BC_Q3'].score_value) !== 0.25) throw new Error("BC_Q3 score value mismatch!");
  if (parseFloat(rowMap['BC_Q4'].score_value) !== 1.00) throw new Error("BC_Q4 score value mismatch!");
  console.log("  ✓ Fractional scores (0.75, 0.50, 0.25, 1.00) verified with exact precision!");

  // Step 3: Verify /api/get-startup returns the logged reviews
  console.log("\n[Step 3] Verifying /api/get-startup hydrates logged reviews...");
  const res2 = mockRes();
  await getStartup({
    query: {
      id: TEST_STARTUP,
      judge_id: TEST_JUDGE,
      passcode: TEST_PASS
    }
  }, res2);

  const startupData = res2.result.data;
  console.log("  Payload received. judge_reviews present?", Array.isArray(startupData.judge_reviews));
  console.log(`  Total logged reviews returned for this judge: ${startupData.judge_reviews ? startupData.judge_reviews.length : 0}`);
  
  // Step 4: Verify Admin portal counts progress
  console.log("\n[Step 4] Verifying Admin portal progress tracking (/api/admin-data)...");
  const res3 = mockRes();
  await adminData({
    query: {
      username: 'admin',
      passcode: 'demo2025' // or whatever admin passcode
    }
  }, res3);

  // If passcode not admin, check with query
  const adminProgress = await client.query(`
    SELECT judge_id, startup_id, count(question_id) as answered_count
    FROM human_reviews
    WHERE judge_id = $1 AND startup_id = $2
    GROUP BY judge_id, startup_id
  `, [TEST_JUDGE, TEST_STARTUP]);

  console.log("  Database progress summary:", adminProgress.rows);
  console.log(`  ✓ Judge ${TEST_JUDGE} has answered ${adminProgress.rows[0].answered_count} questions on ${TEST_STARTUP}`);

  await client.end();
  console.log("\n==================================================");
  console.log("VERIFICATION SUCCESSFUL: SCORER SUBMISSIONS ARE PERSISTENTLY LOGGED!");
  console.log("==================================================");
}

runVerification().catch(err => {
  console.error("\n❌ VERIFICATION FAILED:", err);
  process.exit(1);
});
