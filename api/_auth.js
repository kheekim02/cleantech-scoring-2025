const crypto = require('crypto');
const { promisify } = require('util');

const scrypt = promisify(crypto.scrypt);
const SESSION_TTL_MS = 12 * 60 * 60 * 1000;

function parseCookies(req) {
  return (req.headers?.cookie || '').split(';').reduce((cookies, part) => {
    const [name, ...value] = part.trim().split('=');
    if (name) cookies[name] = decodeURIComponent(value.join('='));
    return cookies;
  }, {});
}

function cookieName(role) {
  return role === 'admin' ? 'cto_admin_session' : 'cto_scorer_session';
}

function setCookie(res, name, value, maxAgeSeconds = SESSION_TTL_MS / 1000) {
  res.setHeader('Set-Cookie', `${name}=${encodeURIComponent(value)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${Math.floor(maxAgeSeconds)}`);
}

async function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const derivedKey = await scrypt(password, salt, 64);
  return `scrypt$${salt}$${derivedKey.toString('hex')}`;
}

async function verifyPassword(password, passwordHash) {
  if (!passwordHash) return false;
  const [scheme, salt, expectedHex] = passwordHash.split('$');
  if (scheme !== 'scrypt' || !salt || !expectedHex) return false;
  const actual = await scrypt(password, salt, 64);
  const expected = Buffer.from(expectedHex, 'hex');
  return expected.length === actual.length && crypto.timingSafeEqual(expected, actual);
}

function validateNewPassword(password) {
  if (typeof password !== 'string' || password.length < 12) {
    return 'Password must contain at least 12 characters.';
  }
  if (!/[A-Z]/.test(password) || !/[a-z]/.test(password) || !/\d/.test(password)) {
    return 'Password must include uppercase, lowercase, and numeric characters.';
  }
  return null;
}

async function createSession(client, role, principalId) {
  const token = crypto.randomBytes(32).toString('base64url');
  const expiresAt = new Date(Date.now() + SESSION_TTL_MS);
  await client.query(
    `INSERT INTO auth_sessions (session_token, role, principal_id, expires_at)
     VALUES ($1, $2, $3, $4)`,
    [token, role, principalId, expiresAt]
  );
  return { token, expiresAt };
}

async function getSession(client, req, role) {
  const token = parseCookies(req)[cookieName(role)];
  if (!token) return null;
  const result = await client.query(
    `SELECT session_token, principal_id, expires_at
     FROM auth_sessions
     WHERE session_token = $1 AND role = $2 AND revoked_at IS NULL AND expires_at > NOW()`,
    [token, role]
  );
  if (result.rows.length === 0) return null;
  await client.query('UPDATE auth_sessions SET last_used_at = NOW() WHERE session_token = $1', [token]);
  return { token, principalId: result.rows[0].principal_id, expiresAt: result.rows[0].expires_at };
}

async function requireSession(client, req, res, role) {
  const session = await getSession(client, req, role);
  if (!session) {
    res.status(401).json({ error: 'Authentication required.' });
    return null;
  }
  return session;
}

async function revokeSession(client, token) {
  if (token) await client.query('UPDATE auth_sessions SET revoked_at = NOW() WHERE session_token = $1', [token]);
}

async function revokeOtherSessions(client, role, principalId, currentToken) {
  await client.query(
    `UPDATE auth_sessions SET revoked_at = NOW()
     WHERE role = $1 AND principal_id = $2 AND session_token <> $3 AND revoked_at IS NULL`,
    [role, principalId, currentToken]
  );
}

module.exports = {
  cookieName,
  createSession,
  getSession,
  hashPassword,
  requireSession,
  revokeOtherSessions,
  revokeSession,
  setCookie,
  validateNewPassword,
  verifyPassword
};
