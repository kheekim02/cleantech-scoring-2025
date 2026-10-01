const fs = require('fs');
const path = require('path');
const { pool } = require('./_db');
const { requireSession, isTestScorer } = require('./_auth');

const DEFAULT_ALLOWED_SCORES = [0, 0.25, 0.5, 0.75, 1];
const RUBRIC_PATH = path.join(__dirname, '..', 'master_282_rubric.json');

/** @type {Map<string, number[]>|null} */
let rubricAllowedScores = null;

function loadRubricAllowedScores() {
  if (rubricAllowedScores) return rubricAllowedScores;
  const rubric = JSON.parse(fs.readFileSync(RUBRIC_PATH, 'utf8'));
  const map = new Map();
  for (const question of rubric) {
    const qid = question.new_q_id || question.q_id;
    if (!qid) continue;
    const allowed =
      Array.isArray(question.options) && question.options.length > 0
        ? question.options.map((option) => Number(option.val))
        : DEFAULT_ALLOWED_SCORES.slice();
    map.set(qid, allowed);
  }
  rubricAllowedScores = map;
  return map;
}

function prepareScoreBatch(scores, allowedByQid) {
  const byQid = new Map();
  for (const item of scores) {
    if (!item || !item.qid) continue;
    byQid.set(item.qid, item);
  }

  const questionIds = [];
  const scoreValues = [];
  const justifications = [];
  const flagValues = [];

  for (const [qid, item] of byQid) {
    const allowedScores = allowedByQid.get(qid);
    if (!allowedScores) {
      const err = new Error(`Unknown question: ${qid}`);
      err.statusCode = 400;
      throw err;
    }
    const scoreVal =
      item.val !== null && item.val !== undefined ? parseFloat(item.val) : null;
    if (
      scoreVal !== null &&
      (!Number.isFinite(scoreVal) || !allowedScores.includes(scoreVal))
    ) {
      const err = new Error(`Invalid score for ${qid}`);
      err.statusCode = 400;
      throw err;
    }
    const justVal = String(item.justification ?? '').trim();
    const isFlagged =
      item.is_flagged !== undefined && item.is_flagged !== null
        ? Boolean(item.is_flagged)
        : null;

    questionIds.push(qid);
    scoreValues.push(scoreVal);
    justifications.push(justVal);
    flagValues.push(isFlagged);
  }

  return { questionIds, scoreValues, justifications, flagValues, count: questionIds.length };
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    return res.status(405).send('Method Not Allowed');
  }

  let payload = req.body;
  if (typeof payload === 'string') {
    try {
      payload = JSON.parse(payload);
    } catch (e) {}
  }

  const { startup_id, scores } = payload || {};

  if (!startup_id) {
    return res.status(400).json({ error: 'Missing startup ID.' });
  }

  try {
    const session = await requireSession(pool, req, res, 'scorer');
    if (!session) return;

    const isTest = await isTestScorer(pool, session.principalId);

    if (isTest) {
      return res.status(200).json({
        success: true,
        message: 'Test / Admin Preview Mode: Scores are not persisted to database.',
        test_mode: true,
      });
    }

    if (!scores || scores.length === 0) {
      return res.status(200).json({ success: true, message: 'Authenticated.' });
    }

    const assignment = await pool.query(
      'SELECT 1 FROM judge_assignments WHERE judge_id = $1 AND startup_id = $2',
      [session.principalId, startup_id]
    );
    if (assignment.rows.length === 0) {
      return res.status(403).json({ error: 'This startup is not assigned to you.' });
    }

    const startup = await pool.query(
      'SELECT 1 FROM startup_extractions WHERE startup_id = $1',
      [startup_id]
    );
    if (startup.rows.length !== 1) {
      return res.status(404).json({ error: 'Startup not found.' });
    }

    let batch;
    try {
      batch = prepareScoreBatch(scores, loadRubricAllowedScores());
    } catch (validationErr) {
      const status = validationErr.statusCode || 400;
      return res.status(status).json({ error: validationErr.message });
    }

    if (batch.count === 0) {
      return res.status(200).json({ success: true, message: 'Authenticated.' });
    }

    await pool.query(
      `
      INSERT INTO human_reviews (startup_id, question_id, judge_id, score_value, justification, is_flagged)
      SELECT
        $1::text,
        x.question_id,
        $2::text,
        x.score_value,
        x.justification,
        COALESCE(x.is_flagged, FALSE)
      FROM UNNEST(
        $3::text[],
        $4::double precision[],
        $5::text[],
        $6::boolean[]
      ) AS x(question_id, score_value, justification, is_flagged)
      ON CONFLICT (startup_id, question_id, judge_id)
      DO UPDATE SET
        score_value = COALESCE(EXCLUDED.score_value, human_reviews.score_value),
        justification = EXCLUDED.justification,
        is_flagged = COALESCE(EXCLUDED.is_flagged, human_reviews.is_flagged),
        updated_at = NOW();
      `,
      [
        startup_id,
        session.principalId,
        batch.questionIds,
        batch.scoreValues,
        batch.justifications,
        batch.flagValues,
      ]
    );

    return res.status(200).json({
      success: true,
      message: `Successfully synced ${batch.count} scores.`,
    });
  } catch (err) {
    console.error('Database Error:', err);
    return res.status(500).json({ error: 'DB Error: ' + err.message });
  }
};
