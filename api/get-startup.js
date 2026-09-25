const { Client } = require('pg');
const { requireSession, isTestScorer } = require('./_auth');

module.exports = async (req, res) => {
  const { id } = req.query || {};

  if (!id) {
    return res.status(400).json({ error: "Missing required parameters" });
  }

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

    const isTest = await isTestScorer(client, session.principalId);

    if (!isTest) {
      const assignment = await client.query(
        'SELECT 1 FROM judge_assignments WHERE judge_id = $1 AND startup_id = $2',
        [session.principalId, id]
      );
      if (assignment.rows.length === 0) {
        await client.end();
        return res.status(403).json({ error: 'This startup is not assigned to you.' });
      }
    }

    const startupQuery = await client.query('SELECT payload FROM startup_extractions WHERE startup_id = $1', [id]);
    if (startupQuery.rows.length === 0) {
      await client.end();
      return res.status(404).json({ error: "Startup not found" });
    }

    const reviewsQuery = isTest
      ? { rows: [] }
      : await client.query(
          'SELECT question_id, score_value, justification FROM human_reviews WHERE startup_id = $1 AND judge_id = $2',
          [id, session.principalId]
        );
    await client.end();

    const payload = startupQuery.rows[0].payload;
    payload.judge_reviews = reviewsQuery.rows;
    payload.is_test = isTest;

    return res.status(200).json(payload);

  } catch (err) {
    console.error("Database Error:", err);
    return res.status(500).json({ error: "DB Error: " + err.message });
  } finally {
    try { await client.end(); } catch(e) {}
  }
};
