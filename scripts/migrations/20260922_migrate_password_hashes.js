const fs = require('fs');
const { Client } = require('pg');
const { hashPassword } = require('../../api/_auth');

function databaseUrlFromEnv() {
  const match = fs.readFileSync('.env', 'utf8').match(/^DATABASE_URL=(.*)$/m);
  if (!match) throw new Error('DATABASE_URL is missing from .env');
  return match[1].trim().replace(/^['"]|['"]$/g, '');
}

async function migrateTable(client, table, idColumn) {
  const result = await client.query(`SELECT ${idColumn}, passcode FROM ${table} WHERE password_hash IS NULL`);
  for (const row of result.rows) {
    const passwordHash = await hashPassword(row.passcode);
    await client.query(`UPDATE ${table} SET password_hash = $1 WHERE ${idColumn} = $2`, [passwordHash, row[idColumn]]);
  }
  return result.rows.length;
}

async function run() {
  const client = new Client({ connectionString: databaseUrlFromEnv(), ssl: { rejectUnauthorized: false } });
  await client.connect();
  try {
    const schemaSql = fs.readFileSync('scripts/migrations/20260922_secure_auth_schema.sql', 'utf8');
    await client.query(schemaSql);
    const admins = await migrateTable(client, 'admins', 'username');
    const scorers = await migrateTable(client, 'judges', 'judge_id');
    await client.query("INSERT INTO auth_audit_log (role, principal_id, action) VALUES ('admin', 'system', 'PASSWORD_HASH_MIGRATION')");
    console.log(`Migrated password hashes for ${admins} admin(s) and ${scorers} scorer(s).`);
  } finally {
    await client.end();
  }
}

run().catch(error => { console.error(`Password migration failed: ${error.message}`); process.exit(1); });
