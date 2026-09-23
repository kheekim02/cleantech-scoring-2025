const fs = require('fs');
let code = fs.readFileSync('site/js/render.js', 'utf-8');

const oldEnd = `    hContainer.innerHTML = hHtml;
  },`;

const newEnd = `    hContainer.innerHTML = hHtml;
    
    // Progressive Disclosure Init: Collapse all unanswered except the first one
    setTimeout(() => {
       const allUnanswered = Array.from(document.querySelectorAll('.h-card:not(.collapsed)'));
       allUnanswered.forEach((c, index) => {
           if (index > 0) c.classList.add('collapsed');
       });
       if (allUnanswered.length > 0) {
           allUnanswered[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
       }
    }, 100);
  },`;

code = code.replace(oldEnd, newEnd);
fs.writeFileSync('site/js/render.js', code);
console.log('Patched init disclosure');
