window.AdminApp = {
  auth: null,
  filterMode: 'ready',
  data: {
    judges: [],
    startups: [],
    assignments: [] // array of { judge_id, startup_id }
  },

  setFilter(mode) {
    this.filterMode = mode;
    const btnReady = document.getElementById('filter-ready-btn');
    const btnAll = document.getElementById('filter-all-btn');
    if (btnReady && btnAll) {
      if (mode === 'ready') {
        btnReady.style.background = '#059669';
        btnReady.style.color = '#fff';
        btnAll.style.background = 'var(--surface-subdued)';
        btnAll.style.color = 'var(--text-muted)';
      } else {
        btnAll.style.background = '#059669';
        btnAll.style.color = '#fff';
        btnReady.style.background = 'var(--surface-subdued)';
        btnReady.style.color = 'var(--text-muted)';
      }
    }
    this.renderAssignments();
  },

  init() {
    const stored = localStorage.getItem('cto_admin_auth');
    if (stored) {
      this.auth = JSON.parse(stored);
      document.getElementById('admin-login-modal').style.display = 'none';
      this.loadData();
    } else {
      document.getElementById('admin-login-modal').style.display = 'flex';
      document.getElementById('admin-dashboard').style.display = 'none';
    }
  },

  async login() {
    const user = document.getElementById('auth-admin-user').value.trim();
    const pass = document.getElementById('auth-admin-pass').value.trim();
    if (!user || !pass) return;

    try {
      const res = await fetch('/api/admin-auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: user, passcode: pass })
      });
      if (res.ok) {
        this.auth = { username: user, passcode: pass };
        localStorage.setItem('cto_admin_auth', JSON.stringify(this.auth));
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
    localStorage.removeItem('cto_admin_auth');
    this.auth = null;
    document.getElementById('admin-login-modal').style.display = 'flex';
    document.getElementById('admin-dashboard').style.display = 'none';
  },

  async loadData() {
    if (!this.auth) return;
    try {
      const res = await fetch(`/api/admin-data?username=${encodeURIComponent(this.auth.username)}&passcode=${encodeURIComponent(this.auth.passcode)}`);
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
      listHtml += `
        <div style="display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid var(--border);">
          <strong style="color: var(--accent-blue);">${j.judge_id}</strong>
          <span style="font-family: monospace; color: var(--text-muted); background: #fff; padding: 2px 6px; border-radius: 4px; border: 1px solid var(--hairline);">${j.passcode}</span>
        </div>
      `;
    });
    
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
    
    // Map progress for this judge
    const progressMap = {};
    if (this.data.progress) {
      this.data.progress
        .filter(p => p.judge_id === selectedJudge)
        .forEach(p => {
          progressMap[p.startup_id] = parseInt(p.answered_count, 10);
        });
    }

    const readyCount = this.data.startups.filter(s => s.clean_ready).length;
    const statusPill = document.getElementById('ready-status-pill');
    if (statusPill) {
      statusPill.textContent = `${readyCount} / ${this.data.startups.length} Ready for Assignment`;
    }

    const startupsToRender = (this.filterMode === 'ready') 
      ? this.data.startups.filter(s => s.clean_ready) 
      : this.data.startups;

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

      // Clean AI Ready Badge
      const readyBadge = s.clean_ready
        ? `<span style="background: #ecfdf5; color: #047857; padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-left: 8px; border: 1px solid #a7f3d0;">✓ Clean AI Ready</span>`
        : `<span style="background: #f3f4f6; color: #6b7280; padding: 2px 7px; border-radius: 4px; font-size: 10px; font-weight: 500; margin-left: 8px;">⏳ Extracting AI</span>`;

      html += `
        <div class="company-item" style="display: flex; align-items: center; justify-content: flex-start; gap: 10px; padding: 10px 12px; border-bottom: 1px solid var(--hairline); background: ${isChecked ? '#fafafa' : '#fff'};">
          <input type="checkbox" id="chk-${s.id}" ${isChecked} onchange="AdminApp.toggleAssignment('${selectedJudge}', '${s.id}', this.checked)" style="margin: 0; width: 16px; height: 16px; cursor: pointer;">
          <label for="chk-${s.id}" style="font-size: 14px; cursor: pointer; display: flex; flex: 1; align-items: center;">
            <span style="font-weight: 500;">${s.name}</span>
            ${readyBadge}
            ${subBadge}
            ${badge}
          </label>
        </div>
      `;
    });
    
    container.innerHTML = html;
  },

  async createScorer() {
    const idInput = document.getElementById('new-judge-id');
    const passInput = document.getElementById('new-judge-pass');
    const msg = document.getElementById('create-msg');
    
    const new_judge_id = idInput.value.trim();
    const new_passcode = passInput.value.trim();
    
    if (!new_judge_id || !new_passcode) {
      msg.textContent = "Please fill out both fields.";
      msg.style.color = 'var(--accent-red)';
      return;
    }
    
    try {
      const res = await fetch('/api/admin-actions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: this.auth.username,
          passcode: this.auth.passcode,
          action: 'CREATE_JUDGE',
          data: { new_judge_id, new_passcode }
        })
      });
      
      if (res.ok) {
        msg.textContent = "Scorer created successfully!";
        msg.style.color = 'var(--accent-green)';
        idInput.value = '';
        passInput.value = '';
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
    
    setTimeout(() => { msg.textContent = ''; }, 3000);
  },

  async toggleAssignment(judge_id, startup_id, assigned) {
    try {
      const res = await fetch('/api/admin-actions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: this.auth.username,
          passcode: this.auth.passcode,
          action: 'TOGGLE_ASSIGNMENT',
          data: { judge_id, startup_id, assigned }
        })
      });
      
      if (res.ok) {
        // Update local state to avoid full reload
        if (assigned) {
          this.data.assignments.push({ judge_id, startup_id });
        } else {
          this.data.assignments = this.data.assignments.filter(a => !(a.judge_id === judge_id && a.startup_id === startup_id));
        }
      } else {
        alert("Failed to update assignment. Refresh the page.");
        this.loadData();
      }
    } catch (e) {
      alert("Network error updating assignment");
      this.loadData();
    }
  }
};

document.addEventListener('DOMContentLoaded', () => AdminApp.init());
