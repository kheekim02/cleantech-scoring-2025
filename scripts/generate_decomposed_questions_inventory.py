import pandas as pd
import numpy as np

meta = pd.read_csv('data/processed/master_questions_metadata.csv')

inventory = []

# --- 1. Business Canvas (5 -> 13) ---
bc_items = [
    ('BC_Q1', 'BC_Q1a', 'BINARY', 'AI', 'Value proposition states specific, quantified performance improvement or cost savings metric'),
    ('BC_Q1', 'BC_Q1b', 'BINARY', 'AI', 'Value proposition explicitly identifies incumbent technology or baseline alternative being replaced'),
    ('BC_Q2', 'BC_Q2a', 'BINARY', 'AI', 'Specific target customer segment or institutional buyer category explicitly named'),
    ('BC_Q2', 'BC_Q2b', 'BINARY', 'AI', 'Defines at least one quantifiable customer attribute (size, fleet, expenditure, geography)'),
    ('BC_Q2', 'BC_Q2c', 'BINARY', 'AI', 'Specific internal decision-maker title or economic buyer identified'),
    ('BC_Q3', 'BC_Q3a', 'BINARY', 'AI', 'States conducting discovery interviews with 5 or more prospective customers'),
    ('BC_Q3', 'BC_Q3b', 'BINARY', 'AI', 'Cites specific direct quotes, synthesis, or feedback derived from customer interviews'),
    ('BC_Q3', 'BC_Q3_val', 'INTEGER', 'AI', 'Total count of customer discovery interviews conducted'),
    ('BC_Q4', 'BC_Q4a', 'BINARY', 'AI', 'Value Propositions block of the BMC completed with text'),
    ('BC_Q4', 'BC_Q4b', 'BINARY', 'AI', 'Customer Segments block completed with text'),
    ('BC_Q4', 'BC_Q4c', 'BINARY', 'AI', 'Revenue Streams block completed with text'),
    ('BC_Q5', 'BC_Q5a', 'BINARY', 'AI', 'Key Partners and Key Activities blocks completed'),
    ('BC_Q5', 'BC_Q5b', 'BINARY', 'AI', 'Cost Structure and Key Resources blocks completed')
]
for orig, new_id, qtype, role, text in bc_items:
    inventory.append({'category': '1. Business Canvas', 'cat_code': 'BC', 'orig_q_id': orig, 'new_q_id': new_id, 'type': qtype, 'verification_role': role, 'text': text})

# --- 2. Impact/ Sustainability (10 -> 13) ---
is_items = [
    ('IS_Q1', 'IS_Q1a', 'BINARY', 'AI', 'Company purpose directly addresses at least 1 UN Sustainable Development Goal'),
    ('IS_Q1', 'IS_Q1b', 'BINARY', 'AI', 'Company purpose directly addresses 2 or more UN SDGs'),
    ('IS_Q2', 'IS_Q2a', 'BINARY', 'AI', 'Maps at least 1 applicable SDG across company value chain'),
    ('IS_Q2', 'IS_Q2b', 'BINARY', 'AI', 'Maps 2 or more applicable SDGs across company value chain'),
    ('IS_Q3', 'IS_Q3', 'BINARY', 'AI', 'Addresses whether impact priority is mitigation, resilience/adaptation, or both'),
    ('IS_Q4', 'IS_Q4', 'BINARY', 'AI', 'Quantifies environmental/efficiency advantage using numerical metrics against baseline'),
    ('IS_Q5', 'IS_Q5a', 'BINARY', 'HUMAN', 'Describes company culture, mission values, and social purpose'),
    ('IS_Q5', 'IS_Q5b', 'BINARY', 'AI', 'Documents policy/plan for reinvestment or allocation of company profits'),
    ('IS_Q6', 'IS_Q6', 'BINARY', 'AI', 'Lists formal certification by environmental or sustainability organizations'),
    ('IS_Q7', 'IS_Q7', 'BINARY', 'AI', 'Identifies applicable environmental/operating regulations (or confirms none exist)'),
    ('IS_Q8', 'IS_Q8', 'BINARY', 'AI', 'Identifies environmental or social risks of materials (toxicity, recyclability, supply)'),
    ('IS_Q9', 'IS_Q9a', 'BINARY', 'AI', 'Identifies largest sources of energy consumption in operations'),
    ('IS_Q9', 'IS_Q9b', 'BINARY', 'AI', 'Identifies largest sources of land use in operations'),
    ('IS_Q10', 'IS_Q10', 'BINARY', 'AI', 'Categorizes operational waste streams by percentage')
]
# Wait, let's see how many is_items: 14? Let's check: IS_Q9 split into 2 makes 14.
for orig, new_id, qtype, role, text in is_items:
    inventory.append({'category': '2. Impact/ Sustainability', 'cat_code': 'IS', 'orig_q_id': orig, 'new_q_id': new_id, 'type': qtype, 'verification_role': role, 'text': text})

