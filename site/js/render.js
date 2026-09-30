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

    // 1. Extract ALL unique PDFs grouped by category
    const allCategories = [];
    let firstAvailablePdfUrl = null;
    let defaultPdfUrl = null;
    
    documentData.sections.forEach(sec => {
        if (sec.pdfs && sec.pdfs.length > 0) {
            const catName = this.categoryNames[sec.cat_code] || sec.heading || sec.cat_code;
            const pdfs = [];
            sec.pdfs.forEach(pdf => {
                if (!firstAvailablePdfUrl) firstAvailablePdfUrl = pdf.url;
                if (sec.cat_code === stepCat && !defaultPdfUrl) defaultPdfUrl = pdf.url;
                pdfs.push({ label: pdf.label || pdf.filename, url: pdf.url });
            });
            allCategories.push({ catName, pdfs });
        }
    });

    if (allCategories.length === 0) {
      container.innerHTML = `<div class="pane-empty"><div class="pane-empty-mark">${this.icons.doc}</div><strong>No Documents Found</strong><p>This applicant has no documents available.</p></div>`;
      return;
    }
    
    // Set default selection
    const activePdfUrl = defaultPdfUrl || firstAvailablePdfUrl;
    
    // 2. Build the Universal Dropdown
    let dropdownHtml = `<select id="universal-pdf-selector" style="width: 100%; padding: 8px 12px; margin-bottom: 16px; border-radius: 6px; border: 1px solid var(--border); font-size: 14px; background-color: var(--surface-sunk); color: var(--text-main); cursor: pointer;" onchange="window.CTO.Render.switchPDF(this.value)">`;
    
    allCategories.forEach(cat => {
        dropdownHtml += `<optgroup label="${cat.catName}">`;
        cat.pdfs.forEach(pdf => {
            const selected = (pdf.url === activePdfUrl) ? 'selected' : '';
            dropdownHtml += `<option value="${pdf.url}" ${selected}>${pdf.label}</option>`;
        });
        dropdownHtml += `</optgroup>`;
    });
    dropdownHtml += `</select>`;
    
    // Optional Notice if category has no explicitly mapped PDF
    let noticeHtml = '';
    if (!defaultPdfUrl) {
        noticeHtml = `<div style="padding: 10px 14px; background: #fff8e1; border-left: 3px solid var(--accent-yellow); margin-bottom: 16px; border-radius: 4px; font-size: 13px; color: #744210;">
          <strong>No specific document mapped.</strong> Displaying alternative application documents.
        </div>`;
    }

    // 3. Render the single Viewer
    let html = `<div class="pdf-viewer-container" style="display:flex; flex-direction:column; height:100%; width:100%;">
      ${dropdownHtml}
      ${noticeHtml}
      <div class="pdf-wrapper" style="flex: 1; display: flex; flex-direction: column; min-height: 600px; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; background: #fff;">
        <iframe id="primary-pdf-viewer" src="${activePdfUrl}#navpanes=0&pagemode=none" width="100%" height="100%" style="border: none; flex: 1;"></iframe>
      </div>
    </div>`;

    container.innerHTML = html;
  },
  
  switchPDF(url) {
    const iframe = document.getElementById('primary-pdf-viewer');
    if (iframe) {
        iframe.src = url + '#navpanes=0&pagemode=none';
    }
  },

  jumpToCitation(pdfFilename, pageNumber) {
    if (!pdfFilename) return;
    const selector = document.getElementById('universal-pdf-selector');
    if (!selector) return;

    const cleanName = pdfFilename.toLowerCase();
    const targetOption = Array.from(selector.options).find(opt => {
      const val = opt.value.toLowerCase();
      return val.endsWith(cleanName) || val.includes(encodeURIComponent(pdfFilename).toLowerCase()) || opt.textContent.toLowerCase().includes(cleanName.replace('.pdf', '').replace(/[_ -]/g, ' '));
    });

    if (targetOption) {
      selector.value = targetOption.value;
      const iframe = document.getElementById('primary-pdf-viewer');
      if (iframe) {
        let hash = pageNumber ? `#page=${pageNumber}` : '';
        hash += `${hash ? '&' : '#'}navpanes=0&pagemode=none`;
        iframe.src = targetOption.value.split('#')[0] + hash;
      }
    }
  },

  renderSectionDropdown(categories, activeCat, humanQuestions = [], humanAnswers = {}) {
    const selector = document.getElementById('section-nav-selector');
    if (!selector) return;

    let html = '';
    categories.forEach((catCode, idx) => {
      const name = this.categoryNames[catCode] || catCode;
      const catHqs = humanQuestions.filter(q => q.cat_code === catCode);
      const total = catHqs.length;
      const answered = catHqs.filter(q => humanAnswers[q.new_q_id || q.q_id] !== undefined && humanAnswers[q.new_q_id || q.q_id] !== null).length;
      const isDone = total > 0 && answered === total;
      const selected = (catCode === activeCat) ? 'selected' : '';
      const checkText = isDone ? ' ✓' : '';
      
      html += `<option value="${catCode}" ${selected}>${idx + 1}. ${name} (${answered}/${total}${checkText})</option>`;
    });

    selector.innerHTML = html;
    selector.value = activeCat;
  },

  renderRightPane(stepCat, stepIndex, totalSteps, humanQuestions, answers, humanJustifications = {}, flags = {}) {
    document.getElementById('step-counter').textContent = `STEP ${stepIndex + 1} OF ${totalSteps}`;
    document.getElementById('step-title').textContent = this.categoryNames[stepCat] || stepCat;
    
    const hqs = humanQuestions.filter(q => q.cat_code === stepCat);
    // Keep the rubric sequence stable. Never reorder by review status.
    const sortedHqs = [...hqs].sort((a, b) =>
      (a.new_q_id || a.q_id || '').localeCompare(
        b.new_q_id || b.q_id || '',
        undefined,
        { numeric: true, sensitivity: 'base' }
      )
    );

    const answeredCount = hqs.filter(q => answers[q.new_q_id] !== undefined).length;
    this.updateProgressText(answeredCount, hqs.length);

    const hContainer = document.getElementById('human-cards-container');
    let hHtml = '';
    
    if (sortedHqs.length === 0) {
      hHtml = `
        <div class="pane-empty verified">
          <div class="pane-empty-mark">${this.icons.shield}</div>
          <strong>No Questions In This Section</strong>
          <p>There are no human review criteria for this category.</p>
        </div>
      `;
    } else {
      sortedHqs.forEach((q, idx) => {
        const safeQuestionText = this.escapeHtml(q.text || '');
        const ans = answers[q.new_q_id];
        const isYesSelected = ans === 1 ? 'selected' : '';
        const isNoSelected = ans === 0 ? 'selected' : '';

        const noteQuestionIds = new Set(['BC_Q1', 'BC_Q2', 'BC_Q3', 'BC_Q4', 'BC_Q5', 'IS_Q7', 'IS_Q16', 'PMF_Q15', 'PMF_Q17', 'TP_Q13', 'TP_Q14', 'TP_Q15', 'F_Q22', 'F_Q23', 'F_Q24', 'IP_Q22', 'IP_Q50']);
        const requiredJustificationIds = new Set(['BC_Q1', 'BC_Q2', 'BC_Q4', 'BC_Q5']);
        const showsNote = noteQuestionIds.has(q.new_q_id);
        const requiresJustification = requiredJustificationIds.has(q.new_q_id);
        const existingJustification = this.escapeHtml(humanJustifications[q.new_q_id] || '');
        
        let justHtml = '';
        if (showsNote) {
          const hasRubric = ['BC_Q1', 'BC_Q2', 'BC_Q3', 'BC_Q4', 'BC_Q5'].includes(q.new_q_id);
          const rubricLink = hasRubric ? `<a href="#" class="view-rubric" data-qid="${q.new_q_id}" style="float: right; color: var(--accent-blue); text-decoration: none; font-weight: 500;">${window.CTO.Render.icons.doc || '📄'} View Examples</a>` : '';
          const noteLabel = requiresJustification ? 'Justification <span style="color: var(--accent-red);">required</span>' : 'Optional note';
          const notePlaceholder = requiresJustification
            ? (hasRubric ? 'Provide justification based on the markdown rubrics...' : 'Provide justification')
            : 'Add context if it would help explain your score';
          
          justHtml = `
            <div class="h-card-justification" style="padding: 0 24px 16px 24px;">
              <label style="display: block; font-size: 13px; font-weight: 600; color: var(--text-main); margin-bottom: 8px;">
                ${noteLabel}
                ${rubricLink}
              </label>
              <textarea class="justification-input" data-qid="${q.new_q_id}" placeholder="${notePlaceholder}" style="width: 100%; min-height: 80px; padding: 12px; border: 1px solid var(--border); border-radius: 6px; font-family: inherit; font-size: 13px; resize: vertical; box-sizing: border-box; background: var(--surface-main);">${existingJustification}</textarea>
            </div>
          `;
        }

        const actionHtml = q.options && q.options.length > 0 ? q.options
          .slice()
          .sort((a, b) => Number(a.val) - Number(b.val))
          .map(opt => {
            const isSel = ans === opt.val ? 'selected' : '';
            const cls = opt.val > 0 ? 'yes' : 'no';
            return `
              <button class="h-btn ${cls} ${isSel}" data-qid="${q.new_q_id || q.q_id}" data-val="${opt.val}">
                ${this.formatPoints(opt.val)}
              </button>
            `;
          }).join('') : `
            <button class="h-btn no ${isNoSelected}" data-qid="${q.new_q_id || q.q_id}" data-val="0">
              ${this.icons.cross} 0 pts
            </button>
            <button class="h-btn yes ${isYesSelected}" data-qid="${q.new_q_id || q.q_id}" data-val="1">
              ${this.icons.check} 1 pt
            </button>
          `;

        const isFlagged = Boolean(flags[q.new_q_id || q.q_id]);
        const flagIconSvg = `<svg class="flag-icon-svg" viewBox="0 0 24 24" fill="${isFlagged ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="13" height="13" style="vertical-align: -1px;"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"></path><line x1="4" y1="22" x2="4" y2="15"></line></svg>`;
        const flagBtnHtml = `
          <button class="flag-btn ${isFlagged ? 'flagged' : ''}" data-action="toggle-flag" data-qid="${q.new_q_id || q.q_id}" title="${isFlagged ? 'Flagged for review (Click to unflag)' : 'Flag this question for review'}">
            <span class="flag-icon">${flagIconSvg}</span>
            <span class="flag-label">${isFlagged ? 'Flagged' : 'Flag for Review'}</span>
          </button>
        `;
        
        hHtml += `
          <div class="h-card ${isFlagged ? 'is-flagged' : ''}" id="card-${q.new_q_id}" data-qid="${q.new_q_id}" style="animation-delay: ${(idx * 40) + 100}ms;">
            <div class="h-card-header">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span class="h-tag">${q.cat_code}</span>
                <span class="h-qid">${q.new_q_id}</span>
              </div>
              <div style="display: flex; align-items: center; gap: 10px;">
                ${flagBtnHtml}
              </div>
            </div>
            <div class="h-card-body">
              ${safeQuestionText}
            </div>
            <div class="h-card-actions">
              <div class="h-actions">
                ${actionHtml}
              </div>
            </div>
            ${justHtml}
            <div class="h-card-footer"></div>
          </div>
        `;
      });
    }
    
    hContainer.innerHTML = hHtml;
    
  },

  formatPoints(value) {
    const score = Number(value);
    if (!Number.isFinite(score)) return String(value);
    return `${score} ${score === 1 ? 'pt' : 'pts'}`;
  },

  escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]);
  },

  renderFooter(stepIndex, totalSteps) {
    const btnPrev = document.getElementById('btn-prev');
    const btnNext = document.getElementById('btn-next');

    btnPrev.disabled = stepIndex === 0;
    btnPrev.innerHTML = `${this.icons.arrowLeft} Previous`;
    btnNext.classList.toggle('btn-submit', stepIndex === totalSteps - 1);
    
    if (stepIndex === totalSteps - 1) {
       btnNext.innerHTML = `Submit Evaluation ${this.icons.arrowRight}`;
    } else {
       btnNext.innerHTML = `Next Section ${this.icons.arrowRight}`;
    }
  },

  updateQuestionState(qid, value) {
    const btns = document.querySelectorAll(`.h-btn[data-qid="${qid}"]`);
    btns.forEach(btn => btn.classList.remove('selected'));
    if (value !== null && value !== undefined) {
      const selectedBtn = Array.from(btns).find(b => parseFloat(b.dataset.val) === value);
      if (selectedBtn) selectedBtn.classList.add('selected');
    }
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
  },

  updateFlagState(qid, isFlagged) {
    const card = document.getElementById(`card-${qid}`);
    if (card) {
      if (isFlagged) {
        card.classList.add('is-flagged');
      } else {
        card.classList.remove('is-flagged');
      }
      const flagBtn = card.querySelector(`[data-action="toggle-flag"]`);
      if (flagBtn) {
        const iconSvg = flagBtn.querySelector('.flag-icon-svg');
        const label = flagBtn.querySelector('.flag-label');
        if (isFlagged) {
          flagBtn.classList.add('flagged');
          flagBtn.title = 'Flagged for review (Click to unflag)';
          if (iconSvg) iconSvg.setAttribute('fill', 'currentColor');
          if (label) label.textContent = 'Flagged';
        } else {
          flagBtn.classList.remove('flagged');
          flagBtn.title = 'Flag this question for review';
          if (iconSvg) iconSvg.setAttribute('fill', 'none');
          if (label) label.textContent = 'Flag for Review';
        }
      }
    }
  },

  updateFlaggedNavBadge(count) {
    const badge = document.getElementById('nav-flagged-count');
    const btn = document.getElementById('btn-flagged-modal');
    if (badge) {
      badge.textContent = count;
      if (count > 0) {
        badge.style.background = '#ef4444';
        badge.style.color = '#ffffff';
        if (btn) {
          btn.style.borderColor = '#fca5a5';
          btn.style.background = '#fef2f2';
          btn.style.color = '#991b1b';
        }
      } else {
        badge.style.background = 'rgba(255, 255, 255, 0.2)';
        badge.style.color = '#ffffff';
        if (btn) {
          btn.style.borderColor = 'rgba(255, 255, 255, 0.16)';
          btn.style.background = 'rgba(255, 255, 255, 0.08)';
          btn.style.color = 'var(--text-light)';
        }
      }
    }
  }
};
