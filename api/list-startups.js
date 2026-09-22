const { Client } = require('pg');
const { requireSession } = require('./_auth');

module.exports = async (req, res) => {
  const client = new Client({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });

  try {
    await client.connect();
    
    const session = await requireSession(client, req, res, 'scorer');
    if (!session) {
      await client.end();
      return;
    }

    const listQuery = await client.query('SELECT s.startup_id as id, s.company_name as name FROM startup_extractions s INNER JOIN judge_assignments ja ON s.startup_id = ja.startup_id WHERE ja.judge_id = $1 ORDER BY s.company_name ASC', [session.principalId]);
    await client.end();

    return res.status(200).json(listQuery.rows);

  } catch (err) {
    console.error("Database Error:", err);
    return res.status(500).json({ error: "DB Error: " + err.message });
  }
};
