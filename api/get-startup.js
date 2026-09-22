const { Client } = require('pg');

module.exports = async (req, res) => {
  const { id, judge_id, passcode } = req.query || {};

  if (!id || !judge_id || !passcode) {
    return res.status(400).json({ error: "Missing required parameters" });
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
      return res.status(401).json({ error: "Unauthorized" });
    }

    const startupQuery = await client.query('SELECT payload FROM startup_extractions WHERE startup_id = $1', [id]);
    if (startupQuery.rows.length === 0) {
      await client.end();
      return res.status(404).json({ error: "Startup not found" });
    }

    const reviewsQuery = await client.query(
      'SELECT question_id, score_value, justification FROM human_reviews WHERE startup_id = $1 AND judge_id = $2',
      [id, judge_id]
    );
    await client.end();

    const payload = startupQuery.rows[0].payload;
    payload.judge_reviews = reviewsQuery.rows;

    return res.status(200).json(payload);

  } catch (err) {
    console.error("Database Error:", err);
    return res.status(500).json({ error: "DB Error: " + err.message });
  }
};
