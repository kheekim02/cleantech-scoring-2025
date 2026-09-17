window.CTO = window.CTO || {};

window.CTO.Render = {
  categoryNames: {
    'BC': 'Business Canvas', 'ES': 'Environmental & Social', 'F': 'Financials',
    'IP': 'Investor Pitch', 'IS': 'Impact Strategy', 'L': 'Legal',
    'M': 'Marketing', 'PMF': 'Product Market Fit', 'T': 'Team', 'TP': 'Tech / Product'
  },

  renderLeftPane(stepCat, documentData) {
    const container = document.getElementById('extraction-viewer');
    const pill = document.getElementById('left-step-pill');
    pill.textContent = this.categoryNames[stepCat] || stepCat;

    if (!documentData || !documentData.sections) {
      container.innerHTML = '<p style="padding: 24px;">No document available.</p>';
      return;
    }

    const sections = documentData.sections.filter(s => s.cat_code === stepCat);
    
    if (sections.length === 0) {
      container.innerHTML = '<p style="padding: 24px; color: var(--text-muted); font-size: 14px;">No specific source document extractions were mapped to this section.</p>';
      return;
    }

    let html = '';
    sections.forEach(sec => {
      let extHtml = '';
      if (sec.extractions && sec.extractions.length > 0) {
        extHtml = sec.extractions.map(ext => `
          <div class="ext-box ${ext.highlight ? 'highlighted' : ''}">
            <div class="ext-label">${ext.label}</div>
            <div class="ext-value">${ext.value}</div>
          </div>
        `).join('');
      }

      html += `
        <div class="doc-card">
          <div class="doc-card-header">📄 ${sec.heading}</div>
          <div class="doc-card-body">
            <div class="doc-text-col">
              <div class="col-label">RAW APPLICATION TEXT</div>
              <div class="raw-text">${sec.text}</div>
            </div>
            <div class="doc-ext-col">
              <div class="col-label">AI DATA EXTRACTION</div>
              ${extHtml || '<div class="ext-value" style="color:var(--text-muted); font-weight:400; font-size:12px;">No specific extractions detected.</div>'}
            </div>
          </div>
        </div>
      `;
    });
    container.innerHTML = html;
  },

  renderRightPane(stepCat, stepIndex, totalSteps, aiCats, humanQuestions, answers) {
    document.getElementById('step-counter').textContent = `STEP ${stepIndex + 1} OF ${totalSteps}`;
    document.getElementById('step-title').textContent = this.categoryNames[stepCat] || stepCat;
    
    const hqs = humanQuestions.filter(q => q.cat_code === stepCat);
    
    // REC 3: Sort human questions before rendering
    const sortedHqs = (window.CTO.Scoring && window.CTO.Scoring.sortHumanQueue) 
        ? window.CTO.Scoring.sortHumanQueue(hqs, answers) 
        : hqs;

    const answeredCount = hqs.filter(q => answers[q.new_q_id] !== undefined).length;
    this.updateProgressText(answeredCount, hqs.length);

    const aiCat = aiCats[stepCat];
    const aiPillsContainer = document.getElementById('ai-pills-container');
    
    if (aiCat && aiCat.questions && aiCat.questions.length > 0) {
      const passed = aiCat.passed;
      const total = aiCat.total;
      document.getElementById('ai-checks-count').textContent = `${passed}/${total} checks passed`;
      document.getElementById('ai-avg-conf').textContent = `Avg Conf: ${aiCat.avg_conf || 0.90}`;
      
      const maxPills = 4;
      let pillsHtml = '';
      let rendered = 0;
      for (let i = 0; i < aiCat.questions.length; i++) {
        const q = aiCat.questions[i];
        if (q.verdict === 1 && q.type !== 'INTEGER') {
           pillsHtml += `<div class="ai-pill">✓ ${q.new_q_id}</div>`;
           rendered++;
           if (rendered >= maxPills) break;
        }
      }
      if (passed > maxPills) {
        pillsHtml += `<div class="ai-pill-more">+ ${passed - maxPills} more checks...</div>`;
      }
      aiPillsContainer.innerHTML = pillsHtml || '<span class="ai-pill-more">No checks passed.</span>';
    } else {
      document.getElementById('ai-checks-count').textContent = `0/0 checks`;
      document.getElementById('ai-avg-conf').textContent = `Avg Conf: N/A`;
      aiPillsContainer.innerHTML = '';
    }

    const hContainer = document.getElementById('human-cards-container');
    let hHtml = '';
    sortedHqs.forEach(q => {
      const ans = answers[q.new_q_id];
      const isYesSelected = ans === 1 ? 'selected' : '';
      const isNoSelected = ans === 0 ? 'selected' : '';
      
      const suggYes = q.ai_suggestion === 1;
      const suggNo = q.ai_suggestion === 0;

      // REC 4: Replaced onclick with data attributes
      hHtml += `
        <div class="h-card" id="card-${q.new_q_id}">
          <div class="h-card-header">
            <div>
              <span class="h-tag">${q.cat_code}</span>
              <span class="h-qid">${q.new_q_id}</span>
            </div>
            <div class="h-ai-suggest">
              🤖 AI Suggests: ${suggYes ? 'YES' : 'NO'} (${q.ai_confidence})
            </div>
          </div>
          <div class="h-card-body">
            ${q.text}
          </div>
          <div class="h-card-footer">
            <a href="#" class="link-source">🔗 Linked to Source</a>
            <div class="h-actions">
              <button class="h-btn yes ${isYesSelected}" data-qid="${q.new_q_id}" data-val="1">
                ✓ YES
              </button>
              <button class="h-btn no ${isNoSelected}" data-qid="${q.new_q_id}" data-val="0">
                ✗ NO
              </button>
            </div>
          </div>
        </div>
      `;
    });
    
    if (sortedHqs.length === 0) {
      hHtml = '<div style="color:var(--text-muted); font-size: 13px;">No human review required for this section.</div>';
    }
    
    hContainer.innerHTML = hHtml;
  },

  renderFooter(stepIndex, totalSteps) {
    const btnPrev = document.getElementById('btn-prev');
    const btnNext = document.getElementById('btn-next');

    btnPrev.disabled = stepIndex === 0;
    
    if (stepIndex === totalSteps - 1) {
       btnNext.textContent = 'Submit Evaluation';
    } else {
       btnNext.textContent = 'Next Section →';
    }
  },

  // REC 1: Surgical DOM updates
  updateQuestionState(qid, value) {
    const btnYes = document.querySelector(`.h-btn.yes[data-qid="${qid}"]`);
    const btnNo = document.querySelector(`.h-btn.no[data-qid="${qid}"]`);
    if (!btnYes || !btnNo) return;

    btnYes.classList.remove('selected');
    btnNo.classList.remove('selected');

    if (value === 1) btnYes.classList.add('selected');
    if (value === 0) btnNo.classList.add('selected');
  },

  updateProgressText(stepAnswered, stepTotal) {
    document.getElementById('step-progress-pill').textContent = `${stepAnswered} / ${stepTotal} human questions done`;
  },

  updateOverallProgress(answeredCount, totalHumanQs) {
    const pct = totalHumanQs > 0 ? (answeredCount / totalHumanQs) * 100 : 0;
    document.getElementById('overall-progress-fill').style.width = `${pct}%`;
    
    const btnNext = document.getElementById('btn-next');
    if (btnNext.textContent.includes('Submit')) {
      if (answeredCount >= totalHumanQs) {
        btnNext.classList.add('ready');
      } else {
        btnNext.classList.remove('ready');
      }
    }
  }
};
