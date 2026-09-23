const fs = require('fs');
let code = fs.readFileSync('site/js/app.js', 'utf-8');
code = code.replace('const val = parseInt(btn.dataset.val, 10);', 'const val = parseFloat(btn.dataset.val);');
fs.writeFileSync('site/js/app.js', code);
console.log('Patched app.js');
