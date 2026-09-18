const { Client } = require('pg');

exports.handler = async (event, context) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: "Method Not Allowed" };
  }

  let payload;
  try {
    payload = JSON.parse(event.body);
  } catch (err) {
    return { statusCode: 400, body: JSON.stringify({ error: "Invalid JSON body" }) };
  }

  const { startup_id, scores, judge_id, passcode } = payload;
  
  if (!judge_id || !passcode) {
    return { statusCode: 401, body: JSON.stringify({ error: "Missing Scorer ID or Passcode" }) };
  }

  // Connect to Supabase via the Connection Pooler
  const client = new Client({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });

  try {
    await client.connect();

    // 1. Internal Authentication: Verify against the judges table
    const authQuery = await client.query('SELECT * FROM judges WHERE judge_id = $1 AND passcode = $2', [judge_id, passcode]);
    
    if (authQuery.rows.length === 0) {
      await client.end();
      return { statusCode: 401, body: JSON.stringify({ error: "Invalid Scorer ID or Passcode." }) };
    }

    // If it's just a login check (scores array is empty), return success early
    if (scores.length === 0) {
      await client.end();
      return { statusCode: 200, body: JSON.stringify({ success: true, message: "Authenticated." }) };
    }

    // 2. Upsert scores into the human_reviews table
    for (const item of scores) {
      await client.query(`
        INSERT INTO human_reviews (startup_id, question_id, judge_id, score_value)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (startup_id, question_id, judge_id) 
        DO UPDATE SET score_value = EXCLUDED.score_value, updated_at = NOW();
      `, [startup_id, item.qid, judge_id, item.val]);
    }

    await client.end();
    return {
      statusCode: 200,
      body: JSON.stringify({ success: true, message: `Successfully synced ${scores.length} scores.` })
    };

  } catch (err) {
    console.error("Database Error:", err);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: "DB Error: " + err.message })
    };
  }
};
