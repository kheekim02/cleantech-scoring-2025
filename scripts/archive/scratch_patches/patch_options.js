const fs = require('fs');
let code = fs.readFileSync('site/js/render.js', 'utf-8');

// Replace the hardcoded .h-actions with a dynamic map over q.options
const oldActionsStart = `              <div class="h-actions">`;
const oldActionsEnd = `              </div>
            </div>
          </div>
        \`;`;

const actionsBlock = code.substring(code.indexOf(oldActionsStart), code.indexOf(oldActionsEnd) + oldActionsEnd.length);

const newActions = `              <div class="h-actions">
                \${q.options ? q.options.map(opt => {
                    const isSel = ans === opt.val ? 'selected' : '';
                    const cls = opt.val > 0 ? 'yes' : 'no';
                    let style = '';
                    if (opt.val > 0 && opt.val < 1) {
                        style = isSel ? 'background: var(--accent-orange); color: white; border-color: var(--accent-orange);' : 'color: var(--accent-orange); border-color: var(--accent-orange);';
                    }
                    return \`
                      <button class="h-btn \${cls} \${isSel}" data-qid="\${q.new_q_id || q.q_id}" data-val="\${opt.val}" style="\${style}">
                        \${opt.label}
                      </button>
                    \`;
                }).join('') : \`
                  <button class="h-btn yes \${ans === 1 ? 'selected' : ''}" data-qid="\${q.new_q_id || q.q_id}" data-val="1">
                    \${this.icons.check} YES
                  </button>
                  <button class="h-btn no \${ans === 0 ? 'selected' : ''}" data-qid="\${q.new_q_id || q.q_id}" data-val="0">
                    \${this.icons.cross} NO
                  </button>
                \`}
              </div>
            </div>
          </div>
        \`;`;

code = code.replace(actionsBlock, newActions);

// Also fix q.new_q_id to fall back to q.q_id since master_282_rubric uses q.q_id
code = code.replace(/q\.new_q_id/g, "(q.new_q_id || q.q_id)");

fs.writeFileSync('site/js/render.js', code);
console.log("Patched render.js to support dynamic point scales!");
