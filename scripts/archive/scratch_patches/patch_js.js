const fs = require('fs');

// Patch render.js
let renderCode = fs.readFileSync('site/js/render.js', 'utf8');

renderCode = renderCode.replace(
  'renderRightPane(stepCat, stepIndex, totalSteps, aiCats, humanQuestions, answers) {',
  'renderRightPane(stepCat, stepIndex, totalSteps, aiCats, humanQuestions, answers, humanJustifications = {}) {'
);

const justLogic = `
        const subjectiveQids = new Set(['BC_Q1', 'BC_Q2', 'BC_Q3', 'BC_Q4', 'BC_Q5', 'IS_Q7', 'IS_Q16', 'PMF_Q15', 'PMF_Q17', 'TP_Q13', 'TP_Q14', 'TP_Q15', 'F_Q22', 'F_Q23', 'F_Q24', 'IP_Q22', 'IP_Q50']);
        const requiresJustification = q.cat_code === 'BC' || subjectiveQids.has(q.new_q_id);
        const existingJustification = humanJustifications[q.new_q_id] || '';
        
        let justHtml = '';
        if (requiresJustification) {
          justHtml = \`
            <div class="h-card-justification" style="margin-top: 12px; margin-bottom: 12px;">
              <label style="display: block; font-size: 12px; font-weight: 600; color: var(--text-main); margin-bottom: 6px;">Justification (Required)</label>
              <textarea class="justification-input" data-qid="\${q.new_q_id}" placeholder="Provide justification based on the markdown rubrics..." style="width: 100%; min-height: 70px; padding: 10px; border: 1px solid var(--border); border-radius: 6px; font-family: inherit; font-size: 13px; resize: vertical; box-sizing: border-box; background: var(--surface-main);">\${existingJustification}</textarea>
            </div>
          \`;
        }
        
        const isAnswered = ans !== undefined && ans !== null;
`;

renderCode = renderCode.replace(
  'const isAnswered = ans !== undefined && ans !== null;',
  justLogic
);

renderCode = renderCode.replace(
  '            ${citeHtml}\n            <div class="h-card-footer">',
  '            ${citeHtml}\n            ${justHtml}\n            <div class="h-card-footer">'
);

fs.writeFileSync('site/js/render.js', renderCode);
console.log('Patched render.js');

// Patch app.js
let appCode = fs.readFileSync('site/js/app.js', 'utf8');

// 1. Initializing state
appCode = appCode.replace(
  `      this.state.evaluations[sId] = { humanAnswers: {} };`,
  `      this.state.evaluations[sId] = { humanAnswers: {}, humanJustifications: {} };`
);

appCode = appCode.replace(
  `this.state.evaluations[sId] = data[sId];`,
  `{
          this.state.evaluations[sId] = data[sId];
          if (!this.state.evaluations[sId].humanJustifications) {
            this.state.evaluations[sId].humanJustifications = {};
          }
        }`
);

// 2. updateUI()
appCode = appCode.replace(
  `      sEval.humanAnswers\n    );`,
  `      sEval.humanAnswers,\n      sEval.humanJustifications\n    );`
);

// 3. answerHuman() update to include justification
appCode = appCode.replace(
  `this.state.syncQueue.push({ qid, value, timestamp: Date.now() });`,
  `const justification = sEval.humanJustifications ? (sEval.humanJustifications[qid] || '') : '';
    this.state.syncQueue.push({ qid, value, justification, timestamp: Date.now() });`
);

// 4. Add answerJustification() after answerHuman() { ... }
const answerJust = `
  answerJustification(qid, text) {
    const sEval = this.state.evaluations[this.state.activeStartupId];
    if (!sEval.humanJustifications) sEval.humanJustifications = {};
    sEval.humanJustifications[qid] = text;
    this.saveState();
    
    const value = sEval.humanAnswers[qid] !== undefined ? sEval.humanAnswers[qid] : null;
    this.state.syncQueue.push({ qid, value, justification: text, timestamp: Date.now() });
  },
`;
appCode = appCode.replace(
  `  refreshOverallProgress() {`,
  answerJust + `\n  refreshOverallProgress() {`
);

// 5. Submit validation
const validationCode = `
    const subjectiveQids = new Set(['BC_Q1', 'BC_Q2', 'BC_Q3', 'BC_Q4', 'BC_Q5', 'IS_Q7', 'IS_Q16', 'PMF_Q15', 'PMF_Q17', 'TP_Q13', 'TP_Q14', 'TP_Q15', 'F_Q22', 'F_Q23', 'F_Q24', 'IP_Q22', 'IP_Q50']);
    const needsJustification = (q) => q.cat_code === 'BC' || subjectiveQids.has(q.new_q_id);
    
    const missingQs = sData.human_questions.filter(q => {
      const hasAnswer = sEval.humanAnswers[q.new_q_id] !== undefined && sEval.humanAnswers[q.new_q_id] !== null;
      const justText = sEval.humanJustifications ? (sEval.humanJustifications[q.new_q_id] || '') : '';
      const hasJustification = justText.trim().length > 0;
      
      if (needsJustification(q)) {
          return !hasAnswer || !hasJustification;
      }
      return !hasAnswer;
    });
`;
appCode = appCode.replace(
  `const missingQs = sData.human_questions.filter(q => sEval.humanAnswers[q.new_q_id] === undefined);`,
  validationCode
);

// 6. Add event listener for textareas
const eventListenerCode = `
    document.getElementById('human-cards-container').addEventListener('input', (e) => {
      if (e.target.classList.contains('justification-input')) {
        const qid = e.target.dataset.qid;
        const text = e.target.value;
        this.answerJustification(qid, text);
      }
    });

    // REC 4: Event Delegation for human review buttons
`;
appCode = appCode.replace(
  `// REC 4: Event Delegation for human review buttons`,
  eventListenerCode
);

// 7. sync worker payload
appCode = appCode.replace(
  `scores: batch.map(b => ({ qid: b.qid, val: b.value }))`,
  `scores: batch.map(b => ({ qid: b.qid, val: b.value !== undefined ? b.value : null, justification: b.justification || '' }))`
);

fs.writeFileSync('site/js/app.js', appCode);
console.log('Patched app.js');

