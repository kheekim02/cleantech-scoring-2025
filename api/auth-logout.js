const { Client } = require('pg');
const { cookieName, getSession, revokeSession, setCookie } = require('./_auth');

module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');
  const payload = typeof req.body === 'string' ? JSON.parse(req.body) : (req.body || {});
  const { role } = payload;
  if (!['admin', 'scorer'].includes(role)) return res.status(400).json({ error: 'Invalid role.' });
  const client = new Client({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
  try {
    await client.connect();
    const session = await getSession(client, req, role);
    if (session) await revokeSession(client, session.token);
    await client.end();
    setCookie(res, cookieName(role), '', 0);
    return res.status(200).json({ success: true });
  } catch (error) {
    console.error('Logout error:', error);
    return res.status(500).json({ error: 'Unable to sign out.' });
  }
};
