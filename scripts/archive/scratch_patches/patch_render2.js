const fs = require('fs');
let code = fs.readFileSync('site/js/render.js', 'utf-8');

const oldFn = `  updateQuestionState(qid, value) {
    const btnYes = document.querySelector(\`.h-btn.yes[data-qid="\${qid}"]\`);
    const btnNo = document.querySelector(\`.h-btn.no[data-qid="\${qid}"]\`);
    if (!btnYes || !btnNo) return;

    btnYes.classList.remove('selected');
    btnNo.classList.remove('selected');

    if (value === 1) btnYes.classList.add('selected');
    if (value === 0) btnNo.classList.add('selected');
  },`;

const newFn = `  updateQuestionState(qid, value) {
    const btns = document.querySelectorAll(\`.h-btn[data-qid="\${qid}"]\`);
    btns.forEach(btn => btn.classList.remove('selected'));
    if (value !== null && value !== undefined) {
      const selectedBtn = Array.from(btns).find(b => parseFloat(b.dataset.val) === value);
      if (selectedBtn) selectedBtn.classList.add('selected');
    }
  },`;

code = code.replace(oldFn, newFn);
fs.writeFileSync('site/js/render.js', code);
console.log('Patched render.js updateQuestionState');
