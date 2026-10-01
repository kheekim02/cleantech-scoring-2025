const { pool } = require('./_db');
const { requireSession, isTestScorer } = require('./_auth');
const { applyHumanProjectionInPlace } = require('./_project_startup');

module.exports = async (req, res) => {
  const { id } = req.query || {};

  if (!id) {
    return res.status(400).json({ error: 'Missing required parameters' });
  }

  try {
    const session = await requireSession(pool, req, res, 'scorer');
    if (!session) return;

    const isTest = await isTestScorer(pool, session.principalId);

    if (!isTest) {
      const assignment = await pool.query(
        'SELECT 1 FROM judge_assignments WHERE judge_id = $1 AND startup_id = $2',
        [session.principalId, id]
      );
      if (assignment.rows.length === 0) {
        return res.status(403).json({ error: 'This startup is not assigned to you.' });
      }
    }

    const startupQuery = await pool.query(
      'SELECT payload FROM startup_extractions WHERE startup_id = $1',
      [id]
    );
    if (startupQuery.rows.length === 0) {
      return res.status(404).json({ error: 'Startup not found' });
    }

    const reviewsQuery = isTest
      ? { rows: [] }
      : await pool.query(
          'SELECT question_id, score_value, justification, is_flagged FROM human_reviews WHERE startup_id = $1 AND judge_id = $2',
          [id, session.principalId]
        );

    const payload = startupQuery.rows[0].payload;
    applyHumanProjectionInPlace(payload, reviewsQuery.rows, isTest);
    return res.status(200).json(payload);
  } catch (err) {
    console.error('Database Error:', err);
    return res.status(500).json({ error: 'DB Error: ' + err.message });
  }
};
