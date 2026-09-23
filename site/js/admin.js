window.AdminApp = {
  auth: null,
  assignmentFilter: 'all',
  companySearch: '',
  selectedJudgeId: sessionStorage.getItem('cto_admin_selected_judge') || '',
  data: {
    judges: [],
    startups: [],
    assignments: [] // array of { judge_id, startup_id, assigned_at }
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
      opt.textContent = j.judge_id;
      select.appendChild(opt);
      
      // List item
      const safeId = j.judge_id.replace(/'/g, "\\'");
      const escapedId = this.escapeHtml(j.judge_id);
      listHtml += `
        <div class="scorer-item" style="padding: 10px 12px; border-bottom: 1px solid var(--border);">
          <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px;">
            <strong style="color: var(--accent-blue); font-size: 13px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapedId}">${escapedId}</strong>
            <div style="display: flex; gap: 6px; align-items: center; flex-shrink: 0;">
              <button class="btn btn-reset-pass" onclick="AdminApp.resetPassword('${safeId}')" style="background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; cursor: pointer; transition: background 0.15s ease;" onmouseover="this.style.background='#bae6fd'" onmouseout="this.style.background='#e0f2fe'">Reset</button>
              <button class="btn btn-delete-scorer" onclick="AdminApp.deleteScorer('${safeId}')" style="background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; cursor: pointer; transition: background 0.15s ease;" onmouseover="this.style.background='#fecaca'" onmouseout="this.style.background='#fee2e2'">Delete</button>
            </div>
          </div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px; display: flex; align-items: center; gap: 4px;">
            <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #10b981;"></span>
            <span>Password protected</span>
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
    
    // 1. Calculate global assignment counts for the Bar Chart
    const globalCounts = {};
    this.data.assignments.forEach(a => {
        globalCounts[a.startup_id] = (globalCounts[a.startup_id] || 0) + 1;
    });

    let count0 = 0, count1 = 0, count2 = 0;
    this.data.startups.forEach(s => {
        const c = globalCounts[s.id] || 0;
        if (c === 0) count0++;
        else if (c === 1) count1++;
        else count2++;
    });
    
    // Render Bar Chart with fixed pixel heights and aligned baseline
    const maxVal = Math.max(count0, count1, count2, 1);
    const trackHeight = 90;
    const bar0 = count0 > 0 ? Math.max(8, Math.round((count0 / maxVal) * trackHeight)) : 3;
    const bar1 = count1 > 0 ? Math.max(8, Math.round((count1 / maxVal) * trackHeight)) : 3;
    const bar2 = count2 > 0 ? Math.max(8, Math.round((count2 / maxVal) * trackHeight)) : 3;
    
    if (chartContainer) {
        chartContainer.innerHTML = `
          <div style="display: flex; justify-content: space-around; gap: 8px; margin-top: 12px; padding: 0 4px;">
            
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 0;">
               <span style="font-size: 13px; font-weight: 700; color: var(--text-main); margin-bottom: 6px;">${count0}</span>
               <div style="height: ${trackHeight}px; width: 100%; display: flex; align-items: flex-end; justify-content: center;">
                 <div style="width: 38px; height: ${bar0}px; background: #fde047; border-radius: 4px 4px 0 0; border: 1px solid #eab308; border-bottom: none; box-sizing: border-box;"></div>
               </div>
               <div style="width: 100%; height: 1px; background: var(--border);"></div>
               <div style="min-height: 32px; display: flex; align-items: flex-start; justify-content: center; text-align: center; margin-top: 6px;">
                 <span style="font-size: 11px; font-weight: 600; color: var(--text-muted); line-height: 1.2;">Unassigned</span>
               </div>
            </div>
            
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 0;">
               <span style="font-size: 13px; font-weight: 700; color: var(--text-main); margin-bottom: 6px;">${count1}</span>
               <div style="height: ${trackHeight}px; width: 100%; display: flex; align-items: flex-end; justify-content: center;">
                 <div style="width: 38px; height: ${bar1}px; background: #fb923c; border-radius: 4px 4px 0 0; border: 1px solid #ea580c; border-bottom: none; box-sizing: border-box;"></div>
               </div>
               <div style="width: 100%; height: 1px; background: var(--border);"></div>
               <div style="min-height: 32px; display: flex; align-items: flex-start; justify-content: center; text-align: center; margin-top: 6px;">
                 <span style="font-size: 11px; font-weight: 600; color: var(--text-muted); line-height: 1.2;">Assigned (1)</span>
               </div>
            </div>
            
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 0;">
               <span style="font-size: 13px; font-weight: 700; color: var(--text-main); margin-bottom: 6px;">${count2}</span>
               <div style="height: ${trackHeight}px; width: 100%; display: flex; align-items: flex-end; justify-content: center;">
                 <div style="width: 38px; height: ${bar2}px; background: #4ade80; border-radius: 4px 4px 0 0; border: 1px solid #16a34a; border-bottom: none; box-sizing: border-box;"></div>
               </div>
               <div style="width: 100%; height: 1px; background: var(--border);"></div>
               <div style="min-height: 32px; display: flex; align-items: flex-start; justify-content: center; text-align: center; margin-top: 6px;">
                 <span style="font-size: 11px; font-weight: 600; color: var(--text-muted); line-height: 1.2;">Fully Assigned (2+)</span>
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
    if (this.data.progress) {
      this.data.progress
        .filter(p => p.judge_id === selectedJudge)
        .forEach(p => {
          progressMap[p.startup_id] = parseInt(p.answered_count, 10);
        });
    }

    const startupsToRender = this.data.startups.filter(s => {
      const assigned = assignedSet.has(s.id);
      const matchesFilter = this.assignmentFilter === 'all' || (this.assignmentFilter === 'assigned' && assigned) || (this.assignmentFilter === 'unassigned' && !assigned);
      return matchesFilter && (!this.companySearch || s.name.toLowerCase().includes(this.companySearch));
    });
    const summary = document.getElementById('assignment-summary');
    if (summary) summary.textContent = `${assignedSet.size} of ${this.data.startups.length} companies assigned to ${selectedJudge} · showing ${startupsToRender.length}`;

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
        if (pCount === 0) {
            subBadge = `<span style="color: #ef4444; font-size: 11px; font-weight: 600; margin-left: 10px; border: 1px solid #fca5a5; padding: 2px 6px; border-radius: 4px; background: #fef2f2;">Not Started</span>`;
        } else {
            subBadge = `<span style="color: #0369a1; font-size: 11px; font-weight: 600; margin-left: 10px; border: 1px solid #7dd3fc; padding: 2px 6px; border-radius: 4px; background: #f0f9ff;">${pCount} Answers</span>`;
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
        ? '🙈 <span class="pass-toggle-label">Hide</span>'
        : '👁️ <span class="pass-toggle-label">Show</span>';
      btn.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
    }
  },

  async createScorer() {
    const idInput = document.getElementById('new-judge-id');
    const passInput = document.getElementById('new-judge-pass');
    const msg = document.getElementById('create-msg');
    
    const new_judge_id = idInput.value.trim();
    const new_password = passInput.value.trim();
    
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
          data: { new_judge_id, new_password }
        })
      });
      
      if (res.ok) {
        msg.innerHTML = `
          <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px 12px; margin-top: 12px; position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
              <div style="font-size: 13px; color: #166534; font-weight: 700;">
                ✓ Scorer <strong>${this.escapeHtml(new_judge_id)}</strong> created!
              </div>
              <button type="button" onclick="document.getElementById('create-msg').innerHTML=''" style="background: none; border: none; font-size: 14px; color: #15803d; cursor: pointer; padding: 0 4px; line-height: 1;" title="Dismiss notification">✕</button>
            </div>
            <div style="margin-top: 6px; font-size: 12px; color: var(--text-muted);">
              Temporary password: <code style="background: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-weight: 700; user-select: all;">${this.escapeHtml(new_password)}</code>
            </div>
            <div style="margin-top: 4px; font-size: 10px; color: #15803d;">
              Notice will remain visible for 1 minute for easy copying.
            </div>
          </div>
        `;
        msg.style.color = 'inherit';
        idInput.value = '';
        passInput.value = '';
        passInput.type = 'password';
        const toggleBtn = document.getElementById('toggle-new-pass-btn');
        if (toggleBtn) {
          toggleBtn.innerHTML = '👁️ <span class="pass-toggle-label">Show</span>';
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

  exportScores() {
    window.location.href = '/api/export-scores';
  }
};

document.addEventListener('DOMContentLoaded', () => AdminApp.init());
