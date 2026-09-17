const { Client } = require('pg');

exports.handler = async (event, context) => {
  const { judge_id, passcode } = event.queryStringParameters || {};

  if (!judge_id || !passcode) {
    return { statusCode: 400, body: JSON.stringify({ error: "Missing required parameters" }) };
  }

  const client = new Client({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });

  try {
    await client.connect();
    
    // Auth Check
    const authQuery = await client.query('SELECT * FROM judges WHERE judge_id = $1 AND passcode = $2', [judge_id, passcode]);
    if (authQuery.rows.length === 0) {
      await client.end();
      return { statusCode: 401, body: JSON.stringify({ error: "Unauthorized" }) };
    }

    // Fetch List
    const listQuery = await client.query('SELECT startup_id as id, company_name as name FROM startup_extractions ORDER BY company_name ASC');
    await client.end();

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(listQuery.rows)
    };

  } catch (err) {
    console.error("Database Error:", err);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: "DB Error: " + err.message })
    };
  }
};
