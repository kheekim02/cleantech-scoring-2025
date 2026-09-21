const { Client } = require('pg');

module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).send("Method Not Allowed");

  let payload = req.body;
  if (typeof payload === 'string') {
    try { payload = JSON.parse(payload); } catch(e) {}
  }

  const { username, passcode } = payload || {};
  if (!username || !passcode) {
    return res.status(400).json({ error: "Missing username or passcode" });
  }

  const client = new Client({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });

  try {
    await client.connect();
    const query = await client.query('SELECT * FROM admins WHERE username = $1 AND passcode = $2', [username, passcode]);
    await client.end();

    if (query.rows.length > 0) {
      return res.status(200).json({ success: true, message: "Authenticated." });
    } else {
      return res.status(401).json({ error: "Invalid admin credentials." });
    }
  } catch (err) {
    console.error("Database Error:", err);
    return res.status(500).json({ error: "DB Error: " + err.message });
  }
};
