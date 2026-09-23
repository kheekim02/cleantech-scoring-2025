const fs = require('fs');
let code = fs.readFileSync('site/js/app.js', 'utf-8');

const anchor = `    // Update step pill counter surgically
    const sData = this.state.startups[this.state.activeStartupId];
    const catCode = this.state.categories[this.state.currentStepIndex];
    const hqs = sData.human_questions.filter(q => q.cat_code === catCode);
    const answeredStep = hqs.filter(q => sEval.humanAnswers[q.new_q_id] !== undefined).length;
    CTO.Render.updateProgressText(answeredStep, hqs.length);

    // REC 5: Optimistic Sync
    this.saveState();
    this.state.syncQueue.push({ qid, value, timestamp: Date.now() });
  },`;

const newCode = `    // Update step pill counter surgically
    const sData = this.state.startups[this.state.activeStartupId];
    const catCode = this.state.categories[this.state.currentStepIndex];
    const hqs = sData.human_questions.filter(q => q.cat_code === catCode);
    const answeredStep = hqs.filter(q => sEval.humanAnswers[q.new_q_id] !== undefined).length;
    CTO.Render.updateProgressText(answeredStep, hqs.length);

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

    // REC 5: Optimistic Sync
    this.saveState();
    this.state.syncQueue.push({ qid, value, timestamp: Date.now() });
  },`;

if (code.includes(anchor)) {
    code = code.replace(anchor, newCode);
    fs.writeFileSync('site/js/app.js', code);
    console.log("Injected auto-advance into answerHuman successfully!");
} else {
    console.log("Anchor not found.");
}
