window.CTO = window.CTO || {};

window.CTO.Scoring = {
  // Compute the total scoring denominator dynamically from the loaded rubric catalog.
  // It sums all questions in ai_by_cat that are of type "BINARY" and adds the human questions.
  computeDenominator(rubricData) {
    if (!rubricData) return 349; // fallback based on known current data
    
    let aiBinaryCount = 0;
    for (const cat in rubricData.ai_by_cat) {
      const questions = rubricData.ai_by_cat[cat];
      aiBinaryCount += questions.filter(q => q.type === 'BINARY').length;
    }
    const humanCount = rubricData.human_questions.length;
    return aiBinaryCount + humanCount;
  },

  // Returns 'high', 'medium', or 'low' based on confidence
  confLevel(conf) {
    if (typeof conf !== 'number') return 'medium';
    if (conf >= 0.75) return 'high';
    if (conf >= 0.50) return 'medium';
    return 'low';
  },

  // Compute full scoring state
  computeTotalScore(aiCats, humanAnswers, overrides, denominator) {
    let aiPassed = 0;
    let aiTotal = 0;
    let aiOverridden = 0;
    
    let humanPassed = 0;
    let humanTotal = 0;

    const byCategory = {};

    // Process AI Categories
    for (const cat in aiCats) {
      if (!byCategory[cat]) byCategory[cat] = { passed: 0, total: 0 };
      
      const categoryData = aiCats[cat];
      categoryData.questions.forEach(q => {
        // Skip informational columns (INTEGER type or non-binary verdicts that aren't 4-state)
        // Note: 4-state uses 1, 0, -1, null. We only score 1 and 0 (and overridden).
        if (q.type === 'INTEGER') return;
        if (q.verdict === null || q.verdict === undefined) return; // Legacy Missing (hidden)
        if (q.verdict === -1) {
          aiTotal++; // It's part of the denominator, but automatically fails for now unless overridden?
          byCategory[cat].total++;
          return;
        }

        let isPass = q.verdict === 1;
        
        // Apply override if present
        if (overrides[q.new_q_id] !== undefined) {
          aiOverridden++;
          isPass = overrides[q.new_q_id] === 1;
        }

        aiTotal++;
        byCategory[cat].total++;
        if (isPass) {
          aiPassed++;
          byCategory[cat].passed++;
        }
      });
    }

    // Process Human Answers
    for (const qId in humanAnswers) {
      const val = humanAnswers[qId];
      if (val === 1 || val === 0) {
        humanTotal++;
        
        // Extract category from QID (e.g., "PMF_Q1b" -> "PMF")
        const cat = qId.split('_')[0];
        if (!byCategory[cat]) byCategory[cat] = { passed: 0, total: 0 };
        
        byCategory[cat].total++;
        if (val === 1) {
          humanPassed++;
          byCategory[cat].passed++;
        }
      }
    }

    // Since we're tracking answers dynamically, humanTotal is just answered questions.
    // The denominator is the total possible (e.g., 349).
    const totalPassed = aiPassed + humanPassed;
    // We use the computed denominator. If not all human questions are answered, 
    // the percentage will be lower than the final potential.
    const percentage = denominator > 0 ? Math.round((totalPassed / denominator) * 100) : 0;
    const aiPercentage = aiTotal > 0 ? Math.round((aiPassed / aiTotal) * 100) : 0;

    // Calculate category percentages
    for (const cat in byCategory) {
      const c = byCategory[cat];
      c.pct = c.total > 0 ? Math.round((c.passed / c.total) * 100) : 0;
    }

    return {
      totalPassed,
      totalBinary: denominator, // the fixed denominator
      percentage,
      aiPassed,
      aiTotal,
      aiOverridden,
      aiPercentage,
      humanPassed,
      humanTotal,
      byCategory
    };
  },

  isSubmittable(humanAnswers, totalHumanQuestions) {
    const answeredCount = Object.values(humanAnswers).filter(v => v === 1 || v === 0).length;
    return answeredCount >= totalHumanQuestions;
  },

  // Sort human questions: unanswered first, then by lowest confidence
  sortHumanQueue(questions, answers) {
    return [...questions].sort((a, b) => {
      const aAns = answers[a.new_q_id];
      const bAns = answers[b.new_q_id];
      const aIsAnswered = (aAns === 1 || aAns === 0);
      const bIsAnswered = (bAns === 1 || bAns === 0);

      // Unanswered first
      if (aIsAnswered && !bIsAnswered) return 1;
      if (!aIsAnswered && bIsAnswered) return -1;

      // Then sort by confidence (lowest first)
      const aConf = a.ai_confidence || 0;
      const bConf = b.ai_confidence || 0;
      return aConf - bConf;
    });
  }
};
