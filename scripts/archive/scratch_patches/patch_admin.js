const fs = require('fs');

// 1. Patch api/admin-data.js to return passcodes
let apiCode = fs.readFileSync('api/admin-data.js', 'utf8');
apiCode = apiCode.replace(
  "SELECT judge_id FROM judges ORDER BY judge_id ASC",
  "SELECT judge_id, passcode FROM judges ORDER BY judge_id ASC"
);
fs.writeFileSync('api/admin-data.js', apiCode);

// 2. Patch site/admin.html to add Existing Scorers list
let htmlCode = fs.readFileSync('site/admin.html', 'utf8');
const existingScorersHtml = `
          <div id="create-msg" style="margin-top: 12px; font-size: 13px; font-weight: 600; text-align: center;"></div>
          
          <div style="margin-top: 32px;">
            <h3 style="font-size: 15px; margin-top: 0; border-bottom: 1px solid var(--border); padding-bottom: 8px; color: var(--text-main);">Existing Scorers</h3>
            <div id="scorers-list" style="max-height: 280px; overflow-y: auto; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface-subdued);">
              <!-- Scorers injected here -->
            </div>
          </div>
`;
htmlCode = htmlCode.replace(
  `<div id="create-msg" style="margin-top: 12px; font-size: 13px; font-weight: 600; text-align: center;"></div>`,
  existingScorersHtml
);
fs.writeFileSync('site/admin.html', htmlCode);

// 3. Patch site/js/admin.js to render both the scorers list and the assignment badges
let jsCode = fs.readFileSync('site/js/admin.js', 'utf8');

const renderScorersRegex = /renderScorers\(\) \{[\s\S]*?this\.renderAssignments\(\);\s*\}/;
const newRenderScorers = `renderScorers() {
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
      listHtml += \`
        <div style="display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid var(--border);">
          <strong style="color: var(--accent-blue);">\${j.judge_id}</strong>
          <span style="font-family: monospace; color: var(--text-muted); background: #fff; padding: 2px 6px; border-radius: 4px; border: 1px solid var(--hairline);">\${j.passcode}</span>
        </div>
      \`;
    });
    
    scorersList.innerHTML = listHtml;
    this.renderAssignments();
  }`;
jsCode = jsCode.replace(renderScorersRegex, newRenderScorers);


const renderAssignmentsRegex = /let html = '';\s*this\.data\.startups\.forEach\(s => \{[\s\S]*?\}\);/;
const newRenderAssignments = `    // Calculate global assignment counts
    const globalCounts = {};
    this.data.assignments.forEach(a => {
        globalCounts[a.startup_id] = (globalCounts[a.startup_id] || 0) + 1;
    });

    let html = '';
    this.data.startups.forEach(s => {
      const isChecked = assignedSet.has(s.id) ? 'checked' : '';
      const count = globalCounts[s.id] || 0;
      
      let badge = '';
      if (count === 0) badge = \`<span style="background: #fef08a; color: #854d0e; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; margin-left: auto;">0 Assigned</span>\`;
      else if (count === 1) badge = \`<span style="background: #fed7aa; color: #9a3412; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; margin-left: auto;">1 Assigned</span>\`;
      else badge = \`<span style="background: #bbf7d0; color: #166534; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700; margin-left: auto;">\${count} Assigned</span>\`;

      html += \`
        <div class="company-item" style="display: flex; align-items: center; justify-content: flex-start; gap: 10px; padding: 10px 12px; border-bottom: 1px solid var(--hairline);">
          <input type="checkbox" id="chk-\${s.id}" \${isChecked} onchange="AdminApp.toggleAssignment('\${selectedJudge}', '\${s.id}', this.checked)" style="margin: 0; width: 16px; height: 16px; cursor: pointer;">
          <label for="chk-\${s.id}" style="font-size: 14px; cursor: pointer; display: flex; flex: 1; align-items: center;">
            <span style="font-weight: 500;">\${s.name}</span>
            <span style="color: var(--text-muted); font-size: 12px; margin-left: 8px;">(\${s.id})</span>
            \${badge}
          </label>
        </div>
      \`;
    });`;
jsCode = jsCode.replace(renderAssignmentsRegex, newRenderAssignments);

fs.writeFileSync('site/js/admin.js', jsCode);
console.log("Patches applied.");
