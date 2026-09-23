const fs = require('fs');
let code = fs.readFileSync('site/js/app.js', 'utf-8');

const brokenBlock = `
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
    }, 350);`;

if (code.includes(brokenBlock)) {
    code = code.replace(brokenBlock, "");
    fs.writeFileSync('site/js/app.js', code);
    console.log("Removed broken block from updateUI!");
} else {
    console.log("Block not found.");
}
