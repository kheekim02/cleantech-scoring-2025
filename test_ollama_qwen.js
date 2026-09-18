const { Client } = require('pg');

async function extractWithOllama(textContext) {
    const url = "http://localhost:11434/api/chat";
    const payload = {
        model: "qwen3-vl:32b",
        format: "json",
        messages: [
            {
                role: "system",
                content: `You are an expert venture capital analyst evaluating a startup application.
CRITICAL: You are acting as a strict extraction engine. You must output a strictly valid JSON object. 

SCHEMA REQUIRED:
{
  "meta": { "id": "string", "name": "string", "cohort_year": 2025, "category": "string" },
  "ai_cats": {
    "BC": {
      "full_name": "Business Canvas", "total": 1, "passed": 1, "avg_conf": 0.90,
      "questions": [
         {
           "new_q_id": "BC_Q1", "text": "Value proposition metric", "type": "BINARY",
           "verdict": 1, "confidence": 0.85, "exact_verbatim_citation": "verbatim quote" 
         }
      ]
    }
  },
  "human_questions": []
}`
            },
            {
                role: "user",
                content: `Extract the required JSON from the following application text:\n\n${textContext}`
            }
        ],
        stream: false
    };

    console.log("Sending request to Ollama over SSH tunnel...");
    const startTime = Date.now();
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log(`Response received in ${(Date.now() - startTime) / 1000} seconds!`);
        return JSON.parse(data.message.content);
    } catch (e) {
        console.error("Ollama Extraction Failed:", e);
        return null;
    }
}

async function main() {
    console.log("Starting AI Extraction Small Batch Test using Remote Ollama (qwen3-vl:32b)...");
    
    // 2. Compile tiny text context
    const context = "Startup Name: SPARK. We are a hardware and AI software company reducing energy costs for commercial properties by up to 30%. Contact: Courtney Fieldman. Website: sparkai.tech.";

    // 3. LLM Extraction via local Ollama
    const llmPayload = await extractWithOllama(context);
    
    if (!llmPayload) {
        console.log("Failed to get JSON payload from LLM.");
        return;
    }

    console.log("Extracted Payload:");
    console.log(JSON.stringify(llmPayload, null, 2));

    // 4. Insert into Supabase
    console.log("Committing SPARK test payload to database...");
    
    if (!llmPayload.meta) llmPayload.meta = {};
    llmPayload.meta.id = "spark_inc";
    llmPayload.meta.name = "SPARK (Live Test)";

    const connectionString = "postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres?pgbouncer=true";
    const client = new Client({
        connectionString,
        ssl: { rejectUnauthorized: false }
    });

    try {
        await client.connect();
        await client.query(`
            INSERT INTO startup_extractions (startup_id, company_name, payload)
            VALUES ($1, $2, $3::jsonb)
            ON CONFLICT (startup_id) DO UPDATE SET payload = EXCLUDED.payload, ingested_at = NOW();
        `, ['spark_inc', 'SPARK (Live Test)', JSON.stringify(llmPayload)]);
        
        console.log("Successfully committed to Supabase! You should see 'SPARK (Live Test)' in the dropdown.");
    } catch (err) {
        console.error("DB Error:", err);
    } finally {
        await client.end();
    }
}

main();
