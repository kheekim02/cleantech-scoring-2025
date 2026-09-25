const { Client } = require('pg');
const { getSession, isTestScorer } = require('./_auth');

module.exports = async (req, res) => {
  const role = req.query?.role;
  if (!['admin', 'scorer'].includes(role)) return res.status(400).json({ error: 'Invalid role.' });
  const client = new Client({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
  try {
    await client.connect();
    const session = await getSession(client, req, role);
    if (!session) {
      await client.end();
      return res.status(401).json({ error: 'No active session.' });
    }
    const isTest = role === 'scorer' ? await isTestScorer(client, session.principalId) : false;
    await client.end();
    return res.status(200).json({ user: { role, id: session.principalId, is_test: isTest }, expires_at: session.expiresAt });
  } catch (error) {
    console.error('Session lookup error:', error);
    return res.status(500).json({ error: 'Unable to verify session.' });
  } finally {
    try { await client.end(); } catch(e) {}
  }
};
