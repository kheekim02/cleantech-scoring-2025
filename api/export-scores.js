const { Client } = require('pg');
const { requireSession } = require('./_auth');

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
        COALESCE(se.company_name, hr.startup_id) AS company_name,
        hr.judge_id,
        hr.question_id,
        hr.score_value,
        hr.justification,
        hr.updated_at,
        se.payload->'human_questions' AS human_questions
      FROM human_reviews hr
      LEFT JOIN startup_extractions se ON hr.startup_id = se.startup_id
      WHERE hr.startup_id NOT ILIKE '%solarpure%'
        AND hr.judge_id NOT IN (SELECT judge_id FROM judges WHERE is_test = true)
      ORDER BY se.company_name ASC, hr.judge_id ASC, hr.question_id ASC;
    `;
    const result = await client.query(query);
    await client.end();

    const headers = [
      'Startup ID',
      'Company Name',
      'Judge ID',
      'Category Code',
      'Category Name',
      'Question ID',
      'Question Text',
      'Human Score',
      'Human Justification',
      'AI Suggestion',
      'AI Confidence',
      'AI Concordance',
      'Source Deliverable',
      'Citation Page',
      'Verbatim Citation',
      'Scored At'
    ];

    const rows = result.rows.map(r => {
      let qs = [];
      try {
        qs = Array.isArray(r.human_questions) ? r.human_questions : JSON.parse(r.human_questions || '[]');
      } catch (e) {
        qs = [];
      }

      const qid = r.question_id;
      const matchedQ = qs.find(q => (q.new_q_id || q.q_id) === qid);

      const catCode = matchedQ?.cat_code || (qid ? qid.split('_')[0] : '');
      const catName = CATEGORY_NAMES[catCode] || catCode;
      const qText = matchedQ?.text || '';
      const aiSug = matchedQ?.ai_suggestion !== undefined && matchedQ?.ai_suggestion !== null ? matchedQ.ai_suggestion : '';
      const aiConf = matchedQ?.ai_confidence !== undefined && matchedQ?.ai_confidence !== null ? matchedQ.ai_confidence : '';
      
      let concordance = 'N/A';
      if (r.score_value !== null && aiSug !== '') {
        concordance = Math.abs(Number(r.score_value) - Number(aiSug)) < 0.001 ? 'AGREED' : 'OVERRULED';
      }

      const sourcePdf = matchedQ?.source_pdf || '';
      const pageNum = matchedQ?.page_number || '';
      const verbatimCitation = matchedQ?.verbatim_citation || '';

      const escapeCsv = (str) => `"${String(str || '').replace(/"/g, '""').replace(/\r?\n/g, ' ')}"`;

      return [
        escapeCsv(r.startup_id),
        escapeCsv(r.company_name),
        escapeCsv(r.judge_id),
        escapeCsv(catCode),
        escapeCsv(catName),
        escapeCsv(qid),
        escapeCsv(qText),
        r.score_value !== null && r.score_value !== undefined ? r.score_value : '',
        escapeCsv(r.justification),
        aiSug,
        aiConf,
        escapeCsv(concordance),
        escapeCsv(sourcePdf),
        pageNum,
        escapeCsv(verbatimCitation),
        r.updated_at ? new Date(r.updated_at).toISOString() : ''
      ];
    });

    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\r\n');

    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename="cleantech_open_scores_${new Date().toISOString().slice(0, 10)}.csv"`);
    return res.status(200).send(csvContent);

  } catch (err) {
    console.error("Export error:", err);
    return res.status(500).json({ error: "Failed to export scores: " + err.message });
  }
};
