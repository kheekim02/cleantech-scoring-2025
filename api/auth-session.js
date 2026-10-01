const { pool } = require('./_db');
const { getSession, isTestScorer } = require('./_auth');

module.exports = async (req, res) => {
  const role = req.query?.role;
  if (!['admin', 'scorer'].includes(role)) return res.status(400).json({ error: 'Invalid role.' });
  try {
    const session = await getSession(pool, req, role);
    if (!session) {
      return res.status(401).json({ error: 'No active session.' });
    }
    const isTest = role === 'scorer' ? await isTestScorer(pool, session.principalId) : false;
    return res.status(200).json({
      user: { role, id: session.principalId, is_test: isTest },
      expires_at: session.expiresAt,
    });
  } catch (error) {
    console.error('Session lookup error:', error);
    return res.status(500).json({ error: 'Unable to verify session.' });
  }
};