# --- 3. Product/ Market Fit (34 -> 36) ---
pmf_meta = meta[meta['category_section'].str.startswith('3.')]
for _, r in pmf_meta.iterrows():
    qid = f"PMF_Q{r['question_number_in_cat']}"
    qnum = r['question_number_in_cat']
    qtext = r['question_text']
    
    if qnum == 1:
        inventory.append({'category': '3. Product/ Market Fit', 'cat_code': 'PMF', 'orig_q_id': qid, 'new_q_id': 'PMF_Q1a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Startup has determined and named a specific target market'})
        inventory.append({'category': '3. Product/ Market Fit', 'cat_code': 'PMF', 'orig_q_id': qid, 'new_q_id': 'PMF_Q1b', 'type': 'BINARY', 'verification_role': 'HUMAN', 'text': 'Startup articulates why it is a superior option compared to alternatives'})
    elif qnum == 9:
        inventory.append({'category': '3. Product/ Market Fit', 'cat_code': 'PMF', 'orig_q_id': qid, 'new_q_id': 'PMF_Q9a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Articulates specific insight or finding learned from customer research'})
        inventory.append({'category': '3. Product/ Market Fit', 'cat_code': 'PMF', 'orig_q_id': qid, 'new_q_id': 'PMF_Q9b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Identifies concrete change made to strategy or product experience based on research'})
    else:
        # Check if subjective
        role = 'HUMAN' if r['is_objective'] == 0 else 'AI'
        inventory.append({'category': '3. Product/ Market Fit', 'cat_code': 'PMF', 'orig_q_id': qid, 'new_q_id': qid, 'type': 'BINARY', 'verification_role': role, 'text': qtext})

# --- 4. Markets (12 -> 14) ---
m_meta = meta[meta['category_section'].str.startswith('4.')]
for _, r in m_meta.iterrows():
    qid = f"M_Q{r['question_number_in_cat']}"
    qnum = r['question_number_in_cat']
    qtext = r['question_text']
    
    if qnum == 1:
        inventory.append({'category': '4. Markets', 'cat_code': 'M', 'orig_q_id': qid, 'new_q_id': 'M_Q1a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Identifies commercial distribution channels for product delivery'})
        inventory.append({'category': '4. Markets', 'cat_code': 'M', 'orig_q_id': qid, 'new_q_id': 'M_Q1b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Identifies media, marketing, or industry channels for customer acquisition'})
    elif qnum == 11:
        inventory.append({'category': '4. Markets', 'cat_code': 'M', 'orig_q_id': qid, 'new_q_id': 'M_Q11a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Provides visual or scheduled product roadmap across future quarters/years'})
        inventory.append({'category': '4. Markets', 'cat_code': 'M', 'orig_q_id': qid, 'new_q_id': 'M_Q11b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Provides technical or commercial rationale for feature sequencing'})
    else:
        role = 'HUMAN' if r['is_objective'] == 0 else 'AI'
        inventory.append({'category': '4. Markets', 'cat_code': 'M', 'orig_q_id': qid, 'new_q_id': qid, 'type': 'BINARY', 'verification_role': role, 'text': qtext})

