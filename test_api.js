const https = require('https');
https.get('https://merry-toffee-84c633.netlify.app/.netlify/functions/list-startups?judge_id=J-001&passcode=demo2025', (resp) => {
  let data = '';
  resp.on('data', (chunk) => { data += chunk; });
  resp.on('end', () => { console.log("Response:", data); });
}).on("error", (err) => { console.log("Error:", err.message); });
