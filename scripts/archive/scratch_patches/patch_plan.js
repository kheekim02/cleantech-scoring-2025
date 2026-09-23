const fs = require('fs');

let plan = fs.readFileSync('/Users/geoffrey/.gemini/antigravity/brain/50b6e66f-df5c-492d-ac2c-8d017d39cdda/implementation_plan.md', 'utf8');

const fallbackSection = `
## Anti-Hallucination Fallback & Safety Plan
To guarantee the UI never breaks due to LLM hallucinations (e.g., outputting "XYZ" or a full conversational sentence instead of a category code), the extraction engine will employ a multi-layered safety circuit:
1. **Strict Schema Validation:** The Python extraction daemon will rigorously check the model's output against the exact 10 approved array values: \`['BC', 'ES', 'F', 'IP', 'IS', 'L', 'M', 'PMF', 'T', 'TP']\`. 
2. **Retry Circuit Breaker:** If the model hallucinates an invalid string, the system will automatically wipe the context and retry the prompt up to 3 times with temperature set strictly to 0.0.
3. **Heuristic Regex Fallback:** If the model fails the schema validation 3 times, or if the Ollama API times out, the system will seamlessly fall back to our patched legacy \`fix_pdfs.js\` regex logic (which correctly handles edge cases like \`m7\` -> \`L\`). 
4. **Audit Logging:** The system will output a deterministic mapping file (\`ai_pdf_mapping.json\`) that flags which documents were classified via AI and which were forced into the heuristic fallback for later review.

## Proposed Architecture
`;

plan = plan.replace('## Proposed Architecture', fallbackSection);
fs.writeFileSync('/Users/geoffrey/.gemini/antigravity/brain/50b6e66f-df5c-492d-ac2c-8d017d39cdda/implementation_plan.md', plan);
console.log("Patched implementation plan with fallback strategy.");
