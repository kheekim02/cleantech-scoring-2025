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
    await client.end();

    if (startupQuery.rows.length === 0) {
      return res.status(404).json({ error: "Startup not found" });
    }

    return res.status(200).json(startupQuery.rows[0].payload);

  } catch (err) {
    console.error("Database Error:", err);
    return res.status(500).json({ error: "DB Error: " + err.message });
  }
};
