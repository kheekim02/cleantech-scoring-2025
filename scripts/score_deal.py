"""
CLI Tool to Score an Incoming Startup Deal
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models.scoring_engine import StartupScoringEngine

def main():
    engine = StartupScoringEngine()
    
    # Sample deal (e.g. $2M valuation inbound deal for Shawn)
    sample_deal = {
        "tech_and_product": 78.0,
        "business_canvas": 65.0,
        "investor_pitch": 70.0,
        "financials": 60.0,
        "executive_summary": 80.0,
        "impact_sustainability": 65.0,
        "markets": 55.0,
        "team": 60.0,
        "product_market_fit": 58.0,
        "legal": 70.0
    }
    
    result = engine.calculate_score(sample_deal)
    
    overall = result["overall_score"]
    tier = result["tier"]
    surv = result["survival_probability_pct"]
    
    print("==================================================")
    print("        STARTUP DEAL EVALUATION SCORECARD         ")
    print("==================================================")
    print(f"Overall Score:        {overall} / 100")
    print(f"Assigned Tier:        {tier}")
    print(f"Predicted Survival:   {surv}%")
    print("--------------------------------------------------")
    print("Category Breakdown:")
    for cat, data in result["category_breakdown"].items():
        cat_name = cat.replace("_", " ").title()
        score = data["score"]
        weight = int(data["weight"] * 100)
        print(f"  - {cat_name:<22}: {score:>5}% (Weight: {weight:>2}%)")
    print("==================================================")

if __name__ == "__main__":
    main()
