import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos, TableBordersLayout, TableCellFillMode

class InstitutionalReportPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        # System Fonts: Georgia for editorial authority, Arial for clean data/tables
        self.add_font("Georgia", "", "/System/Library/Fonts/Supplemental/Georgia.ttf")
        self.add_font("Georgia", "B", "/System/Library/Fonts/Supplemental/Georgia Bold.ttf")
        self.add_font("Georgia", "I", "/System/Library/Fonts/Supplemental/Georgia Italic.ttf")
        self.add_font("Georgia", "BI", "/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf")
        
        self.add_font("Arial", "", "/System/Library/Fonts/Supplemental/Arial.ttf")
        self.add_font("Arial", "B", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")
        self.add_font("Arial", "I", "/System/Library/Fonts/Supplemental/Arial Italic.ttf")
        
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(18, 16, 18)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Arial", "", 7.5)
        self.set_text_color(120, 130, 145)
        self.cell(100, 5, "VC UNCOVERED // RESEARCH MEMORANDUM", align="L")
        self.cell(0, 5, "EARLY-STAGE VENTURE INTELLIGENCE", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.25)
        self.line(18, self.get_y() + 1, 192, self.get_y() + 1)
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.2)
        self.line(18, self.get_y(), 192, self.get_y())
        self.ln(2)
        self.set_font("Arial", "", 7.5)
        self.set_text_color(140, 150, 165)
        self.cell(100, 4, "Institutional Research Memo | Not for Public Redistribution", align="L")
        self.cell(0, 4, f"{self.page_no()}", align="R")

    def masthead(self):
        self.set_font("Arial", "B", 8)
        self.set_text_color(37, 99, 235)
        self.cell(0, 4.5, "INDUSTRY RESEARCH REPORT  |  VENTURE CAPITAL LANDSCAPE", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)
        
        self.set_font("Georgia", "B", 20)
        self.set_text_color(15, 23, 42)
        self.cell(0, 8.5, "The Counter-Consensus in Venture Capital", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        self.set_font("Georgia", "I", 10.5)
        self.set_text_color(71, 85, 105)
        self.cell(0, 5.5, "Ideas, Strategic Camps, and Outlier Models Across 81 Emerging Fund Profiles", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)
        
        # Meta info bar
        self.set_draw_color(15, 23, 42)
        self.set_line_width(0.8)
        self.line(18, self.get_y(), 192, self.get_y())
        self.ln(2)
        
        self.set_font("Arial", "", 7.5)
        self.set_text_color(100, 116, 139)
        self.cell(40, 4, "DATASET: 81 Venture Profiles")
        self.cell(45, 4, "CORPUS: 128,105 Words")
        self.cell(45, 4, "SEGMENTS: 5 Distinct Cohorts")
        self.cell(0, 4, "DATE: September 2026", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.2)
        self.line(18, self.get_y() + 1, 192, self.get_y() + 1)
        self.ln(4)

    def section_header(self, num, title):
        self.ln(3)
        self.set_font("Arial", "B", 8)
        self.set_text_color(37, 99, 235)
        self.cell(0, 4, f"SECTION {num}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        self.set_font("Georgia", "B", 13)
        self.set_text_color(15, 23, 42)
        self.cell(0, 6.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def subhead(self, title):
        self.set_font("Arial", "B", 9.5)
        self.set_text_color(30, 41, 59)
        self.cell(0, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(0.5)

    def body(self, text):
        self.set_font("Arial", "", 8.5)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 4.2, text)
        self.ln(2.2)

    def pullquote(self, quote, speaker, firm):
        self.ln(1)
        w = 174
        self.set_font("Georgia", "I", 9)
        lines = self.multi_cell(w - 12, 4.2, f"“{quote}”", dry_run=True, output="LINES")
        h = len(lines) * 4.2 + 8.5

        if self.get_y() + h > 280:
            self.add_page()

        start_y = self.get_y()
        self.set_fill_color(250, 250, 252)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.rect(18, start_y, w, h, style="FD")
        
        # Left accent bar
        self.set_fill_color(37, 99, 235)
        self.rect(18, start_y, 2, h, style="F")
        self.set_fill_color(255, 255, 255) # Always reset fill color to pure white

        self.set_xy(23, start_y + 2.5)
        self.set_font("Georgia", "I", 9)
        self.set_text_color(30, 41, 59)
        self.multi_cell(w - 8, 4.2, f"“{quote}”")
        
        self.set_xy(23, self.get_y() + 0.8)
        self.set_font("Arial", "B", 7.5)
        self.set_text_color(37, 99, 235)
        self.cell(0, 3.5, f"— {speaker}, {firm}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(start_y + h + 2.5)

    def cohort_block(self, title, thesis, details_dict):
        self.ln(1.5)
        if self.get_y() > 240:
            self.add_page()
            
        self.set_font("Georgia", "B", 10.5)
        self.set_text_color(15, 23, 42)
        self.cell(0, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        self.set_font("Georgia", "I", 8.5)
        self.set_text_color(71, 85, 105)
        self.multi_cell(0, 4, thesis)
        self.ln(1.5)
        
        self.set_fill_color(255, 255, 255)
        with self.table(col_widths=(32, 142), borders_layout=TableBordersLayout.HORIZONTAL_LINES, line_height=4, first_row_as_headings=False, cell_fill_mode=TableCellFillMode.NONE) as t:
            for k, v in details_dict.items():
                r = t.row()
                self.set_font("Arial", "B", 7.5)
                self.set_text_color(100, 116, 139)
                r.cell(k.upper())
                
                self.set_font("Arial", "", 8)
                self.set_text_color(30, 41, 59)
                r.cell(v)
        self.ln(3)

def build_pdf():
    pdf = InstitutionalReportPDF()
    pdf.add_page()
    pdf.masthead()

    # Executive Overview
    pdf.set_font("Georgia", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 5.5, "Executive Overview", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body(
        "Silicon Valley's traditional early-stage playbook—bidding up Stanford CS graduates building horizontal software—has "
        "quietly broken down. Across 81 deep-dive interviews with emerging fund managers profiled on VC Uncovered, a decisive "
        "counter-consensus is taking shape. The post-ZIRP environment has forced investors to abandon superficial pedigree filters "
        "and speculative TAM expansions. In their place, a disciplined breed of managers is concentrating capital in historically "
        "overlooked territory: heavy industrial supply chains, state and municipal procurement, unglamorous enterprise workflows, "
        "and post-check distribution execution."
    )

    # Section I
    pdf.section_header("I", "The Four Structural Shifts Defining Modern Early-Stage VC")
    
    pdf.subhead("1. The Death of Logo Worship & The 'Earned Secret'")
    pdf.body(
        "Over two-thirds (69%) of profiled managers explicitly de-prioritize resume credentials like Ivy League degrees, "
        "ex-FAANG engineering titles, or McKinsey stints. Instead, they underwrite what Vaughn E. Crowe (nvp capital) terms the "
        "'earned secret'—an acute operational insight developed through direct exposure to a broken system. Crowe illustrates this "
        "with Vitable Health founder Joseph Kitonga, who learned the friction of healthcare administration by working directly inside "
        "his immigrant parents' home care agency. The investment thesis is grounded in lived adversity rather than theoretical market research."
    )

    pdf.subhead("2. Software Commoditization: Sales Execution as the True Moat")
    pdf.body(
        "In a market where generative AI and modern frameworks allow developers to stand up functional software in days, code velocity "
        "has ceased to be a defensive barrier. As Jennifer Richard (Bonfire Ventures) points out, enterprise buyers are now bombarded "
        "with automated, polished pitches. The bottleneck has shifted from building to selling: founders must demonstrate rigorous "
        "commercial literacy, understanding who the buyer is, navigating procurement red tape, and driving contracted revenue."
    )

    pdf.subhead("3. Capital as Table Stakes: The Agency & Studio Co-Building Model")
    pdf.body(
        "Early-stage check size is no longer a differentiator. The emerging cohort wins allocations against tier-1 multi-billion-dollar "
        "funds by providing contractual, embedded execution. Firms like FGV / Fiat Ventures built a full-service 50-person growth "
        "agency before raising their fund, trading cap table equity for guaranteed customer acquisition. Similarly, venture studios like "
        "super{set} build companies from scratch alongside technical operators, turning passive capital into hands-on company building."
    )

    pdf.subhead("4. Embedded Financial Infrastructure: 'Everything is Fintech'")
    pdf.body(
        "While standalone consumer neobanking has largely evaporated, 56% of profiles touch fintech as an embedded layer. "
        "As Sheel Mohnot (Better Tomorrow Ventures) articulates, the most durable vertical SaaS companies eventually derive the majority "
        "of their enterprise value from monetizing embedded payments, lending, insurance, and liquidity within specific trade niches."
    )

    # Page 2: Cohorts
    pdf.add_page()
    pdf.section_header("II", "The Five Strategic Cohorts: Where Like-Minded Thinkers Cluster")
    pdf.body(
        "Through latent semantic clustering across all 81 profile narratives, investors divide into five cohesive philosophical camps. "
        "Each operates with distinct sourcing networks, risk tolerances, and underwriting heuristics:"
    )

    pdf.cohort_block(
        "1. Industrial Tech & Regulated Deeptech",
        "Software has saturated knowledge workers; true alpha lies where code meets physical atoms, domestic supply chains, and complex regulatory bureaucracies.",
        {
            "Key Managers": "Christine Keung (J2 Ventures), Rachel Stern (Govtech Ventures), Atlas Berry (M1C), Natan Reddy (Ironspring Ventures), Vaughn E. Crowe (nvp capital)",
            "Target Arenas": "GovTech procurement, defense dual-use, mineral supply security, heavy industrial logistics, manufacturing automation",
            "Underwriting Heuristic": "Tolerance for 12-18 month procurement cycles; resilience to bureaucratic capture; commercialization grit in non-tech native environments"
        }
    )

    pdf.cohort_block(
        "2. The 'Earned Secret' & Non-Consensus Grinders",
        "Venture returns are maximized by backing founders whom traditional tier-1 algorithmic pattern-matching filters automatically discard.",
        {
            "Key Managers": "Charles Hudson (Precursor Ventures), Andrew Peng & Elias Mufarech (Collide Capital), Haley Bryant (Hustle Fund), Nicole DeTommaso (Harlem Capital), Alexis Maciel (Unshackled)",
            "Target Arenas": "Under-digitized legacy services, immigrant-founded infrastructure, overlooked regional business hubs across the US",
            "Underwriting Heuristic": "Obsession over pedigree; deep personal stake in the problem; high 'Day-Zero' learning velocity; demonstrated grit under adversity"
        }
    )

    pdf.cohort_block(
        "3. Fintech, Embedded Infrastructure & Capital Velocity",
        "Financial workflows are the core nervous system of commerce; winning investments embed liquidity and compliance into neglected vertical workflows.",
        {
            "Key Managers": "Sheel Mohnot (Better Tomorrow Ventures), Edwin Andrade & David Roos (Core Innovation Capital), Vikas Raj (ResilienceVC), John Onwualu (Flourish), Miguel Armaza (Gilgamesh)",
            "Target Arenas": "Vertical SaaS monetizing via payments, SMB working capital liquidity, cross-border remittances, regulatory orchestration",
            "Underwriting Heuristic": "Net revenue retention; clear customer margin expansion; compliance defensibility; near-zero churn durability"
        }
    )

    pdf.cohort_block(
        "4. Post-Check Operators & GTM Hardliners",
        "Passive advice and quarterly board governance add zero value; funds must function as operational distribution engines that accelerate revenue.",
        {
            "Key Managers": "Marcos Fernandez & Drew Glover (Fiat Ventures / FGV Capital), Jennifer Richard (Bonfire Ventures), Peter Day (super{set}), Jeff Becker (Antler)",
            "Target Arenas": "Enterprise B2B software, developer infrastructure, automated enterprise workflow tools",
            "Underwriting Heuristic": "Exceptional storytelling across selling, recruiting, and fundraising; enterprise sales literacy; unit economics sanity from day one"
        }
    )

    pdf.cohort_block(
        "5. Demographic, Care & Cultural Shift Backers",
        "Macro demographic transformations—aging populations, female financial dominance, the care crisis—represent under-capitalized systemic markets.",
        {
            "Key Managers": "Courtney Leimkuhler (Springbank.VC), Monique Woodard (Cake Ventures), Assia Grazioli-Venier (Muse Capital), Brittney Gavini (Pivotal Ventures)",
            "Target Arenas": "Care economy, women's health and wellness, eldercare infrastructure, future of family work, culture-driven digital consumer",
            "Underwriting Heuristic": "Deep organic customer resonance; massive lifetime value hidden behind fragmented industries; structural shifts in who controls capital"
        }
    )

    # Page 3: Outliers
    pdf.add_page()
    pdf.section_header("III", "The Contrarians: Profiles in Non-Consensus Investing")
    pdf.body(
        "In venture capital, outsized alpha is by definition non-consensus and right. By mapping mathematical distance from cluster centroids, "
        "several managers emerge as extreme outliers who run fundamentally contrarian operating models:"
    )

    pdf.subhead("Rachel Stern (Govtech Ventures) — The Anti-Velocity Friction Moat")
    pdf.body(
        "Conventional venture is universally addicted to rapid iteration and viral SaaS loops. Rachel Stern operates in the exact opposite "
        "environment: municipal, county, and state government procurement. Where other investors see fatal bureaucratic drag, Stern "
        "identifies an impregnable economic fortress. Once a company survives the 18-month RFP gauntlet, contracts enjoy 80%+ gross margins "
        "and near-zero churn for decades."
    )
    pdf.pullquote(
        "Most VCs see state and local government as slow, fragmented and unglamorous. I see 80% margins, near-zero churn, and acquirers actively paying premium multiples for early-stage companies.",
        "Rachel Stern", "Govtech Ventures"
    )

    pdf.subhead("Atlas Berry (M1C) — Re-Industrializing the Physical World")
    pdf.body(
        "An endurance athlete with roots in South African mining and private wealth, Atlas Berry rejects software-first dogmas. "
        "His core thesis argues that the next phase of computing and AI cannot happen without a massive rebuild of the physical world—domestic "
        "rare earth mineral refining, electrical transformers, and hard manufacturing facilities. He actively seeks out CapEx-heavy, dirty-fingernail "
        "enterprises that typical venture partners cannot underwrite."
    )
    pdf.pullquote(
        "The world is industrializing... we want to back the founders that are pushing forward this next industrial era.",
        "Atlas Berry", "M1C"
    )

    pdf.subhead("Peter Day (super{set}) — The Anti-Chatbot Technical Realist")
    pdf.body(
        "While mainstream venture firms rush to fund conversational LLM interfaces and chat wrappers, Peter Day takes a sharply contrarian stance. "
        "At venture studio super{set}, he argues that conversational interfaces fail enterprise utility tests. His investment criteria strictly "
        "mandate deterministic, invisible data pipelines that automate complex operational workflows without requiring human chat interaction."
    )
    pdf.pullquote(
        "At the moment there’s this unwritten belief that AI is a chatbot. And I think that in the not too distant future, that will be seen as the dumbest integration of AI for most use cases.",
        "Peter Day", "super{set}"
    )

    pdf.subhead("Drew Glover & Marcos Fernandez (Fiat Ventures) — The Agency-First Model")
    pdf.body(
        "Instead of raising an investment fund and subsequently attempting to hire platform staff, Glover and Fernandez built a 50-person "
        "growth marketing agency (Fiat Growth) first. By offering guaranteed customer acquisition and distribution from day zero, their $35M Fund II "
        "consistently wins competitive allocations against multi-billion-dollar funds without participating in valuation bidding wars."
    )
    pdf.pullquote(
        "Don’t chase hype. Chase simplicity, focus, and traction. The best companies are often the ones that are the most boring.",
        "Marcos Fernandez", "Fiat Ventures"
    )

    pdf.subhead("Jeff Becker (Antler) — The 'Maniac' Co-Location Crucible")
    pdf.body(
        "Becker discards the standard pitch meeting format. Antler embeds prospective entrepreneurs in an in-person, two-month intensive "
        "residency before writing a check. The structure is designed to stress-test co-founder dynamics under real operating pressure, filtering "
        "for the rare obsessives capable of enduring extreme market friction."
    )
    pdf.pullquote(
        "We work with founders for two months in person, and we back the maniacs.",
        "Jeff Becker", "Antler"
    )

    # Page 4: Matrix & Conclusion
    pdf.add_page()
    pdf.section_header("IV", "Strategic Comparison: Legacy Consensus vs. The Emerging Playbook")
    pdf.body(
        "The following matrix summarizes the fundamental operational and philosophical divergence between consensus Silicon Valley "
        "orthodoxy and the empirical practices of the emerging vanguard:"
    )

    table_data = [
        ("Core Dimension", "Consensus Silicon Valley (2020-2022)", "The Emerging Playbook (2024-2026)"),
        ("Primary Founder Signal", "Marquee pedigree (Stanford, FAANG, ex-Unicorn)", "Earned Secret (direct, lived industry friction)"),
        ("Underwriting Focus", "Product elegance & feature velocity", "Go-to-market mechanics & commercial sales literacy"),
        ("Defensive Moat", "Proprietary software codebase", "Distribution reach, regulatory lock-in & workflow stickiness"),
        ("AI Approach", "Conversational chatbots & thin LLM wrappers", "Deterministic data pipelines & invisible automated execution"),
        ("Target Sectors", "Broad horizontal SaaS, developer tooling & consumer", "Friction-heavy verticals: GovTech, Defense, Supply Chain"),
        ("Value Proposition", "Check size, prestige logo branding & passive boards", "Embedded growth agencies, contractual sales, studio co-building"),
        ("Fintech Strategy", "Standalone consumer neobanks & commoditized cards", "Vertical embedded payments, lending & SMB balance sheet liquidity"),
        ("Procurement Stance", "Flee from slow enterprise/government sales cycles", "Embrace high friction for 80%+ gross margins & near-zero churn"),
        ("Geographic Mindset", "Coastal concentration (Bay Area, New York)", "Distributed alpha (Midwest, Texas, Southeast, Frontier)")
    ]

    # Explicitly ensure clean white fill and NO table background
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(203, 213, 225) # Clean subtle gray hairline border
    pdf.set_line_width(0.25)

    with pdf.table(
        col_widths=(34, 70, 70),
        borders_layout=TableBordersLayout.HORIZONTAL_LINES,
        line_height=4.8,
        first_row_as_headings=False,
        cell_fill_mode=TableCellFillMode.NONE
    ) as t:
        # Header Row
        r = t.row()
        for h in table_data[0]:
            pdf.set_font("Arial", "B", 7.5)
            pdf.set_text_color(15, 23, 42)
            r.cell(h.upper())
            
        # Data Rows
        for row in table_data[1:]:
            r = t.row()
            # Dimension: Crisp dark navy bold
            pdf.set_font("Arial", "B", 7.2)
            pdf.set_text_color(15, 23, 42)
            r.cell(row[0])
            
            # Legacy: Muted slate regular
            pdf.set_font("Arial", "", 7.2)
            pdf.set_text_color(100, 116, 139)
            r.cell(row[1])
            
            # New Guard: Crisp dark slate bold (high contrast, perfectly legible)
            pdf.set_font("Arial", "B", 7.2)
            pdf.set_text_color(15, 23, 42)
            r.cell(row[2])

    pdf.ln(5)
    pdf.set_font("Georgia", "B", 10.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 5.5, "Concluding Strategic Memo", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body(
        "The overarching lesson from VC Uncovered is that early-stage venture alpha is shifting from ease to friction. "
        "When software creation is cheap and abundant, building another frictionless tool produces diminishing returns. "
        "The managers delivering outsized performance in this environment do not compete on check size or prestige logos. "
        "They find founders with hard-earned industry secrets, underwrite businesses wrapped in regulatory or physical complexity, "
        "and provide tangible distribution muscle where traditional venture provides only advice."
    )

    pdf.output("VC_Uncovered_Executive_Summary.pdf")
    print("Report generated cleanly with white table background!")

if __name__ == "__main__":
    build_pdf()
