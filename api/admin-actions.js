const { Client } = require('pg');

module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).send("Method Not Allowed");

  let payload = req.body;
  if (typeof payload === 'string') {
    try { payload = JSON.parse(payload); } catch(e) {}
  }

  const { username, passcode, action, data } = payload || {};
  if (!username || !passcode || !action) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  const client = new Client({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });

  try {
    await client.connect();
    
    // Auth check
    const authQuery = await client.query('SELECT * FROM admins WHERE username = $1 AND passcode = $2', [username, passcode]);
    if (authQuery.rows.length === 0) {
      await client.end();
      return res.status(401).json({ error: "Unauthorized" });
    }

    if (action === 'CREATE_JUDGE') {
      const { new_judge_id, new_passcode } = data || {};
      if (!new_judge_id || !new_passcode) throw new Error("Missing judge credentials");
      
      await client.query('INSERT INTO judges (judge_id, passcode) VALUES ($1, $2)', [new_judge_id, new_passcode]);
      await client.end();
      return res.status(200).json({ success: true });
      
    } else if (action === 'TOGGLE_ASSIGNMENT') {
      const { judge_id, startup_id, assigned } = data || {};
      if (!judge_id || !startup_id || assigned === undefined) throw new Error("Missing assignment data");
      
      if (assigned) {
        const assignmentRes = await client.query(
          `INSERT INTO judge_assignments (judge_id, startup_id, assigned_at)
           VALUES ($1, $2, NOW())
           ON CONFLICT (judge_id, startup_id) DO UPDATE
             SET assigned_at = judge_assignments.assigned_at
           RETURNING judge_id, startup_id, assigned_at`,
          [judge_id, startup_id]
        );
        await client.end();
        return res.status(200).json({ success: true, assignment: assignmentRes.rows[0] });
      } else {
        await client.query('DELETE FROM judge_assignments WHERE judge_id = $1 AND startup_id = $2', [judge_id, startup_id]);
      }
      
      await client.end();
      return res.status(200).json({ success: true });
    } else {
      await client.end();
      return res.status(400).json({ error: "Unknown action" });
    }

  } catch (err) {
    console.error("Database Error:", err);
    return res.status(500).json({ error: err.message });
  }
};
