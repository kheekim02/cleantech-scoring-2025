import re

with open('site/js/render.js', 'r') as f:
    js = f.read()

# The block to remove:
old_block = """
                    let style = '';
                    if (opt.val > 0 && opt.val < 1) {
                        style = isSel ? 'background: var(--accent-orange); color: white; border-color: var(--accent-orange);' : 'color: var(--accent-orange); border-color: var(--accent-orange);';
                    }
                    return `
                      <button class="h-btn ${cls} ${isSel}" data-qid="${q.new_q_id || q.q_id}" data-val="${opt.val}" style="${style}">
                        ${opt.label}
                      </button>
                    `;
"""

new_block = """
                    const style = '';
                    return `
                      <button class="h-btn ${cls} ${isSel}" data-qid="${q.new_q_id || q.q_id}" data-val="${opt.val}" style="${style}">
                        ${opt.label}
                      </button>
                    `;
"""

if old_block.strip() in js:
    js = js.replace(old_block.strip(), new_block.strip())
    with open('site/js/render.js', 'w') as f:
        f.write(js)
    print("Patched button styles!")
else:
    print("Could not find block.")
