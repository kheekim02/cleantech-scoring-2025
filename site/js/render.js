window.CTO = window.CTO || {};

window.CTO.Render = {
  icons: {
    doc: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>',
    check: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>',
    cross: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>',
    spark: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.2l1.85 4.95L18.8 10l-4.95 1.85L12 16.8l-1.85-4.95L5.2 10l4.95-1.85z"/><path d="M18.5 16.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z"/></svg>',
    link: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
    scan: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 12h10"/></svg>',
    shield: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>',
    arrowRight: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>',
    arrowLeft: '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>'
  },

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
      container.innerHTML = `<div class="pane-empty"><div class="pane-empty-mark">${this.icons.doc}</div><strong>No document loaded</strong><p>The source record for this applicant has not been ingested yet.</p></div>`;
      return;
    }

    const sections = documentData.sections.filter(s => s.cat_code === stepCat);
    
    if (sections.length === 0) {
      container.innerHTML = `<div class="pane-empty"><div class="pane-empty-mark">${this.icons.scan}</div><strong>Nothing mapped here</strong><p>No passages from the source application were mapped to this rubric section.</p></div>`;
      return;
    }

    let html = '';
    sections.forEach((sec, idx) => {
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
        <div class="doc-card" style="animation-delay: ${idx * 40}ms">
          <div class="doc-card-header">${this.icons.doc}<span>${sec.heading}</span></div>
          <div class="doc-card-body">
            <div class="doc-text-col">
              <div class="col-label">Raw Application Text</div>
              <div class="raw-text">${sec.text}</div>
            </div>
            <div class="doc-ext-col">
              <div class="col-label">AI Data Extraction</div>
              ${extHtml || '<div class="ext-value" style="color:var(--text-faint); font-weight:400; font-size:13px;">No specific extractions detected.</div>'}
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
      
      const maxPills = 6;
      let pillsHtml = '';
      let rendered = 0;
      for (let i = 0; i < aiCat.questions.length; i++) {
        const q = aiCat.questions[i];
        if (q.verdict === 1 && q.type !== 'INTEGER') {
           pillsHtml += `<div class="ai-pill" style="animation-delay: ${rendered * 30}ms">${this.icons.check}${q.new_q_id}</div>`;
           rendered++;
           if (rendered >= maxPills) break;
        }
      }
      if (passed > maxPills) {
        pillsHtml += `<div class="ai-pill-more" style="animation-delay: ${rendered * 30}ms">+${passed - maxPills} more verified</div>`;
      }
      aiPillsContainer.innerHTML = pillsHtml || '<span class="ai-pill-more">No checks passed.</span>';
    } else {
      document.getElementById('ai-checks-count').textContent = `0/0 checks`;
      document.getElementById('ai-avg-conf').textContent = `N/A`;
      aiPillsContainer.innerHTML = '';
    }

    const hContainer = document.getElementById('human-cards-container');
    let hHtml = '';
    
    if (sortedHqs.length === 0) {
      hHtml = `
        <div class="pane-empty verified">
          <div class="pane-empty-mark">${this.icons.shield}</div>
          <strong>Fully Machine-Verified</strong>
          <p>All checks in this section passed automated extraction. No human review is required.</p>
        </div>
      `;
    } else {
      sortedHqs.forEach((q, idx) => {
        const ans = answers[q.new_q_id];
        const isYesSelected = ans === 1 ? 'selected' : '';
        const isNoSelected = ans === 0 ? 'selected' : '';
        
        const suggYes = q.ai_suggestion === 1;
        const suggNo = q.ai_suggestion === 0;

        // Confidence Tier Badge Logic
        const confNum = parseFloat(q.ai_confidence || 0);
        let tierClass = 'conf-amber';
        if (confNum >= 0.85) tierClass = 'conf-green';
        if (confNum < 0.60) tierClass = 'conf-red';

        hHtml += `
          <div class="h-card" id="card-${q.new_q_id}" data-cite="${q.citation_id || ''}" style="animation-delay: ${(idx * 40) + 100}ms; cursor: pointer;">
            <div class="h-card-header">
              <div>
                <span class="h-tag">${q.cat_code}</span>
                <span class="h-qid">${q.new_q_id}</span>
              </div>
              <div class="h-ai-suggest ${tierClass}">
                ${this.icons.spark}
                <span class="verdict">${suggYes ? 'YES' : 'NO'}</span>
                <span class="divider"></span>
                <span class="score">${q.ai_confidence}</span>
              </div>
            </div>
            <div class="h-card-body">
              ${q.text}
            </div>
            <div class="h-card-footer">
              <a href="#" class="link-source">${this.icons.link} Linked to Source</a>
              <div class="h-actions">
                <button class="h-btn yes ${isYesSelected}" data-qid="${q.new_q_id}" data-val="1">
                  ${this.icons.check} YES
                </button>
                <button class="h-btn no ${isNoSelected}" data-qid="${q.new_q_id}" data-val="0">
                  ${this.icons.cross} NO
                </button>
              </div>
            </div>
          </div>
        `;
      });
    }
    
    hContainer.innerHTML = hHtml;
  },

  renderFooter(stepIndex, totalSteps) {
    const btnPrev = document.getElementById('btn-prev');
    const btnNext = document.getElementById('btn-next');

    btnPrev.disabled = stepIndex === 0;
    btnPrev.innerHTML = `${this.icons.arrowLeft} Previous`;
    
    if (stepIndex === totalSteps - 1) {
       btnNext.innerHTML = `Submit Evaluation ${this.icons.arrowRight}`;
    } else {
       btnNext.innerHTML = `Next Section ${this.icons.arrowRight}`;
    }
  },

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
    document.getElementById('step-progress-pill').textContent = `${stepAnswered} / ${stepTotal} answered`;
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
