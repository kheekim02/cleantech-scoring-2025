const fs = require('fs');
let jsCode = fs.readFileSync('site/js/admin.js', 'utf8');

// 1. Remove the duplicated (id)
jsCode = jsCode.replace(
  /<span style="color: var\(--text-muted\); font-size: 12px; margin-left: 8px;">\(\$\{s\.id\}\)<\/span>/g,
  ""
);

// 2. Add progress bar chart logic to renderAssignments
// Currently, `renderAssignments()` starts like this:
//   renderAssignments() {
//     const container = document.getElementById('company-list-container');
//     const selectedJudge = document.getElementById('judge-select').value;
//     
//     if (!selectedJudge) {

const oldRenderStart = `  renderAssignments() {
    const container = document.getElementById('company-list-container');
    const selectedJudge = document.getElementById('judge-select').value;
    
    if (!selectedJudge) {`;

const newRenderStart = `  renderAssignments() {
    const container = document.getElementById('company-list-container');
    const selectedJudge = document.getElementById('judge-select').value;
    
    // Calculate global assignment counts for progress bar
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
    
    const total = this.data.startups.length || 1;
    const pct0 = (count0 / total) * 100;
    const pct1 = (count1 / total) * 100;
    const pct2 = (count2 / total) * 100;

    const progressHtml = \`
      <div style="margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 6px;">
          <span style="color: #166534;">Fully Assigned (2+): \${count2}</span>
          <span style="color: #9a3412;">Assigned (1): \${count1}</span>
          <span style="color: #854d0e;">Unassigned (0): \${count0}</span>
        </div>
        <div style="display: flex; height: 10px; border-radius: 5px; overflow: hidden; background: var(--surface-sunk); border: 1px solid var(--border);">
          <div style="width: \${pct2}%; background: #4ade80;" title="\${count2} fully assigned"></div>
          <div style="width: \${pct1}%; background: #fb923c;" title="\${count1} partially assigned"></div>
          <div style="width: \${pct0}%; background: #fde047;" title="\${count0} unassigned"></div>
        </div>
      </div>
    \`;

    // Inject progress bar into DOM if we have a placeholder, or just above the dropdown.
    // Wait, the select is static in HTML. Let's create a placeholder for it dynamically or inject it.
    let progressContainer = document.getElementById('progress-container');
    if (!progressContainer) {
        const selectDiv = document.getElementById('judge-select').parentNode;
        progressContainer = document.createElement('div');
        progressContainer.id = 'progress-container';
        selectDiv.parentNode.insertBefore(progressContainer, selectDiv);
    }
    progressContainer.innerHTML = progressHtml;

    if (!selectedJudge) {`;

jsCode = jsCode.replace(oldRenderStart, newRenderStart);

// We need to remove the duplicate `globalCounts` calculation further down since we moved it to the top.
const duplicateGlobalCounts = `    // Calculate global assignment counts
    const globalCounts = {};
    this.data.assignments.forEach(a => {
        globalCounts[a.startup_id] = (globalCounts[a.startup_id] || 0) + 1;
    });`;

jsCode = jsCode.replace(duplicateGlobalCounts, "");

fs.writeFileSync('site/js/admin.js', jsCode);
console.log("Patched progress bar and removed ID.");
