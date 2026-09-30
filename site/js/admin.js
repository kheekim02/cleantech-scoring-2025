window.AdminApp = {
  auth: null,
  assignmentFilter: 'all',
  feedbackFilter: 'all',
  companySearch: '',
  coverageFilter: 'all',
  coverageSearch: '',
  selectedJudgeId: sessionStorage.getItem('cto_admin_selected_judge') || '',
  data: {
    judges: [],
    startups: [],
    assignments: [], // array of { judge_id, startup_id, assigned_at }
    feedback: []
  },

  formatTimeAgo(isoString) {
    if (!isoString) return 'No activity';
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return 'Unknown';
    const diffSec = Math.floor((Date.now() - date.getTime()) / 1000);
    if (diffSec < 60) return 'Just now';
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDays = Math.floor(diffHr / 24);
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  },

  formatFullDateTime(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return '';
    return date.toLocaleString(undefined, { 
      month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' 
    });
  },

  setAssignmentFilter(filter) {
    this.assignmentFilter = filter;
    document.querySelectorAll('.assignment-filter').forEach(button => button.classList.toggle('active', button.dataset.filter === filter));
    this.renderAssignments();
  },

  setSearch(value) {
    this.companySearch = value.trim().toLowerCase();
    this.renderAssignments();
  },

  init() {
    fetch('/api/auth-session?role=admin').then(async res => {
      if (!res.ok) throw new Error('No active session');
      return res.json();
    }).then(data => {
      this.auth = data.user;
      document.getElementById('admin-login-modal').style.display = 'none';
      this.loadData();
    }).catch(() => {
      document.getElementById('admin-login-modal').style.display = 'flex';
      document.getElementById('admin-dashboard').style.display = 'none';
    });
  },

  async login() {
    const user = document.getElementById('auth-admin-user').value.trim();
    const pass = document.getElementById('auth-admin-pass').value.trim();
    if (!user || !pass) return;

    try {
      const res = await fetch('/api/auth-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: 'admin', username: user, password: pass })
      });
      if (res.ok) {
        this.auth = (await res.json()).user;
        document.getElementById('admin-login-modal').style.display = 'none';
        this.loadData();
      } else {
        alert("Invalid admin credentials");
      }
    } catch (e) {
      alert("Error: " + e.message);
    }
  },

  logout() {
    fetch('/api/auth-logout', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ role: 'admin' }) });
    this.auth = null;
    document.getElementById('admin-login-modal').style.display = 'flex';
    document.getElementById('admin-dashboard').style.display = 'none';
  },

  async loadData() {
    if (!this.auth) return;
    try {
      const res = await fetch('/api/admin-data');
      if (res.status === 401) {
        this.logout();
        return;
      }
      this.data = await res.json();
      document.getElementById('admin-dashboard').style.display = 'block';
      this.renderScorers();
      this.renderFeedback();
      this.renderCoverageBoard();
    } catch (e) {
      console.error(e);
      alert("Failed to load admin data");
    }
  },

  renderScorers() {
    const select = document.getElementById('judge-select');
    const scorersList = document.getElementById('scorers-list');
    
    select.innerHTML = '<option value="">-- Choose a Scorer --</option>';
    let listHtml = '';
    
    this.data.judges.forEach(j => {
      // Dropdown option
      const opt = document.createElement('option');
      opt.value = j.judge_id;
      opt.textContent = j.is_test ? `${j.judge_id} (Test Mode)` : j.judge_id;
      select.appendChild(opt);
      
      // Calculate scorer activity and progress
      const judgeProgress = (this.data.progress || []).filter(p => p.judge_id === j.judge_id);
      const judgeAssignments = (this.data.assignments || []).filter(a => a.judge_id === j.judge_id);

      let latestSave = null;
      let totalAnswered = 0;
      let fullyScoredCount = 0;

      judgeProgress.forEach(p => {
        if (p.last_saved) {
          const t = new Date(p.last_saved).getTime();
          if (!latestSave || t > latestSave) latestSave = t;
        }
        const ans = parseInt(p.answered_count || 0, 10);
        totalAnswered += ans;
        if (ans >= 282) fullyScoredCount++;
      });

      const lastActiveText = latestSave 
        ? `Last active: ${this.formatTimeAgo(new Date(latestSave).toISOString())}`
        : 'No activity yet';

      const statusLabel = j.is_test ? 'Test Account · Views all companies, no DB writes' : 'Password protected';
      const workloadText = j.is_test 
        ? 'Preview mode'
        : `${judgeAssignments.length} assigned · ${fullyScoredCount} complete`;

      // List item
      const safeId = j.judge_id.replace(/'/g, "\\'");
      const escapedId = this.escapeHtml(j.judge_id);
      const testBadge = j.is_test ? `<span style="background: #fef3c7; color: #92400e; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; border: 1px solid #fcd34d;">Test Mode</span>` : '';
      listHtml += `
        <div class="scorer-item" style="padding: 10px 12px; border-bottom: 1px solid var(--border);">
          <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
            <div style="display: flex; align-items: center; gap: 6px; min-width: 0;">
              <strong style="color: var(--accent-blue); font-size: 13px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapedId}">${escapedId}</strong>
              ${testBadge}
            </div>
            <div style="display: flex; gap: 6px; align-items: center; flex-shrink: 0;">
              <button class="btn btn-reset-pass" onclick="AdminApp.resetPassword('${safeId}')" style="background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; cursor: pointer; transition: background 0.15s ease;" onmouseover="this.style.background='#bae6fd'" onmouseout="this.style.background='#e0f2fe'">Reset</button>
              <button class="btn btn-delete-scorer" onclick="AdminApp.deleteScorer('${safeId}')" style="background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; cursor: pointer; transition: background 0.15s ease;" onmouseover="this.style.background='#fecaca'" onmouseout="this.style.background='#fee2e2'">Delete</button>
            </div>
          </div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 5px; display: flex; justify-content: space-between; align-items: center; gap: 8px;">
            <div style="display: flex; align-items: center; gap: 4px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: ${j.is_test ? '#d97706' : (latestSave ? '#10b981' : '#94a3b8')}; flex-shrink: 0;"></span>
              <span title="${statusLabel} · ${workloadText}">${statusLabel} · ${workloadText}</span>
            </div>
            <span style="font-weight: 600; color: ${latestSave ? 'var(--text-main)' : 'var(--text-muted)'}; flex-shrink: 0;" title="${latestSave ? this.formatFullDateTime(new Date(latestSave).toISOString()) : ''}">${lastActiveText}</span>
          </div>
        </div>
      `;
    });
    if (this.data.judges.some(j => j.judge_id === this.selectedJudgeId)) select.value = this.selectedJudgeId;
    select.onchange = () => {
      this.selectedJudgeId = select.value;
      sessionStorage.setItem('cto_admin_selected_judge', this.selectedJudgeId);
      this.renderAssignments();
    };
    
    scorersList.innerHTML = listHtml;
    this.renderAssignments();
  },

  renderAssignments() {
    const container = document.getElementById('company-list-container');
    const chartContainer = document.getElementById('assignment-chart');
    const selectedJudge = document.getElementById('judge-select').value;
    
    // 1. Calculate scoring progress for the Bar Chart
    const progressByStartup = {};
    if (this.data.progress) {
        this.data.progress.forEach(p => {
            const count = parseInt(p.answered_count || 0, 10);
            if (!progressByStartup[p.startup_id] || count > progressByStartup[p.startup_id]) {
                progressByStartup[p.startup_id] = count;
            }
        });
    }
    // 1b. Calculate global assignment counts for the list badges
    const globalCounts = {};
    this.data.assignments.forEach(a => {
        globalCounts[a.startup_id] = (globalCounts[a.startup_id] || 0) + 1;
    });

    let countNotStarted = 0, countInProgress = 0, countFullyScored = 0;
    this.data.startups.forEach(s => {
        const maxScoreCount = progressByStartup[s.id] || 0;
        if (maxScoreCount === 0) countNotStarted++;
        else if (maxScoreCount < 282) countInProgress++;
        else countFullyScored++;
    });
    
    // Render Bar Chart with fixed pixel heights and aligned baseline
    const maxVal = Math.max(countNotStarted, countInProgress, countFullyScored, 1);
    const trackHeight = 90;
    const bar0 = countNotStarted > 0 ? Math.max(8, Math.round((countNotStarted / maxVal) * trackHeight)) : 3;
    const bar1 = countInProgress > 0 ? Math.max(8, Math.round((countInProgress / maxVal) * trackHeight)) : 3;
    const bar2 = countFullyScored > 0 ? Math.max(8, Math.round((countFullyScored / maxVal) * trackHeight)) : 3;
    
    if (chartContainer) {
        chartContainer.innerHTML = `
          <div style="display: flex; justify-content: space-around; gap: 8px; margin-top: 12px; padding: 0 4px;">
            
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 0;">
               <span style="font-size: 13px; font-weight: 700; color: var(--text-main); margin-bottom: 6px;">${countNotStarted}</span>
               <div style="height: ${trackHeight}px; width: 100%; display: flex; align-items: flex-end; justify-content: center;">
                 <div style="width: 38px; height: ${bar0}px; background: #e2e8f0; border-radius: 4px 4px 0 0; border: 1px solid #cbd5e1; border-bottom: none; box-sizing: border-box;"></div>
               </div>
               <div style="width: 100%; height: 1px; background: var(--border);"></div>
               <div style="min-height: 32px; display: flex; align-items: flex-start; justify-content: center; text-align: center; margin-top: 6px;">
                 <span style="font-size: 11px; font-weight: 600; color: var(--text-muted); line-height: 1.2;">Not Started</span>
               </div>
            </div>
            
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 0;">
               <span style="font-size: 13px; font-weight: 700; color: var(--text-main); margin-bottom: 6px;">${countInProgress}</span>
               <div style="height: ${trackHeight}px; width: 100%; display: flex; align-items: flex-end; justify-content: center;">
                 <div style="width: 38px; height: ${bar1}px; background: #fef08a; border-radius: 4px 4px 0 0; border: 1px solid #eab308; border-bottom: none; box-sizing: border-box;"></div>
               </div>
               <div style="width: 100%; height: 1px; background: var(--border);"></div>
               <div style="min-height: 32px; display: flex; align-items: flex-start; justify-content: center; text-align: center; margin-top: 6px;">
                 <span style="font-size: 11px; font-weight: 600; color: var(--text-muted); line-height: 1.2;">In Progress</span>
               </div>
            </div>
            
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 0;">
               <span style="font-size: 13px; font-weight: 700; color: var(--text-main); margin-bottom: 6px;">${countFullyScored}</span>
               <div style="height: ${trackHeight}px; width: 100%; display: flex; align-items: flex-end; justify-content: center;">
                 <div style="width: 38px; height: ${bar2}px; background: #4ade80; border-radius: 4px 4px 0 0; border: 1px solid #16a34a; border-bottom: none; box-sizing: border-box;"></div>
               </div>
               <div style="width: 100%; height: 1px; background: var(--border);"></div>
               <div style="min-height: 32px; display: flex; align-items: flex-start; justify-content: center; text-align: center; margin-top: 6px;">
                 <span style="font-size: 11px; font-weight: 600; color: var(--text-muted); line-height: 1.2;">Fully Scored</span>
               </div>
            </div>
            
          </div>
        `;
    }

    if (!selectedJudge) {
      container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 14px;">Please select a scorer first.</div>';
      return;
    }

    // 2. Filter assignments for this judge
    const assignedSet = new Set(
      this.data.assignments
        .filter(a => a.judge_id === selectedJudge)
        .map(a => a.startup_id)
    );
    const assignmentByStartup = new Map(
      this.data.assignments
        .filter(a => a.judge_id === selectedJudge)
        .map(a => [a.startup_id, a])
    );
    
    // Map progress for this judge
    const progressMap = {};
    const savedMap = {};
    const flaggedMap = {};
    if (this.data.progress) {
      this.data.progress
        .filter(p => p.judge_id === selectedJudge)
        .forEach(p => {
          progressMap[p.startup_id] = parseInt(p.answered_count, 10);
          savedMap[p.startup_id] = p.last_saved;
          flaggedMap[p.startup_id] = parseInt(p.flagged_count || 0, 10);
        });
    }

    const startupsToRender = this.data.startups.filter(s => {
      const assigned = assignedSet.has(s.id);
      const matchesFilter = this.assignmentFilter === 'all' || (this.assignmentFilter === 'assigned' && assigned) || (this.assignmentFilter === 'unassigned' && !assigned);
      return matchesFilter && (!this.companySearch || s.name.toLowerCase().includes(this.companySearch));
    });
    const summary = document.getElementById('assignment-summary');
    const isTestJudge = this.data.judges.find(j => j.judge_id === selectedJudge)?.is_test;
    if (summary) {
      if (isTestJudge) {
        summary.innerHTML = `<span style="color: #92400e; font-weight: 600;">Test / Preview Account: Automatically has access to all ${this.data.startups.length} companies. Assignments are not needed and scores will not be logged.</span>`;
      } else {
        summary.textContent = `${assignedSet.size} of ${this.data.startups.length} companies assigned to ${selectedJudge} · showing ${startupsToRender.length}`;
      }
    }

    let html = '';
    if (startupsToRender.length === 0) {
      html = '<div style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 14px;">No startups found for current filter.</div>';
    }

    startupsToRender.forEach(s => {
      const isChecked = assignedSet.has(s.id) ? 'checked' : '';
      const count = globalCounts[s.id] || 0;
      
      // Global Assignment Badge
      let badge = '';
      if (count === 0) badge = `<span style="background: #fef08a; color: #854d0e; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 700; margin-left: auto;">0 Assigned</span>`;
      else if (count === 1) badge = `<span style="background: #fed7aa; color: #9a3412; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 700; margin-left: auto;">1 Assigned</span>`;
      else badge = `<span style="background: #bbf7d0; color: #166534; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 700; margin-left: auto;">${count} Assigned</span>`;

      // Submission Tracker Badge (only if assigned to this judge)
      let subBadge = '';
      if (isChecked) {
        const pCount = progressMap[s.id] || 0;
        const pSaved = savedMap[s.id];
        const pFlagged = flaggedMap[s.id] || 0;

        if (pCount === 0) {
            subBadge = `<span style="color: #ef4444; font-size: 11px; font-weight: 600; margin-left: 10px; border: 1px solid #fca5a5; padding: 2px 6px; border-radius: 4px; background: #fef2f2;">Not Started (0/282)</span>`;
        } else if (pCount < 282) {
            const pct = Math.round((pCount / 282) * 100);
            subBadge = `<span style="color: #0369a1; font-size: 11px; font-weight: 600; margin-left: 10px; border: 1px solid #7dd3fc; padding: 2px 6px; border-radius: 4px; background: #f0f9ff;">${pCount} / 282 Answers (${pct}%)</span>`;
        } else {
            subBadge = `<span style="color: #166534; font-size: 11px; font-weight: 600; margin-left: 10px; border: 1px solid #86efac; padding: 2px 6px; border-radius: 4px; background: #f0fdf4;">Completed (282/282)</span>`;
        }

        if (pSaved) {
          subBadge += `<span style="color: var(--text-muted); font-size: 11px; margin-left: 6px; border: 1px solid var(--border); padding: 2px 6px; border-radius: 4px; background: #f8fafc;" title="Exact save time: ${this.formatFullDateTime(pSaved)}">Saved ${this.formatTimeAgo(pSaved)}</span>`;
        }
        if (pFlagged > 0) {
          subBadge += `<span style="color: #b45309; font-size: 11px; font-weight: 600; margin-left: 6px; border: 1px solid #fcd34d; padding: 2px 6px; border-radius: 4px; background: #fffbeb;">${pFlagged} Flagged</span>`;
        }
      }

      const assignmentTiming = isChecked
        ? this.formatAssignmentTiming(assignmentByStartup.get(s.id)?.assigned_at)
        : '';

      html += `
        <div class="company-item" style="background: ${isChecked ? '#fafafa' : '#fff'};">
          <input type="checkbox" id="chk-${s.id}" ${isChecked} onchange="AdminApp.toggleAssignment('${selectedJudge}', '${s.id}', this.checked)" style="margin: 0; width: 16px; height: 16px; cursor: pointer;">
          <label for="chk-${s.id}" class="company-details" style="cursor: pointer;">
            <span class="company-name" title="${s.name}">${s.name}</span>
            <span class="assignment-meta">${subBadge}${assignmentTiming}</span>
          </label>
          <span class="assignment-badge">${badge}</span>
        </div>
      `;
    });
    
    container.innerHTML = html;
  },

  formatAssignmentTiming(assignedAt) {
    if (!assignedAt) {
      return `<span style="color: var(--text-muted); font-size: 11px; margin-left: 10px;">Assigned before date tracking</span>`;
    }

    const assignmentDate = new Date(assignedAt);
    if (Number.isNaN(assignmentDate.getTime())) {
      return `<span style="color: var(--text-muted); font-size: 11px; margin-left: 10px;">Assignment date unavailable</span>`;
    }

    const elapsedMs = Math.max(0, Date.now() - assignmentDate.getTime());
    const elapsedDays = Math.floor(elapsedMs / (1000 * 60 * 60 * 24));
    const elapsedText = elapsedDays === 0 ? 'today' : `${elapsedDays} ${elapsedDays === 1 ? 'day' : 'days'} ago`;
    const dateText = new Intl.DateTimeFormat(undefined, {
      month: 'short', day: 'numeric', year: 'numeric'
    }).format(assignmentDate);

    return `<span style="color: #0369a1; font-size: 11px; font-weight: 600; margin-left: 10px; border: 1px solid #7dd3fc; padding: 2px 6px; border-radius: 4px; background: #f0f9ff;">Assigned ${dateText} · ${elapsedText}</span>`;
  },

  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  },

  togglePassVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';
    if (btn) {
      btn.innerHTML = isPassword
        ? '<span class="pass-toggle-label">Hide</span>'
        : '<span class="pass-toggle-label">Show</span>';
      btn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
    }
  },

  async createScorer() {
    const idInput = document.getElementById('new-judge-id');
    const passInput = document.getElementById('new-judge-pass');
    const testInput = document.getElementById('new-judge-test');
    const msg = document.getElementById('create-msg');
    
    const new_judge_id = idInput.value.trim();
    const new_password = passInput.value.trim();
    const is_test = testInput ? testInput.checked : false;
    
    if (!new_judge_id || !new_password) {
      msg.textContent = "Please fill out both fields.";
      msg.style.color = 'var(--accent-red)';
      return;
    }
    
    try {
      const res = await fetch('/api/admin-actions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'CREATE_JUDGE',
          data: { new_judge_id, new_password, is_test }
        })
      });
      
      if (res.ok) {
        msg.innerHTML = `
          <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px 12px; margin-top: 12px; position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
              <div style="font-size: 13px; color: #166534; font-weight: 700;">
                ✓ ${is_test ? 'Test / Preview Scorer' : 'Scorer'} <strong>${this.escapeHtml(new_judge_id)}</strong> created!
              </div>
              <button type="button" onclick="document.getElementById('create-msg').innerHTML=''" style="background: none; border: none; font-size: 14px; color: #15803d; cursor: pointer; padding: 0 4px; line-height: 1;" title="Dismiss notification">✕</button>
            </div>
            <div style="margin-top: 6px; font-size: 12px; color: var(--text-muted);">
              Temporary password: <code style="background: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-weight: 700; user-select: all;">${this.escapeHtml(new_password)}</code>
            </div>
            ${is_test ? '<div style="margin-top: 4px; font-size: 11px; color: #92400e; font-weight: 600;">Configured as Test Account: Views all companies, scores will NOT be logged to DB.</div>' : ''}
            <div style="margin-top: 4px; font-size: 10px; color: #15803d;">
              Notice will remain visible for 1 minute for easy copying.
            </div>
          </div>
        `;
        msg.style.color = 'inherit';
        idInput.value = '';
        passInput.value = '';
        passInput.type = 'password';
        if (testInput) testInput.checked = false;
        const toggleBtn = document.getElementById('toggle-new-pass-btn');
        if (toggleBtn) {
          toggleBtn.innerHTML = '<span class="pass-toggle-label">Show</span>';
          toggleBtn.setAttribute('aria-label', 'Toggle password visibility');
        }
        this.loadData(); // refresh list
      } else {
        const err = await res.json();
        msg.textContent = "Error: " + err.error;
        msg.style.color = 'var(--accent-red)';
      }
    } catch(e) {
      msg.textContent = "Network error";
      msg.style.color = 'var(--accent-red)';
    }
    
    if (this.createMsgTimer) clearTimeout(this.createMsgTimer);
    this.createMsgTimer = setTimeout(() => { msg.innerHTML = ''; }, 60000);
  },

  async toggleAssignment(judge_id, startup_id, assigned) {
    try {
      const res = await fetch('/api/admin-actions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'TOGGLE_ASSIGNMENT',
          data: { judge_id, startup_id, assigned }
        })
      });
      
      if (res.ok) {
        const result = await res.json();
        // Update local state to avoid full reload
        if (assigned) {
          const assignment = result.assignment || { judge_id, startup_id, assigned_at: new Date().toISOString() };
          const existingIndex = this.data.assignments.findIndex(a => a.judge_id === judge_id && a.startup_id === startup_id);
          if (existingIndex === -1) this.data.assignments.push(assignment);
          else this.data.assignments[existingIndex] = assignment;
        } else {
          this.data.assignments = this.data.assignments.filter(a => !(a.judge_id === judge_id && a.startup_id === startup_id));
        }
        this.renderAssignments();
        this.renderCoverageBoard();
      } else {
        alert("Failed to update assignment. Refresh the page.");
        this.loadData();
      }
    } catch (e) {
      alert("Network error updating assignment");
      this.loadData();
    }
  },

  async deleteScorer(judge_id) {
    if (!confirm(`Are you sure you want to permanently delete scorer "${judge_id}"?\n\nThis will remove the account and all their assigned companies.`)) {
      return;
    }
    const msg = document.getElementById('create-msg');
    try {
      const res = await fetch('/api/admin-actions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'DELETE_JUDGE',
          data: { judge_id }
        })
      });
      if (res.ok) {
        if (msg) {
          msg.textContent = `Scorer "${judge_id}" deleted successfully.`;
          msg.style.color = 'var(--accent-green)';
        }
        if (this.selectedJudgeId === judge_id) {
          this.selectedJudgeId = '';
          sessionStorage.removeItem('cto_admin_selected_judge');
        }
        this.loadData();
      } else {
        const err = await res.json();
        alert("Error: " + (err.error || "Failed to delete scorer"));
      }
    } catch (e) {
      alert("Network error deleting scorer: " + e.message);
    }
    if (msg) setTimeout(() => { msg.textContent = ''; }, 3500);
  },

  async resetPassword(judge_id) {
    const new_password = prompt(`Enter new password for scorer "${judge_id}":`);
    if (new_password === null) return; // user cancelled
    if (!new_password.trim()) {
      alert("Password cannot be empty.");
      return;
    }
    const msg = document.getElementById('create-msg');
    try {
      const res = await fetch('/api/admin-actions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'RESET_JUDGE_PASSWORD',
          data: { judge_id, new_password: new_password.trim() }
        })
      });
      if (res.ok) {
        if (msg) {
          msg.textContent = `Password reset successfully for "${judge_id}".`;
          msg.style.color = 'var(--accent-green)';
        }
        alert(`Password for scorer "${judge_id}" has been reset successfully.`);
      } else {
        const err = await res.json();
        alert("Error resetting password: " + (err.error || "Failed to reset password"));
      }
    } catch (e) {
      alert("Network error resetting password: " + e.message);
    }
    if (msg) setTimeout(() => { msg.textContent = ''; }, 3500);
  },

  async exportScores() {
    const btn = document.querySelector('button[onclick="AdminApp.exportScores()"]');
    if (!btn) {
      window.location.href = '/api/export-scores';
      return;
    }
    
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Compiling Export...';
    btn.disabled = true;

    try {
      let offset = 0;
      const limit = 2500;
      let keepFetching = true;
      let fullCsv = "";

      while (keepFetching) {
        btn.innerHTML = `Compiling Export... (${offset} rows)`;
        const res = await fetch(`/api/export-scores?offset=${offset}&limit=${limit}&chunk=true`);
        if (!res.ok) throw new Error("Export failed");
        
        const data = await res.json();
        const { header, rows, hasMore } = data;
        
        if (offset === 0) {
          fullCsv += header + '\r\n';
        }
        
        if (rows && rows.length > 0) {
          fullCsv += rows.join('\r\n') + '\r\n';
        }

        if (!hasMore) {
          keepFetching = false;
        } else {
          offset += limit;
        }
      }

      const blob = new Blob([fullCsv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cleantech_open_scores_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      alert("Export failed: " + err.message);
      // Fallback for older browsers or fetch errors
      window.location.href = '/api/export-scores';
    } finally {
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  },

  setFeedbackFilter(filter) {
    this.feedbackFilter = filter;
    document.querySelectorAll('[data-fb-filter]').forEach(button => {
      button.classList.toggle('active', button.dataset.fbFilter === filter);
    });
    this.renderFeedback();
  },

  renderFeedback() {
    const container = document.getElementById('feedback-feed-container');
    const badge = document.getElementById('feedback-count-badge');
    if (!container) return;

    const allFeedback = this.data.feedback || [];
    const newCount = allFeedback.filter(f => f.status === 'new').length;
    if (badge) {
      badge.textContent = `${newCount} New / ${allFeedback.length} Total`;
    }

    let items = allFeedback;
    if (this.feedbackFilter && this.feedbackFilter !== 'all') {
      items = items.filter(f => f.status === this.feedbackFilter);
    }

    if (items.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px 16px; color: var(--text-muted);">
          <strong style="color: var(--text-main); font-size: 15px;">No Feedback Found</strong>
          <p style="font-size: 13px; margin-top: 6px; margin-bottom: 0;">
            ${this.feedbackFilter === 'all' ? 'No scorer feedback notes have been submitted yet.' : `No feedback with status "${this.feedbackFilter}".`}
          </p>
        </div>
      `;
      return;
    }

    let html = '';
    items.forEach(item => {
      const escapedText = this.escapeHtml(item.feedback_text);
      const escapedScorer = this.escapeHtml(item.scorer_id);
      const companyTag = item.startup_name 
        ? `<span style="background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 11px;">${this.escapeHtml(item.startup_name)}</span>` 
        : (item.startup_id ? `<span style="background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 11px;">${this.escapeHtml(item.startup_id)}</span>` : '');
      const catTag = item.category_code
        ? `<span style="background: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 4px; font-family: var(--mono); font-size: 11px; font-weight: 600;">${this.escapeHtml(item.category_code)}</span>`
        : '';
      
      let statusBadge = '';
      if (item.status === 'new') {
        statusBadge = `<span style="background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 700;">NEW</span>`;
      } else if (item.status === 'reviewed') {
        statusBadge = `<span style="background: #fef3c7; color: #92400e; border: 1px solid #fde68a; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 700;">REVIEWED</span>`;
      } else if (item.status === 'resolved') {
        statusBadge = `<span style="background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 700;">RESOLVED</span>`;
      }

      const dateStr = item.created_at ? new Date(item.created_at).toLocaleString() : '';

      html += `
        <div style="background: var(--surface-subdued); border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; margin-bottom: 12px; transition: box-shadow 0.2s;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <strong style="font-size: 13.5px; color: var(--text-main);">${escapedScorer}</strong>
              ${statusBadge}
              ${companyTag}
              ${catTag}
            </div>
            <div style="font-size: 12px; color: var(--text-muted); font-family: var(--mono);">
              ${dateStr}
            </div>
          </div>
          <div style="font-size: 13.5px; color: var(--text-main); line-height: 1.5; white-space: pre-wrap; background: #fff; border: 1px solid var(--border); border-radius: 6px; padding: 10px 12px; margin-bottom: 10px;">${escapedText}</div>
          <div style="display: flex; justify-content: flex-end; gap: 8px; align-items: center;">
            ${item.status !== 'reviewed' ? `<button class="btn" style="background: #f59e0b; color: white; padding: 4px 10px; font-size: 11.5px;" onclick="AdminApp.updateFeedbackStatus(${item.id}, 'reviewed')">Mark Reviewed</button>` : ''}
            ${item.status !== 'resolved' ? `<button class="btn" style="background: #10b981; color: white; padding: 4px 10px; font-size: 11.5px;" onclick="AdminApp.updateFeedbackStatus(${item.id}, 'resolved')">Resolve</button>` : ''}
            ${item.status !== 'new' ? `<button class="btn" style="background: var(--surface-subdued); color: var(--text-muted); border: 1px solid var(--border); padding: 4px 10px; font-size: 11.5px;" onclick="AdminApp.updateFeedbackStatus(${item.id}, 'new')">Reopen</button>` : ''}
            <button class="btn" style="background: transparent; color: var(--accent-red); padding: 4px 8px; font-size: 11.5px; border: 1px solid #fecaca;" onclick="AdminApp.deleteFeedback(${item.id})">Delete</button>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;
  },

  async updateFeedbackStatus(feedbackId, newStatus) {
    try {
      const res = await fetch('/api/admin-actions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'UPDATE_FEEDBACK_STATUS',
          data: { feedback_id: feedbackId, status: newStatus }
        })
      });
      if (res.ok) {
        const item = (this.data.feedback || []).find(f => f.id === feedbackId);
        if (item) item.status = newStatus;
        this.renderFeedback();
      } else {
        const err = await res.json();
        alert('Failed to update status: ' + (err.error || 'Server error'));
      }
    } catch (e) {
      alert('Network error: ' + e.message);
    }
  },

  async deleteFeedback(feedbackId) {
    if (!confirm('Are you sure you want to permanently delete this feedback submission?')) return;
    try {
      const res = await fetch('/api/admin-actions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'DELETE_FEEDBACK',
          data: { feedback_id: feedbackId }
        })
      });
      if (res.ok) {
        this.data.feedback = (this.data.feedback || []).filter(f => f.id !== feedbackId);
        this.renderFeedback();
      } else {
        const err = await res.json();
        alert('Failed to delete feedback: ' + (err.error || 'Server error'));
      }
    } catch (e) {
      alert('Network error: ' + e.message);
    }
  },

  setCoverageFilter(filter) {
    this.coverageFilter = filter;
    document.querySelectorAll('.coverage-filter').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.lane === filter);
    });
    this.renderCoverageBoard();
  },

  setCoverageSearch(value) {
    this.coverageSearch = (value || '').trim().toLowerCase();
    this.renderCoverageBoard();
  },

  renderCoverageBoard() {
    if (!this.data || !this.data.startups) return;

    const testJudgeSet = new Set(
      (this.data.judges || []).filter(j => j.is_test).map(j => j.judge_id)
    );

    // Map progress by judge_id + startup_id
    const progMap = new Map();
    (this.data.progress || []).forEach(p => {
      progMap.set(`${p.judge_id}__${p.startup_id}`, p);
    });

    // Map assignments by startup_id
    const assignmentsByStartup = new Map();
    (this.data.assignments || []).forEach(a => {
      if (testJudgeSet.has(a.judge_id)) return; // Don't count test accounts towards real 2x quorum
      if (!assignmentsByStartup.has(a.startup_id)) {
        assignmentsByStartup.set(a.startup_id, []);
      }
      assignmentsByStartup.get(a.startup_id).push(a);
    });

    // Analyze each startup
    let count2xScored = 0;
    let count1xScored = 0;
    let countInProgress = 0;
    let countZeroAssigned = 0;
    let totalRealAssignments = 0;

    const lane1List = []; // Needs Attention / Under-Assigned (< 2 assigned or 0 progress)
    const lane2List = []; // In Progress / Single-Scored (1 complete or active progress)
    const lane3List = []; // 2x Fully Scored (2 completed)

    this.data.startups.forEach(s => {
      const assigned = assignmentsByStartup.get(s.id) || [];
      totalRealAssignments += assigned.length;

      // Analyze each assigned reviewer's progress
      let fullyScoredCount = 0;
      let inProgressCount = 0;
      const reviewers = [];

      assigned.forEach(a => {
        const p = progMap.get(`${a.judge_id}__${s.id}`);
        const answered = p ? parseInt(p.answered_count || 0, 10) : 0;
        const lastSaved = p ? p.last_saved : null;
        const flagged = p ? parseInt(p.flagged_count || 0, 10) : 0;
        const isComplete = answered >= 282;
        const isProg = answered > 0 && answered < 282;

        if (isComplete) fullyScoredCount++;
        else if (isProg) inProgressCount++;

        reviewers.push({
          judge_id: a.judge_id,
          assigned_at: a.assigned_at,
          answered_count: answered,
          last_saved: lastSaved,
          flagged_count: flagged,
          is_complete: isComplete,
          is_in_progress: isProg
        });
      });

      if (assigned.length === 0) countZeroAssigned++;

      const startupMeta = {
        id: s.id,
        name: s.name,
        assigned_count: assigned.length,
        fully_scored_count: fullyScoredCount,
        in_progress_count: inProgressCount,
        reviewers
      };

      if (fullyScoredCount >= 2) {
        count2xScored++;
        lane3List.push(startupMeta);
      } else if (fullyScoredCount === 1 || inProgressCount > 0) {
        if (fullyScoredCount === 1) count1xScored++;
        else countInProgress++;
        lane2List.push(startupMeta);
      } else {
        lane1List.push(startupMeta);
      }
    });

    // Update KPI Header
    const totalStartups = this.data.startups.length;
    const targetAssignments = totalStartups * 2;
    const coveragePct = targetAssignments > 0 
      ? ((totalRealAssignments / targetAssignments) * 100).toFixed(1) 
      : '0.0';

    const elTotal = document.getElementById('kpi-total-startups');
    const el2x = document.getElementById('kpi-2x-scored');
    const el1x = document.getElementById('kpi-1x-scored');
    const elInProg = document.getElementById('kpi-in-prog');
    const elUnassigned = document.getElementById('kpi-unassigned');
    const elCoverage = document.getElementById('kpi-assignment-coverage');

    if (elTotal) elTotal.textContent = totalStartups;
    if (el2x) el2x.textContent = count2xScored;
    if (el1x) el1x.textContent = count1xScored;
    if (elInProg) elInProg.textContent = countInProgress;
    if (elUnassigned) elUnassigned.textContent = countZeroAssigned;
    if (elCoverage) elCoverage.textContent = `${coveragePct}% (${totalRealAssignments}/${targetAssignments})`;

    // Filter by search & selected tab
    const searchFilter = (list) => {
      if (!this.coverageSearch) return list;
      return list.filter(item => {
        const matchesName = item.name.toLowerCase().includes(this.coverageSearch);
        const matchesReviewer = item.reviewers.some(r => r.judge_id.toLowerCase().includes(this.coverageSearch));
        return matchesName || matchesReviewer;
      });
    };

    const filteredLane1 = searchFilter(lane1List);
    const filteredLane2 = searchFilter(lane2List);
    const filteredLane3 = searchFilter(lane3List);

    // Update Lane Count Badges
    const badge1 = document.getElementById('lane-1-count');
    const badge2 = document.getElementById('lane-2-count');
    const badge3 = document.getElementById('lane-3-count');
    if (badge1) badge1.textContent = `${filteredLane1.length} of ${lane1List.length}`;
    if (badge2) badge2.textContent = `${filteredLane2.length} of ${lane2List.length}`;
    if (badge3) badge3.textContent = `${filteredLane3.length} of ${lane3List.length}`;

    // Render cards into lanes based on active filter
    const lane1El = document.getElementById('lane-1');
    const lane2El = document.getElementById('lane-2');
    const lane3El = document.getElementById('lane-3');

    const activeFilter = this.coverageFilter || 'all';
    if (lane1El) lane1El.style.display = (activeFilter === 'all' || activeFilter === 'lane1') ? 'flex' : 'none';
    if (lane2El) lane2El.style.display = (activeFilter === 'all' || activeFilter === 'lane2') ? 'flex' : 'none';
    if (lane3El) lane3El.style.display = (activeFilter === 'all' || activeFilter === 'lane3') ? 'flex' : 'none';

    const renderCard = (meta) => {
      const escapedName = this.escapeHtml(meta.name);
      const safeId = meta.id.replace(/'/g, "\\'");
      const safeName = meta.name.replace(/'/g, "\\'");

      // Badge for header
      let badgeClass = 'c-badge-empty';
      let badgeText = `${meta.assigned_count}/2 Assigned`;
      if (meta.fully_scored_count >= 2) {
        badgeClass = 'c-badge-goal';
        badgeText = '2x Fully Scored';
      } else if (meta.fully_scored_count === 1) {
        badgeClass = 'c-badge-single';
        badgeText = '1/2 Fully Scored';
      } else if (meta.in_progress_count > 0) {
        badgeClass = 'c-badge-prog';
        badgeText = 'In Progress';
      } else if (meta.assigned_count > 0) {
        badgeClass = 'c-badge-prog';
        badgeText = `${meta.assigned_count}/2 Assigned (0 Answers)`;
      }

      // Render 2 slots
      let slotsHtml = '';
      for (let i = 0; i < 2; i++) {
        const rev = meta.reviewers[i];
        if (rev) {
          const safeRevId = this.escapeHtml(rev.judge_id);
          let slotClass = 'c-slot-unstarted';
          let progClass = 'unstarted';
          let progText = '0 / 282 Answers';

          if (rev.is_complete) {
            slotClass = 'c-slot-complete';
            progClass = 'complete';
            progText = 'Completed (282/282)';
          } else if (rev.is_in_progress) {
            slotClass = 'c-slot-prog';
            progClass = 'in-prog';
            progText = `${rev.answered_count} / 282 (${Math.round((rev.answered_count / 282) * 100)}%)`;
          }

          const savedText = rev.last_saved 
            ? `Saved ${this.formatTimeAgo(rev.last_saved)}`
            : 'Not started';

          const flagBadge = rev.flagged_count > 0 
            ? `<span style="background: #fef3c7; color: #92400e; padding: 1px 5px; border-radius: 4px; font-size: 10px; font-weight: 700;">${rev.flagged_count} Flagged</span>`
            : '';

          slotsHtml += `
            <div class="c-slot ${slotClass}">
              <div class="c-slot-top">
                <span class="c-slot-label">Evaluator ${i + 1}</span>
                <span class="c-slot-scorer" title="${safeRevId}">${safeRevId}</span>
              </div>
              <div class="c-slot-meta">
                <span class="c-slot-progress ${progClass}">${progText}</span>
                <div style="display: flex; align-items: center; gap: 4px;">
                  ${flagBadge}
                  <span class="c-slot-time" title="${rev.last_saved ? this.formatFullDateTime(rev.last_saved) : ''}">${savedText}</span>
                </div>
              </div>
            </div>
          `;
        } else {
          // Empty slot
          slotsHtml += `
            <div class="c-slot c-slot-empty">
              <div class="c-slot-top">
                <span class="c-slot-label">Evaluator ${i + 1}</span>
                <span style="font-size: 11px; color: var(--text-muted); font-style: italic;">Unassigned</span>
              </div>
              <div class="c-slot-meta" style="justify-content: flex-end; margin-top: 3px;">
                <button type="button" class="c-slot-action-btn" onclick="AdminApp.openAssignModal('${safeId}', '${safeName}')">
                  + Assign Evaluator
                </button>
              </div>
            </div>
          `;
        }
      }

      return `
        <div class="c-card" data-startup-id="${meta.id}">
          <div class="c-card-header">
            <span class="c-card-title" title="${escapedName}">${escapedName}</span>
            <span class="c-card-badge ${badgeClass}">${badgeText}</span>
          </div>
          <div class="c-card-slots">
            ${slotsHtml}
          </div>
        </div>
      `;
    };

    const container1 = document.getElementById('lane-1-cards');
    const container2 = document.getElementById('lane-2-cards');
    const container3 = document.getElementById('lane-3-cards');

    if (container1) {
      container1.innerHTML = filteredLane1.length > 0 
        ? filteredLane1.map(renderCard).join('')
        : '<div style="padding: 30px 10px; text-align: center; color: var(--text-muted); font-size: 12.5px;">No startups in this lane.</div>';
    }
    if (container2) {
      container2.innerHTML = filteredLane2.length > 0 
        ? filteredLane2.map(renderCard).join('')
        : '<div style="padding: 30px 10px; text-align: center; color: var(--text-muted); font-size: 12.5px;">No startups in this lane.</div>';
    }
    if (container3) {
      container3.innerHTML = filteredLane3.length > 0 
        ? filteredLane3.map(renderCard).join('')
        : '<div style="padding: 30px 10px; text-align: center; color: var(--text-muted); font-size: 12.5px;">No startups reached 2x quorum yet.</div>';
    }
  },

  openAssignModal(startupId, startupName) {
    const modal = document.getElementById('quick-assign-modal');
    if (!modal) return;

    document.getElementById('qa-startup-id').value = startupId;
    document.getElementById('qa-startup-name').textContent = startupName;

    // Find currently assigned judges for this startup
    const testJudgeSet = new Set((this.data.judges || []).filter(j => j.is_test).map(j => j.judge_id));
    const currentAssignments = (this.data.assignments || []).filter(a => a.startup_id === startupId && !testJudgeSet.has(a.judge_id));
    const currentJudgeIds = new Set(currentAssignments.map(a => a.judge_id));

    // Show current evaluators
    const currentEl = document.getElementById('qa-current-evaluators');
    if (currentEl) {
      if (currentAssignments.length === 0) {
        currentEl.innerHTML = '<span>Current status: <strong>0 evaluators assigned</strong></span>';
      } else {
        const names = currentAssignments.map(a => `<code style="font-weight:700; color:var(--text-main);">${this.escapeHtml(a.judge_id)}</code>`).join(', ');
        currentEl.innerHTML = `<span>Currently assigned: ${names}</span>`;
      }
    }

    // Populate dropdown with available non-test judges not yet assigned to this company
    const select = document.getElementById('qa-judge-select');
    select.innerHTML = '';

    // Count workloads for each judge
    const workloadMap = {};
    (this.data.assignments || []).forEach(a => {
      workloadMap[a.judge_id] = (workloadMap[a.judge_id] || 0) + 1;
    });

    const eligibleJudges = (this.data.judges || []).filter(j => !j.is_test && !currentJudgeIds.has(j.judge_id));

    if (eligibleJudges.length === 0) {
      select.innerHTML = '<option value="">No eligible evaluators available</option>';
    } else {
      select.innerHTML = '<option value="">-- Choose an Evaluator --</option>';
      eligibleJudges.forEach(j => {
        const count = workloadMap[j.judge_id] || 0;
        const opt = document.createElement('option');
        opt.value = j.judge_id;
        opt.textContent = `${j.judge_id} (${count} companies currently assigned)`;
        select.appendChild(opt);
      });
    }

    modal.style.display = 'flex';
  },

  closeAssignModal() {
    const modal = document.getElementById('quick-assign-modal');
    if (modal) modal.style.display = 'none';
  },

  async confirmQuickAssign() {
    const startupId = document.getElementById('qa-startup-id').value;
    const judgeId = document.getElementById('qa-judge-select').value;
    if (!startupId || !judgeId) {
      alert("Please select an evaluator.");
      return;
    }
    this.closeAssignModal();
    await this.toggleAssignment(judgeId, startupId, true);
    this.renderCoverageBoard();
  }
};

document.addEventListener('DOMContentLoaded', () => AdminApp.init());
