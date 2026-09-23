const http = require('http');
http.get('http://localhost:8888/api/get-startup?id=SolarPure_Inc', (resp) => {
  let data = '';
  resp.on('data', (chunk) => { data += chunk; });
  resp.on('end', () => {
    try {
        const json = JSON.parse(data);
        console.log("Keys:", Object.keys(json));
        console.log("Human Qs type:", typeof json.human_questions, Array.isArray(json.human_questions));
        if (json.human_questions && json.human_questions.length > 0) {
            console.log("Q1:", json.human_questions[0].q_id || json.human_questions[0].new_q_id);
        }
        console.log("Document:", !!json.document);
    } catch(e) {
        console.log("JSON Parse Error:", e);
        console.log(data);
    }
  });
}).on("error", (err) => {
  console.log("Error: " + err.message);
});