# --- 5. Tech and Product (16 -> 26) ---
tp_meta = meta[meta['category_section'].str.startswith('5.')]
for _, r in tp_meta.iterrows():
    qid = f"TP_Q{r['question_number_in_cat']}"
    qnum = r['question_number_in_cat']
    qtext = r['question_text']
    
    if qnum == 5:
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q5a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Filed at least 1 patent application (utility, non-provisional, or PCT)'})
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q5b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Filed 3 or more patent applications'})
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q5c', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Patent application serial numbers explicitly listed in materials'})
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q5_val', 'type': 'INTEGER', 'verification_role': 'AI', 'text': 'Total count of filed patent applications'})
    elif qnum == 6:
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q6a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Owns or exclusively licenses at least 1 granted patent'})
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q6b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Owns or exclusively licenses 3 or more granted patents'})
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q6_val', 'type': 'INTEGER', 'verification_role': 'AI', 'text': 'Total count of granted patents'})
    elif qnum == 7:
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q7a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Technology validated in laboratory environment (TRL >= 4)'})
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q7b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Integrated system demonstrated in operational field environment (TRL >= 7)'})
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q7c', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'TRL validated by external 3rd-party engineering report or partner letter'})
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q7_val', 'type': 'INTEGER', 'verification_role': 'AI', 'text': 'Explicitly stated Technology Readiness Level (1-9)'})
    elif qnum == 12:
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q12a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Engaged an independent 3rd-party validation entity'})
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q12b', 'type': 'BINARY', 'verification_role': 'AI', 'text': '3rd-party technical validation testing completed with formal documentation delivered'})
    elif qnum == 15:
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q15a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Product certification (UL, ASTM) obtained or confirmed not needed'})
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': 'TP_Q15b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Formal written roadmap/testing plan to achieve required certifications'})
    elif qnum == 16:
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': qid, 'type': 'BINARY', 'verification_role': 'HUMAN', 'text': qtext})
    else:
        inventory.append({'category': '5. Tech and Product', 'cat_code': 'TP', 'orig_q_id': qid, 'new_q_id': qid, 'type': 'BINARY', 'verification_role': 'AI', 'text': qtext})

# --- 6. Financials (29 -> 41) ---
f_meta = meta[meta['category_section'].str.startswith('6.')]
for _, r in f_meta.iterrows():
    qid = f"F_Q{r['question_number_in_cat']}"
    qnum = r['question_number_in_cat']
    qtext = r['question_text']
    
    if qnum == 2:
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q2a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Operating budget includes projected revenues'})
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q2b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Operating budget includes projected operating expenses'})
    elif qnum == 3:
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q3a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Revenues broken down by individual customer stream, SKU, or contract'})
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q3b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Expenses categorized by functional line item (COGS, R&D, S&M, G&A)'})
    elif qnum == 6:
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q6a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Operating budget includes at least 3 years of pro-forma projections'})
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q6b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Operating budget includes 5 or more years of pro-forma projections'})
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q6c', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Model projects market share or unit volume adoption alongside dollars'})
    elif qnum == 10:
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q10a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Capital budget includes revenues broken down by project'})
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q10b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Capital budget includes expenses broken down by project'})
    elif qnum == 11:
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q11a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Project revenues identified by source or contract line item'})
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q11b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Project expenses identified by category line item'})
    elif qnum == 14:
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q14a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Capital budget includes 3-year multi-project projections'})
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q14b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Capital budget includes 5-year multi-project projections'})
    elif qnum == 16:
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q16a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Profit and loss statement (P&L / Income Statement) provided'})
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q16b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Balance sheet provided'})
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q16c', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Cash flow statement provided'})
    elif qnum == 19:
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q19a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Return on equity (ROE) calculated in financial model'})
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q19b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Return on assets (ROA) calculated in financial model'})
    elif qnum == 20:
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q20a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Projections for Return on Equity (ROE) provided for 3+ years'})
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q20b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Projections for Return on Assets (ROA) provided for 3+ years'})
    elif qnum == 27:
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q27a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Sales or revenue data projected for at least 3 years'})
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': 'F_Q27b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Sales or revenue data projected for 5 or more years'})
    else:
        inventory.append({'category': '6. Financials', 'cat_code': 'F', 'orig_q_id': qid, 'new_q_id': qid, 'type': 'BINARY', 'verification_role': 'AI', 'text': qtext})

# --- 7. Legal (53 -> 54) ---
l_meta = meta[meta['category_section'].str.startswith('7.')]
for _, r in l_meta.iterrows():
    qid = f"L_Q{r['question_number_in_cat']}"
    qnum = r['question_number_in_cat']
    qtext = r['question_text']
    
    if qnum == 9:
        inventory.append({'category': '7. Legal', 'cat_code': 'L', 'orig_q_id': qid, 'new_q_id': 'L_Q9a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Conducted formal trademark clearance search with the USPTO'})
        inventory.append({'category': '7. Legal', 'cat_code': 'L', 'orig_q_id': qid, 'new_q_id': 'L_Q9b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Filed formal trademark application for primary commercial brand name'})
    elif qnum in [30, 31, 47]:
        inventory.append({'category': '7. Legal', 'cat_code': 'L', 'orig_q_id': qid, 'new_q_id': qid, 'type': 'BINARY', 'verification_role': 'HUMAN', 'text': qtext})
    else:
        inventory.append({'category': '7. Legal', 'cat_code': 'L', 'orig_q_id': qid, 'new_q_id': qid, 'type': 'BINARY', 'verification_role': 'AI', 'text': qtext})

