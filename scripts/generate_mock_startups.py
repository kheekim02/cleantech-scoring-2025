import json
import random
import os

def generate_startup(rubric, meta, target_score_pct, docs):
    random.seed(hash(meta['id']))
    
    startup = {
        "meta": meta,
        "document": {
            "title": f"Executive Summary: {meta['name']}",
            "sections": docs
        },
        "ai_cats": {},
        "human_questions": []
    }
    
    cat_names = {
        'BC': 'Business Canvas', 'ES': 'Environmental & Social', 'F': 'Financials',
        'IP': 'Investor Pitch', 'IS': 'Impact Strategy', 'L': 'Legal',
        'M': 'Marketing', 'PMF': 'Product Market Fit', 'T': 'Team', 'TP': 'Tech / Product'
    }

    # Generate AI questions
    for cat_code, questions in rubric['ai_by_cat'].items():
        cat_total = 0
        cat_passed = 0
        cat_qs = []
        
        for q in questions:
            q_type = q.get('type', 'BINARY')
            verdict = None
            conf = None
            citation = None
            
            if q_type == 'INTEGER':
                verdict = random.randint(10, 1000)
            else:
                cat_total += 1
                if random.random() < 0.02:
                    verdict = -1
                else:
                    is_pass = random.random() < target_score_pct
                    verdict = 1 if is_pass else 0
                    if is_pass:
                        cat_passed += 1
                    base_conf = 0.85 if is_pass else 0.5
                    conf = min(0.99, max(0.40, random.gauss(base_conf, 0.10)))
                    citation = f"...evidence showing {q['text'].lower()[:40]}..."
            
            cat_qs.append({
                "new_q_id": q['new_q_id'],
                "text": q['text'],
                "type": q_type,
                "verdict": verdict,
                "confidence": round(conf, 2) if conf else None,
                "citation": citation
            })
            
        startup['ai_cats'][cat_code] = {
            "full_name": cat_names.get(cat_code, cat_code),
            "total": cat_total,
            "passed": cat_passed,
            "failed": cat_total - cat_passed,
            "avg_conf": round(random.uniform(0.85, 0.98), 2),
            "questions": cat_qs
        }
        
    # Generate Human Questions
    for q in rubric['human_questions']:
        conf = random.gauss(0.7, 0.15)
        conf = min(0.95, max(0.45, conf))
        sugg = 1 if random.random() < target_score_pct else 0
        
        startup['human_questions'].append({
            "cat_code": q['cat_code'],
            "new_q_id": q['new_q_id'],
            "text": q['text'],
            "ai_suggestion": sugg,
            "ai_confidence": round(conf, 2)
        })
        
    return startup

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rubric_path = os.path.join(base_dir, 'data', 'processed', 'scoring_interface_data.json')
    site_data_dir = os.path.join(base_dir, 'site', 'data', 'startups')
    
    with open(rubric_path) as f:
        rubric = json.load(f)
        
    startups_def = [
        {
            "meta": {
                "id": "solarpure",
                "name": "SolarPure Inc.",
                "cohort_year": 2025,
                "founder": "Dr. Elena Vasquez",
                "category": "Solar Performance Intelligence"
            },
            "target": 0.90,
            "docs": [
                {
                    "cat_code": "BC",
                    "heading": "Company Overview & Value Prop",
                    "text": "SolarPure Inc. is an AI-driven solar performance monitoring platform. <span class=\"cite highlight\">Our proprietary technology reduces utility-scale solar underperformance losses by 34% through edge-based anomaly detection.</span> By deploying intelligent sensor pods directly at the inverter level, we provide real-time diagnostics.",
                    "extractions": [
                        {"label": "EXTRACTED METRIC", "value": "34% reduction in underperformance losses", "highlight": True},
                        {"label": "CORE TECHNOLOGY", "value": "Edge-based anomaly detection", "highlight": False}
                    ]
                },
                {
                    "cat_code": "BC",
                    "heading": "Target Market",
                    "text": "Our target customer segment is strictly utility-scale solar asset owners and O&M providers managing portfolios larger than 20MW.",
                    "extractions": [
                        {"label": "PRIMARY SEGMENT", "value": "Utility-scale solar asset owners", "highlight": False},
                        {"label": "CONSTRAINTS", "value": "Portfolios > 20MW", "highlight": False}
                    ]
                },
                {
                    "cat_code": "ES",
                    "heading": "Environmental Impact",
                    "text": "By optimizing existing infrastructure, we <span class=\"cite highlight\">prevent 12,000 tons of CO2 emissions annually per 100MW managed.</span>",
                    "extractions": [
                        {"label": "EMISSIONS REDUCTION", "value": "12,000 tons CO2/yr per 100MW", "highlight": True}
                    ]
                }
            ]
        }
    ]
    
    # Just generating SolarPure for exact UI match for now, we can clone it for others if needed.
    for s_def in startups_def:
        data = generate_startup(rubric, s_def['meta'], s_def['target'], s_def['docs'])
        # To make it render something for all 10 steps, copy the BC docs to other categories for the mock
        all_cats = ['F', 'IP', 'IS', 'L', 'M', 'PMF', 'T', 'TP']
        for cat in all_cats:
            data['document']['sections'].append({
                "cat_code": cat,
                "heading": f"Generic Data for {cat}",
                "text": "This is mock extraction text for this specific category step.",
                "extractions": [
                    {"label": "EXTRACTED METRIC", "value": f"Mock metric for {cat}", "highlight": False}
                ]
            })
            
        out_path = os.path.join(site_data_dir, f"{s_def['meta']['id']}.json")
        with open(out_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Generated {out_path}")

if __name__ == '__main__':
    main()
