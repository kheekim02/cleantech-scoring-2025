const { Client } = require('pg');

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    return res.status(405).send("Method Not Allowed");
  }

  let payload = req.body;
  if (typeof payload === 'string') {
    try { payload = JSON.parse(payload); } catch(e) {}
  }

  const { startup_id, scores, judge_id, passcode } = payload || {};
  
  if (!judge_id || !passcode) {
    return res.status(401).json({ error: "Missing Scorer ID or Passcode" });
  }

  const client = new Client({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });

  try {
    await client.connect();

    const authQuery = await client.query('SELECT * FROM judges WHERE judge_id = $1 AND passcode = $2', [judge_id, passcode]);
    
    if (authQuery.rows.length === 0) {
      await client.end();
      return res.status(401).json({ error: "Invalid Scorer ID or Passcode." });
    }

    if (!scores || scores.length === 0) {
      await client.end();
      return res.status(200).json({ success: true, message: "Authenticated." });
    }

    for (const item of scores) {
      const scoreVal = (item.val !== null && item.val !== undefined) ? parseFloat(item.val) : null;
      const justVal = (item.justification && item.justification.trim().length > 0) ? item.justification.trim() : null;

      await client.query(`
        INSERT INTO human_reviews (startup_id, question_id, judge_id, score_value, justification)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (startup_id, question_id, judge_id) 
        DO UPDATE SET 
          score_value = COALESCE(EXCLUDED.score_value, human_reviews.score_value),
          justification = COALESCE(EXCLUDED.justification, human_reviews.justification),
          updated_at = NOW();
      `, [startup_id, item.qid, judge_id, scoreVal, justVal]);
    }

    await client.end();
    return res.status(200).json({ success: true, message: `Successfully synced ${scores.length} scores.` });

  } catch (err) {
    console.error("Database Error:", err);
    return res.status(500).json({ error: "DB Error: " + err.message });
  }
};