# --- 8. Team (31 -> 50) ---
t_meta = meta[meta['category_section'].str.startswith('8.')]
for _, r in t_meta.iterrows():
    qid = f"T_Q{r['question_number_in_cat']}"
    qnum = r['question_number_in_cat']
    qtext = r['question_text']
    
    if qnum == 1:
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q1a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Any co-founder previously founded/co-founded a funded startup'})
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q1b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Any co-founder previously worked as early employee (<= 10th) at a venture startup'})
    elif qnum == 2:
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q2a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Team members previously involved with at least 1 startup'})
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q2b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Team members previously involved with 3 or more startups'})
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q2_val', 'type': 'INTEGER', 'verification_role': 'AI', 'text': 'Total count of prior startups team members were involved with'})
    elif qnum == 3:
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q3a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Any full-time executive involved in at least 1 prior startup exit (M&A/IPO)'})
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q3b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Any full-time executive involved in 2 or more prior startup exits'})
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q3_val', 'type': 'INTEGER', 'verification_role': 'AI', 'text': 'Total count of prior exits across full-time founders'})
    elif qnum == 4:
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q4a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Team has 5 or more combined years of experience in company target industry'})
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q4b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Team has 15 or more combined years of experience in company target industry'})
    elif qnum == 5:
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q5a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Team member previously held VP or Director level seniority in target industry'})
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q5b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Team member previously held CEO or C-Suite seniority in target industry'})
    elif qnum in [6, 7, 8, 9, 10, 11, 12, 13, 14]:
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': qid, 'type': 'BINARY', 'verification_role': 'AI', 'text': qtext})
    elif qnum == 15:
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q15a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Technical executive holds Master degree or higher'})
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q15b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Technical executive holds Ph.D. or terminal engineering doctorate'})
    elif qnum == 16:
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q16', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Management executive holds MBA, JD, or Master degree'})
    elif qnum == 17:
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q17a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Scientific advisor holds Master degree or higher'})
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q17b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Scientific advisor holds Ph.D.'})
    elif qnum == 18:
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q18a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Board member holds Master, MBA, or JD degree'})
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q18b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Board member holds Ph.D.'})
    elif qnum == 19:
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q19a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Primary CEO/founder dedicated full-time to startup with no outside employment'})
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q19b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'All primary co-founders operating full-time on the business'})
    elif qnum == 21:
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q21a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Team has worked together for at least 1 year'})
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': 'T_Q21b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Team has worked together for more than 3 years'})
    elif qnum in [23, 24, 25]:
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': qid, 'type': 'BINARY', 'verification_role': 'HUMAN', 'text': qtext})
    elif qnum in [26, 27, 28, 29, 30]:
        src_map = {26: 'Angel Investors', 27: 'Family Offices', 28: 'VCs', 29: 'Grants/NGOs', 30: 'Strategic Investors'}
        sname = src_map[qnum]
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': f'T_Q{qnum}a', 'type': 'BINARY', 'verification_role': 'AI', 'text': f'Raised capital from or completed deals with {sname}'})
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': f'T_Q{qnum}b', 'type': 'BINARY', 'verification_role': 'AI', 'text': f'Raised >= $1M in cumulative capital from {sname}'})
    else:
        inventory.append({'category': '8. Team', 'cat_code': 'T', 'orig_q_id': qid, 'new_q_id': qid, 'type': 'BINARY', 'verification_role': 'AI', 'text': qtext})

