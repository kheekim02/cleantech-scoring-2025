window.AdminApp = {
  auth: null,
  data: {
    judges: [],
    startups: [],
    assignments: [] // array of { judge_id, startup_id }
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
    const selectedJudge = document.getElementById('judge-select').value;
    
    if (!selectedJudge) {
      container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 14px;">Please select a scorer first.</div>';
      return;
    }

    // Filter assignments for this judge
    const assignedSet = new Set(
      this.data.assignments
        .filter(a => a.judge_id === selectedJudge)
        .map(a => a.startup_id)
    );

        // Calculate global assignment counts
    const globalCounts = {};
    this.data.assignments.forEach(a => {
        globalCounts[a.startup_id] = (globalCounts[a.startup_id] || 0) + 1;
    });

    let html = '';
    this.data.startups.forEach(s => {
      const isChecked = assignedSet.has(s.id) ? 'checked' : '';
      const count = globalCounts[s.id] || 0;
      
      let badge = '';
      if (count === 0) badge = `<span style="background: #fef08a; color: #854d0e; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; margin-left: auto;">0 Assigned</span>`;
      else if (count === 1) badge = `<span style="background: #fed7aa; color: #9a3412; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; margin-left: auto;">1 Assigned</span>`;
      else badge = `<span style="background: #bbf7d0; color: #166534; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; margin-left: auto;">${count} Assigned</span>`;

      html += `
        <div class="company-item" style="display: flex; align-items: center; justify-content: flex-start; gap: 10px; padding: 10px 12px; border-bottom: 1px solid var(--hairline);">
          <input type="checkbox" id="chk-${s.id}" ${isChecked} onchange="AdminApp.toggleAssignment('${selectedJudge}', '${s.id}', this.checked)" style="margin: 0; width: 16px; height: 16px; cursor: pointer;">
          <label for="chk-${s.id}" style="font-size: 14px; cursor: pointer; display: flex; flex: 1; align-items: center;">
            <span style="font-weight: 500;">${s.name}</span>
            <span style="color: var(--text-muted); font-size: 12px; margin-left: 8px;">(${s.id})</span>
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
