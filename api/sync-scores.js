const { Client } = require('pg');
const { requireSession, isTestScorer } = require('./_auth');

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    return res.status(405).send("Method Not Allowed");
  }

  let payload = req.body;
  if (typeof payload === 'string') {
    try { payload = JSON.parse(payload); } catch(e) {}
  }

  const { startup_id, scores } = payload || {};
  
  if (!startup_id) {
    return res.status(400).json({ error: 'Missing startup ID.' });
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

    // CRITICAL: If test/preview account, DO NOT touch human_reviews table!
    if (isTest) {
      await client.end();
      return res.status(200).json({
        success: true,
        message: 'Test / Admin Preview Mode: Scores are not persisted to database.',
        test_mode: true
      });
    }

    if (!scores || scores.length === 0) {
      await client.end();
      return res.status(200).json({ success: true, message: "Authenticated." });
    }

    const assignment = await client.query(
      'SELECT 1 FROM judge_assignments WHERE judge_id = $1 AND startup_id = $2',
      [session.principalId, startup_id]
    );
    if (assignment.rows.length === 0) {
      await client.end();
      return res.status(403).json({ error: 'This startup is not assigned to you.' });
    }

    const startup = await client.query('SELECT payload FROM startup_extractions WHERE startup_id = $1', [startup_id]);
    if (startup.rows.length !== 1) {
      await client.end();
      return res.status(404).json({ error: 'Startup not found.' });
    }
    const questions = new Map((startup.rows[0].payload?.human_questions || []).map(question => [question.new_q_id || question.q_id, question]));

    for (const item of scores) {
      const question = questions.get(item.qid);
      if (!question) {
        await client.end();
        return res.status(400).json({ error: `Unknown question: ${item.qid}` });
      }
      const scoreVal = (item.val !== null && item.val !== undefined) ? parseFloat(item.val) : null;
      const justVal = (item.justification && item.justification.trim().length > 0) ? item.justification.trim() : null;
      const allowedScores = Array.isArray(question.options) && question.options.length > 0
        ? question.options.map(option => Number(option.val))
        : [0, 0.25, 0.5, 0.75, 1];
      if (scoreVal !== null && (!Number.isFinite(scoreVal) || !allowedScores.includes(scoreVal))) {
        await client.end();
        return res.status(400).json({ error: `Invalid score for ${item.qid}` });
      }
      await client.query(`
        INSERT INTO human_reviews (startup_id, question_id, judge_id, score_value, justification)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (startup_id, question_id, judge_id) 
        DO UPDATE SET 
          score_value = COALESCE(EXCLUDED.score_value, human_reviews.score_value),
          justification = COALESCE(EXCLUDED.justification, human_reviews.justification),
          updated_at = NOW();
      `, [startup_id, item.qid, session.principalId, scoreVal, justVal]);
    }

    await client.end();
    return res.status(200).json({ success: true, message: `Successfully synced ${scores.length} scores.` });

  } catch (err) {
    console.error("Database Error:", err);
    return res.status(500).json({ error: "DB Error: " + err.message });
  } finally {
    try { await client.end(); } catch(e) {}
  }
};
