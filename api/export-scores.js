const { pool } = require('./_db');
const { requireSession } = require('./_auth');
const path = require('path');
const fs = require('fs');

const CATEGORY_NAMES = {
  'BC': 'Business Canvas',
  'ES': 'Environmental & Social',
  'F': 'Financials',
  'IP': 'Investor Pitch',
  'IS': 'Executive Summary / Impact',
  'L': 'Legal & Governance',
  'M': 'Market & Customers',
  'PMF': 'Product Market Fit',
  'T': 'Team Targets',
  'TP': 'Tech / Product'
};

const rubricMap = new Map();
try {
  const rubricPath = path.resolve(__dirname, '../master_282_rubric.json');
  if (fs.existsSync(rubricPath)) {
    const rubricData = JSON.parse(fs.readFileSync(rubricPath, 'utf8'));
    rubricData.forEach(q => {
      const qid = q.new_q_id || q.q_id;
      if (qid) rubricMap.set(qid, q);
    });
  }
} catch (e) {
  console.warn("Could not load master_282_rubric.json in export-scores:", e.message);
}

module.exports = async (req, res) => {
  if (req.method !== 'GET') return res.status(405).send("Method Not Allowed");

  try {
    
    const session = await requireSession(pool, req, res, 'admin');
    if (!session) {
            return;
    }

    const isChunked = req.query.chunk === 'true';
    let paginationSql = '';
    const params = [];
    let fetchLimit = 0;

    if (isChunked) {
      const limit = parseInt(req.query.limit, 10) || 2500;
      const offset = parseInt(req.query.offset, 10) || 0;
      fetchLimit = limit;
      paginationSql = 'LIMIT $1 OFFSET $2';
      params.push(limit + 1, offset);
    }

    const query = `
      SELECT 
        hr.startup_id,
        COALESCE(se.company_name, hr.startup_id) AS company_name,
        hr.judge_id,
        hr.question_id,
        hr.score_value,
        hr.justification,
        hr.is_flagged,
        hr.updated_at
      FROM human_reviews hr
      LEFT JOIN startup_extractions se ON hr.startup_id = se.startup_id
      WHERE hr.startup_id NOT ILIKE '%solarpure%'
        AND hr.judge_id NOT IN (SELECT judge_id FROM judges WHERE is_test = true)
      ORDER BY se.company_name ASC, hr.judge_id ASC, hr.question_id ASC
      ${paginationSql};
    `;
    const result = await pool.query(query, params);
    
    const hasMore = isChunked && result.rows.length > fetchLimit;
    const processRows = hasMore ? result.rows.slice(0, fetchLimit) : result.rows;

    const headers = [
      'Startup ID',
      'Company Name',
      'Judge ID',
      'Category Code',
      'Category Name',
      'Question ID',
      'Question Text',
      'Score',
      'Justification',
      'Flagged for Review',
      'Scored At'
    ];

    const escapeCsv = (str) => `"${String(str ?? '').replace(/"/g, '""').replace(/\r?\n/g, ' ')}"`;

    const mappedRows = processRows.map(r => {
      const qid = r.question_id;
      const matchedQ = rubricMap.get(qid);

      const catCode = matchedQ?.cat_code || (qid ? qid.split('_')[0] : '');
      const catName = CATEGORY_NAMES[catCode] || catCode;
      const qText = matchedQ?.text || '';
      const scoreVal = (r.score_value !== null && r.score_value !== undefined) ? r.score_value : '';
      const flaggedVal = r.is_flagged ? 'Yes' : 'No';
      const scoredAt = r.updated_at ? new Date(r.updated_at).toISOString() : '';

      return [
        escapeCsv(r.startup_id),
        escapeCsv(r.company_name),
        escapeCsv(r.judge_id),
        escapeCsv(catCode),
        escapeCsv(catName),
        escapeCsv(qid),
        escapeCsv(qText),
        scoreVal,
        escapeCsv(r.justification),
        flaggedVal,
        scoredAt
      ];
    });

    if (isChunked) {
      return res.status(200).json({
        header: headers.join(','),
        rows: mappedRows.map(r => r.join(',')),
        hasMore
      });
    }

    const csvContent = [headers.join(','), ...mappedRows.map(r => r.join(','))].join('\r\n');

    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename="cleantech_open_scores_${new Date().toISOString().slice(0, 10)}.csv"`);
    return res.status(200).send(csvContent);

  } catch (err) {
    console.error("Export error:", err);
    return res.status(500).json({ error: "Failed to export scores: " + err.message });
  }
};
