const { Client } = require('pg');

async function main() {
    const connectionString = "postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres?pgbouncer=true";
    const client = new Client({
        connectionString,
        ssl: { rejectUnauthorized: false }
    });

    try {
        await client.connect();
        
        const dummyPayload = {
            "meta": {
                "id": "spark_inc",
                "name": "SPARK (Live Test)",
                "cohort_year": 2025,
                "category": "Energy Intelligence"
            },
            "document": {
                "title": "SPARK Executive Summary",
                "sections": [
                    {
                        "cat_code": "BC",
                        "heading": "Value Proposition",
                        "text": "SPARK helps commercial property operators cut rising energy costs and protect asset value through <span class=\"cite highlight\">AI-driven energy intelligence</span>.",
                        "extractions": []
                    }
                ]
            },
            "ai_cats": {
                "BC": {
                    "full_name": "Business Canvas",
                    "total": 1,
                    "passed": 1,
                    "avg_conf": 0.95,
                    "questions": [
                        {
                            "new_q_id": "BC_Q1",
                            "text": "AI-driven value prop identified",
                            "type": "BINARY",
                            "verdict": 1,
                            "confidence": 0.95,
                            "citation": "AI-driven energy intelligence"
                        }
                    ]
                }
            },
            "human_questions": []
        };

        await client.query(`
            INSERT INTO startup_extractions (startup_id, company_name, payload)
            VALUES ($1, $2, $3::jsonb)
            ON CONFLICT (startup_id) DO UPDATE SET payload = EXCLUDED.payload, ingested_at = NOW();
        `, ['spark_inc', 'SPARK (Live Test)', JSON.stringify(dummyPayload)]);
        
        console.log("Successfully committed 'SPARK (Live Test)' to Supabase!");
    } catch (err) {
        console.error("DB Error:", err);
    } finally {
        await client.end();
    }
}

main();
