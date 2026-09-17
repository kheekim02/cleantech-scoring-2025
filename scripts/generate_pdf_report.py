import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

class VCReportPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        # Load System Fonts with full UTF-8 Unicode support
        self.add_font("Arial", "", "/System/Library/Fonts/Supplemental/Arial.ttf")
        self.add_font("Arial", "B", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")
        self.add_font("Arial", "I", "/System/Library/Fonts/Supplemental/Arial Italic.ttf")
        self.add_font("Arial", "BI", "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf")
        self.set_auto_page_break(auto=True, margin=16)
        self.set_margins(16, 16, 16)

    def header(self):
        if self.page_no() == 1:
            return  # Suppress running header on cover/first page
        self.set_font("Arial", "I", 8)
        self.set_text_color(140, 150, 165)
        self.cell(0, 5, "VC UNCOVERED: EMPIRICAL ANALYSIS & STRATEGIC COHORTS", align="L")
        self.cell(0, 5, "EXECUTIVE BRIEFING", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.line(16, self.get_y() + 1, 194, self.get_y() + 1)
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.3)
        self.line(16, self.get_y(), 194, self.get_y())
        self.ln(2)
        self.set_font("Arial", "", 8)
        self.set_text_color(140, 150, 165)
        self.cell(0, 5, "Confidential Venture Intelligence Summary", align="L")
        self.cell(0, 5, f"Page {self.page_no()}", align="R")

    def chapter_title(self, title, tag=None):
        self.ln(3)
        if tag:
            self.set_fill_color(239, 246, 255)
            self.set_text_color(37, 99, 235)
            self.set_font("Arial", "B", 7.5)
            w_tag = len(tag) * 2.2 + 6
            self.cell(w_tag, 4.5, tag.upper(), fill=True, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(1.5)
        self.set_font("Arial", "B", 13.5)
        self.set_text_color(15, 23, 42)
        self.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(37, 99, 235)
        self.set_line_width(0.8)
        self.line(16, self.get_y() + 0.8, 48, self.get_y() + 0.8)
        self.ln(4)

    def section_subtitle(self, title):
        self.set_font("Arial", "B", 10)
        self.set_text_color(30, 41, 59)
        self.cell(0, 5.5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(0.8)

    def paragraph(self, text):
        self.set_font("Arial", "", 9)
        self.set_text_color(51, 65, 85)
        self.multi_cell(0, 4.5, text)
        self.ln(2.5)

    def quote_box(self, quote, author, firm):
        w = 178
        self.set_font("Arial", "I", 8.5)
        lines = self.multi_cell(w - 12, 4.2, f"“{quote}”", dry_run=True, output="LINES")
        h = len(lines) * 4.2 + 11

        if self.get_y() + h > 280:
            self.add_page()

        start_y = self.get_y()
        self.set_fill_color(248, 250, 252)
        self.set_draw_color(203, 213, 225)
        self.set_line_width(0.4)
        self.rect(16, start_y, w, h, style="FD")
        
        # Accent bar
        self.set_fill_color(37, 99, 235)
        self.rect(16, start_y, 2.5, h, style="F")

        self.set_xy(22, start_y + 3)
        self.set_font("Arial", "I", 8.5)
        self.set_text_color(30, 41, 59)
        self.multi_cell(w - 10, 4.2, f"“{quote}”")
        
        self.set_xy(22, self.get_y() + 0.5)
        self.set_font("Arial", "B", 8)
        self.set_text_color(37, 99, 235)
        self.cell(0, 4, f"— {author}, {firm}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(start_y + h + 2.5)

    def card(self, title, items_dict):
        w = 178
        # Estimate height
        content_h = 7.5
        for k, v in items_dict.items():
            content_h += 4.5 + (len(v) // 85) * 4.2

        if self.get_y() + content_h > 280:
            self.add_page()

        start_y = self.get_y()
        self.set_fill_color(248, 250, 252)
        self.set_draw_color(226, 232, 240)
        self.set_line_width(0.35)
        self.rect(16, start_y, w, content_h, style="FD")
        
        # Header bar
        self.set_fill_color(241, 245, 249)
        self.rect(16, start_y, w, 6.5, style="FD")
        self.set_xy(20, start_y + 0.8)
        self.set_font("Arial", "B", 9)
        self.set_text_color(15, 23, 42)
        self.cell(0, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        current_y = start_y + 8.5
        for k, v in items_dict.items():
            self.set_xy(20, current_y)
            self.set_font("Arial", "B", 8)
            self.set_text_color(71, 85, 105)
            self.cell(36, 4.2, f"{k}:")
            
            self.set_font("Arial", "", 8)
            self.set_text_color(30, 41, 59)
            self.set_xy(56, current_y)
            self.multi_cell(w - 42, 4.2, str(v))
            current_y = self.get_y() + 1.2

        self.set_y(current_y + 2.5)

def generate_report(output_filename="VC_Uncovered_Executive_Summary.pdf"):
    pdf = VCReportPDF()
    pdf.add_page()

    # ==================== COVER / HEADER BANNER ====================
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 44, style="F")

    pdf.set_xy(16, 10)
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, "VC UNCOVERED: THE NEW VENTURE PLAYBOOK", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Arial", "", 9.5)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 5.5, "An Empirical Study of Ideas, Mindsets, Philosophical Clusters, and Contrarian Outliers", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Metadata pills
    pdf.set_xy(16, 29)
    pdf.set_font("Arial", "B", 7.5)
    pdf.set_text_color(226, 232, 240)
    pdf.cell(0, 5, "DATASET SCOPE: 81 In-Depth Profile Analyses | 128,105 Words Analyzed | 5 Strategic Cohorts", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(49)

    # ==================== EXECUTIVE SUMMARY ====================
    pdf.chapter_title("Executive Summary: The Post-ZIRP Frontier", "Research Synthesis")
    pdf.paragraph(
        "A rigorous empirical analysis of 81 investor profiles from VC Uncovered reveals a definitive "
        "structural inflection in early-stage venture capital. The era of ZIRP-fueled growth-at-all-costs, "
        "marquee credential worship, and speculative platform investing has been replaced by a rigorous, "
        "pragmatic, and operationally demanding new playbook."
    )
    pdf.paragraph(
        "Modern top-performing seed and pre-seed fund managers are actively fleeing crowded consumer and "
        "horizontal AI wrapper markets. Instead, they are concentrating capital around unglamorous friction "
        "points: supply chain re-shoring, state and local procurement, enterprise sales execution, dual-use national security, "
        "and embedded financial infrastructure. Rather than relying on generic pedigree matching, these investors "
        "systematically underwrite non-consensus founders possessing rare domain insight."
    )

    # ==================== PART 1: SYSTEMIC PATTERNS ====================
    pdf.chapter_title("Part 1: Core Theses & Systemic Patterns", "Macro Dynamics")
    
    pdf.section_subtitle("1. The Death of Credentialism: 'Earned Secrets' vs. Marquee Pedigree")
    pdf.paragraph(
        "Across 69% of the analyzed investor profiles, managers explicitly reject traditional credentialism "
        "(Ivy League degrees, Goldman Sachs/McKinsey backgrounds, marquee tech logos) as a reliable predictive signal for alpha. "
        "Investors have shifted their underwriting focus toward what Vaughn E. Crowe (nvp capital) terms the 'Earned Secret': "
        "a proprietary thesis developed through direct, lived friction inside an industry—such as operating a family healthcare "
        "business, managing military logistics, or working factory floors. The primary filter is no longer where the founder "
        "worked, but whether their personal history directly explains why they are uniquely equipped to solve an unglamorous problem."
    )

    pdf.section_subtitle("2. Software Commoditization: Distribution & GTM as the Sole Moats")
    pdf.paragraph(
        "In 62% of profiles, investors note that modern development frameworks and AI tooling have commoditized pure code generation. "
        "Because anyone can now build a capable prototype over a weekend, product-led velocity is no longer a durable barrier to entry. "
        "Consequently, investors like Jennifer Richard (Bonfire Ventures) and Drew Glover (Fiat Ventures) prioritize commercialization grit, "
        "sales endurance, and customer acquisition mechanics over technical elegance. As customer inboxes are inundated with automated outreach, "
        "the ability to navigate enterprise procurement and secure committed revenue is the ultimate early-stage hurdle."
    )

    pdf.section_subtitle("3. Capital as a Commodity: The Rise of Post-Check Operating Engines")
    pdf.paragraph(
        "Check size alone has ceased to be a competitive differentiator. Emerging managers increasingly position their funds as "
        "operational engines with investment vehicles attached. Firms such as FGV / Fiat Ventures, super{set}, and Hustle Fund win allocations "
        "against multi-billion-dollar coastal funds by providing embedded growth agencies, dedicated enterprise sales pipelines, "
        "or hands-on co-founding studio infrastructure. Capital is treated as table stakes; operational lift is the primary currency."
    )

    pdf.section_subtitle("4. Embedded Financial Infrastructure: 'Everything is Fintech'")
    pdf.paragraph(
        "While standalone consumer neobanking has largely fallen out of favor, 56% of analyzed profiles evaluate fintech through the lens "
        "of embedded infrastructure. As articulated by Sheel Mohnot (Better Tomorrow Ventures), modern vertical software companies are "
        "fundamentally fintech businesses in disguise, generating the preponderance of their long-term terminal value from transaction fees, "
        "embedded credit, liquidity management, and compliance orchestration."
    )

    # ==================== PART 2: THE 5 STRATEGIC CLUMPS ====================
    pdf.chapter_title("Part 2: The 5 Strategic Cohorts of Venture Thinkers", "Clustering Analysis")
    pdf.paragraph(
        "Through latent semantic vectorization and agglomerative clustering, the 81 investors partition into five distinct "
        "philosophical cohorts, each defined by a coherent investment methodology, target problem space, and founder selection criteria:"
    )

    # Cohort 1
    pdf.card(
        "Cohort 1: Industrial, GovTech & Physical World Modernizers",
        {
            "Strategic Worldview": "Software has saturated knowledge workers; true alpha lies where code meets physical atoms, domestic supply chains, and complex regulatory bureaucracies.",
            "Target Sectors": "GovTech, Defense / Dual-Use, Heavy Industry, Domestic Mineral Supply, Supply Chain Logistics, Manufacturing Automation.",
            "Core Evaluation Filter": "Tolerance for long procurement cycles (12-18 months), understanding of regulatory capture, commercialization grit in non-tech native environments.",
            "Key Representative VCs": "Christine Keung (J2 Ventures), Rachel Stern (Govtech Ventures), Atlas Berry (M1C), Natan Reddy (Ironspring Ventures), Vaughn E. Crowe (nvp capital)."
        }
    )

    # Cohort 2
    pdf.card(
        "Cohort 2: The 'Earned Secret' & Non-Consensus Grinders",
        {
            "Strategic Worldview": "Superior venture returns require backing founders whom traditional tier-1 algorithmic pattern-matching filters automatically discard.",
            "Target Sectors": "Under-digitized legacy services, cross-border commerce, immigrant-founded infrastructure, regional hubs outside Silicon Valley.",
            "Core Evaluation Filter": "Deep lived experience, obsession with the specific customer problem, high learning velocity ('Day-Zero speed'), and demonstrated resilience under adversity.",
            "Key Representative VCs": "Charles Hudson (Precursor Ventures), Andrew Peng & Elias Mufarech (Collide Capital), Haley Bryant (Hustle Fund), Nicole DeTommaso (Harlem Capital), Alexis Maciel (Unshackled Ventures)."
        }
    )

    # Cohort 3
    pdf.card(
        "Cohort 3: Fintech, Financial Inclusion & Capital Velocity",
        {
            "Strategic Worldview": "Financial workflows represent the core nervous system of enterprise. The largest opportunities exist in embedding liquidity, credit, and compliance into neglected workflows.",
            "Target Sectors": "Vertical embedded finance, SMB liquidity, cross-border remittances, regulatory compliance tech, financial resilience platforms.",
            "Core Evaluation Filter": "Net revenue retention, margin expansion through payments/credit, compliance defensibility, zero-churn durability.",
            "Key Representative VCs": "Sheel Mohnot (Better Tomorrow Ventures), Edwin Andrade & David Roos (Core Innovation Capital), Vikas Raj (ResilienceVC), John Onwualu (Flourish Ventures), Miguel Armaza (Gilgamesh Ventures)."
        }
    )

    # Cohort 4
    pdf.card(
        "Cohort 4: Post-Check Operators & GTM Hardliners",
        {
            "Strategic Worldview": "Advice and board governance are negligible value-adds. Early-stage venture returns are maximized by directly accelerating the portfolio company's distribution and customer pipeline.",
            "Target Sectors": "Enterprise B2B SaaS, developer infrastructure, automated workflow platforms, commercial software.",
            "Core Evaluation Filter": "World-class storytelling (recruiting, selling, fundraising), operational discipline, enterprise sales literacy, coachability.",
            "Key Representative VCs": "Marcos Fernandez & Drew Glover (Fiat Ventures / FGV Capital), Jennifer Richard (Bonfire Ventures), Peter Day (super{set}), Jeff Becker (Antler)."
        }
    )

    # Cohort 5
    pdf.card(
        "Cohort 5: Demographic, Care & Cultural Shift Backers",
        {
            "Strategic Worldview": "Massive macro-demographic transformations (aging populations, female financial dominance, the caregiving crisis) represent massive, under-capitalized market opportunities.",
            "Target Sectors": "Care economy, women's health and wellness, eldercare infrastructure, future of family work, culture-driven digital consumer.",
            "Core Evaluation Filter": "Authentic audience resonance, high organic customer lifetime value (LTV), structural market size hidden by traditional industry categories.",
            "Key Representative VCs": "Courtney Leimkuhler (Springbank.VC), Monique Woodard (Cake Ventures), Assia Grazioli-Venier (Muse Capital), Brittney Gavini (Pivotal Ventures)."
        }
    )

    # ==================== PART 3: THE CONTRARIANS & OUTLIERS ====================
    pdf.chapter_title("Part 3: The Contrarians & Strategic Outliers", "Outlier Analysis")
    pdf.paragraph(
        "By calculating multidimensional distance from cluster centroids and identifying structural deviations from standard venture capital practices, "
        "several distinct outliers emerge. These investors break sharply with consensus Silicon Valley doctrine:"
    )

    # Outlier 1: Rachel Stern
    pdf.section_subtitle("1. The Anti-Velocity Outlier: Rachel Stern (Govtech Ventures)")
    pdf.paragraph(
        "While conventional venture capital is universally obsessed with product release speed and viral adoption loops, Rachel Stern "
        "builds conviction in the exact opposite environment: municipal, state, and local government procurement. "
        "Where others see fatal friction, Stern identifies an impenetrable economic moat."
    )
    pdf.quote_box(
        "Most VCs see state and local government as slow, fragmented and unglamorous. I see 80% margins, near-zero churn, "
        "and acquirers actively paying premium multiples for early-stage companies.",
        "Rachel Stern", "Govtech Ventures"
    )

    # Outlier 2: Atlas Berry
    pdf.section_subtitle("2. The Heavy Industry & Atoms Outlier: Atlas Berry (M1C)")
    pdf.paragraph(
        "With an unconventional background bridging South African mining operations and high-endurance athletics, Atlas Berry rejects "
        "the software-first paradigm. His core thesis argues that the AI revolution cannot expand without a massive physical buildout—rare earth "
        "minerals, electrical power grid components, and industrial manufacturing capacity. He intentionally seeks out high CapEx, "
        "dirty physical facilities, and hard asset businesses that typical venture software funds are structurally unequipped to underwrite."
    )
    pdf.quote_box(
        "The world is industrializing... we want to back the founders that are pushing forward this next industrial era.",
        "Atlas Berry", "M1C"
    )

    # Outlier 3: Peter Day
    pdf.section_subtitle("3. The Anti-Chatbot Technical Realist: Peter Day (super{set})")
    pdf.paragraph(
        "Amid widespread venture euphoria surrounding generative AI and chatbot interfaces, Day articulates a starkly contrarian view. "
        "As an investor and venture studio builder, he views conversational chat as an ephemeral interface that fails to deliver enterprise ROI. "
        "His filter strictly mandates deterministic data pipelines and invisible automated workflow execution over conversational novelties."
    )
    pdf.quote_box(
        "At the moment there’s this unwritten belief that AI is a chatbot. And I think that in the not too distant future, "
        "that will be seen as the dumbest integration of AI for most use cases.",
        "Peter Day", "super{set}"
    )

    # Outlier 4: Drew Glover & Marcos Fernandez
    pdf.section_subtitle("4. The Agency-First Structural Outlier: Drew Glover & Marcos Fernandez (Fiat Ventures)")
    pdf.paragraph(
        "Instead of launching an investment fund and subsequently attempting to hire 'platform' support staff, Glover and Fernandez "
        "established a full-service 50+ person growth marketing and customer acquisition firm (Fiat Growth) first. By guaranteeing proven "
        "distribution and customer acquisition from day one, their $35M fund consistently wins allocations and co-invests alongside "
        "top-tier institutional funds without participating in valuation bidding wars."
    )
    pdf.quote_box(
        "Don’t chase hype. Chase simplicity, focus, and traction. The best companies are often the ones that are the most boring.",
        "Marcos Fernandez", "Fiat Ventures / FGV Capital"
    )

    # Outlier 5: Jeff Becker
    pdf.section_subtitle("5. The 'Maniac' Co-Location Model: Jeff Becker (Antler)")
    pdf.paragraph(
        "Becker eliminates the conventional 30-minute pitch meeting paradigm. Antler embeds prospective founders in an in-person, "
        "two-month intensive crucible before finalizing Day-Zero capital commitments. Becker's underwriting framework filters specifically "
        "for extreme psychological resilience and co-founder dispute resolution under high-stress operating conditions."
    )
    pdf.quote_box(
        "We work with founders for two months in person, and we back the maniacs.",
        "Jeff Becker", "Antler"
    )

    # ==================== PART 4: COMPARATIVE SYNTHESIS ====================
    pdf.chapter_title("Part 4: Consensus VC vs. The Emerging New Guard", "Strategic Comparison")
    pdf.paragraph(
        "The table below contrasts the operating parameters of legacy consensus venture capital against the empirical "
        "findings from the 81 investors profiled across VC Uncovered:"
    )

    table_data = [
        ("Dimension", "Consensus Silicon Valley Model", "The Emerging New Guard"),
        ("Founder Signal", "Elite pedigree (Stanford, FAANG, Ex-Unicorn)", "Earned Secret (direct lived industry friction)"),
        ("Primary Moat", "Proprietary software & code velocity", "Distribution, sales execution & regulatory endurance"),
        ("AI Stance", "Thin LLM wrappers, chatbots & agent interfaces", "Invisible data pipelines, deterministic workflows"),
        ("Target Markets", "Broad horizontal SaaS & consumer apps", "Unsexy verticals: GovTech, Defense, Supply Chain"),
        ("Value Proposition", "Check size, prestige branding & passive boards", "Embedded growth agencies, studio co-building"),
        ("Fintech Model", "Standalone consumer neobanking & cards", "Embedded compliance, lending & SMB vertical liquidity"),
        ("Procurement Stance", "Flee from slow enterprise/government sales", "Embrace high friction for 80% margins & zero churn"),
        ("Geography", "Coastal concentration (Bay Area, NYC)", "Distributed alpha (Atlanta, Texas, Midwest, Frontier)")
    ]

    col_w = [30, 74, 74]
    
    # Check page space for table
    if pdf.get_y() > 200:
        pdf.add_page()

    # Table Header
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(226, 232, 240)
    pdf.set_line_width(0.3)
    pdf.set_font("Arial", "B", 8)
    
    pdf.cell(col_w[0], 6.5, table_data[0][0], border=1, fill=True, align="C")
    pdf.cell(col_w[1], 6.5, table_data[0][1], border=1, fill=True, align="C")
    pdf.cell(col_w[2], 6.5, table_data[0][2], border=1, fill=True, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Table Body
    for i, row in enumerate(table_data[1:]):
        bg = (248, 250, 252) if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        
        # Dimension
        pdf.set_font("Arial", "B", 7.5)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(col_w[0], 5.8, f" {row[0]}", border=1, fill=True)
        
        # Consensus
        pdf.set_font("Arial", "", 7.5)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(col_w[1], 5.8, f" {row[1]}", border=1, fill=True)
        
        # New Guard
        pdf.set_font("Arial", "B", 7.5)
        pdf.set_text_color(37, 99, 235)
        pdf.cell(col_w[2], 5.8, f" {row[2]}", border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(5)
    pdf.section_subtitle("Conclusion")
    pdf.paragraph(
        "The emerging generation of venture capital investors profiled in this study demonstrate that true alpha in early-stage investing "
        "is no longer generated by bidding up consensus founders in frictionless categories. Sustainable venture performance belongs to "
        "investors who embrace unglamorous friction, back non-consensus operators with earned industry secrets, and provide measurable, "
        "contractual distribution support beyond the check."
    )

    pdf.output(output_filename)
    print(f"Report successfully written to {output_filename}")

if __name__ == "__main__":
    generate_report("VC_Uncovered_Executive_Summary.pdf")
