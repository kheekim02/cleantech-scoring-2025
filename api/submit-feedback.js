const { pool } = require('./_db');
const { getSession } = require('./_auth');

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  let payload = req.body;
  if (typeof payload === 'string') {
    try { payload = JSON.parse(payload); } catch(e) {}
  }

  const { feedback_text, startup_id, category_code } = payload || {};

  if (!feedback_text || typeof feedback_text !== 'string' || !feedback_text.trim()) {
    return res.status(400).json({ error: 'Feedback text is required.' });
  }

  const trimmedText = feedback_text.trim();
  if (trimmedText.length > 5000) {
    return res.status(400).json({ error: 'Feedback must be under 5,000 characters.' });
  }

  try {
    
    // Authenticate: check scorer session first, then admin session
    let session = await getSession(pool, req, 'scorer');
    if (!session) {
      session = await getSession(pool, req, 'admin');
    }

    if (!session) {
            return res.status(401).json({ error: 'Authentication required to submit feedback.' });
    }

    const scorerId = session.principalId;
    const cleanStartupId = (typeof startup_id === 'string' && startup_id.trim()) ? startup_id.trim() : null;
    const cleanCategoryCode = (typeof category_code === 'string' && category_code.trim()) ? category_code.trim() : null;

    const insertResult = await pool.query(
      `INSERT INTO scorer_feedback (scorer_id, startup_id, category_code, feedback_text, status, created_at)
       VALUES ($1, $2, $3, $4, 'new', NOW())
       RETURNING id, created_at`,
      [scorerId, cleanStartupId, cleanCategoryCode, trimmedText]
    );

    
    return res.status(200).json({
      success: true,
      message: 'Feedback submitted successfully.',
      feedback_id: insertResult.rows[0].id,
      created_at: insertResult.rows[0].created_at
    });

  } catch (err) {
    console.error('Submit feedback error:', err);
    return res.status(500).json({ error: 'Database error while submitting feedback: ' + err.message });
  }
};
