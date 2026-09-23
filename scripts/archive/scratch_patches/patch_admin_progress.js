const fs = require('fs');

// 1. Patch api/admin-data.js
let apiCode = fs.readFileSync('api/admin-data.js', 'utf8');
if (!apiCode.includes('progressRes')) {
  apiCode = apiCode.replace(
    "const assignmentsRes = await client.query('SELECT judge_id, startup_id FROM judge_assignments');",
    "const assignmentsRes = await client.query('SELECT judge_id, startup_id FROM judge_assignments');\n    const progressRes = await client.query('SELECT judge_id, startup_id, count(question_id) as answered_count FROM human_reviews GROUP BY judge_id, startup_id');"
  );
  apiCode = apiCode.replace(
    "assignments: assignmentsRes.rows",
    "assignments: assignmentsRes.rows,\n      progress: progressRes.rows"
  );
  fs.writeFileSync('api/admin-data.js', apiCode);
}

// 2. Patch site/admin.html
let htmlCode = fs.readFileSync('site/admin.html', 'utf8');
if (!htmlCode.includes('id="assignment-chart"')) {
  htmlCode = htmlCode.replace(
    '<!-- Scorers injected here -->\n            </div>\n          </div>',
    '<!-- Scorers injected here -->\n            </div>\n          </div>\n          \n          <div style="margin-top: 32px;">\n            <h3 style="font-size: 15px; margin-top: 0; border-bottom: 1px solid var(--border); padding-bottom: 8px; color: var(--text-main);">Assignment Distribution</h3>\n            <div id="assignment-chart" style="padding: 10px 0;"></div>\n          </div>'
  );
  fs.writeFileSync('site/admin.html', htmlCode);
}

// 3. Patch site/js/admin.js
let jsCode = fs.readFileSync('site/js/admin.js', 'utf8');

// Remove the old stacked progress bar logic
const regexRemoveOld = /const pct0 =[\s\S]*?progressContainer\.innerHTML = progressHtml;/g;
jsCode = jsCode.replace(regexRemoveOld, "");

// We need to inject the Bar Chart logic and the submission tracker logic
// Let's rewrite `renderAssignments` completely to be clean.
const oldRenderAssignmentsRegex = /renderAssignments\(\) \{[\s\S]*?async createScorer\(\)/;

const newRenderAssignments = `renderAssignments() {
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
    
    // Render Bar Chart
    const maxVal = Math.max(count0, count1, count2, 1);
    const h0 = (count0 / maxVal) * 100;
    const h1 = (count1 / maxVal) * 100;
    const h2 = (count2 / maxVal) * 100;
    
    if (chartContainer) {
        chartContainer.innerHTML = \`
          <div style="display: flex; align-items: flex-end; justify-content: space-around; height: 140px; border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-top: 10px;">
            
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
               <span style="font-size: 11px; font-weight: 600; margin-bottom: 4px; color: var(--text-muted);">\${count0}</span>
               <div style="width: 40px; height: \${h0}%; background: #fde047; border-radius: 4px 4px 0 0; min-height: 4px; border: 1px solid #eab308; border-bottom: none;"></div>
               <span style="font-size: 11px; margin-top: 8px; font-weight: 600; text-align: center;">Unassigned</span>
            </div>
            
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
               <span style="font-size: 11px; font-weight: 600; margin-bottom: 4px; color: var(--text-muted);">\${count1}</span>
               <div style="width: 40px; height: \${h1}%; background: #fb923c; border-radius: 4px 4px 0 0; min-height: 4px; border: 1px solid #ea580c; border-bottom: none;"></div>
               <span style="font-size: 11px; margin-top: 8px; font-weight: 600; text-align: center;">Assigned (1)</span>
            </div>
            
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
               <span style="font-size: 11px; font-weight: 600; margin-bottom: 4px; color: var(--text-muted);">\${count2}</span>
               <div style="width: 40px; height: \${h2}%; background: #4ade80; border-radius: 4px 4px 0 0; min-height: 4px; border: 1px solid #16a34a; border-bottom: none;"></div>
               <span style="font-size: 11px; margin-top: 8px; font-weight: 600; text-align: center;">Fully Assigned (2+)</span>
            </div>
            
          </div>
        \`;
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

    let html = '';
    this.data.startups.forEach(s => {
      const isChecked = assignedSet.has(s.id) ? 'checked' : '';
      const count = globalCounts[s.id] || 0;
      
      // Global Assignment Badge
      let badge = '';
      if (count === 0) badge = \`<span style="background: #fef08a; color: #854d0e; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 700; margin-left: auto;">0 Assigned</span>\`;
      else if (count === 1) badge = \`<span style="background: #fed7aa; color: #9a3412; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 700; margin-left: auto;">1 Assigned</span>\`;
      else badge = \`<span style="background: #bbf7d0; color: #166534; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 700; margin-left: auto;">\${count} Assigned</span>\`;

      // Submission Tracker Badge (only if assigned to this judge)
      let subBadge = '';
      if (isChecked) {
        const pCount = progressMap[s.id] || 0;
        if (pCount === 0) {
            subBadge = \`<span style="color: #ef4444; font-size: 11px; font-weight: 600; margin-left: 10px; border: 1px solid #fca5a5; padding: 2px 6px; border-radius: 4px; background: #fef2f2;">Not Started</span>\`;
        } else {
            subBadge = \`<span style="color: #0369a1; font-size: 11px; font-weight: 600; margin-left: 10px; border: 1px solid #7dd3fc; padding: 2px 6px; border-radius: 4px; background: #f0f9ff;">\${pCount} Answers</span>\`;
        }
      }

      html += \`
        <div class="company-item" style="display: flex; align-items: center; justify-content: flex-start; gap: 10px; padding: 10px 12px; border-bottom: 1px solid var(--hairline); background: \${isChecked ? '#fafafa' : '#fff'};">
          <input type="checkbox" id="chk-\${s.id}" \${isChecked} onchange="AdminApp.toggleAssignment('\${selectedJudge}', '\${s.id}', this.checked)" style="margin: 0; width: 16px; height: 16px; cursor: pointer;">
          <label for="chk-\${s.id}" style="font-size: 14px; cursor: pointer; display: flex; flex: 1; align-items: center;">
            <span style="font-weight: 500;">\${s.name}</span>
            \${subBadge}
            \${badge}
          </label>
        </div>
      \`;
    });
    
    container.innerHTML = html;
  }

  async createScorer()`;

jsCode = jsCode.replace(oldRenderAssignmentsRegex, newRenderAssignments);
fs.writeFileSync('site/js/admin.js', jsCode);
console.log("Patched admin.js with bar chart and submission tracker");
