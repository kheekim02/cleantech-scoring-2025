const { Client } = require('pg');
const { createSession, setCookie, verifyPassword } = require('./_auth');

module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');
  const payload = typeof req.body === 'string' ? JSON.parse(req.body) : (req.body || {});
  const { role, username, judge_id, password } = payload;
  if (!['admin', 'scorer'].includes(role) || !password) return res.status(400).json({ error: 'Invalid login request.' });
  const principalId = role === 'admin' ? username : judge_id;
  if (!principalId) return res.status(400).json({ error: 'Username and password are required.' });

  const client = new Client({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
  try {
    await client.connect();
    const table = role === 'admin' ? 'admins' : 'judges';
    const idColumn = role === 'admin' ? 'username' : 'judge_id';
    const result = await client.query(`SELECT password_hash FROM ${table} WHERE ${idColumn} = $1`, [principalId]);
    if (result.rows.length !== 1 || !(await verifyPassword(password, result.rows[0].password_hash))) {
      await client.end();
      return res.status(401).json({ error: 'Invalid username or password.' });
    }
    const session = await createSession(client, role, principalId);
    setCookie(res, role === 'admin' ? 'cto_admin_session' : 'cto_scorer_session', session.token);
    await client.end();
    return res.status(200).json({ success: true, user: { role, id: principalId } });
  } catch (error) {
    console.error('Login error:', error);
    return res.status(500).json({ error: 'Unable to sign in.' });
  }
};
