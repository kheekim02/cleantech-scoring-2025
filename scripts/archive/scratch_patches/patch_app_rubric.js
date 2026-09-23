const fs = require('fs');
let appCode = fs.readFileSync('site/js/app.js', 'utf8');

const rubricLogic = `
      const rubricLink = e.target.closest('.view-rubric');
      if (rubricLink) {
        e.preventDefault();
        this.openRubricModal(rubricLink.dataset.qid);
        return;
      }
`;

appCode = appCode.replace(
  `// Toggle citation logic for PDFs`,
  `// Toggle rubric modal
${rubricLogic}
      // Toggle citation logic for PDFs`
);

const openRubricModalFunc = `
  openRubricModal(qid) {
    const modal = document.getElementById('rubric-modal');
    const title = document.getElementById('rubric-modal-title');
    const body = document.getElementById('rubric-modal-body');
    
    let rubricContent = '';
    
    // Hardcoded tables parsed from markdown for rapid reference (0 - 1 point scale)
    if (qid === 'BC_Q1') {
      title.textContent = 'Value Proposition Scoring (BC_Q1)';
      rubricContent = \`
      <div style="margin-bottom: 12px; font-size: 13px; color: var(--text-muted);">
        Official scoring criteria mapped to the <strong>0 – 1 Scale</strong>:
      </div>
      <table style="width: 100%; border-collapse: collapse; text-align: left;">
        <thead>
          <tr style="background: var(--surface-sunk);">
            <th style="padding: 10px; border: 1px solid var(--border); width: 110px;">Score</th>
            <th style="padding: 10px; border: 1px solid var(--border);">Example Justification / Content</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 4px; border: 1px solid #cbd5e1; font-size: 12px;">0 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Dirty water solution, we remove the waste just like other companies."</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fff7ed; color: #c2410c; padding: 3px 8px; border-radius: 4px; border: 1px solid #fed7aa; font-size: 12px;">0.25 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Municipalities, industrial facilities, and commercial establishments grappling with diverse wastewater treatment requirements."</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fef9c3; color: #854d0e; padding: 3px 8px; border-radius: 4px; border: 1px solid #fde047; font-size: 12px;">0.5 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Save customer money while reducing carbon footprint, help meet upcoming regulations and requirements set by industry."</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f0fdf4; color: #15803d; padding: 3px 8px; border-radius: 4px; border: 1px solid #bbf7d0; font-size: 12px;">0.75 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Easy integratable filtration technology, save 60% on costs, creates a more eco friendly and efficient wastewater process, cost competitive price with reliable service."</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #ecfdf5; color: #047857; padding: 3px 8px; border-radius: 4px; border: 1px solid #6ee7b7; font-size: 12px;">1 PT</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Advanced filtration membrane designed to effectively remove up to 95% of contaminants and pollutants from wastewater, help reduce WTTP energy costs of up to 60%... provide a more cost effective way to deal with your wastewater than market alternatives."</td>
          </tr>
        </tbody>
      </table>
      \`;
    } else if (qid === 'BC_Q2') {
      title.textContent = 'Customer Segments Scoring (BC_Q2)';
      rubricContent = \`
      <div style="margin-bottom: 12px; font-size: 13px; color: var(--text-muted);">
        Official scoring criteria mapped to the <strong>0 – 1 Scale</strong>:
      </div>
      <table style="width: 100%; border-collapse: collapse; text-align: left;">
        <thead>
          <tr style="background: var(--surface-sunk);">
            <th style="padding: 10px; border: 1px solid var(--border); width: 110px;">Score</th>
            <th style="padding: 10px; border: 1px solid var(--border);">Example Justification / Content</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 4px; border: 1px solid #cbd5e1; font-size: 12px;">0 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Businesses who need to deal with wastewater"</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fff7ed; color: #c2410c; padding: 3px 8px; border-radius: 4px; border: 1px solid #fed7aa; font-size: 12px;">0.25 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Industrial waste benefaction, chemical producers, power companies, manufacturing companies, and biochemical industries"</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fef9c3; color: #854d0e; padding: 3px 8px; border-radius: 4px; border: 1px solid #fde047; font-size: 12px;">0.5 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Industrial waste benefaction Chemical producers Power companies... Manufacturing companies Biochemical industries"</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f0fdf4; color: #15803d; padding: 3px 8px; border-radius: 4px; border: 1px solid #bbf7d0; font-size: 12px;">0.75 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Domestic US Corporations: chief sustainability officer And health and safety. Communities: Waste management & economic Development"</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #ecfdf5; color: #047857; padding: 3px 8px; border-radius: 4px; border: 1px solid #6ee7b7; font-size: 12px;">1 PT</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">"Oil and gas: Refinery wastewater Treatment Hydraulic fracturing... Commercial Properties: Hotels, Restaurants... Agriculture: Fertilizer production Livestock operations Irrigation water reuse"</td>
          </tr>
        </tbody>
      </table>
      \`;
    } else if (qid === 'BC_Q3') {
      title.textContent = 'Customer Interviews Scoring (BC_Q3)';
      rubricContent = \`
      <div style="margin-bottom: 12px; font-size: 13px; color: var(--text-muted);">
        Official scoring criteria mapped to the <strong>0 – 1 Scale</strong>:
      </div>
      <table style="width: 100%; border-collapse: collapse; text-align: left;">
        <thead>
          <tr style="background: var(--surface-sunk);">
            <th style="padding: 10px; border: 1px solid var(--border); width: 110px;">Score</th>
            <th style="padding: 10px; border: 1px solid var(--border);">Interview Threshold & Evidence</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 4px; border: 1px solid #cbd5e1; font-size: 12px;">0 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">0 customer interviews documented; no customer discovery evidence found.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fff7ed; color: #c2410c; padding: 3px 8px; border-radius: 4px; border: 1px solid #fed7aa; font-size: 12px;">0.25 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">1 customer interview conducted or vague anecdotal customer interactions mentioned.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fef9c3; color: #854d0e; padding: 3px 8px; border-radius: 4px; border: 1px solid #fde047; font-size: 12px;">0.5 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">2–3 customer interviews documented with basic qualitative feedback.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f0fdf4; color: #15803d; padding: 3px 8px; border-radius: 4px; border: 1px solid #bbf7d0; font-size: 12px;">0.75 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">4 customer interviews documented with structured insights and segment context.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #ecfdf5; color: #047857; padding: 3px 8px; border-radius: 4px; border: 1px solid #6ee7b7; font-size: 12px;">1 PT</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);">5 or more customer interviews documented with names/titles, learnings, and quotes.</td>
          </tr>
        </tbody>
      </table>
      \`;
    } else if (qid === 'BC_Q4') {
      title.textContent = 'Big Sections Scoring (BC_Q4)';
      rubricContent = \`
      <div style="margin-bottom: 12px; font-size: 13px; color: var(--text-muted);">
        Official scoring criteria mapped to the <strong>0 – 1 Scale</strong>:
      </div>
      <p style="margin-top: 8px; margin-bottom: 10px; font-size: 13px;"><strong>Key BMC Sections:</strong> Value Propositions, Customer Segments, Channels, Customer Relationships, Revenue Streams</p>
      <table style="width: 100%; border-collapse: collapse; text-align: left;">
        <thead>
          <tr style="background: var(--surface-sunk);">
            <th style="padding: 10px; border: 1px solid var(--border); width: 110px;">Score</th>
            <th style="padding: 10px; border: 1px solid var(--border);">Evaluation Standard & Criteria</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 4px; border: 1px solid #cbd5e1; font-size: 12px;">0 – 0.25 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);"><strong>Vague generalities:</strong> Minimal detail or generic placeholders (e.g. "social media", "branding", "businesses") with no specific execution plan.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fef9c3; color: #854d0e; padding: 3px 8px; border-radius: 4px; border: 1px solid #fde047; font-size: 12px;">0.5 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);"><strong>Moderate detail:</strong> Includes specific mediums (e.g. "Trade show participation", direct sales outreach) but lacks granular segmentation, pricing, or relationship models.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #ecfdf5; color: #047857; padding: 3px 8px; border-radius: 4px; border: 1px solid #6ee7b7; font-size: 12px;">0.75 – 1 PT</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);"><strong>Extremely detailed & articulate:</strong> Granular pricing ("Starter kit: $1,000", "Annual O&M service $2,000"), distinct relationships (short-term transactional vs long-term SLA contracts), and robust customer acquisition channels.</td>
          </tr>
        </tbody>
      </table>
      \`;
    } else if (qid === 'BC_Q5') {
      title.textContent = 'Small Sections Scoring (BC_Q5)';
      rubricContent = \`
      <div style="margin-bottom: 12px; font-size: 13px; color: var(--text-muted);">
        Official scoring criteria mapped to the <strong>0 – 1 Scale</strong>:
      </div>
      <p style="margin-top: 8px; margin-bottom: 10px; font-size: 13px;"><strong>Key BMC Sections:</strong> Key Partners, Key Activities, Key Resources, Cost Structure</p>
      <table style="width: 100%; border-collapse: collapse; text-align: left;">
        <thead>
          <tr style="background: var(--surface-sunk);">
            <th style="padding: 10px; border: 1px solid var(--border); width: 110px;">Score</th>
            <th style="padding: 10px; border: 1px solid var(--border);">Evaluation Standard & Criteria</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #f1f5f9; color: #475569; padding: 3px 8px; border-radius: 4px; border: 1px solid #cbd5e1; font-size: 12px;">0 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);"><strong>Generic or placeholder:</strong> Superficial descriptions (e.g. "The cost to manufacture", "Money and employees") with no breakdown of cost drivers or core partners.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #fef9c3; color: #854d0e; padding: 3px 8px; border-radius: 4px; border: 1px solid #fde047; font-size: 12px;">0.5 PTS</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);"><strong>Partially specified:</strong> Mentions some specific resources or partner entities (e.g. "Columbia university lab", fabrication partner) but lacks cost allocation or resource depth.</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid var(--border); font-weight: bold; white-space: nowrap;"><span style="background: #ecfdf5; color: #047857; padding: 3px 8px; border-radius: 4px; border: 1px solid #6ee7b7; font-size: 12px;">1 PT</span></td>
            <td style="padding: 10px; border: 1px solid var(--border);"><strong>Exhaustive & granular:</strong> Specific breakdowns across partners and activities ("M&E costs for prototype", "3rd party lab validation", "Local permitting requirements", "Unit Operations vs Ammonia Sales").</td>
          </tr>
        </tbody>
      </table>
      \`;
    }
    
    body.innerHTML = rubricContent;
    modal.style.display = 'flex';
  },
`;

// Add openRubricModal to CTO.App
appCode = appCode.replace(
  `  updateUI() {`,
  `${openRubricModalFunc}\n  updateUI() {`
);

// Add event listener to close modal
const closeModalCode = `
    document.getElementById('rubric-modal-close').addEventListener('click', () => {
      document.getElementById('rubric-modal').style.display = 'none';
    });
    document.getElementById('rubric-modal').addEventListener('click', (e) => {
      if (e.target.id === 'rubric-modal') {
        e.target.style.display = 'none';
      }
    });
`;

appCode = appCode.replace(
  `    document.getElementById('submit-modal').addEventListener('click', (e) => {`,
  `${closeModalCode}\n    document.getElementById('submit-modal').addEventListener('click', (e) => {`
);

fs.writeFileSync('site/js/app.js', appCode);
console.log("Patched app.js for modals");
