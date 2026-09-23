import re

with open('site/js/render.js', 'r') as f:
    js = f.read()

old_logic = """
        const suggYes = q.ai_suggestion === 1;
        const suggNo = q.ai_suggestion === 0;

        const confNum = parseFloat(q.ai_confidence || 0);
"""

new_logic = """
        const confNum = parseFloat(q.ai_confidence || 0);
        let confText = (q.ai_confidence !== undefined && q.ai_confidence !== null) ? `${Math.round(q.ai_confidence * 100)}%` : 'N/A';
        
        let verdictText = 'N/A';
        if (q.ai_suggestion !== undefined && q.ai_suggestion !== null) {
            if (q.options && q.options.length > 0) {
                const optMatch = q.options.find(o => o.val === q.ai_suggestion);
                if (optMatch) verdictText = optMatch.label;
                else verdictText = q.ai_suggestion;
            } else {
                verdictText = q.ai_suggestion === 1 ? 'YES' : 'NO';
            }
        }
"""
js = js.replace(old_logic.strip(), new_logic.strip())

old_html = """
              <div class="h-ai-suggest ${tierClass}">
                ${this.icons.spark}
                <span class="verdict">${suggYes ? 'YES' : 'NO'}</span>
                <span class="divider"></span>
                <span class="score">${q.ai_confidence}</span>
              </div>
"""

new_html = """
              <div class="h-ai-suggest ${tierClass}">
                ${this.icons.spark}
                <span class="verdict">${verdictText}</span>
                <span class="divider"></span>
                <span class="score">${confText}</span>
              </div>
"""
js = js.replace(old_html.strip(), new_html.strip())

with open('site/js/render.js', 'w') as f:
    f.write(js)

with open('site/style.css', 'r') as f:
    css = f.read()

css = css.replace(
    'padding: 16px 24px; border-top: 1px solid var(--hairline); display: flex; justify-content: space-between; align-items: center;',
    'padding: 16px 24px; border-top: 1px solid var(--hairline); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;'
)

css = css.replace(
    '.h-actions { display: flex; gap: 12px; }',
    '.h-actions { display: flex; gap: 12px; flex-wrap: wrap; justify-content: flex-end; }'
)

css = css.replace(
    'padding: 10px 24px; border-radius: 8px;',
    'padding: 10px 16px; border-radius: 8px;'
)

with open('site/style.css', 'w') as f:
    f.write(css)

print("Patched UI successfully.")
