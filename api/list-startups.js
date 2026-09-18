const { Client } = require('pg');

module.exports = async (req, res) => {
  const { judge_id, passcode } = req.query || {};

  if (!judge_id || !passcode) {
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

    const listQuery = await client.query('SELECT startup_id as id, company_name as name FROM startup_extractions ORDER BY company_name ASC');
    await client.end();

    return res.status(200).json(listQuery.rows);

  } catch (err) {
    console.error("Database Error:", err);
    return res.status(500).json({ error: "DB Error: " + err.message });
  }
};
