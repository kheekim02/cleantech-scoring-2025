const { Client } = require('pg');
const { hashPassword, requireSession, validateNewPassword } = require('./_auth');

module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).send("Method Not Allowed");

  let payload = req.body;
  if (typeof payload === 'string') {
    try { payload = JSON.parse(payload); } catch(e) {}
  }

  const { action, data } = payload || {};
  if (!action) {
    return res.status(400).json({ error: "Missing required fields" });
  }

  const client = new Client({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });

  try {
    await client.connect();
    
    const session = await requireSession(client, req, res, 'admin');
    if (!session) {
      await client.end();
      return;
    }

    if (action === 'CREATE_JUDGE') {
      const { new_judge_id, new_password } = data || {};
      if (!new_judge_id || !new_password) throw new Error("Missing scorer credentials");
      const passwordError = validateNewPassword(new_password);
      if (passwordError) {
        await client.end();
        return res.status(400).json({ error: passwordError });
      }
      const passwordHash = await hashPassword(new_password);
      
      await client.query('INSERT INTO judges (judge_id, password_hash) VALUES ($1, $2)', [new_judge_id, passwordHash]);
      await client.query(`INSERT INTO auth_audit_log (role, principal_id, action) VALUES ('scorer', $1, 'SCORER_CREATED')`, [new_judge_id]);
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
        await client.query(`INSERT INTO auth_audit_log (role, principal_id, action) VALUES ('admin', $1, 'ASSIGNMENT_UPDATED')`, [session.principalId]);
        await client.end();
        return res.status(200).json({ success: true, assignment: assignmentRes.rows[0] });
      } else {
        await client.query('DELETE FROM judge_assignments WHERE judge_id = $1 AND startup_id = $2', [judge_id, startup_id]);
      }
      await client.query(`INSERT INTO auth_audit_log (role, principal_id, action) VALUES ('admin', $1, 'ASSIGNMENT_UPDATED')`, [session.principalId]);
      
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
