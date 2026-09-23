const fs = require('fs');
let code = fs.readFileSync('site/js/app.js', 'utf-8');

const oldSyntax = `const card = e.target.closest('.h-card.collapsed');
      if (card) {
        CTO.Render.expandCard(card.dataset.qid, card.dataset.citation);
        return;
      }`;
      
const newSyntax = `const collapsedCard = e.target.closest('.h-card.collapsed');
      if (collapsedCard) {
        CTO.Render.expandCard(collapsedCard.dataset.qid, collapsedCard.dataset.citation);
        return;
      }`;

code = code.replace(oldSyntax, newSyntax);
fs.writeFileSync('site/js/app.js', code);
console.log('Patched app.js syntax');
