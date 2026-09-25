const { Client } = require('pg');
const { getSession, hashPassword, revokeOtherSessions, validateNewPassword, verifyPassword } = require('./_auth');

module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).send('Method Not Allowed');
  let payload;
  try { payload = typeof req.body === 'string' ? JSON.parse(req.body) : (req.body || {}); }
  catch { return res.status(400).json({ error: 'Invalid request body.' }); }
  const { role, current_password, new_password, confirm_password } = payload;
  if (!['admin', 'scorer'].includes(role)) return res.status(400).json({ error: 'Invalid role.' });
  if (new_password !== confirm_password) return res.status(400).json({ error: 'New passwords do not match.' });
  const validationError = validateNewPassword(new_password);
  if (validationError) return res.status(400).json({ error: validationError });

  const client = new Client({ connectionString: process.env.DATABASE_URL, ssl: { rejectUnauthorized: false } });
  try {
    await client.connect();
    const session = await getSession(client, req, role);
    if (!session) {
      await client.end();
      return res.status(401).json({ error: 'Authentication required.' });
    }
    const table = role === 'admin' ? 'admins' : 'judges';
    const idColumn = role === 'admin' ? 'username' : 'judge_id';
    const user = await client.query(`SELECT password_hash FROM ${table} WHERE ${idColumn} = $1`, [session.principalId]);
    if (user.rows.length !== 1 || !(await verifyPassword(current_password, user.rows[0].password_hash))) {
      await client.end();
      return res.status(401).json({ error: 'Current password is incorrect.' });
    }
    const passwordHash = await hashPassword(new_password);
    await client.query(`UPDATE ${table} SET password_hash = $1 WHERE ${idColumn} = $2`, [passwordHash, session.principalId]);
    await revokeOtherSessions(client, role, session.principalId, session.token);
    await client.query(
      `INSERT INTO auth_audit_log (role, principal_id, action) VALUES ($1, $2, 'PASSWORD_CHANGED')`,
      [role, session.principalId]
    );
    await client.end();
    return res.status(200).json({ success: true, message: 'Password updated. Other active sessions were signed out.' });
  } catch (error) {
    console.error('Password change error:', error);
    return res.status(500).json({ error: 'Unable to change password.' });
  } finally {
    try { await client.end(); } catch(e) {}
  }
};