# --- 9. Executive Summary (34 -> 46) ---
es_meta = meta[meta['category_section'].str.startswith('9.')]
for _, r in es_meta.iterrows():
    qid = f"ES_Q{r['question_number_in_cat']}"
    qnum = r['question_number_in_cat']
    qtext = r['question_text']
    
    if qnum == 7:
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q7a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Clear non-technical problem and solution summary statement provided'})
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q7b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Specific initial beachhead market defined'})
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q7c', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Operational route-to-market or distribution channel described'})
    elif qnum == 10:
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q10a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Identifies upstream suppliers and manufacturing partners in value chain'})
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q10b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Identifies downstream distributors and buyers in value chain'})
    elif qnum == 11:
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q11a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Company has paying commercial customers who have purchased product'})
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q11b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Company has active confirmed beta testing or pilot development partners'})
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q11c', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Company has signed non-binding Letters of Intent (LOIs) or MOUs'})
    elif qnum == 16:
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q16a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Environmental impact goals and metrics stated'})
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q16b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Social or community impact goals stated'})
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q16c', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Financial sustainability / cost benefit impact stated'})
    elif qnum == 18:
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q18a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Numerical Total Addressable Market (TAM) dollar valuation explicitly stated'})
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q18b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Underlying TAM calculation assumptions and methodology documented'})
    elif qnum == 19:
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q19a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Numerical Serviceable Available Market (SAM) dollar valuation explicitly stated'})
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q19b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Underlying SAM calculation assumptions and methodology documented'})
    elif qnum == 20:
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q20a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Target market share percentage explicitly presented'})
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q20b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Market share capture assumptions documented'})
    elif qnum == 23:
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q23a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Identifies direct competitors'})
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q23b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Identifies indirect competitors and substitutes'})
    elif qnum == 32:
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q32a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Historical revenue stated (or stated zero if pre-revenue)'})
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': 'ES_Q32b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Forward-looking multi-year revenue projections presented'})
    else:
        inventory.append({'category': '9. Executive Summary', 'cat_code': 'ES', 'orig_q_id': qid, 'new_q_id': qid, 'type': 'BINARY', 'verification_role': 'AI', 'text': qtext})

# --- 10. Investor Pitch (58 -> 62) ---
ip_meta = meta[meta['category_section'].str.startswith('10.')]
for _, r in ip_meta.iterrows():
    qid = f"IP_Q{r['question_number_in_cat']}"
    qnum = r['question_number_in_cat']
    qtext = r['question_text']
    
    if qnum == 22:
        inventory.append({'category': '10. Investor Pitch', 'cat_code': 'IP', 'orig_q_id': qid, 'new_q_id': 'IP_Q22a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Explicitly names legacy corporate incumbents in market'})
        inventory.append({'category': '10. Investor Pitch', 'cat_code': 'IP', 'orig_q_id': qid, 'new_q_id': 'IP_Q22b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Identifies emerging venture-backed startup competitors'})
        inventory.append({'category': '10. Investor Pitch', 'cat_code': 'IP', 'orig_q_id': qid, 'new_q_id': 'IP_Q22c', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Includes competitive matrix, 2x2 quadrant, or comparison table'})
    elif qnum == 50:
        inventory.append({'category': '10. Investor Pitch', 'cat_code': 'IP', 'orig_q_id': qid, 'new_q_id': 'IP_Q50a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'P&L / Income statement slide provided'})
        inventory.append({'category': '10. Investor Pitch', 'cat_code': 'IP', 'orig_q_id': qid, 'new_q_id': 'IP_Q50b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Balance sheet summary slide provided'})
    elif qnum == 53:
        inventory.append({'category': '10. Investor Pitch', 'cat_code': 'IP', 'orig_q_id': qid, 'new_q_id': 'IP_Q53a', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Financials include pre-tax profit (loss) projection'})
        inventory.append({'category': '10. Investor Pitch', 'cat_code': 'IP', 'orig_q_id': qid, 'new_q_id': 'IP_Q53b', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Financials include cash flow and capital requirements'})
        inventory.append({'category': '10. Investor Pitch', 'cat_code': 'IP', 'orig_q_id': qid, 'new_q_id': 'IP_Q53c', 'type': 'BINARY', 'verification_role': 'AI', 'text': 'Financials include headcount / staffing projections'})
    else:
        role = 'HUMAN' if r['is_objective'] == 0 else 'AI'
        inventory.append({'category': '10. Investor Pitch', 'cat_code': 'IP', 'orig_q_id': qid, 'new_q_id': qid, 'type': 'BINARY', 'verification_role': role, 'text': qtext})

df_inv = pd.DataFrame(inventory)
df_inv.to_csv('data/processed/master_decomposed_rubric_inventory.csv', index=False)
print("Saved inventory to data/processed/master_decomposed_rubric_inventory.csv")
print(f"Total rows in inventory: {len(df_inv)}")
print(df_inv.groupby(['category', 'verification_role']).size().unstack(fill_value=0))
