const { Pool } = require('pg');

/**
 * Shared PostgreSQL pool for warm Vercel serverless isolates.
 * Prefer a Supabase transaction-pooler DATABASE_URL when available.
 * Keep max low — each isolate may hold its own pool.
 */
let pool = null;

function getPool() {
  if (pool) return pool;
  if (!process.env.DATABASE_URL) {
    throw new Error('DATABASE_URL is not configured');
  }
  pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
    max: 5,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 10000,
  });
  pool.on('error', (err) => {
    console.error('Unexpected idle pool client error:', err);
  });
  return pool;
}

async function query(text, params) {
  return getPool().query(text, params);
}

module.exports = {
  getPool,
  query,
  get pool() {
    return getPool();
  },
};
