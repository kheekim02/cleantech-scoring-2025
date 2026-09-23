const fs = require('fs');

// 1. UPDATE CSS
let css = fs.readFileSync('site/style.css', 'utf-8');
if (!css.includes('.h-card.collapsed')) {
css += `

/* Progressive Disclosure UX */
.h-card {
  transition: all 0.3s ease;
}
.h-card.collapsed {
  cursor: pointer;
  padding: 12px 16px;
  opacity: 0.6;
  background: var(--surface-sunk);
}
.h-card.collapsed:hover {
  opacity: 1;
  background: var(--surface-hover);
}
.h-card.collapsed .h-ai-suggest,
.h-card.collapsed .h-actions,
.h-card.collapsed .h-card-citation,
.h-card.collapsed .link-source {
  display: none !important;
}
.h-collapsed-summary {
  display: none;
  font-size: 13px;
  font-weight: 700;
  color: var(--accent-green);
  margin-top: 6px;
}
.h-card.collapsed .h-collapsed-summary {
  display: block;
}
.h-card.collapsed .h-card-title {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 4px;
  color: var(--text-muted);
}
`;
fs.writeFileSync('site/style.css', css);
console.log('Updated style.css');
}

// 2. UPDATE RENDER.JS
let render = fs.readFileSync('site/js/render.js', 'utf-8');

// A. Inject expandCard method
if (!render.includes('expandCard(qid')) {
  const expandMethod = `  expandCard(qid, citation) {
    document.querySelectorAll('.h-card').forEach(c => {
       if (c.querySelector('.h-btn.selected') && c.dataset.qid !== qid) {
           c.classList.add('collapsed');
       }
    });
    const target = document.querySelector(\`.h-card[data-qid="\${qid}"]\`);
    if (target) {
        target.classList.remove('collapsed');
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    // PDF Auto-Scrolling (Context Anchoring)
    if (citation && citation.length > 5) {
        const words = citation.replace(/[^a-zA-Z0-9 ]/g, '').split(' ').filter(w => w.length > 3).slice(0, 5).join(' ');
        if (words) {
            const searchStr = encodeURIComponent(words);
            document.querySelectorAll('.pdf-wrapper iframe').forEach(iframe => {
                const baseSrc = iframe.src.split('#')[0];
                iframe.src = \`\${baseSrc}#search=\${searchStr}&navpanes=0\`;
            });
        }
    }
  },

  updateQuestionState`;
  render = render.replace('  updateQuestionState', expandMethod);
}

// B. Inject collapsed state and dataset into renderRightPane
const oldCardStart = `<div class="h-card" id="card-\${q.new_q_id}" style="animation-delay: \${(idx * 40) + 100}ms;">`;
const newCardStart = `
        const isAnswered = ans !== undefined && ans !== null;
        const collapsedClass = isAnswered ? 'collapsed' : '';
        const summaryText = isAnswered ? \`Answered: \${ans} PTS\` : '';
        const safeCit = (q.verbatim_citation || '').replace(/"/g, '&quot;');
        
        hHtml += \`
          <div class="h-card \${collapsedClass}" id="card-\${q.new_q_id}" data-qid="\${q.new_q_id}" data-citation="\${safeCit}" style="animation-delay: \${(idx * 40) + 100}ms;">`;

render = render.replace(/hHtml \+= `\s*<div class="h-card" id="card-\$\{q\.new_q_id\}" style="animation-delay: \$\{\(idx \* 40\) \+ 100\}ms;">/g, newCardStart);

// C. Inject collapsed summary div
const oldTitle = `<div class="h-card-title">\${q.text}</div>`;
const newTitle = `<div class="h-card-title">\${q.text}</div>
              <div class="h-collapsed-summary h-summary-text">\${summaryText}</div>`;
render = render.replace(oldTitle, newTitle);
fs.writeFileSync('site/js/render.js', render);
console.log('Updated render.js');

// 3. UPDATE APP.JS
let app = fs.readFileSync('site/js/app.js', 'utf-8');

// A. Handle click on collapsed card
const oldClick = `const btn = e.target.closest('.h-btn');`;
const newClick = `const card = e.target.closest('.h-card.collapsed');
      if (card) {
        CTO.Render.expandCard(card.dataset.qid, card.dataset.citation);
        return;
      }
      
      const btn = e.target.closest('.h-btn');`;
app = app.replace(oldClick, newClick);

// B. Handle auto-collapse and advance on answer
const oldAnswerEnd = `this.refreshOverallProgress();
  },`;
const newAnswerEnd = `this.refreshOverallProgress();

    // Progressive Disclosure: auto-advance
    setTimeout(() => {
       const allCards = Array.from(document.querySelectorAll('.h-card'));
       const currentIdx = allCards.findIndex(c => c.dataset.qid === qid);
       if (currentIdx === -1) return;
       
       const currCard = allCards[currentIdx];
       currCard.classList.add('collapsed');
       const summary = currCard.querySelector('.h-summary-text');
       if (summary) summary.textContent = \`Answered: \${value} PTS\`;

       // Find next unanswered
       for (let i = currentIdx + 1; i < allCards.length; i++) {
           if (!allCards[i].querySelector('.h-btn.selected')) {
               CTO.Render.expandCard(allCards[i].dataset.qid, allCards[i].dataset.citation);
               break;
           }
       }
    }, 350);
  },`;
app = app.replace(oldAnswerEnd, newAnswerEnd);

fs.writeFileSync('site/js/app.js', app);
console.log('Updated app.js');
