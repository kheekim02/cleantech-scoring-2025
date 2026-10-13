const { pool } = require('./_db');
const { requireSession, isTestScorer } = require('./_auth');

module.exports = async (req, res) => {
  try {
    const session = await requireSession(pool, req, res, 'scorer');
    if (!session) return;

    const isTest = await isTestScorer(pool, session.principalId);
    let listQuery;
    if (isTest) {
      listQuery = await pool.query(
        "SELECT startup_id as id, company_name as name, 0::int as answered_count, false as is_submitted FROM startup_extractions WHERE startup_id NOT ILIKE '%solarpure%' ORDER BY company_name ASC"
      );
    } else {
      listQuery = await pool.query(
        `SELECT s.startup_id as id, s.company_name as name,
                COALESCE(COUNT(CASE WHEN hr.score_value IS NOT NULL THEN 1 END), 0)::int as answered_count,
                (COALESCE(COUNT(CASE WHEN hr.score_value IS NOT NULL THEN 1 END), 0) >= 282) as is_submitted
         FROM startup_extractions s
         INNER JOIN judge_assignments ja ON s.startup_id = ja.startup_id
         LEFT JOIN human_reviews hr ON hr.startup_id = s.startup_id AND hr.judge_id = ja.judge_id
         WHERE ja.judge_id = $1 AND s.startup_id NOT ILIKE '%solarpure%'
         GROUP BY s.startup_id, s.company_name
         ORDER BY s.company_name ASC`,
        [session.principalId]
      );
    }

    return res.status(200).json(listQuery.rows);
  } catch (err) {
    console.error('Database Error:', err);
    return res.status(500).json({ error: 'DB Error: ' + err.message });
  }
};
