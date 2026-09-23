const fs = require('fs');
let code = fs.readFileSync('api/list-startups.js', 'utf8');

code = code.replace(
  "const listQuery = await client.query('SELECT startup_id as id, company_name as name FROM startup_extractions ORDER BY company_name ASC');",
  "const listQuery = await client.query('SELECT s.startup_id as id, s.company_name as name FROM startup_extractions s INNER JOIN judge_assignments ja ON s.startup_id = ja.startup_id WHERE ja.judge_id = $1 ORDER BY s.company_name ASC', [judge_id]);"
);

fs.writeFileSync('api/list-startups.js', code);
console.log("Patched list-startups.js");
