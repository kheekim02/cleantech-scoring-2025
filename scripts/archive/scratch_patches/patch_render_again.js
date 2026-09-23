const fs = require('fs');
let renderCode = fs.readFileSync('site/js/render.js', 'utf8');

const regex = /let justHtml = '';\s*if\s*\(requiresJustification\)\s*\{[\s\S]*?\}\s*const isAnswered/g;

const newJustHtml = `        let justHtml = '';
        if (requiresJustification) {
          const hasRubric = ['BC_Q1', 'BC_Q2', 'BC_Q4', 'BC_Q5'].includes(q.new_q_id);
          const rubricLink = hasRubric ? \`<a href="#" class="view-rubric" data-qid="\${q.new_q_id}" style="float: right; color: var(--accent-blue); text-decoration: none; font-weight: 500;">\${window.CTO.Render.icons.doc || '📄'} View Examples</a>\` : '';
          
          justHtml = \`
            <div class="h-card-justification" style="padding: 0 24px 16px 24px;">
              <label style="display: block; font-size: 13px; font-weight: 600; color: var(--text-main); margin-bottom: 8px;">
                Justification
                \${rubricLink}
              </label>
              <textarea class="justification-input" data-qid="\${q.new_q_id}" placeholder="Provide justification based on the markdown rubrics..." style="width: 100%; min-height: 80px; padding: 12px; border: 1px solid var(--border); border-radius: 6px; font-family: inherit; font-size: 13px; resize: vertical; box-sizing: border-box; background: var(--surface-main);">\${existingJustification}</textarea>
            </div>
          \`;
        }
        
        const isAnswered`;

renderCode = renderCode.replace(regex, newJustHtml);

fs.writeFileSync('site/js/render.js', renderCode);
console.log("Regex replaced");
