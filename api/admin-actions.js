const { pool } = require('./_db');
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

  try {
        
    const session = await requireSession(pool, req, res, 'admin');
    if (!session) {
            return;
    }

    if (action === 'CREATE_JUDGE') {
      const { new_judge_id, new_password, is_test } = data || {};
      if (!new_judge_id || !new_password) throw new Error("Missing scorer credentials");
      const passwordError = validateNewPassword(new_password);
      if (passwordError) {
                return res.status(400).json({ error: passwordError });
      }
      const passwordHash = await hashPassword(new_password);
      
      await pool.query(
        'INSERT INTO judges (judge_id, passcode, password_hash, is_test) VALUES ($1, $2, $3, $4)',
        [new_judge_id, new_password, passwordHash, !!is_test]
      );
      await pool.query(
        `INSERT INTO auth_audit_log (role, principal_id, action) VALUES ('scorer', $1, $2)`,
        [new_judge_id, is_test ? 'TEST_SCORER_CREATED' : 'SCORER_CREATED']
      );
            return res.status(200).json({ success: true, is_test: !!is_test });
      
    } else if (action === 'TOGGLE_ASSIGNMENT') {
      const { judge_id, startup_id, assigned } = data || {};
      if (!judge_id || !startup_id || assigned === undefined) throw new Error("Missing assignment data");
      
      if (assigned) {
        const assignmentRes = await pool.query(
          `INSERT INTO judge_assignments (judge_id, startup_id, assigned_at)
           VALUES ($1, $2, NOW())
           ON CONFLICT (judge_id, startup_id) DO UPDATE
             SET assigned_at = judge_assignments.assigned_at
           RETURNING judge_id, startup_id, assigned_at`,
          [judge_id, startup_id]
        );
        await pool.query(`INSERT INTO auth_audit_log (role, principal_id, action) VALUES ('admin', $1, 'ASSIGNMENT_UPDATED')`, [session.principalId]);
                return res.status(200).json({ success: true, assignment: assignmentRes.rows[0] });
      } else {
        await pool.query('DELETE FROM judge_assignments WHERE judge_id = $1 AND startup_id = $2', [judge_id, startup_id]);
      }
      await pool.query(`INSERT INTO auth_audit_log (role, principal_id, action) VALUES ('admin', $1, 'ASSIGNMENT_UPDATED')`, [session.principalId]);
      
            return res.status(200).json({ success: true });
    } else if (action === 'DELETE_JUDGE') {
      const { judge_id } = data || {};
      if (!judge_id) throw new Error("Missing scorer ID to delete");

      await pool.query('DELETE FROM judge_assignments WHERE judge_id = $1', [judge_id]);
      await pool.query("DELETE FROM auth_sessions WHERE role = 'scorer' AND principal_id = $1", [judge_id]);
      await pool.query('DELETE FROM human_reviews WHERE judge_id = $1', [judge_id]);
      await pool.query('DELETE FROM judges WHERE judge_id = $1', [judge_id]);
      await pool.query("INSERT INTO auth_audit_log (role, principal_id, action) VALUES ('admin', $1, 'SCORER_DELETED')", [session.principalId]);

            return res.status(200).json({ success: true, deleted: judge_id });
    } else if (action === 'RESET_JUDGE_PASSWORD') {
      const { judge_id, new_password } = data || {};
      if (!judge_id || !new_password) throw new Error("Missing scorer ID or new password");

      const passwordError = validateNewPassword(new_password);
      if (passwordError) {
                return res.status(400).json({ error: passwordError });
      }

      const passwordHash = await hashPassword(new_password);
      const updateRes = await pool.query('UPDATE judges SET password_hash = $1 WHERE judge_id = $2', [passwordHash, judge_id]);
      if (updateRes.rowCount === 0) {
                return res.status(404).json({ error: "Scorer not found" });
      }

      // Revoke any active sessions for this judge to force re-login with the new password
      await pool.query("UPDATE auth_sessions SET revoked_at = NOW() WHERE role = 'scorer' AND principal_id = $1 AND revoked_at IS NULL", [judge_id]);
      await pool.query("INSERT INTO auth_audit_log (role, principal_id, action) VALUES ('admin', $1, 'SCORER_PASSWORD_RESET')", [session.principalId]);

            return res.status(200).json({ success: true, message: `Password reset successfully for ${judge_id}` });
    } else if (action === 'UPDATE_FEEDBACK_STATUS') {
      const { feedback_id, status } = data || {};
      if (!feedback_id || !status) throw new Error("Missing feedback ID or status");

      const validStatuses = ['new', 'reviewed', 'resolved'];
      if (!validStatuses.includes(status)) throw new Error("Invalid feedback status");

      const updateRes = await pool.query('UPDATE scorer_feedback SET status = $1 WHERE id = $2', [status, feedback_id]);
      if (updateRes.rowCount === 0) {
                return res.status(404).json({ error: "Feedback item not found" });
      }

            return res.status(200).json({ success: true, feedback_id, status });
    } else if (action === 'DELETE_FEEDBACK') {
      const { feedback_id } = data || {};
      if (!feedback_id) throw new Error("Missing feedback ID");

      await pool.query('DELETE FROM scorer_feedback WHERE id = $1', [feedback_id]);
            return res.status(200).json({ success: true, deleted: feedback_id });
    } else {
            return res.status(400).json({ error: "Unknown action" });
    }

  } catch (err) {
    console.error("Database Error:", err);
    return res.status(500).json({ error: err.message });
  }
};
