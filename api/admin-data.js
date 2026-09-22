const { Client } = require('pg');
const { requireSession } = require('./_auth');

module.exports = async (req, res) => {
  const client = new Client({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });

  try {
    await client.connect();
    
    const session = await requireSession(client, req, res, 'admin');
    if (!session) {
      await client.end();
      return;
    }

    // Fetch data
    const judgesRes = await client.query('SELECT judge_id FROM judges ORDER BY judge_id ASC');
    const startupsRes = await client.query("SELECT startup_id as id, company_name as name, COALESCE((payload->'meta'->>'clean_ready')::boolean, false) as clean_ready FROM startup_extractions ORDER BY company_name ASC");
    const assignmentsRes = await client.query('SELECT judge_id, startup_id, assigned_at FROM judge_assignments');
    const progressRes = await client.query('SELECT judge_id, startup_id, count(question_id) as answered_count FROM human_reviews GROUP BY judge_id, startup_id');
    
    // Optional: Fetch review progress (how many distinct startups each judge has started/completed)
    // For simplicity, we just return the raw data and let the frontend compute relationships.
    
    await client.end();

    return res.status(200).json({
      judges: judgesRes.rows,
      startups: startupsRes.rows,
      assignments: assignmentsRes.rows,
      progress: progressRes.rows
    });

  } catch (err) {
    console.error("Database Error:", err);
    return res.status(500).json({ error: "DB Error: " + err.message });
  }
};
