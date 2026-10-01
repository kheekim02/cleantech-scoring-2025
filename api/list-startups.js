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
        "SELECT startup_id as id, company_name as name FROM startup_extractions WHERE startup_id NOT ILIKE '%solarpure%' ORDER BY company_name ASC"
      );
    } else {
      listQuery = await pool.query(
        'SELECT s.startup_id as id, s.company_name as name FROM startup_extractions s INNER JOIN judge_assignments ja ON s.startup_id = ja.startup_id WHERE ja.judge_id = $1 AND s.startup_id NOT ILIKE \'%solarpure%\' ORDER BY s.company_name ASC',
        [session.principalId]
      );
    }

    return res.status(200).json(listQuery.rows);
  } catch (err) {
    console.error('Database Error:', err);
    return res.status(500).json({ error: 'DB Error: ' + err.message });
  }
};
