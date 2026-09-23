const fs = require('fs');
let appJs = fs.readFileSync('site/js/app.js', 'utf8');
appJs = appJs.replace(
    'fetch(`/api/get-startup?id=${this.state.activeStartupId}&judge_id=${this.currentUser.id}&passcode=${this.currentUser.passcode}`)',
    'fetch(`/api/get-startup?id=${encodeURIComponent(this.state.activeStartupId)}&judge_id=${encodeURIComponent(this.currentUser.id)}&passcode=${encodeURIComponent(this.currentUser.passcode)}`)'
);
fs.writeFileSync('site/js/app.js', appJs);
console.log("Patched app.js encoding!");
