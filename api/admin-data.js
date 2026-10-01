const { pool } = require('./_db');
const { requireSession } = require('./_auth');

module.exports = async (req, res) => {

  try {
        
    const session = await requireSession(pool, req, res, 'admin');
    if (!session) {
            return;
    }

    // Fetch data
    const judgesRes = await pool.query('SELECT judge_id, is_test FROM judges ORDER BY judge_id ASC');
    const startupsRes = await pool.query('SELECT startup_id as id, company_name as name FROM startup_extractions ORDER BY company_name ASC');
    const assignmentsRes = await pool.query('SELECT judge_id, startup_id, assigned_at FROM judge_assignments');
    const progressRes = await pool.query(`
      SELECT 
        judge_id, 
        startup_id, 
        COUNT(CASE WHEN score_value IS NOT NULL THEN 1 END)::int as answered_count,
        COUNT(CASE WHEN is_flagged = TRUE THEN 1 END)::int as flagged_count,
        MAX(updated_at) as last_saved
      FROM human_reviews 
      GROUP BY judge_id, startup_id
    `);
    const feedbackRes = await pool.query(`
      SELECT sf.id, sf.scorer_id, sf.startup_id, sf.feedback_text, sf.category_code, 
             sf.status, sf.admin_notes, sf.created_at,
             se.company_name as startup_name
      FROM scorer_feedback sf
      LEFT JOIN startup_extractions se ON sf.startup_id = se.startup_id
      ORDER BY sf.created_at DESC
      LIMIT 200
    `);
    
    
    return res.status(200).json({
      judges: judgesRes.rows,
      startups: startupsRes.rows,
      assignments: assignmentsRes.rows,
      progress: progressRes.rows,
      feedback: feedbackRes.rows
    });

  } catch (err) {
    console.error("Database Error:", err);
    return res.status(500).json({ error: "DB Error: " + err.message });
  }
};
