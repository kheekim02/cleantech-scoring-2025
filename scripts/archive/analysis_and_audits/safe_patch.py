import sys

with open('site/js/render.js', 'r') as f:
    lines = f.readlines()

new_lines = []
in_actions = False

new_logic = """              <div class="h-actions">
                ${q.options && q.options.length > 0 ? q.options.map(opt => {
                    const isSel = ans === opt.val ? 'selected' : '';
                    const cls = opt.val > 0 ? 'yes' : 'no';
                    let style = '';
                    if (opt.val > 0 && opt.val < 1) {
                        style = isSel ? 'background: var(--accent-orange); color: white; border-color: var(--accent-orange);' : 'color: var(--accent-orange); border-color: var(--accent-orange);';
                    }
                    return `
                      <button class="h-btn ${cls} ${isSel}" data-qid="${q.new_q_id || q.q_id}" data-val="${opt.val}" style="${style}">
                        ${opt.label}
                      </button>
                    `;
                }).join('') : `
                  <button class="h-btn yes ${ans === 1 ? 'selected' : ''}" data-qid="${q.new_q_id || q.q_id}" data-val="1">
                    ${this.icons.check} YES
                  </button>
                  <button class="h-btn no ${ans === 0 ? 'selected' : ''}" data-qid="${q.new_q_id || q.q_id}" data-val="0">
                    ${this.icons.cross} NO
                  </button>
                `}
              </div>
"""

skip_next = False
for idx, line in enumerate(lines):
    if skip_next:
        if '              </div>' in line and '</div>' in lines[idx+1] and '</div>' in lines[idx+2]:
            skip_next = False
            # Wait, line 197 is `              </div>`.
        continue

    if '<div class="h-actions">' in line:
        new_lines.append(new_logic)
        skip_next = True
    else:
        new_lines.append(line)

with open('site/js/render.js', 'w') as f:
    f.writelines(new_lines)
