const { Client } = require('pg');

module.exports = async (req, res) => {
  const { username, passcode } = req.query || {};

  if (!username || !passcode) {
    return res.status(401).json({ error: "Missing auth" });
  }

  const client = new Client({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });

  try {
    await client.connect();
    
    // Auth check
    const authQuery = await client.query('SELECT * FROM admins WHERE username = $1 AND passcode = $2', [username, passcode]);
    if (authQuery.rows.length === 0) {
      await client.end();
      return res.status(401).json({ error: "Unauthorized" });
    }

    // Fetch data
    const judgesRes = await client.query('SELECT judge_id FROM judges ORDER BY judge_id ASC');
    const startupsRes = await client.query('SELECT startup_id as id, company_name as name FROM startup_extractions ORDER BY company_name ASC');
    const assignmentsRes = await client.query('SELECT judge_id, startup_id FROM judge_assignments');
    
    // Optional: Fetch review progress (how many distinct startups each judge has started/completed)
    // For simplicity, we just return the raw data and let the frontend compute relationships.
    
    await client.end();

    return res.status(200).json({
      judges: judgesRes.rows,
      startups: startupsRes.rows,
      assignments: assignmentsRes.rows
    });

  } catch (err) {
    console.error("Database Error:", err);
    return res.status(500).json({ error: "DB Error: " + err.message });
  }
};
