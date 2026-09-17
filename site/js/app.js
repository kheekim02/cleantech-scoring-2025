window.CTO = window.CTO || {};

CTO.App = {
  state: {
    activeStartupId: 'solarpure',
    currentStepIndex: 0,
    categories: ['BC', 'ES', 'F', 'IP', 'IS', 'L', 'M', 'PMF', 'T', 'TP'],
    evaluations: {},
    startups: {},
    syncQueue: [] // REC 5: Optimistic Sync Queue
  },

  init() {
    if (window.netlifyIdentity) {
      window.netlifyIdentity.init(); // Initialize widget
      
      const user = window.netlifyIdentity.currentUser();
      if (!user) {
        // Open modal if not logged in
        window.netlifyIdentity.open('login');
        
        window.netlifyIdentity.on("login", user => {
          this.currentUser = user;
          window.netlifyIdentity.close();
          this.startApp();
        });
      } else {
        this.currentUser = user;
        this.startApp();
      }
    } else {
      // Fallback
      this.startApp();
    }
  },

  async startApp() {
    try {
      const res = await fetch('data/startups/solarpure.json');
      const data = await res.json();
      this.state.startups['solarpure'] = data;
    } catch (e) {
      console.error("Failed to load startup", e);
    }

    this.loadState();
    this.setupListeners();
    this.startSyncWorker(); // REC 5
    this.updateUI();
  },

  setupListeners() {
    document.getElementById('btn-prev').addEventListener('click', () => {
      if (this.state.currentStepIndex > 0) {
        this.state.currentStepIndex--;
        this.updateUI();
      }
    });

    document.getElementById('btn-next').addEventListener('click', () => {
      if (this.state.currentStepIndex < this.state.categories.length - 1) {
        this.state.currentStepIndex++;
        this.updateUI();
      } else {
        this.submitEvaluation();
      }
    });

    // REC 4: Event Delegation for human review buttons
    document.getElementById('human-cards-container').addEventListener('click', (e) => {
      const btn = e.target.closest('.h-btn');
      if (!btn) return;
      const qid = btn.dataset.qid;
      const val = parseInt(btn.dataset.val, 10);
      this.answerHuman(qid, val);
    });

    // REC 2: Event Delegation for audit list jumps
    document.getElementById('submit-modal').addEventListener('click', (e) => {
      if (e.target.tagName === 'A' && e.target.dataset.qid) {
        e.preventDefault();
        const catCode = e.target.dataset.cat;
        const qid = e.target.dataset.qid;
        this.jumpToQuestion(catCode, qid);
      }
    });
  },

  updateUI() {
    const sId = this.state.activeStartupId;
    const sData = this.state.startups[sId];
    const sEval = this.state.evaluations[sId];
    
    if (!sData) return;

    const catCode = this.state.categories[this.state.currentStepIndex];
    
    CTO.Render.renderLeftPane(catCode, sData.document);
    CTO.Render.renderRightPane(
      catCode,
      this.state.currentStepIndex,
      this.state.categories.length,
      sData.ai_cats,
      sData.human_questions,
      sEval.humanAnswers
    );
    CTO.Render.renderFooter(
      this.state.currentStepIndex,
      this.state.categories.length
    );
    this.refreshOverallProgress();
  },

  answerHuman(qid, value) {
    const sEval = this.state.evaluations[this.state.activeStartupId];
    
    // Toggle logic
    if (sEval.humanAnswers[qid] === value) {
       delete sEval.humanAnswers[qid]; 
       value = null; // Explicit null for deselection
    } else {
       sEval.humanAnswers[qid] = value;
    }

    // REC 1: Surgical DOM update (no thrashing)
    CTO.Render.updateQuestionState(qid, value);

    // Update progress indicators surgically
    this.refreshOverallProgress();

    // Update step pill counter surgically
    const sData = this.state.startups[this.state.activeStartupId];
    const catCode = this.state.categories[this.state.currentStepIndex];
    const hqs = sData.human_questions.filter(q => q.cat_code === catCode);
    const answeredStep = hqs.filter(q => sEval.humanAnswers[q.new_q_id] !== undefined).length;
    CTO.Render.updateProgressText(answeredStep, hqs.length);

    // REC 5: Optimistic Sync
    this.saveState();
    this.state.syncQueue.push({ qid, value, timestamp: Date.now() });
  },

  refreshOverallProgress() {
    const sId = this.state.activeStartupId;
    const sData = this.state.startups[sId];
    const sEval = this.state.evaluations[sId];
    if (!sData) return;

    const totalHumanQs = sData.human_questions.length;
    const answeredCount = Object.values(sEval.humanAnswers).filter(v => v === 1 || v === 0).length;
    CTO.Render.updateOverallProgress(answeredCount, totalHumanQs);
  },

  submitEvaluation() {
    const sId = this.state.activeStartupId;
    const sData = this.state.startups[sId];
    const sEval = this.state.evaluations[sId];
    
    const missingQs = sData.human_questions.filter(q => sEval.humanAnswers[q.new_q_id] === undefined);
    
    const modal = document.getElementById('submit-modal');
    const title = document.getElementById('modal-title');
    const desc = document.getElementById('modal-desc');
    const auditContainer = document.getElementById('audit-container');
    const auditList = document.getElementById('audit-list');
    const confirmBtn = document.getElementById('modal-confirm-btn');

    // REC 2: The Audit Screen
    if (missingQs.length > 0) {
      title.textContent = 'Incomplete Evaluation';
      title.style.color = 'var(--accent-red)';
      desc.textContent = `You are missing ${missingQs.length} question(s). Please complete them before submitting.`;
      
      auditList.innerHTML = missingQs.map(q => 
        `<li><a href="#" data-cat="${q.cat_code}" data-qid="${q.new_q_id}" style="color: var(--accent-blue); text-decoration: none; font-weight: 600;">[${q.cat_code}] ${q.new_q_id}</a> <span style="color: var(--text-muted);">- ${CTO.Render.categoryNames[q.cat_code]}</span></li>`
      ).join('');
      
      auditContainer.style.display = 'block';
      confirmBtn.style.display = 'none';
    } else {
      title.textContent = 'Evaluation Complete';
      title.style.color = 'inherit';
      desc.textContent = 'All categories have been reviewed. Are you ready to submit this scorecard?';
      auditContainer.style.display = 'none';
      confirmBtn.style.display = 'inline-block';
    }
    
    modal.style.display = 'flex';
  },

  // REC 2: Jump to question
  jumpToQuestion(catCode, qid) {
    document.getElementById('submit-modal').style.display = 'none';
    
    const targetIndex = this.state.categories.indexOf(catCode);
    if (targetIndex !== -1 && targetIndex !== this.state.currentStepIndex) {
      this.state.currentStepIndex = targetIndex;
      this.updateUI();
    }

    // Delay to allow DOM to render if we switched tabs
    setTimeout(() => {
      const card = document.getElementById(`card-${qid}`);
      if (card) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        card.style.transition = 'box-shadow 0.3s';
        card.style.boxShadow = '0 0 0 3px var(--accent-yellow)';
        setTimeout(() => card.style.boxShadow = '0 1px 2px rgba(0,0,0,0.05)', 1500);
      }
    }, 50);
  },

  // REC 5: Background Sync Worker (Updated for JWT / 401 Handling)
  startSyncWorker() {
    setInterval(async () => {
      // Suspend queue if empty or currently attempting to refresh an expired token
      if (this.state.syncQueue.length === 0 || this.state.isRefreshingToken) return;

      const batch = [...this.state.syncQueue];
      this.state.syncQueue = []; // Optimistically clear
      
      try {
        const token = window.netlifyIdentity?.currentUser()?.token?.access_token;
        if (!token) {
           console.log("No token available, skipping sync.");
           this.state.syncQueue.unshift(...batch);
           return;
        }

        console.log(`[Sync Worker] Dispatching ${batch.length} updates...`);
        
        const res = await fetch('/.netlify/functions/sync-scores', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            startup_id: 'solarpure_inc', // Connected to the mock/demo startup
            scores: batch.map(b => ({ qid: b.qid, val: b.value }))
          })
        });

        if (res.status === 401) {
          throw new Error("401_UNAUTHORIZED");
        }
        if (!res.ok) throw new Error("NETWORK_ERROR");

      } catch (error) {
        // Restore batch to queue to prevent data loss
        this.state.syncQueue.unshift(...batch);
        
        if (error.message === "401_UNAUTHORIZED") {
           console.warn("JWT Expired. Suspending queue and requesting silent token refresh...");
           this.state.isRefreshingToken = true;
           
           if (window.netlifyIdentity) {
             window.netlifyIdentity.refresh().then((jwt) => {
               console.log("Token refreshed silently. Resuming sync queue.");
               this.state.isRefreshingToken = false;
             }).catch(() => {
               alert('Your session has expired. Please re-authenticate to save your latest scores.');
               window.netlifyIdentity.open('login');
             });
           }
        }
      }
    }, 3000);
  },

  loadState() {
    const sId = this.state.activeStartupId;
    if (!this.state.evaluations[sId]) {
      this.state.evaluations[sId] = { humanAnswers: {} };
    }
    try {
      const stored = localStorage.getItem('cto2025_state');
      if (stored) {
        const data = JSON.parse(stored);
        if (data[sId]) this.state.evaluations[sId] = data[sId];
      }
    } catch (e) {}
  },

  saveState() {
    try {
      const stored = localStorage.getItem('cto2025_state');
      let data = stored ? JSON.parse(stored) : {};
      data[this.state.activeStartupId] = this.state.evaluations[this.state.activeStartupId];
      localStorage.setItem('cto2025_state', JSON.stringify(data));
    } catch (e) {}
  }
};

document.addEventListener('DOMContentLoaded', () => CTO.App.init());
