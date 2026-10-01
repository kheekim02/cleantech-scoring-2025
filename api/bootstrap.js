const { pool } = require('./_db');
const { requireSession, isTestScorer } = require('./_auth');
const { applyHumanProjectionInPlace } = require('./_project_startup');

module.exports = async (req, res) => {
  try {
    const session = await requireSession(pool, req, res, 'scorer');
    if (!session) return;

    const isTest = await isTestScorer(pool, session.principalId);

    let startups;
    if (isTest) {
      const listQuery = await pool.query(
        "SELECT startup_id as id, company_name as name FROM startup_extractions WHERE startup_id NOT ILIKE '%solarpure%' ORDER BY company_name ASC"
      );
      startups = listQuery.rows;
    } else {
      const listQuery = await pool.query(
        `SELECT s.startup_id as id, s.company_name as name
         FROM startup_extractions s
         INNER JOIN judge_assignments ja ON s.startup_id = ja.startup_id
         WHERE ja.judge_id = $1 AND s.startup_id NOT ILIKE '%solarpure%'
         ORDER BY s.company_name ASC`,
        [session.principalId]
      );
      startups = listQuery.rows;
    }

    const requestedId = (req.query && req.query.startup_id) || null;
    let activeId = null;
    if (requestedId && startups.some((s) => s.id === requestedId)) {
      activeId = requestedId;
    } else if (startups.length > 0) {
      activeId = startups[0].id;
    }

    let active_startup = null;
    if (activeId) {
      if (!isTest) {
        const assignment = await pool.query(
          'SELECT 1 FROM judge_assignments WHERE judge_id = $1 AND startup_id = $2',
          [session.principalId, activeId]
        );
        if (assignment.rows.length === 0) {
          return res.status(403).json({ error: 'This startup is not assigned to you.' });
        }
      }

      const startupQuery = await pool.query(
        'SELECT payload FROM startup_extractions WHERE startup_id = $1',
        [activeId]
      );
      if (startupQuery.rows.length === 0) {
        return res.status(404).json({ error: 'Startup not found' });
      }

      const reviewsQuery = isTest
        ? { rows: [] }
        : await pool.query(
            'SELECT question_id, score_value, justification, is_flagged FROM human_reviews WHERE startup_id = $1 AND judge_id = $2',
            [activeId, session.principalId]
          );

      const payload = startupQuery.rows[0].payload || {};
      active_startup = applyHumanProjectionInPlace(payload, reviewsQuery.rows, isTest);
      if (!active_startup.meta) active_startup.meta = {};
      if (!active_startup.meta.name) {
        const match = startups.find((s) => s.id === activeId);
        active_startup.meta.name = (match && match.name) || activeId;
      }
      active_startup.startup_id = activeId;
    }

    return res.status(200).json({
      user: {
        role: 'scorer',
        id: session.principalId,
        is_test: isTest,
      },
      startups,
      active_startup_id: activeId,
      active_startup,
      expires_at: session.expiresAt,
    });
  } catch (err) {
    console.error('Bootstrap error:', err);
    return res.status(500).json({ error: 'Unable to bootstrap workspace.' });
  }
};
