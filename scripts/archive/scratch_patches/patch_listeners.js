const fs = require('fs');
let appJs = fs.readFileSync('site/js/app.js', 'utf8');

// Add a flag to prevent multiple event listeners
if (!appJs.includes('if (this._listenersSetup) return;')) {
    appJs = appJs.replace(
        'setupListeners() {', 
        'setupListeners() {\n    if (this._listenersSetup) return;\n    this._listenersSetup = true;'
    );
    fs.writeFileSync('site/js/app.js', appJs);
    console.log("Patched setupListeners to run exactly once!");
} else {
    console.log("Already patched.");
}
