const { Client } = require('pg');

exports.handler = async (event, context) => {
  // 1. Verify Authentication via Netlify Identity
  const user = context.clientContext && context.clientContext.user;
  if (!user) {
    return {
      statusCode: 401,
      body: JSON.stringify({ error: "Unauthorized. Please log in." })
    };
  }

  // Only allow POST requests
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: "Method Not Allowed" };
  }

  let payload;
  try {
    payload = JSON.parse(event.body);
  } catch (err) {
    return { statusCode: 400, body: JSON.stringify({ error: "Invalid JSON body" }) };
  }

  const { startup_id, scores } = payload;
  if (!startup_id || !Array.isArray(scores)) {
    return { statusCode: 400, body: JSON.stringify({ error: "Missing startup_id or scores array" }) };
  }

  // 2. Connect to Supabase via the Connection Pooler
  const client = new Client({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });

  try {
    await client.connect();

    // 3. Upsert scores into the human_reviews table
    for (const item of scores) {
      await client.query(`
        INSERT INTO human_reviews (startup_id, question_id, judge_id, score_value)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (startup_id, question_id, judge_id) 
        DO UPDATE SET score_value = EXCLUDED.score_value, updated_at = NOW();
      `, [startup_id, item.qid, user.email, item.val]);
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
      body: JSON.stringify({ error: "Internal Database Error" })
    };
  }
};
