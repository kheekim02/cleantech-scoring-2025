const { Client } = require('pg');

exports.handler = async (event, context) => {
  const { id, judge_id, passcode } = event.queryStringParameters || {};

  if (!id || !judge_id || !passcode) {
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

    // Fetch Startup
    const startupQuery = await client.query('SELECT payload FROM startup_extractions WHERE startup_id = $1', [id]);
    await client.end();

    if (startupQuery.rows.length === 0) {
      return { statusCode: 404, body: JSON.stringify({ error: "Startup not found" }) };
    }

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(startupQuery.rows[0].payload)
    };

  } catch (err) {
    console.error("Database Error:", err);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: "DB Error: " + err.message })
    };
  }
};
