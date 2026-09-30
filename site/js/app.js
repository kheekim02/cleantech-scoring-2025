const CTO = window.CTO = window.CTO || {};

CTO.App = {
  state: {
    activeStartupId: 'solarpure',
    currentStepIndex: 0,
    categories: ['BC', 'ES', 'F', 'IP', 'IS', 'L', 'M', 'PMF', 'T', 'TP'],
    evaluations: {},
    startups: {},
    syncQueue: [] // REC 5: Optimistic Sync Queue
  },

  init() {
    fetch('/api/auth-session?role=scorer').then(async res => {
      if (!res.ok) throw new Error('No active session');
      return res.json();
    }).then(data => {
      this.currentUser = data.user;
      this.applyUserRoleUI();
      document.getElementById('login-modal').style.display = 'none';
      this.loadStartupsList().then(() => this.startApp());
    }).catch(() => {
      document.getElementById('login-modal').style.display = 'flex';
      this.setSaveStatus('Sign in required');
    });
  },

  applyUserRoleUI() {
    const banner = document.getElementById('test-mode-banner');
    if (banner) {
      banner.style.display = this.currentUser?.is_test ? 'flex' : 'none';
    }
    const accountLabel = document.getElementById('nav-account-label');
    const dropdownUserId = document.getElementById('dropdown-user-id');
    const username = this.currentUser?.id || 'Account';
    if (accountLabel) accountLabel.textContent = username;
    if (dropdownUserId) dropdownUserId.textContent = username;
  },

  async handleLogin() {
    const id = document.getElementById('auth-judge-id').value.trim();
    const pass = document.getElementById('auth-passcode').value.trim();
    if (!id || !pass) return;
    
    const btn = document.querySelector('#login-modal button');
    btn.textContent = 'Verifying...';
    
    try {
      const res = await fetch('/api/auth-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'scorer', judge_id: id, password: pass })
      });
      
      if (res.ok) {
        const authData = await res.json();
        this.currentUser = authData.user;
        this.applyUserRoleUI();
        document.getElementById('login-modal').style.display = 'none';
        this.loadStartupsList().then(() => this.startApp());
      } else {
        const errData = await res.json();
        document.getElementById('login-error').textContent = errData.error || 'Invalid credentials.';
        document.getElementById('login-error').style.display = 'block';
        btn.textContent = 'Authenticate';
      }
    } catch (e) {
      document.getElementById('login-error').textContent = 'Network error connecting to database.';
      document.getElementById('login-error').style.display = 'block';
      btn.textContent = 'Authenticate';
    }
  },


  async loadStartupsList() {
    try {
      const res = await fetch('/api/list-startups');
      if (res.ok) {
        const startups = await res.json();
        const picker = document.getElementById('startup-picker');
        picker.innerHTML = startups.map(s => `<option value="${s.id}">${CTO.Render.escapeHtml(s.name)}</option>`).join('');
        picker.style.display = 'inline-block';
        
        // If the current activeStartupId is not in the list, default to first
        if (!startups.find(s => s.id === this.state.activeStartupId) && startups.length > 0) {
          this.state.activeStartupId = startups[0].id;
        } else {
          picker.value = this.state.activeStartupId;
        }

        picker.addEventListener('change', (e) => {
          this.state.activeStartupId = e.target.value;
          this.state.currentStepIndex = 0;
          this.startApp();
        });
      }
    } catch (e) {
      console.error("Failed to load startups list", e);
    }
  },

  async startApp() {

    try {
      const res = await fetch(`/api/get-startup?id=${encodeURIComponent(this.state.activeStartupId)}`);
      const data = await res.json();
      this.state.startups[this.state.activeStartupId] = data;
      document.getElementById('hdr-startup-name').textContent = data.meta?.name || this.state.activeStartupId;
    } catch (e) {
      console.error("Failed to load startup", e);
    }

    this.loadState();
    this.setupListeners();
    this.startSyncWorker(); // REC 5
    this.setSaveStatus('Saved');
    this.updateUI();
  },

  setupListeners() {
    if (this._listenersSetup) return;
    this._listenersSetup = true;
    document.getElementById('btn-prev').addEventListener('click', () => {
      if (this.state.currentStepIndex > 0) {
        this.state.currentStepIndex--;
        this.updateUI();
        const scrollArea = document.querySelector('.right-scroll-area');
        if (scrollArea) scrollArea.scrollTop = 0;
      }
    });

    document.getElementById('btn-next').addEventListener('click', () => {
      if (this.state.currentStepIndex < this.state.categories.length - 1) {
        this.state.currentStepIndex++;
        this.updateUI();
        const scrollArea = document.querySelector('.right-scroll-area');
        if (scrollArea) scrollArea.scrollTop = 0;
      } else {
        this.submitEvaluation();
      }
    });

    
    document.getElementById('human-cards-container').addEventListener('input', (e) => {
      if (e.target.classList.contains('justification-input')) {
        const qid = e.target.dataset.qid;
        const text = e.target.value;
        this.answerJustification(qid, text);
      }
    });

    // REC 4: Event Delegation for human review buttons

    document.getElementById('human-cards-container').addEventListener('click', (e) => {
      // Toggle flag for review
      const flagBtn = e.target.closest('[data-action="toggle-flag"]');
      if (flagBtn) {
        e.preventDefault();
        const qid = flagBtn.dataset.qid;
        this.toggleFlag(qid);
        return;
      }

      // Toggle rubric modal
      const rubricLink = e.target.closest('.view-rubric');
      if (rubricLink) {
        e.preventDefault();
        this.openRubricModal(rubricLink.dataset.qid);
        return;
      }

      // Direct jump link inside dossier
      const jumpBtn = e.target.closest('[data-action="jump-pdf"]');
      if (jumpBtn) {
        e.preventDefault();
        if (jumpBtn.dataset.pdf) {
          CTO.Render.jumpToCitation(jumpBtn.dataset.pdf, jumpBtn.dataset.page);
        }
        return;
      }

      // Toggle AI Diligence Dossier logic
      let card = e.target.closest('.h-card');
      const link = e.target.closest('.link-source');
      if (link) {
        e.preventDefault(); // prevent default anchor jump
        if (card) {
          const citeBlock = card.querySelector('.h-card-citation');
          if (citeBlock) {
            const isHidden = citeBlock.style.display === 'none';
            citeBlock.style.display = isHidden ? 'block' : 'none';
            const dossierTitle = link.dataset.title || 'AI Diligence Dossier';
            link.innerHTML = isHidden 
              ? `${CTO.Render.icons.link} Collapse ${dossierTitle} ↑` 
              : `${CTO.Render.icons.link} Expand ${dossierTitle} ↓`;
            
            // Auto-jump viewer to document & page when opening citation
            if (isHidden && link.dataset.pdf) {
              CTO.Render.jumpToCitation(link.dataset.pdf, link.dataset.page);
            }
          }
        }
      }

      // Button answer logic
      const btn = e.target.closest('.h-btn');
      if (btn) {
        const qid = btn.dataset.qid;
        const val = parseFloat(btn.dataset.val);
        this.answerHuman(qid, val);
      }
    });

    // REC 2: Event Delegation for audit list jumps

    document.getElementById('rubric-modal-close').addEventListener('click', () => {
      document.getElementById('rubric-modal').style.display = 'none';
    });
    document.getElementById('rubric-modal').addEventListener('click', (e) => {
      if (e.target.id === 'rubric-modal') {
        e.target.style.display = 'none';
      }
    });

    const btnFlagged = document.getElementById('btn-flagged-modal');
    if (btnFlagged) {
      btnFlagged.addEventListener('click', (e) => {
        e.preventDefault();
        this.openFlaggedModal();
      });
    }

    const flaggedModal = document.getElementById('flagged-modal');
    if (flaggedModal) {
      flaggedModal.addEventListener('click', (e) => {
        if (e.target.id === 'flagged-modal') {
          this.closeFlaggedModal();
        }
      });
    }

    const btnFeedback = document.getElementById('btn-feedback-modal');
    if (btnFeedback) {
      btnFeedback.addEventListener('click', (e) => {
        e.preventDefault();
        this.openFeedbackModal();
      });
    }

    const feedbackModal = document.getElementById('feedback-modal');
    if (feedbackModal) {
      feedbackModal.addEventListener('click', (e) => {
        if (e.target.id === 'feedback-modal') {
          this.closeFeedbackModal();
        }
      });
    }

    const feedbackInput = document.getElementById('feedback-input');
    if (feedbackInput) {
      feedbackInput.addEventListener('input', () => {
        const charCount = document.getElementById('feedback-char-count');
        if (charCount) {
          charCount.textContent = `${feedbackInput.value.length.toLocaleString()} / 5,000 chars`;
        }
      });
    }

    document.addEventListener('click', (e) => {
      if (!e.target.closest('.nav-dropdown')) {
        this.closeAllDropdowns();
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeAllDropdowns();
        this.closeFlaggedModal();
        this.closeFeedbackModal();
        this.closeFaqModal();
        this.closePasswordModal();
      }
    });

    document.getElementById('submit-modal').addEventListener('click', (e) => {
      if (e.target.tagName === 'A' && e.target.dataset.qid) {
        e.preventDefault();
        const catCode = e.target.dataset.cat;
        const qid = e.target.dataset.qid;
        this.jumpToQuestion(catCode, qid);
      }
    });

    const confirmBtn = document.getElementById('modal-confirm-btn');
    if (confirmBtn) {
      confirmBtn.addEventListener('click', async () => {
        confirmBtn.textContent = 'Submitting to Database...';
        confirmBtn.disabled = true;

        const saved = await this.flushSyncQueue();
        if (!saved) {
          confirmBtn.textContent = 'Save failed — retry';
          confirmBtn.disabled = false;
          this.setSaveStatus('Save failed — retrying');
          return;
        }

        confirmBtn.textContent = '✓ Logged to Database';
        confirmBtn.style.background = 'var(--accent-green)';
        setTimeout(() => {
          document.getElementById('submit-modal').style.display = 'none';
          confirmBtn.textContent = 'Confirm & Submit';
          confirmBtn.disabled = false;
          confirmBtn.style.background = '';
          alert('Your evaluation has been successfully submitted and logged in the database!');
        }, 800);
      });
    }
  },


  openRubricModal(qid) {
    const modal = document.getElementById('rubric-modal');
    const title = document.getElementById('rubric-modal-title');
    const body = document.getElementById('rubric-modal-body');
    
    let rubricContent = '';
    
    // Hardcoded tables parsed from markdown for rapid reference (0 - 1 point scale)
    if (qid === 'BC_Q1') {
      title.textContent = 'Value Proposition Scoring (BC_Q1)';
      rubricContent = `
      <div style="margin-bottom: 12px; font-size: 13px; color: var(--text-muted);">
        Official scoring criteria mapped to the <strong>0 – 1 Scale</strong>:
      </div>
      <table style="width: 100%; border-collapse: collapse; text-align: left;">
        <thead>
          <tr style="background: var(--surface-sunk);">
            <th style="padding: 10px; border: 1px solid var(--border); width: 110px;">Score</th>
            <th style="padding: 10px; border: 1px solid var(--border);">Example Justification / Content</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 4px; border: 1px solid #cbd5e1; font-size: 12px;">0 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Dirty water solution, we remove the waste just like other companies."</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fff7ed; color: #c2410c; padding: 3px 8px; border-radius: 4px; border: 1px solid #fed7aa; font-size: 12px;">0.25 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Municipalities, industrial facilities, and commercial establishments grappling with diverse wastewater treatment requirements."</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fef9c3; color: #854d0e; padding: 3px 8px; border-radius: 4px; border: 1px solid #fde047; font-size: 12px;">0.5 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Save customer money while reducing carbon footprint, help meet upcoming regulations and requirements set by industry."</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f0fdf4; color: #15803d; padding: 3px 8px; border-radius: 4px; border: 1px solid #bbf7d0; font-size: 12px;">0.75 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Easy integratable filtration technology, save 60% on costs, creates a more eco friendly and efficient wastewater process, cost competitive price with reliable service."</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #ecfdf5; color: #047857; padding: 3px 8px; border-radius: 4px; border: 1px solid #6ee7b7; font-size: 12px;">1 pt</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Advanced filtration membrane designed to effectively remove up to 95% of contaminants and pollutants from wastewater, help reduce WTTP energy costs of up to 60%... provide a more cost effective way to deal with your wastewater than market alternatives."</td>
          </tr>
        </tbody>
      </table>
      `;
    } else if (qid === 'BC_Q2') {
      title.textContent = 'Customer Segments Scoring (BC_Q2)';
      rubricContent = `
      <div style="margin-bottom: 12px; font-size: 13px; color: var(--text-muted);">
        Official scoring criteria mapped to the <strong>0 – 1 Scale</strong>:
      </div>
      <table style="width: 100%; border-collapse: collapse; text-align: left;">
        <thead>
          <tr style="background: var(--surface-sunk);">
            <th style="padding: 10px; border: 1px solid var(--border); width: 110px;">Score</th>
            <th style="padding: 10px; border: 1px solid var(--border);">Example Justification / Content</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 4px; border: 1px solid #cbd5e1; font-size: 12px;">0 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Businesses who need to deal with wastewater"</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fff7ed; color: #c2410c; padding: 3px 8px; border-radius: 4px; border: 1px solid #fed7aa; font-size: 12px;">0.25 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Industrial waste benefaction, chemical producers, power companies, manufacturing companies, and biochemical industries"</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fef9c3; color: #854d0e; padding: 3px 8px; border-radius: 4px; border: 1px solid #fde047; font-size: 12px;">0.5 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Industrial waste benefaction Chemical producers Power companies... Manufacturing companies Biochemical industries"</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f0fdf4; color: #15803d; padding: 3px 8px; border-radius: 4px; border: 1px solid #bbf7d0; font-size: 12px;">0.75 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Domestic US Corporations: chief sustainability officer And health and safety. Communities: Waste management & economic Development"</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #ecfdf5; color: #047857; padding: 3px 8px; border-radius: 4px; border: 1px solid #6ee7b7; font-size: 12px;">1 pt</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Oil and gas: Refinery wastewater Treatment Hydraulic fracturing... Commercial Properties: Hotels, Restaurants... Agriculture: Fertilizer production Livestock operations Irrigation water reuse"</td>
          </tr>
        </tbody>
      </table>
      `;
    } else if (qid === 'BC_Q3') {
      title.textContent = 'Customer Interviews Scoring (BC_Q3)';
      rubricContent = `
      <div style="margin-bottom: 12px; font-size: 13px; color: var(--text-muted);">
        Official scoring criteria mapped to the <strong>0 – 1 Scale</strong>:
      </div>
      <table style="width: 100%; border-collapse: collapse; text-align: left;">
        <thead>
          <tr style="background: var(--surface-sunk);">
            <th style="padding: 10px; border: 1px solid var(--border); width: 110px;">Score</th>
            <th style="padding: 10px; border: 1px solid var(--border);">Interview Threshold & Evidence</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 4px; border: 1px solid #cbd5e1; font-size: 12px;">0 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">0 customer interviews documented; no customer discovery evidence found.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fff7ed; color: #c2410c; padding: 3px 8px; border-radius: 4px; border: 1px solid #fed7aa; font-size: 12px;">0.25 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">1 customer interview conducted or vague anecdotal customer interactions mentioned.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fef9c3; color: #854d0e; padding: 3px 8px; border-radius: 4px; border: 1px solid #fde047; font-size: 12px;">0.5 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">2–3 customer interviews documented with basic qualitative feedback.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f0fdf4; color: #15803d; padding: 3px 8px; border-radius: 4px; border: 1px solid #bbf7d0; font-size: 12px;">0.75 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">4 customer interviews documented with structured insights and segment context.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #ecfdf5; color: #047857; padding: 3px 8px; border-radius: 4px; border: 1px solid #6ee7b7; font-size: 12px;">1 pt</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">5 or more customer interviews documented with names/titles, learnings, and quotes.</td>
          </tr>
        </tbody>
      </table>
      `;
    } else if (qid === 'BC_Q4') {
      title.textContent = 'Large Brackets Scoring (BC_Q4)';
      rubricContent = `
      <div style="margin-bottom: 12px; font-size: 13px; color: var(--text-muted);">
        Official scoring criteria mapped to the <strong>0 – 1 Scale</strong>:
      </div>
      <div style="margin-top: 8px; margin-bottom: 12px; padding: 8px 12px; background: #f0f9ff; border-left: 4px solid #0284c7; border-radius: 4px; font-size: 13px;">
        <strong>Large / Big Brackets (🔵 Blue in Strategyzer Template):</strong><br>
        <span style="font-size: 12px; color: #0369a1; font-weight: 600;">1. Key Partners &nbsp;·&nbsp; 2. Value Propositions &nbsp;·&nbsp; 3. Customer Segments &nbsp;·&nbsp; 4. Cost Structure &nbsp;·&nbsp; 5. Revenue Streams</span>
      </div>
      <div style="text-align: center; margin: 10px 0 14px 0;">
        <img src="img/bmc_brackets_strategyzer.png" alt="Strategyzer BMC Brackets" style="width: 100%; max-height: 220px; object-fit: contain; border-radius: 6px; border: 1px solid #cbd5e1; box-shadow: 0 1px 2px rgba(0,0,0,0.08);">
      </div>
      <table style="width: 100%; border-collapse: collapse; text-align: left;">
        <thead>
          <tr style="background: var(--surface-sunk);">
            <th style="padding: 10px; border: 1px solid var(--border); width: 110px;">Score</th>
            <th style="padding: 10px; border: 1px solid var(--border);">Evaluation Standard & Criteria</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 4px; border: 1px solid #cbd5e1; font-size: 12px;">0 – 0.25 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);"><strong>Vague generalities:</strong> Minimal detail or generic placeholders (e.g. "social media", "branding", "businesses") with no specific execution plan.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fef9c3; color: #854d0e; padding: 3px 8px; border-radius: 4px; border: 1px solid #fde047; font-size: 12px;">0.5 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);"><strong>Moderate detail:</strong> Includes specific mediums (e.g. "Trade show participation", direct sales outreach) but lacks granular segmentation, pricing, or relationship models.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #ecfdf5; color: #047857; padding: 3px 8px; border-radius: 4px; border: 1px solid #6ee7b7; font-size: 12px;">0.75 – 1 pt</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);"><strong>Extremely detailed & articulate:</strong> Granular pricing ("Starter kit: $1,000", "Annual O&M service $2,000"), distinct relationships (short-term transactional vs long-term SLA contracts), and robust customer acquisition channels.</td>
          </tr>
        </tbody>
      </table>
      `;
    } else if (qid === 'BC_Q5') {
      title.textContent = 'Small Brackets Scoring (BC_Q5)';
      rubricContent = `
      <div style="margin-bottom: 12px; font-size: 13px; color: var(--text-muted);">
        Official scoring criteria mapped to the <strong>0 – 1 Scale</strong>:
      </div>
      <div style="margin-top: 8px; margin-bottom: 12px; padding: 8px 12px; background: #fefce8; border-left: 4px solid #ca8a04; border-radius: 4px; font-size: 13px;">
        <strong>Small / Connecting Brackets (🟡 Yellow in Strategyzer Template):</strong><br>
        <span style="font-size: 12px; color: #854d0e; font-weight: 600;">1. Key Activities &nbsp;·&nbsp; 2. Key Resources &nbsp;·&nbsp; 3. Customer Relationships &nbsp;·&nbsp; 4. Channels</span>
      </div>
      <div style="text-align: center; margin: 10px 0 14px 0;">
        <img src="img/bmc_brackets_strategyzer.png" alt="Strategyzer BMC Brackets" style="width: 100%; max-height: 220px; object-fit: contain; border-radius: 6px; border: 1px solid #cbd5e1; box-shadow: 0 1px 2px rgba(0,0,0,0.08);">
      </div>
      <table style="width: 100%; border-collapse: collapse; text-align: left;">
        <thead>
          <tr style="background: var(--surface-sunk);">
            <th style="padding: 10px; border: 1px solid var(--border); width: 110px;">Score</th>
            <th style="padding: 10px; border: 1px solid var(--border);">Evaluation Standard & Criteria</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 4px; border: 1px solid #cbd5e1; font-size: 12px;">0 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);"><strong>Generic or placeholder:</strong> Superficial descriptions (e.g. "The cost to manufacture", "Money and employees") with no breakdown of cost drivers or core partners.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fef9c3; color: #854d0e; padding: 3px 8px; border-radius: 4px; border: 1px solid #fde047; font-size: 12px;">0.5 pts</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);"><strong>Partially specified:</strong> Mentions some specific resources or partner entities (e.g. "Columbia university lab", fabrication partner) but lacks cost allocation or resource depth.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #ecfdf5; color: #047857; padding: 3px 8px; border-radius: 4px; border: 1px solid #6ee7b7; font-size: 12px;">1 pt</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);"><strong>Exhaustive & granular:</strong> Specific breakdowns across partners and activities ("M&E costs for prototype", "3rd party lab validation", "Local permitting requirements", "Unit Operations vs Ammonia Sales").</td>
          </tr>
        </tbody>
      </table>
      `;
    }
    
    body.innerHTML = rubricContent;
    modal.style.display = 'flex';
  },

  updateUI() {
    const sId = this.state.activeStartupId;
    const sData = this.state.startups[sId];
    const sEval = this.state.evaluations[sId];
    
    if (!sData) return;

    const catCode = this.state.categories[this.state.currentStepIndex];
    
    CTO.Render.renderLeftPane(catCode, sData.document);
    CTO.Render.renderSectionDropdown(
      this.state.categories,
      catCode,
      sData.human_questions,
      sEval.humanAnswers
    );
    CTO.Render.renderRightPane(
      catCode,
      this.state.currentStepIndex,
      this.state.categories.length,
      sData.ai_cats,
      sData.human_questions,
      sEval.humanAnswers,
      sEval.humanJustifications,
      sEval.humanFlags || {}
    );
    CTO.Render.renderFooter(
      this.state.currentStepIndex,
      this.state.categories.length
    );
    this.refreshOverallProgress();
    this.refreshFlaggedCount();

  },

  answerHuman(qid, value) {
    const sEval = this.state.evaluations[this.state.activeStartupId];
    
    // Toggle logic
    if (sEval.humanAnswers[qid] === value) {
       delete sEval.humanAnswers[qid]; 
       value = null; // Explicit null for deselection
    } else {
       sEval.humanAnswers[qid] = value;
    }

    // REC 1: Surgical DOM update (no thrashing)
    CTO.Render.updateQuestionState(qid, value);

    // Update progress indicators surgically
    this.refreshOverallProgress();

    // Update step pill counter surgically
    const sData = this.state.startups[this.state.activeStartupId];
    const catCode = this.state.categories[this.state.currentStepIndex];
    const hqs = sData.human_questions.filter(q => q.cat_code === catCode);
    const answeredStep = hqs.filter(q => sEval.humanAnswers[q.new_q_id] !== undefined).length;
    CTO.Render.updateProgressText(answeredStep, hqs.length);
    CTO.Render.renderSectionDropdown(
      this.state.categories,
      catCode,
      sData.human_questions,
      sEval.humanAnswers
    );

    // REC 5: Optimistic Sync
    this.saveState();
    const justification = sEval.humanJustifications ? (sEval.humanJustifications[qid] || '') : '';
    this.state.syncQueue.push({ qid, value, justification, timestamp: Date.now() });
    this.setSaveStatus('Saving…');
  },


  answerJustification(qid, text) {
    const sEval = this.state.evaluations[this.state.activeStartupId];
    if (!sEval.humanJustifications) sEval.humanJustifications = {};
    sEval.humanJustifications[qid] = text;
    this.saveState();
    
    const value = sEval.humanAnswers[qid] !== undefined ? sEval.humanAnswers[qid] : null;
    this.state.syncQueue.push({ qid, value, justification: text, timestamp: Date.now() });
    this.setSaveStatus('Saving…');
  },

  toggleFlag(qid) {
    const sEval = this.state.evaluations[this.state.activeStartupId];
    if (!sEval.humanFlags) sEval.humanFlags = {};

    const currentlyFlagged = Boolean(sEval.humanFlags[qid]);
    const newFlagState = !currentlyFlagged;

    if (newFlagState) {
      sEval.humanFlags[qid] = true;
    } else {
      delete sEval.humanFlags[qid];
    }

    // Surgical DOM update for card
    CTO.Render.updateFlagState(qid, newFlagState);

    // Update top nav flagged counter
    this.refreshFlaggedCount();

    // Persist to local state & enqueue to database sync
    this.saveState();
    const value = sEval.humanAnswers[qid] !== undefined ? sEval.humanAnswers[qid] : null;
    const justification = sEval.humanJustifications ? (sEval.humanJustifications[qid] || '') : '';
    this.state.syncQueue.push({ qid, value, justification, is_flagged: newFlagState, timestamp: Date.now() });
    this.setSaveStatus('Saving…');
  },

  refreshFlaggedCount() {
    const sEval = this.state.evaluations[this.state.activeStartupId];
    const flags = sEval?.humanFlags || {};
    const count = Object.values(flags).filter(Boolean).length;
    CTO.Render.updateFlaggedNavBadge(count);
  },

  refreshOverallProgress() {
    const sId = this.state.activeStartupId;
    const sData = this.state.startups[sId];
    const sEval = this.state.evaluations[sId];
    if (!sData) return;

    const totalHumanQs = sData.human_questions.length;
    const answeredCount = Object.values(sEval.humanAnswers).filter(v => v !== null && v !== undefined && !isNaN(v)).length;
    CTO.Render.updateOverallProgress(answeredCount, totalHumanQs);
  },

  async flushSyncQueue() {
    if (this.state.syncQueue.length === 0) return true;
    const batch = [...this.state.syncQueue];
    this.state.syncQueue = [];
    try {
      const res = await fetch('/api/sync-scores', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          startup_id: this.state.activeStartupId,
          scores: batch.map(b => ({
            qid: b.qid,
            val: b.value !== undefined ? b.value : null,
            justification: b.justification || '',
            is_flagged: b.is_flagged !== undefined ? b.is_flagged : null
          }))
        })
      });
      if (!res.ok) throw new Error('SAVE_FAILED');
      this.setSaveStatus('Saved');
      return true;
    } catch (e) {
      console.error('Flush sync failed:', e);
      this.state.syncQueue.unshift(...batch);
      this.setSaveStatus('Save failed — retrying');
      return false;
    }
  },

  submitEvaluation() {
    const sId = this.state.activeStartupId;
    const sData = this.state.startups[sId];
    const sEval = this.state.evaluations[sId];
    
    
    const requiredJustificationIds = new Set(['BC_Q1', 'BC_Q2', 'BC_Q4', 'BC_Q5']);
    const missingQs = sData.human_questions.filter(q => {
      const hasAnswer = sEval.humanAnswers[q.new_q_id] !== undefined && sEval.humanAnswers[q.new_q_id] !== null;
      const justification = sEval.humanJustifications?.[q.new_q_id] || '';
      return !hasAnswer || (requiredJustificationIds.has(q.new_q_id) && !justification.trim());
    });

    
    const modal = document.getElementById('submit-modal');
    const title = document.getElementById('modal-title');
    const desc = document.getElementById('modal-desc');
    const auditContainer = document.getElementById('audit-container');
    const auditList = document.getElementById('audit-list');
    const confirmBtn = document.getElementById('modal-confirm-btn');

    // REC 2: The Audit Screen
    if (missingQs.length > 0) {
      title.textContent = 'Incomplete Evaluation';
      title.style.color = 'var(--accent-red)';
      desc.textContent = `You are missing ${missingQs.length} required response(s). Please complete them before submitting.`;
      
      auditList.innerHTML = missingQs.map(q => 
        `<li><a href="#" data-cat="${q.cat_code}" data-qid="${q.new_q_id}" style="color: var(--accent-blue); text-decoration: none; font-weight: 600;">[${q.cat_code}] ${q.new_q_id}</a> <span style="color: var(--text-muted);">- ${CTO.Render.categoryNames[q.cat_code]}</span></li>`
      ).join('');
      
      auditContainer.style.display = 'block';
      confirmBtn.style.display = 'none';
    } else {
      title.textContent = 'Evaluation Complete';
      title.style.color = 'inherit';
      desc.textContent = 'All categories have been reviewed. Are you ready to submit this scorecard?';
      auditContainer.style.display = 'none';
      confirmBtn.style.display = 'inline-block';
    }

    const flags = sEval?.humanFlags || {};
    const flaggedQids = Object.keys(flags).filter(qid => flags[qid]);
    const flaggedNotice = document.getElementById('flagged-submit-notice');
    const flaggedList = document.getElementById('flagged-submit-list');

    if (flaggedQids.length > 0 && flaggedNotice) {
      flaggedNotice.style.display = 'block';
      if (flaggedList) {
        flaggedList.innerHTML = flaggedQids.map(qid => {
          const q = sData.human_questions.find(item => (item.new_q_id || item.q_id) === qid);
          const cat = q?.cat_code || qid.split('_')[0];
          return `<li><a href="#" data-cat="${cat}" data-qid="${qid}" style="color: #92400e; font-weight: 600; text-decoration: underline;">[${cat}] ${qid}</a> <span style="color: #78350f;">- ${q?.text ? (q.text.slice(0, 70) + '…') : ''}</span></li>`;
        }).join('');
      }
    } else if (flaggedNotice) {
      flaggedNotice.style.display = 'none';
    }
    
    modal.style.display = 'flex';
  },

  jumpToCategory(catCode) {
    const targetIndex = this.state.categories.indexOf(catCode);
    if (targetIndex !== -1 && targetIndex !== this.state.currentStepIndex) {
      this.state.currentStepIndex = targetIndex;
      this.updateUI();
      const scrollArea = document.querySelector('.right-scroll-area');
      if (scrollArea) scrollArea.scrollTop = 0;
    }
  },

  // REC 2: Jump to question
  jumpToQuestion(catCode, qid) {
    document.getElementById('submit-modal').style.display = 'none';
    
    const targetIndex = this.state.categories.indexOf(catCode);
    if (targetIndex !== -1 && targetIndex !== this.state.currentStepIndex) {
      this.state.currentStepIndex = targetIndex;
      this.updateUI();
    }

    // Delay to allow DOM to render if we switched tabs
    setTimeout(() => {
      const card = document.getElementById(`card-${qid}`);
      if (card) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        card.style.transition = 'box-shadow 0.3s';
        card.style.boxShadow = '0 0 0 3px var(--accent-yellow)';
        setTimeout(() => card.style.boxShadow = '0 1px 2px rgba(0,0,0,0.05)', 1500);
      }
    }, 50);
  },

  openFlaggedModal() {
    try {
      const modal = document.getElementById('flagged-modal');
      if (!modal) {
        console.error('[Flagged Modal] #flagged-modal element not found in DOM.');
        return;
      }

      const sId = this.state.activeStartupId;
      const sData = this.state.startups ? this.state.startups[sId] : null;
      const sEval = this.state.evaluations ? this.state.evaluations[sId] : null;
      const flags = sEval?.humanFlags || {};
      const flaggedQids = Object.keys(flags).filter(qid => flags[qid]);

      const modalBody = document.getElementById('flagged-modal-body');
      if (modalBody) {
        if (flaggedQids.length === 0) {
          modalBody.innerHTML = `
            <div style="text-align: center; padding: 36px 16px; color: var(--text-muted);">
              <div style="margin-bottom: 10px; color: var(--text-faint);">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="36" height="36"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"></path><line x1="4" y1="22" x2="4" y2="15"></line></svg>
              </div>
              <strong style="color: var(--text-main); font-size: 15px;">No Flagged Questions</strong>
              <p style="font-size: 13px; margin-top: 6px; max-width: 320px; margin-left: auto; margin-right: auto; line-height: 1.4;">
                Click the <strong>Flag for Review</strong> button on any question card to keep track of items you want to return to later.
              </p>
            </div>
          `;
        } else {
          const qMap = new Map((sData?.human_questions || []).map(q => [q.new_q_id || q.q_id, q]));
          let html = '';

          flaggedQids.forEach(qid => {
            const q = qMap.get(qid) || { cat_code: qid.split('_')[0], new_q_id: qid, text: '' };
            const catName = (window.CTO?.Render?.categoryNames && window.CTO.Render.categoryNames[q.cat_code]) || q.cat_code;
            const answerVal = sEval?.humanAnswers ? sEval.humanAnswers[qid] : undefined;
            const isAnswered = answerVal !== undefined && answerVal !== null;
            
            let scoreBadge = '';
            if (isAnswered) {
              const ptText = window.CTO?.Render?.formatPoints ? window.CTO.Render.formatPoints(answerVal) : `${answerVal} pts`;
              scoreBadge = `<span style="background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; padding: 2px 8px; border-radius: 10px; font-family: var(--mono); font-size: 11px; font-weight: 700;">Score: ${ptText}</span>`;
            } else {
              scoreBadge = `<span style="background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; padding: 2px 8px; border-radius: 10px; font-family: var(--mono); font-size: 11px; font-weight: 700;">Unscored</span>`;
            }

            const safeSnippet = window.CTO?.Render?.escapeHtml ? window.CTO.Render.escapeHtml(q.text || '') : (q.text || '');

            html += `
              <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; padding: 12px 14px; background: var(--surface-sunk); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 10px;">
                <div style="flex: 1; min-width: 0;">
                  <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap;">
                    <span class="h-tag">${q.cat_code}</span>
                    <strong style="font-family: var(--mono); font-size: 12px;">${q.new_q_id}</strong>
                    <span style="font-size: 12px; color: var(--text-muted);">&bull; ${catName}</span>
                    ${scoreBadge}
                  </div>
                  <div style="font-size: 13px; color: var(--text-main); line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                    ${safeSnippet}
                  </div>
                </div>
                <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 6px; flex-shrink: 0;">
                  <button class="nav-btn btn-next ready" style="padding: 5px 12px; font-size: 12px;" onclick="window.CTO.App.jumpFromFlagModal('${q.cat_code}', '${q.new_q_id}')">Jump →</button>
                  <button class="nav-btn" style="padding: 3px 8px; font-size: 11px; color: var(--accent-red); background: transparent;" onclick="window.CTO.App.unflagFromModal('${q.new_q_id}')">Unflag</button>
                </div>
              </div>
            `;
          });

          modalBody.innerHTML = html;
        }
      }

      modal.style.display = 'flex';
    } catch (err) {
      console.error('[Flagged Modal] Error opening modal:', err);
      const modal = document.getElementById('flagged-modal');
      if (modal) modal.style.display = 'flex';
    }
  },

  closeFlaggedModal() {
    const modal = document.getElementById('flagged-modal');
    if (modal) modal.style.display = 'none';
  },

  jumpFromFlagModal(catCode, qid) {
    this.closeFlaggedModal();
    this.jumpToQuestion(catCode, qid);
  },

  unflagFromModal(qid) {
    this.toggleFlag(qid);
    this.openFlaggedModal();
  },

  // REC 5: Background Sync Worker (Updated for JWT / 401 Handling)
  startSyncWorker() {
    setInterval(async () => {
      // Suspend queue if empty or currently attempting to refresh an expired token
      if (this.state.syncQueue.length === 0 || this.state.isRefreshingToken) return;

      const batch = [...this.state.syncQueue];
      this.state.syncQueue = []; // Optimistically clear
      
      try {
        if (!this.currentUser || !this.currentUser.id) {
           console.log("No credentials available, skipping sync.");
           this.state.syncQueue.unshift(...batch);
           return;
        }

        console.log(`[Sync Worker] Dispatching ${batch.length} updates...`);
        
        const res = await fetch('/api/sync-scores', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            startup_id: this.state.activeStartupId,
            scores: batch.map(b => ({
              qid: b.qid,
              val: b.value !== undefined ? b.value : null,
              justification: b.justification || '',
              is_flagged: b.is_flagged !== undefined ? b.is_flagged : null
            }))
          })
        });

        if (res.status === 401) {
          throw new Error("401_UNAUTHORIZED");
        }
        if (!res.ok) throw new Error("NETWORK_ERROR");
        this.setSaveStatus('Saved');

      } catch (error) {
        this.state.syncQueue.unshift(...batch);
        
        if (error.message === "401_UNAUTHORIZED") {
           console.warn("Credentials rejected by server.");
           alert('Your scorer access has been revoked or expired. Please log in again.');
           document.getElementById('login-modal').style.display = 'flex';
        }
      }
    }, 3000);
  },

  loadState() {
    const sId = this.state.activeStartupId;
    if (!this.state.evaluations[sId]) {
      this.state.evaluations[sId] = { humanAnswers: {}, humanJustifications: {}, humanFlags: {} };
    }
    if (!this.state.evaluations[sId].humanFlags) {
      this.state.evaluations[sId].humanFlags = {};
    }

    // 1. Seed from database reviews if returned by API
    const sData = this.state.startups[sId];
    if (sData && Array.isArray(sData.judge_reviews)) {
      sData.judge_reviews.forEach(r => {
        if (r.score_value !== null && r.score_value !== undefined) {
          this.state.evaluations[sId].humanAnswers[r.question_id] = parseFloat(r.score_value);
        }
        if (r.justification) {
          this.state.evaluations[sId].humanJustifications[r.question_id] = r.justification;
        }
        if (r.is_flagged) {
          this.state.evaluations[sId].humanFlags[r.question_id] = true;
        }
      });
    }

    // 2. Overlay any local storage changes
    try {
      const stored = localStorage.getItem('cto2025_state');
      if (stored) {
        const data = JSON.parse(stored);
        const draftKey = `${this.currentUser?.id || 'unknown'}:${sId}`;
        if (data[draftKey]) {
          if (data[draftKey].humanAnswers) {
            Object.assign(this.state.evaluations[sId].humanAnswers, data[draftKey].humanAnswers);
          }
          if (data[draftKey].humanJustifications) {
            Object.assign(this.state.evaluations[sId].humanJustifications, data[draftKey].humanJustifications);
          }
          if (data[draftKey].humanFlags) {
            Object.assign(this.state.evaluations[sId].humanFlags, data[draftKey].humanFlags);
          }
        }
      }
    } catch (e) {}
  },

  saveState() {
    try {
      const stored = localStorage.getItem('cto2025_state');
      let data = stored ? JSON.parse(stored) : {};
      const draftKey = `${this.currentUser?.id || 'unknown'}:${this.state.activeStartupId}`;
      data[draftKey] = this.state.evaluations[this.state.activeStartupId];
      localStorage.setItem('cto2025_state', JSON.stringify(data));
    } catch (e) {}
  },

  setSaveStatus(message) {
    const status = document.getElementById('save-status');
    if (status) status.textContent = message;
  },

  async logout() {
    await fetch('/api/auth-logout', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ role: 'scorer' }) });
    this.currentUser = null;
    this.applyUserRoleUI();
    document.getElementById('login-modal').style.display = 'flex';
    this.setSaveStatus('Signed out');
  },

  openFaqModal() {
    const modal = document.getElementById('faq-modal');
    if (modal) modal.style.display = 'flex';
  },

  closeFaqModal() {
    const modal = document.getElementById('faq-modal');
    if (modal) modal.style.display = 'none';
  },

  openPasswordModal() {
    document.getElementById('password-modal').style.display = 'flex';
  },

  closePasswordModal() {
    document.getElementById('password-modal').style.display = 'none';
    document.getElementById('password-message').textContent = '';
  },

  openFeedbackModal() {
    const modal = document.getElementById('feedback-modal');
    if (!modal) return;

    const sId = this.state.activeStartupId;
    const sData = this.state.startups ? this.state.startups[sId] : null;
    const currentCat = this.state.categories[this.state.currentStepIndex] || '';
    const catName = (window.CTO?.Render?.categoryNames && window.CTO.Render.categoryNames[currentCat]) || currentCat;
    const startupName = sData?.meta?.name || sId || 'General';

    const contextHint = document.getElementById('feedback-context-hint');
    if (contextHint) {
      contextHint.textContent = `Context: ${startupName} • Section: ${catName}`;
    }

    const input = document.getElementById('feedback-input');
    if (input) {
      input.value = '';
      setTimeout(() => input.focus(), 50);
    }

    const charCount = document.getElementById('feedback-char-count');
    if (charCount) {
      charCount.textContent = '0 / 5,000 chars';
    }

    const statusMsg = document.getElementById('feedback-status-msg');
    if (statusMsg) {
      statusMsg.style.display = 'none';
      statusMsg.textContent = '';
    }

    const submitBtn = document.getElementById('btn-submit-feedback');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Submit Feedback';
    }

    modal.style.display = 'flex';
  },

  closeFeedbackModal() {
    const modal = document.getElementById('feedback-modal');
    if (modal) modal.style.display = 'none';
  },

  async submitFeedback() {
    const input = document.getElementById('feedback-input');
    const statusMsg = document.getElementById('feedback-status-msg');
    const submitBtn = document.getElementById('btn-submit-feedback');
    if (!input || !statusMsg) return;

    const text = input.value.trim();
    if (!text) {
      statusMsg.style.display = 'block';
      statusMsg.style.background = '#fef2f2';
      statusMsg.style.color = '#991b1b';
      statusMsg.style.border = '1px solid #fecaca';
      statusMsg.textContent = 'Please enter your feedback before submitting.';
      input.focus();
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Submitting...';
    }

    statusMsg.style.display = 'none';

    try {
      const res = await fetch('/api/submit-feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          feedback_text: text,
          startup_id: this.state.activeStartupId || null,
          category_code: this.state.categories[this.state.currentStepIndex] || null
        })
      });

      const data = await res.json();

      if (res.ok && data.success) {
        statusMsg.style.display = 'block';
        statusMsg.style.background = '#ecfdf5';
        statusMsg.style.color = '#065f46';
        statusMsg.style.border = '1px solid #a7f3d0';
        statusMsg.textContent = '✓ Thank you! Your feedback has been submitted to the admin team.';
        input.value = '';

        setTimeout(() => {
          this.closeFeedbackModal();
        }, 1500);
      } else {
        throw new Error(data.error || 'Failed to submit feedback.');
      }
    } catch (err) {
      console.error('Error submitting feedback:', err);
      statusMsg.style.display = 'block';
      statusMsg.style.background = '#fef2f2';
      statusMsg.style.color = '#991b1b';
      statusMsg.style.border = '1px solid #fecaca';
      statusMsg.textContent = `Error: ${err.message || 'Unable to submit feedback.'}`;
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Try Again';
      }
    }
  },

  async changePassword() {
    const current_password = document.getElementById('current-password').value;
    const new_password = document.getElementById('new-password').value;
    const confirm_password = document.getElementById('confirm-password').value;
    const message = document.getElementById('password-message');
    const res = await fetch('/api/change-password', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role: 'scorer', current_password, new_password, confirm_password })
    });
    const body = await res.json();
    message.textContent = body.message || body.error;
    message.style.color = res.ok ? 'var(--accent-green)' : 'var(--accent-red)';
  },

  toggleDropdown(menuId) {
    const menu = document.getElementById(menuId);
    if (!menu) return;
    const isVisible = menu.style.display === 'block';
    this.closeAllDropdowns();
    if (!isVisible) {
      menu.style.display = 'block';
      menu.parentElement?.classList.add('open');
    }
  },

  closeAllDropdowns() {
    document.querySelectorAll('.nav-dropdown-menu').forEach(menu => {
      menu.style.display = 'none';
      menu.parentElement?.classList.remove('open');
    });
  }
};

document.addEventListener('DOMContentLoaded', () => CTO.App.init());
