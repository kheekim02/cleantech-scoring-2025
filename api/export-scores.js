const { Client } = require('pg');
const { requireSession } = require('./_auth');

module.exports = async (req, res) => {
  if (req.method !== 'GET') return res.status(405).send("Method Not Allowed");

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

    const query = `
      SELECT 
        hr.startup_id,
        se.company_name,
        hr.judge_id,
        hr.question_id,
        hr.score_value,
        hr.justification,
        hr.updated_at
      FROM human_reviews hr
      LEFT JOIN startup_extractions se ON hr.startup_id = se.startup_id
      ORDER BY se.company_name ASC, hr.judge_id ASC, hr.question_id ASC;
    `;
    const result = await client.query(query);
    await client.end();

    // Format as CSV
    const headers = ['Startup ID', 'Company Name', 'Judge ID', 'Question ID', 'Score', 'Justification', 'Updated At'];
    const rows = result.rows.map(r => [
      `"${(r.startup_id || '').replace(/"/g, '""')}"`,
      `"${(r.company_name || '').replace(/"/g, '""')}"`,
      `"${(r.judge_id || '').replace(/"/g, '""')}"`,
      `"${(r.question_id || '').replace(/"/g, '""')}"`,
      r.score_value !== null ? r.score_value : '',
      `"${(r.justification || '').replace(/"/g, '""')}"`,
      r.updated_at ? new Date(r.updated_at).toISOString() : ''
    ]);

    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\r\n');

    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename="cleantech_open_scores_${new Date().toISOString().slice(0, 10)}.csv"`);
    return res.status(200).send(csvContent);

  } catch (err) {
    console.error("Export error:", err);
    return res.status(500).json({ error: "Failed to export scores: " + err.message });
  }
};
