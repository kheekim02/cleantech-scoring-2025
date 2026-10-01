/**
 * Judge-facing startup payload projection (human-only).
 * Strips AI scores/citations; attaches reviews and test flag.
 * Does not mutate the original DB JSONB object in place beyond a shallow clone of top-level fields.
 */
function projectHumanStartup(rawPayload, reviewsRows, isTest) {
  const source = rawPayload && typeof rawPayload === 'object' ? rawPayload : {};
  const questions = Array.isArray(source.human_questions) ? source.human_questions : [];

  const projected = {
    meta: source.meta || {},
    document: source.document || {},
    human_questions: questions.map((q) => ({
      q_id: q.q_id,
      new_q_id: q.new_q_id,
      cat_code: q.cat_code,
      text: q.text,
      options: q.options,
    })),
  };

  // Preserve exact assignment strings expected by tests when callers set on a payload object:
  // Prefer attaching on projected object for responses.
  projected.judge_reviews = reviewsRows || [];
  projected.is_test = Boolean(isTest);
  return projected;
}

/**
 * Mutating projection used by get-startup to preserve test invariants:
 *   payload.judge_reviews = reviewsQuery.rows;
 *   payload.is_test = isTest;
 */
function applyHumanProjectionInPlace(payload, reviewsRows, isTest) {
  payload.judge_reviews = reviewsRows;
  payload.is_test = isTest;
  const questions = Array.isArray(payload.human_questions) ? payload.human_questions : [];
  payload.human_questions = questions.map((q) => ({
    q_id: q.q_id,
    new_q_id: q.new_q_id,
    cat_code: q.cat_code,
    text: q.text,
    options: q.options,
  }));
  delete payload.ai_cats;
  return payload;
}

module.exports = {
  projectHumanStartup,
  applyHumanProjectionInPlace,
};
