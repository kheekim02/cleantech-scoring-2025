import os

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scoring Interface 2025</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { font-family: 'Inter', sans-serif; overflow: hidden; }
        .highlight-passage { background-color: transparent; transition: background-color 0.2s ease; border-radius: 2px; padding: 0 2px; }
        .active-highlight { background-color: #fef08a; }
        .card-enter { transition: all 0.2s ease; }
        .collapsed-card { height: 48px; overflow: hidden; opacity: 0.8; cursor: pointer; }
        .cat-BC { background-color: #4f46e5; color: white; }
        .cat-ES { background-color: #0ea5e9; color: white; }
        .cat-F { background-color: #22c55e; color: white; }
        .cat-IP { background-color: #a855f7; color: white; }
        .cat-IS { background-color: #14b8a6; color: white; }
        .cat-L { background-color: #f97316; color: white; }
        .cat-M { background-color: #06b6d4; color: white; }
        .cat-PMF { background-color: #f43f5e; color: white; }
        .cat-T { background-color: #f59e0b; color: white; }
        .cat-TP { background-color: #3b82f6; color: white; }
        .scrollbar-hide::-webkit-scrollbar { display: none; }
        .scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }
    </style>
</head>
<body class="bg-gray-100 flex flex-col h-screen text-gray-800">

    <!-- Header -->
    <header class="h-[60px] bg-indigo-900 text-white flex items-center justify-between px-6 flex-shrink-0 z-10 shadow-md">
        <div class="font-semibold text-lg flex items-center gap-2">
            <span>🌱 CleanTech Open 2025 | Scoring Interface</span>
        </div>
        <div class="text-indigo-200 font-medium">SolarPure Inc. ● DEMO</div>
        <div class="flex items-center gap-4">
            <div class="flex items-center gap-2">
                <span class="text-sm">Progress: <span id="header-progress-text">0/43</span></span>
                <div class="w-32 h-2 bg-indigo-950 rounded-full overflow-hidden">
                    <div id="header-progress-bar" class="h-full bg-green-400 w-0 transition-all duration-300"></div>
                </div>
                <span id="header-progress-pct" class="text-sm w-8">0%</span>
            </div>
            <button id="reset-btn" class="bg-indigo-700 hover:bg-indigo-600 text-xs px-3 py-1.5 rounded transition">Reset Demo</button>
        </div>
    </header>

    <!-- Main Content -->
    <div class="flex flex-1 overflow-hidden">
        
        <!-- Left Pane (Document) -->
        <div class="w-[35%] bg-gray-200 p-6 overflow-y-auto" id="left-pane">
            <div class="bg-white p-8 rounded shadow-lg max-w-2xl mx-auto min-h-full">
                <h1 class="text-3xl font-bold mb-6 text-gray-900 border-b pb-4">Executive Summary: SolarPure Inc.</h1>
                
                <section class="mb-6 space-y-4 text-gray-700 leading-relaxed">
                    <h2 class="text-xl font-semibold text-gray-800">1. Company Overview</h2>
                    <p>SolarPure Inc. — AI-driven solar performance monitoring platform. Value prop: reduces solar underperformance losses by 34% through proprietary edge-based anomaly detection.</p>
                </section>

                <section class="mb-6 space-y-4 text-gray-700 leading-relaxed">
                    <h2 class="text-xl font-semibold text-gray-800">2. Mission & Culture</h2>
                    <p><span class="highlight-passage" data-qid="IS_Q5a">SolarPure's mission is to accelerate the clean energy transition through transparent performance intelligence. We believe in radical transparency, continuous learning, and equitable access to clean energy data.</span></p>
                </section>

                <section class="mb-6 space-y-4 text-gray-700 leading-relaxed">
                    <h2 class="text-xl font-semibold text-gray-800">3. Problem & Market</h2>
                    <p><span class="highlight-passage" data-qid="IP_Q5">Utility-scale solar operators are losing $2.1B annually to undetected panel underperformance, inverter faults, and soiling losses.</span></p>
                    <p><span class="highlight-passage" data-qid="IP_Q6">FERC Order 881 now mandates hourly performance reporting — making real-time monitoring a regulatory requirement, not an option.</span></p>
                    <p><span class="highlight-passage" data-qid="IP_Q10">The utility-scale solar monitoring market is valued at $4.8B and growing at 18% CAGR through 2030.</span></p>
                </section>

                <section class="mb-6 space-y-4 text-gray-700 leading-relaxed">
                    <h2 class="text-xl font-semibold text-gray-800">4. Solution</h2>
                    <p>SolarPure deploys edge-computing sensor pods at each inverter cluster, running our <span class="highlight-passage" data-qid="L_Q30">proprietary edge-processing algorithm (patent-pending, USPTO App. No. 17/234,891)</span> that detects anomalies in sub-second intervals — 10x faster than cloud-based alternatives.</p>
                </section>

                <section class="mb-6 space-y-4 text-gray-700 leading-relaxed">
                    <h2 class="text-xl font-semibold text-gray-800">5. Traction</h2>
                    <p><span class="highlight-passage" data-qid="IP_Q9">'SolarPure caught a string inverter fault that saved us $180K in one month' — Operations Director, Pacific Power</span>.</p>
                    <p>Three paying pilot customers: Pacific Power (50MW), SunGrid LLC (28MW), Desert Solar Partners (15MW). <span class="highlight-passage" data-qid="TP_Q16">Our system is fully integrated into commercial deployment at Pacific Power's 50MW facility, running continuously since Q1 2026.</span> Two signed LOIs from municipal utilities.</p>
                </section>

                <section class="mb-6 space-y-4 text-gray-700 leading-relaxed">
                    <h2 class="text-xl font-semibold text-gray-800">6. Team</h2>
                    <p><span class="highlight-passage" data-qid="IP_Q43">The leadership team brings combined 40 years of utility-scale energy experience.</span> CEO: former VP Engineering at SunPower (12 years). CTO: MIT PhD, Power Systems. 8 full-time employees.</p>
                </section>

                <section class="mb-6 space-y-4 text-gray-700 leading-relaxed">
                    <h2 class="text-xl font-semibold text-gray-800">7. IP & Legal</h2>
                    <p>Filed patents: USPTO App. No. 17/234,891 (edge anomaly detection) and 17/456,012 (soiling pattern classification).</p>
                    <p><span class="highlight-passage" data-qid="L_Q47">No cap table structural issues. Clean C-Corp formation (Delaware, 2022). Standard 4-year vesting with 1-year cliff for all co-founders.</span> No pending litigation. <span class="highlight-passage" data-qid="L_Q30">All employees have signed NDA and invention assignment agreements protecting our edge-processing algorithms.</span></p>
                </section>

                <section class="mb-6 space-y-4 text-gray-700 leading-relaxed">
                    <h2 class="text-xl font-semibold text-gray-800">8. Financials</h2>
                    <p>3-year projections: Y1 $420K ARR, Y2 $1.8M, Y3 $6.2M. Operating budget includes COGS (42%), R&D (28%), S&M (18%), G&A (12%) line items.</p>
                </section>

                <section class="mb-6 space-y-4 text-gray-700 leading-relaxed">
                    <h2 class="text-xl font-semibold text-gray-800">9. Market</h2>
                    <p>TAM: $4.8B (utility-scale solar monitoring). SAM: $890M (North American operators >10MW). SOM Year 3: $62M. TRL 7 — validated by NREL independent field testing.</p>
                </section>
            </div>
        </div>

        <!-- Right Pane (Evaluation) -->
        <div class="w-[65%] flex flex-col bg-gray-50 border-l relative overflow-hidden">
            <div class="flex-1 overflow-y-auto p-6 pb-32" id="right-pane-scroll">
                
                <!-- Section 1: AI Auto-Verified Block -->
                <div class="bg-white rounded-lg shadow-sm border border-gray-200 mb-8 overflow-hidden">
                    <div class="bg-slate-50 px-4 py-3 border-b border-gray-200 flex items-center justify-between cursor-pointer" id="ai-block-header">
                        <h2 class="font-semibold text-slate-700"><i class="fa-solid fa-robot mr-2 text-indigo-500"></i>🤖 AI Auto-Verified: 307 / 312 checks passed <span class="text-xs font-normal text-slate-500 ml-2">(avg confidence: 0.92)</span></h2>
                        <i class="fa-solid fa-chevron-down text-slate-400 transition-transform" id="ai-block-icon"></i>
                    </div>
                    <div class="divide-y divide-gray-100 hidden" id="ai-block-content">
                        <!-- Filled by JS -->
                    </div>
                </div>

                <!-- Section 2: Human Review Queue -->
                <div>
                    <h2 class="font-bold text-lg text-gray-800 mb-4 flex items-center"><i class="fa-solid fa-user-check mr-2 text-blue-500"></i>👤 Human Review Queue <span class="ml-2 bg-blue-100 text-blue-800 text-xs py-0.5 px-2 rounded-full" id="queue-count-badge">43 remaining</span></h2>
                    
                    <div id="cards-container" class="space-y-4">
                        <!-- Cards injected by JS -->
                    </div>
                </div>
            </div>

            <!-- Sticky Session Summary -->
            <div class="absolute bottom-0 left-0 right-0 bg-white border-t p-4 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)] flex items-center justify-between text-sm z-20">
                <div class="flex items-center gap-6">
                    <div class="font-medium text-slate-600"><i class="fa-solid fa-robot text-slate-400 mr-1"></i> AI Score: <span class="text-slate-900 font-bold">307 / 312</span> auto-verified</div>
                    <div class="font-medium text-slate-600"><i class="fa-solid fa-user text-slate-400 mr-1"></i> Human: <span class="text-slate-900 font-bold" id="bottom-human-count">0 / 43</span> reviewed</div>
                    <div class="font-medium text-slate-600"><i class="fa-solid fa-chart-pie text-slate-400 mr-1"></i> Combined: <span class="text-slate-900 font-bold" id="bottom-combined-score">307 / 355 — 86.5%</span></div>
                </div>
                <div class="font-medium text-orange-600 bg-orange-50 px-3 py-1.5 rounded-full"><i class="fa-solid fa-clock mr-1"></i> Est. Time Remaining: <span id="time-remaining">8</span> min</div>
            </div>
        </div>
    </div>

    <script>
        const aiCategories = [
            { cat: 'BC', name: 'Business Canvas', passed: 12, total: 13, conf: 0.97, pills: ['BC_Q1a✅(0.94)', 'BC_Q1b✅(0.97)', 'BC_Q2a✅(0.98)', 'BC_Q2b✅(0.95)', 'BC_Q2c✅(0.93)', 'BC_Q3a✅(0.99)', 'BC_Q3b✅(0.96)', 'BC_Q3_val✅(0.98)', 'BC_Q4a✅(0.97)', 'BC_Q4b✅(0.98)', 'BC_Q4c✅(0.92)', 'BC_Q5a✅(0.96)', 'BC_Q5b❌(0.31)'], more: 0 },
            { cat: 'ES', name: 'Executive Summary', passed: 46, total: 46, conf: 0.96, pills: ['ES_Q1a✅(0.99)', 'ES_Q2✅(0.97)', 'ES_Q7a✅(0.95)', 'ES_Q7b✅(0.93)', 'ES_Q7c✅(0.94)', 'ES_Q11a✅(0.98)', 'ES_Q11b✅(0.97)', 'ES_Q11c✅(0.96)', 'ES_Q18a✅(0.99)', 'ES_Q18b✅(0.94)'], more: 36 },
            { cat: 'F', name: 'Financials', passed: 40, total: 41, conf: 0.91, pills: ['F_Q3a✅(0.97)', 'F_Q3b✅(0.95)', 'F_Q6a✅(0.93)', 'F_Q6b✅(0.88)', 'F_Q16a✅(0.96)', 'F_Q16b✅(0.91)'], more: 34 },
            { cat: 'IP', name: 'Investor Pitch', passed: 40, total: 42, conf: 0.96, pills: ['IP_Q1✅(0.99)', 'IP_Q2✅(0.98)', 'IP_Q16✅(0.95)', 'IP_Q22a✅(0.97)', 'IP_Q22b✅(0.94)', 'IP_Q47✅(0.96)'], more: 34 },
            { cat: 'IS', name: 'Impact & Sustainability', passed: 13, total: 13, conf: 0.91, pills: ['IS_Q1a✅(0.97)', 'IS_Q1b✅(0.92)', 'IS_Q2a✅(0.94)', 'IS_Q2b✅(0.90)', 'IS_Q3✅(0.95)', 'IS_Q4✅(0.88)'], more: 7 },
            { cat: 'L', name: 'Legal & IP', passed: 51, total: 51, conf: 0.94, pills: ['L_Q1✅(0.98)', 'L_Q3✅(0.97)', 'L_Q4✅(0.96)', 'L_Q6✅(0.99)', 'L_Q9a✅(0.95)', 'L_Q9b✅(0.93)'], more: 45 },
            { cat: 'M', name: 'Markets & GTM', passed: 10, total: 10, conf: 0.93, pills: ['M_Q1a✅(0.96)', 'M_Q1b✅(0.94)', 'M_Q3✅(0.92)', 'M_Q7✅(0.95)', 'M_Q8✅(0.91)', 'M_Q10✅(0.90)'], more: 4 },
            { cat: 'PMF', name: 'Product / Market Fit', passed: 26, total: 26, conf: 0.93, pills: ['PMF_Q1a✅(0.97)', 'PMF_Q3✅(0.96)', 'PMF_Q6✅(0.94)', 'PMF_Q7✅(0.93)', 'PMF_Q13✅(0.92)', 'PMF_Q29✅(0.91)'], more: 20 },
            { cat: 'T', name: 'Team', passed: 45, total: 45, conf: 0.89, pills: ['T_Q1a✅(0.94)', 'T_Q1b✅(0.92)', 'T_Q3a✅(0.91)', 'T_Q4b✅(0.88)', 'T_Q15b✅(0.90)', 'T_Q19a✅(0.87)'], more: 39 },
            { cat: 'TP', name: 'Tech & Product', passed: 24, total: 25, conf: 0.90, pills: ['TP_Q5a✅(0.97)', 'TP_Q5b✅(0.93)', 'TP_Q6a✅(0.95)', 'TP_Q7a✅(0.96)', 'TP_Q7b✅(0.92)', 'TP_Q7c✅(0.89)'], more: 18 }
        ];

        const humanQuestions = [
            {id:'IS_Q5a', cat:'IS', text:'Describes company culture, mission values, and social purpose', conf:0.75, sugg:1, hasPassage:true},
            {id:'PMF_Q1b', cat:'PMF', text:'Startup articulates why it is a superior option compared to alternatives', conf:0.41, sugg:0, hasPassage:false},
            {id:'PMF_Q12', cat:'PMF', text:'Did the startup identify important psychographic attributes associated with their target audience?', conf:0.55, sugg:0, hasPassage:false},
            {id:'PMF_Q18', cat:'PMF', text:'Has the startup identified and addressed the needs of all key stakeholders?', conf:0.52, sugg:0, hasPassage:false},
            {id:'PMF_Q23', cat:'PMF', text:'Startup has a logo that is discernible when smaller than half an inch.', conf:0.81, sugg:1, hasPassage:false},
            {id:'PMF_Q24', cat:'PMF', text:'Startup has a logo that is discernible when billboard size.', conf:0.77, sugg:1, hasPassage:false},
            {id:'PMF_Q25', cat:'PMF', text:'Startup has a logo that is discernible in greyscale.', conf:0.89, sugg:1, hasPassage:false},
            {id:'PMF_Q26', cat:'PMF', text:'Startup has a cohesive visual design system consistent across email, website, and other assets.', conf:0.45, sugg:0, hasPassage:false},
            {id:'PMF_Q28', cat:'PMF', text:'Startup has a brand strategy based in customer insights.', conf:0.63, sugg:0, hasPassage:false},
            {id:'PMF_Q31', cat:'PMF', text:'Has the startup identified unique value that it can deliver to customers?', conf:0.42, sugg:0, hasPassage:false},
            {id:'PMF_Q34', cat:'PMF', text:'Has the startup validated customer experience pain-points through user research?', conf:0.52, sugg:0, hasPassage:false},
            {id:'M_Q2', cat:'M', text:'Does the startup have a clear operational plan to distribute its product via distribution channels customers use?', conf:0.68, sugg:1, hasPassage:false},
            {id:'M_Q4', cat:'M', text:'Has the startup designed a viral marketing campaign for their product targeted at a specific audience?', conf:0.41, sugg:0, hasPassage:false},
            {id:'M_Q5', cat:'M', text:'Has the startup created engagement mechanisms to allow for different levels of user participation?', conf:0.51, sugg:0, hasPassage:false},
            {id:'M_Q6', cat:'M', text:'Has the startup generated a clear strategy to on-board new users?', conf:0.76, sugg:1, hasPassage:false},
            {id:'TP_Q16', cat:'TP', text:'Is the product ready for manufacture or commercial deployment?', conf:0.70, sugg:1, hasPassage:true},
            {id:'L_Q30', cat:'L', text:'Has the company identified technical information that qualifies as a defensible trade secret?', conf:0.52, sugg:0, hasPassage:true},
            {id:'L_Q31', cat:'L', text:'Has the company identified business information that qualifies as a defensible trade secret?', conf:0.72, sugg:1, hasPassage:false},
            {id:'L_Q47', cat:'L', text:'Are there corporate or equity structural issues that may pose problems for future investors or partners?', conf:0.85, sugg:1, hasPassage:true},
            {id:'T_Q23', cat:'T', text:'Is the team actively using assessment insights to improve founding team dynamics?', conf:0.40, sugg:0, hasPassage:false},
            {id:'T_Q24', cat:'T', text:'Is there a structured approach to engaging the advisory team?', conf:0.84, sugg:1, hasPassage:false},
            {id:'T_Q25', cat:'T', text:'What percent of advisors are actively engaged with the company?', conf:0.78, sugg:1, hasPassage:false},
            {id:'IP_Q5', cat:'IP', text:'Is there a compelling pain point that will make a customer write a check?', conf:0.59, sugg:0, hasPassage:true},
            {id:'IP_Q6', cat:'IP', text:'Is it a must-solve, not merely a nice-to-solve, problem?', conf:0.49, sugg:0, hasPassage:true},
            {id:'IP_Q9', cat:'IP', text:'Are meaningful validating customer quotes included in the presentation?', conf:0.93, sugg:1, hasPassage:true},
            {id:'IP_Q10', cat:'IP', text:'Does the problem framing suggest a genuinely large market opportunity?', conf:0.59, sugg:0, hasPassage:true},
            {id:'IP_Q11', cat:'IP', text:'Is the solution a compelling value proposition clearly benefitting the customer business?', conf:0.45, sugg:0, hasPassage:false},
            {id:'IP_Q13', cat:'IP', text:"Does the solution clearly fit into the customer's existing operational ecosystem?", conf:0.45, sugg:0, hasPassage:false},
            {id:'IP_Q14', cat:'IP', text:'Does the presentation depict differentiation and technical elegance while avoiding the weeds?', conf:0.87, sugg:1, hasPassage:false},
            {id:'IP_Q15', cat:'IP', text:'Does the presentation clearly define the boundaries of the target market?', conf:0.73, sugg:1, hasPassage:false},
            {id:'IP_Q20', cat:'IP', text:'Does the market sizing methodology combine quantitative rigor with qualitative sensitivity?', conf:0.84, sugg:1, hasPassage:false},
            {id:'IP_Q21', cat:'IP', text:'Is there a credible balance between the scale of the opportunity vs. the chance of success?', conf:0.80, sugg:1, hasPassage:false},
            {id:'IP_Q23', cat:'IP', text:'Does the presentation provide a differentiation framework (e.g., BCG grid, benefits matrix)?', conf:0.69, sugg:1, hasPassage:false},
            {id:'IP_Q25', cat:'IP', text:'Does the presentation demonstrate knowledge of the competitive landscape including past failures?', conf:0.94, sugg:1, hasPassage:false},
            {id:'IP_Q30', cat:'IP', text:'Does the presentation remain focused on the essential value proposition without drift?', conf:0.61, sugg:0, hasPassage:false},
            {id:'IP_Q31', cat:'IP', text:'Does it address peripheral issues and details while avoiding clutter?', conf:0.70, sugg:1, hasPassage:false},
            {id:'IP_Q33', cat:'IP', text:'Does it show that the company will invent only uniquely competitive elements?', conf:0.86, sugg:1, hasPassage:false},
            {id:'IP_Q34', cat:'IP', text:'Does it show an incremental development path that reduces risk?', conf:0.74, sugg:1, hasPassage:false},
            {id:'IP_Q43', cat:'IP', text:'Does the presentation show credibility and strategic orchestration of team members?', conf:0.87, sugg:1, hasPassage:true},
            {id:'IP_Q44', cat:'IP', text:'Does the team demonstrate genuine domain expertise and proprietary customer insight?', conf:0.72, sugg:1, hasPassage:false},
            {id:'IP_Q45', cat:'IP', text:'Does the CEO demonstrate the self-awareness to hire leaders with skills better than their own?', conf:0.79, sugg:1, hasPassage:false},
            {id:'IP_Q46', cat:'IP', text:'Does the presentation honestly acknowledge gaps, or demonstrate that nothing critical is missing?', conf:0.43, sugg:0, hasPassage:false},
            {id:'IP_Q49', cat:'IP', text:'Does the Company present thorough and realistic financial forecasts?', conf:0.53, sugg:0, hasPassage:false}
        ];

        let state = {
            answered: 0,
            answers: {},
            activeCardId: null
        };

        const totalQuestions = humanQuestions.length;

        function initAIBlock() {
            const content = document.getElementById('ai-block-content');
            aiCategories.forEach((cat, index) => {
                const header = document.createElement('div');
                header.className = 'px-4 py-3 flex items-center justify-between hover:bg-slate-50 cursor-pointer group';
                header.innerHTML = `
                    <div class="flex items-center gap-3">
                        <span class="cat-${cat.cat} text-xs font-bold px-2 py-0.5 rounded">${cat.cat}</span>
                        <span class="font-medium text-slate-700">${cat.name}</span>
                        <span class="bg-slate-100 text-slate-600 text-xs px-2 py-0.5 rounded-full">${cat.passed}/${cat.total} passed</span>
                        <span class="text-xs text-slate-400">conf: ${cat.conf}</span>
                    </div>
                    <i class="fa-solid fa-chevron-down text-slate-300 group-hover:text-slate-500 transition-transform" id="ai-cat-icon-${index}"></i>
                `;
                
                const detail = document.createElement('div');
                detail.className = 'hidden px-4 pb-3 pt-1 bg-slate-50';
                detail.id = `ai-cat-detail-${index}`;
                
                let pillsHtml = cat.pills.map(p => {
                    let isFail = p.includes('❌');
                    return `<span class="${isFail ? 'bg-red-50 text-red-700 border-red-200' : 'bg-green-50 text-green-700 border-green-200'} border text-xs px-2 py-1 rounded-full whitespace-nowrap shadow-sm">${p}</span>`;
                }).join('');
                
                if (cat.more > 0) {
                    pillsHtml += `<span class="bg-gray-100 text-gray-500 border border-gray-200 text-xs px-2 py-1 rounded-full whitespace-nowrap shadow-sm">+ ${cat.more} more</span>`;
                }

                detail.innerHTML = `<div class="flex flex-wrap gap-2">${pillsHtml}</div>`;

                header.addEventListener('click', () => {
                    detail.classList.toggle('hidden');
                    const icon = document.getElementById(`ai-cat-icon-${index}`);
                    icon.classList.toggle('rotate-180');
                });

                content.appendChild(header);
                content.appendChild(detail);
            });
        }

        document.getElementById('ai-block-header').addEventListener('click', () => {
            document.getElementById('ai-block-content').classList.toggle('hidden');
            document.getElementById('ai-block-icon').classList.toggle('rotate-180');
        });

        function getConfColor(conf) {
            if (conf >= 0.75) return 'bg-green-100 text-green-800 border-green-200';
            if (conf >= 0.50) return 'bg-amber-100 text-amber-800 border-amber-200';
            return 'bg-red-100 text-red-800 border-red-200';
        }

        function getSuggText(sugg, conf) {
            if (sugg === 1) return `YES (${conf.toFixed(2)})`;
            if (sugg === 0 && conf < 0.50) return `UNCERTAIN (${conf.toFixed(2)})`;
            return `NO (${conf.toFixed(2)})`;
        }

        function renderCards() {
            const container = document.getElementById('cards-container');
            container.innerHTML = '';

            humanQuestions.forEach((q, idx) => {
                const isAnswered = state.answers[q.id] !== undefined;
                const card = document.createElement('div');
                card.id = `card-${q.id}`;
                card.className = `bg-white border rounded-lg shadow-sm card-enter ${isAnswered ? 'collapsed-card border-gray-200' : 'border-slate-200 hover:border-slate-300'}`;
                
                if (isAnswered) {
                    const ans = state.answers[q.id];
                    const isConfirmed = (ans === 1 && q.sugg === 1) || (ans === 0 && q.sugg === 0);
                    const txt = isConfirmed ? `✓ Confirmed: ${ans === 1 ? 'YES' : 'NO'}` : `✗ Overridden → ${ans === 1 ? 'YES' : 'NO'}`;
                    const color = ans === 1 ? 'text-green-700' : 'text-red-700';
                    card.innerHTML = `
                        <div class="px-4 py-3 flex items-center justify-between bg-slate-50">
                            <div class="flex items-center gap-3">
                                <span class="cat-${q.cat} text-xs font-bold px-2 py-0.5 rounded w-10 text-center">${q.cat}</span>
                                <span class="text-xs text-slate-500 font-mono w-16">${q.id}</span>
                                <span class="text-sm font-medium ${color}">${txt}</span>
                            </div>
                            <button class="text-xs text-blue-600 hover:underline" onclick="undoAnswer('${q.id}', event)">Undo</button>
                        </div>
                    `;
                } else {
                    card.innerHTML = `
                        <div class="p-5 cursor-pointer" onclick="highlightPassage('${q.id}', ${q.hasPassage})">
                            <div class="flex items-center justify-between mb-3">
                                <div class="flex items-center gap-2">
                                    <span class="cat-${q.cat} text-xs font-bold px-2 py-0.5 rounded shadow-sm">${q.cat}</span>
                                    <span class="text-xs text-slate-500 font-mono bg-slate-100 px-2 py-0.5 rounded border border-slate-200">${q.id}</span>
                                    <span class="text-xs px-2 py-0.5 rounded-full border ${getConfColor(q.conf)}">conf: ${q.conf.toFixed(2)}</span>
                                </div>
                                ${q.hasPassage ? `<button class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-600 px-2 py-1 rounded border border-slate-200 transition-colors" onclick="highlightPassage('${q.id}', true, event)"><i class="fa-regular fa-file-lines mr-1"></i>View in Document</button>` : ''}
                            </div>
                            <p class="text-slate-800 font-medium mb-4 text-base leading-snug">${q.text}</p>
                            <div class="flex items-center justify-between bg-slate-50 p-3 rounded border border-slate-100">
                                <div class="text-sm">
                                    <span class="text-slate-500">🤖 AI Suggests:</span> 
                                    <span class="font-bold text-slate-700 ml-1">${getSuggText(q.sugg, q.conf)}</span>
                                </div>
                                <div class="flex gap-2">
                                    <button class="bg-green-600 hover:bg-green-700 text-white text-sm font-medium px-4 py-1.5 rounded transition shadow-sm" onclick="answerQuestion('${q.id}', ${q.sugg}, event)">✓ Confirm</button>
                                    <button class="bg-slate-600 hover:bg-slate-700 text-white text-sm font-medium px-4 py-1.5 rounded transition shadow-sm" onclick="answerQuestion('${q.id}', ${q.sugg === 1 ? 0 : 1}, event)">✗ Override</button>
                                </div>
                            </div>
                        </div>
                    `;
                }
                container.appendChild(card);
            });
        }

        window.highlightPassage = function(qid, hasPassage, event) {
            if (event) event.stopPropagation();
            
            // clear old highlights
            document.querySelectorAll('.highlight-passage').forEach(el => el.classList.remove('active-highlight'));
            
            if (hasPassage) {
                const el = document.querySelector(`.highlight-passage[data-qid="${qid}"]`);
                if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    el.classList.add('active-highlight');
                }
            }
        };

        window.answerQuestion = function(qid, val, event) {
            event.stopPropagation();
            state.answers[qid] = val;
            state.answered++;
            updateStats();
            renderCards();
        };

        window.undoAnswer = function(qid, event) {
            event.stopPropagation();
            delete state.answers[qid];
            state.answered--;
            updateStats();
            renderCards();
        };

        document.getElementById('reset-btn').addEventListener('click', () => {
            state.answers = {};
            state.answered = 0;
            document.querySelectorAll('.highlight-passage').forEach(el => el.classList.remove('active-highlight'));
            updateStats();
            renderCards();
        });

        function updateStats() {
            const pct = Math.round((state.answered / totalQuestions) * 100);
            
            document.getElementById('header-progress-text').innerText = `${state.answered}/${totalQuestions}`;
            document.getElementById('header-progress-pct').innerText = `${pct}%`;
            document.getElementById('header-progress-bar').style.width = `${pct}%`;
            
            document.getElementById('queue-count-badge').innerText = `${totalQuestions - state.answered} remaining`;
            document.getElementById('bottom-human-count').innerText = `${state.answered} / ${totalQuestions}`;
            
            let yesCount = 0;
            for (let k in state.answers) {
                if (state.answers[k] === 1) yesCount++;
            }
            
            const totalScore = 307 + yesCount;
            const totalPossible = 355;
            const scorePct = ((totalScore / totalPossible) * 100).toFixed(1);
            document.getElementById('bottom-combined-score').innerText = `${totalScore} / ${totalPossible} — ${scorePct}%`;
            
            const timeRemaining = Math.max(0, Math.round(8 - (state.answered * 11 / 60)));
            document.getElementById('time-remaining').innerText = timeRemaining;
        }

        // Init
        initAIBlock();
        renderCards();
        updateStats();

    </script>
</body>
</html>
"""

path = "/Users/geoffrey/Desktop/Scoring_Interface_2025_Prototype.html"
with open(path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"File size: {os.path.getsize(path)} bytes")
