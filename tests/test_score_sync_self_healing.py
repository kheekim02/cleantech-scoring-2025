"""Falsifiable verification suite for localStorage-to-DB score synchronization self-healing."""
import json
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
APP_JS_PATH = ROOT / "site" / "js" / "app.js"
SYNC_SCORES_JS_PATH = ROOT / "api" / "sync-scores.js"
INDEX_HTML_PATH = ROOT / "site" / "index.html"
RUBRIC_PATH = ROOT / "master_282_rubric.json"


NODE_HARNESS_PREAMBLE = r"""
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT_DIR = process.cwd();
const RUBRIC = JSON.parse(fs.readFileSync(path.join(ROOT_DIR, 'master_282_rubric.json'), 'utf8'));

class RelationalDB {
  constructor() {
    this.reviews = new Map(); // key: `${startup_id}::${judge_id}::${question_id}`
    this.assignments = new Set(); // key: `${judge_id}::${startup_id}`
    this.startups = new Set(); // key: `${startup_id}`
    this.queries = [];
  }

  _key(startup_id, judge_id, question_id) {
    return `${startup_id}::${judge_id}::${question_id}`;
  }

  seedStartup(startup_id, judge_id) {
    this.startups.add(startup_id);
    this.assignments.add(`${judge_id}::${startup_id}`);
  }

  upsertRow(startup_id, judge_id, question_id, score_value, justification = '', is_flagged = false) {
    const key = this._key(startup_id, judge_id, question_id);
    this.reviews.set(key, {
      startup_id,
      judge_id,
      question_id,
      score_value: score_value !== undefined ? score_value : null,
      justification: justification !== undefined && justification !== null ? String(justification) : '',
      is_flagged: Boolean(is_flagged)
    });
  }

  getRow(startup_id, judge_id, question_id) {
    const r = this.reviews.get(this._key(startup_id, judge_id, question_id));
    return r ? { ...r } : null;
  }

  getReviewsForStartup(startup_id, judge_id) {
    const out = [];
    for (const r of this.reviews.values()) {
      if (r.startup_id === startup_id && r.judge_id === judge_id) {
        out.push({ ...r });
      }
    }
    return out;
  }

  getAnsweredCount(startup_id, judge_id) {
    let count = 0;
    for (const r of this.reviews.values()) {
      if (
        r.startup_id === startup_id &&
        r.judge_id === judge_id &&
        r.score_value !== null &&
        r.score_value !== undefined &&
        !Number.isNaN(Number(r.score_value))
      ) {
        count++;
      }
    }
    return count;
  }

  async query(sql, params = []) {
    this.queries.push({ sql, params });
    const norm = sql.replace(/\s+/g, ' ').trim();

    if (norm.includes('FROM judge_assignments')) {
      const [judge_id, startup_id] = params;
      if (this.assignments.has(`${judge_id}::${startup_id}`)) {
        return { rows: [{ '?column?': 1 }] };
      }
      return { rows: [] };
    }

    if (norm.includes('FROM startup_extractions')) {
      const [startup_id] = params;
      if (this.startups.has(startup_id)) {
        return { rows: [{ '?column?': 1 }] };
      }
      return { rows: [] };
    }

    if (norm.includes('INSERT INTO human_reviews')) {
      const [startup_id, judge_id, questionIds, scoreValues, justifications, flagValues, hasJustificationArr] = params;
      const preservesEmptyViaSql =
        /NULLIF\s*\(\s*EXCLUDED\.justification/i.test(norm) ||
        /CASE\s+WHEN/i.test(norm) ||
        /COALESCE\s*\(\s*EXCLUDED\.justification\s*,\s*human_reviews\.justification\s*\)/i.test(norm);

      for (let i = 0; i < questionIds.length; i++) {
        const qid = questionIds[i];
        const scoreVal = scoreValues[i];
        const justVal = justifications[i];
        const flagVal = flagValues[i];
        const explicitJust = Array.isArray(hasJustificationArr) ? hasJustificationArr[i] : undefined;

        const key = this._key(startup_id, judge_id, qid);
        const existing = this.reviews.get(key);
        if (!existing) {
          this.reviews.set(key, {
            startup_id,
            judge_id,
            question_id: qid,
            score_value: scoreVal !== undefined ? scoreVal : null,
            justification: justVal !== null && justVal !== undefined ? String(justVal) : '',
            is_flagged: Boolean(flagVal)
          });
        } else {
          if (scoreVal !== null && scoreVal !== undefined) {
            existing.score_value = scoreVal;
          }
          if (explicitJust === false || justVal === null || justVal === undefined) {
            // preserve existing.justification
          } else if (justVal === '' && preservesEmptyViaSql) {
            // preserve existing.justification when SQL guards against empty overwrite
          } else {
            existing.justification = String(justVal);
          }
          if (flagVal !== null && flagVal !== undefined) {
            existing.is_flagged = Boolean(flagVal);
          }
        }
      }
      return { rows: [] };
    }

    if (norm.includes('FROM human_reviews') && /COUNT\s*\(/i.test(norm)) {
      const [startup_id, judge_id] = params;
      const answered_count = this.getAnsweredCount(startup_id, judge_id);
      return { rows: [{ answered_count }] };
    }

    return { rows: [] };
  }
}

function createSyncScoresHandler(db, sessionState = { principalId: 'aditya', isTest: false }) {
  const dbPath = require.resolve('./api/_db');
  const authPath = require.resolve('./api/_auth');
  const syncPath = require.resolve('./api/sync-scores');

  delete require.cache[syncPath];
  require.cache[dbPath] = {
    id: dbPath,
    filename: dbPath,
    loaded: true,
    exports: {
      pool: {
        query: (sql, params) => db.query(sql, params)
      }
    }
  };
  require.cache[authPath] = {
    id: authPath,
    filename: authPath,
    loaded: true,
    exports: {
      async requireSession() { return { principalId: sessionState.principalId }; },
      async isTestScorer() { return Boolean(sessionState.isTest); }
    }
  };

  const syncScores = require('./api/sync-scores');
  return async function invokeSyncScores(bodyObj) {
    let statusCode = 200;
    let responseData = null;
    const req = { method: 'POST', body: bodyObj };
    const res = {
      status(c) { statusCode = c; return this; },
      json(d) { responseData = d; return this; },
      send(d) { responseData = d; return this; }
    };
    await syncScores(req, res);
    return {
      ok: statusCode >= 200 && statusCode < 300,
      status: statusCode,
      data: responseData,
      async json() { return responseData; }
    };
  };
}

function createHarness(options = {}) {
  const storageMap = new Map(Object.entries(options.localStorage || {}));
  const localStorage = {
    getItem(k) { return storageMap.has(k) ? storageMap.get(k) : null; },
    setItem(k, v) { storageMap.set(k, String(v)); },
    removeItem(k) { storageMap.delete(k); },
    _dump() { return Object.fromEntries(storageMap.entries()); }
  };

  const elements = new Map();
  function makeElement(id) {
    const el = {
      id,
      style: {
        display: '',
        background: '',
        color: '',
        border: '',
        boxShadow: '',
        transition: '',
        _props: {},
        setProperty(k, v) { this._props[k] = v; },
        getPropertyValue(k) { return this._props[k] || ''; }
      },
      dataset: {},
      className: '',
      innerHTML: '',
      textContent: '',
      value: '',
      title: '',
      disabled: false,
      scrollTop: 0,
      parentElement: { classList: { add() {}, remove() {}, toggle() {} } },
      classList: {
        _set: new Set(),
        add(c) { this._set.add(c); },
        remove(c) { this._set.delete(c); },
        toggle(c, force) {
          if (force === undefined) {
            if (this._set.has(c)) this._set.delete(c);
            else this._set.add(c);
          } else if (force) {
            this._set.add(c);
          } else {
            this._set.delete(c);
          }
        },
        contains(c) { return this._set.has(c); }
      },
      listeners: {},
      addEventListener(type, fn) {
        if (!this.listeners[type]) this.listeners[type] = [];
        this.listeners[type].push(fn);
      },
      removeEventListener() {},
      querySelector() { return makeElement(id + ':child'); },
      getBoundingClientRect() { return { width: 1200, left: 0 }; },
      setAttribute(k, v) { this[k] = v; },
      scrollIntoView() {},
      focus() {},
      closest() { return null; }
    };
    return el;
  }

  function getElement(id) {
    if (!elements.has(id)) {
      elements.set(id, makeElement(id));
    }
    return elements.get(id);
  }

  const docListeners = {};
  const winListeners = {};
  const fetchCalls = [];
  const scheduledTimeouts = [];

  const fetchImpl = options.fetch || (async (url, init = {}) => {
    fetchCalls.push({ url, init });
    if (options.syncHandler && String(url).startsWith('/api/sync-scores')) {
      const parsedBody = typeof init.body === 'string' ? JSON.parse(init.body) : init.body;
      return options.syncHandler(parsedBody, init);
    }
    return {
      ok: true,
      status: 200,
      async json() {
        return options.fetchJsonResponse || {
          success: true,
          startup_id: 'Renovigo_Chemicals',
          answered_count: 282,
          is_submitted: true
        };
      }
    };
  });

  const windowObj = {
    location: { search: options.locationSearch || '' },
    CTO: {
      Render: {
        escapeHtml(s) { return String(s ?? ''); },
        renderLeftPane() {},
        renderSectionDropdown() {},
        renderRightPane() {},
        renderFooter() {},
        updateQuestionState() {},
        updateProgressText() {},
        updateFlagState() {},
        updateFlaggedNavBadge() {},
        updateOverallProgress() {},
        formatPoints(v) { return `${v} pts`; },
        categoryNames: {
          BC: 'Business Canvas',
          ES: 'Environmental & Social',
          F: 'Financials',
          IP: 'Investor Pitch',
          IS: 'Executive Summary',
          L: 'Legal',
          M: 'Market',
          PMF: 'Product Market Fit',
          T: 'Team',
          TP: 'Tech / Product'
        }
      }
    },
    addEventListener(type, fn) {
      if (!winListeners[type]) winListeners[type] = [];
      winListeners[type].push(fn);
    },
    removeEventListener() {},
    requestAnimationFrame() { return 1; },
    cancelAnimationFrame() {}
  };

  const documentObj = {
    body: makeElement('body'),
    visibilityState: 'visible',
    getElementById(id) { return getElement(id); },
    querySelector(sel) { return getElement(sel); },
    querySelectorAll() { return []; },
    addEventListener(type, fn) {
      if (!docListeners[type]) docListeners[type] = [];
      docListeners[type].push(fn);
    }
  };

  let currentNow = options.initialNow || 1000;
  const CustomDate = class extends Date {
    static now() { return currentNow; }
  };

  const sandbox = {
    window: windowObj,
    document: documentObj,
    localStorage,
    URLSearchParams,
    Date: CustomDate,
    Buffer,
    fetch: (...args) => fetchImpl(...args),
    setTimeout(fn, ms) {
      const id = scheduledTimeouts.length + 1;
      scheduledTimeouts.push({ id, fn, ms, cleared: false });
      return id;
    },
    clearTimeout(id) {
      const item = scheduledTimeouts.find(t => t.id === id);
      if (item) item.cleared = true;
    },
    setInterval() { return 1; },
    clearInterval() {},
    requestAnimationFrame() { return 1; },
    cancelAnimationFrame() {},
    alert() {},
    console
  };

  const appCode = fs.readFileSync(options.appJsPath || path.join(ROOT_DIR, 'site/js/app.js'), 'utf8');
  vm.createContext(sandbox);
  vm.runInContext(appCode, sandbox, { filename: 'app.js' });

  return {
    CTO: sandbox.window.CTO,
    elements,
    getElement,
    localStorage,
    fetchCalls,
    scheduledTimeouts,
    docListeners,
    winListeners,
    setNow(t) { currentNow = t; },
    getNow() { return currentNow; }
  };
}
"""


def run_node_script(script_body: str) -> dict:
    full_script = NODE_HARNESS_PREAMBLE + "\n" + textwrap.dedent(script_body)
    proc = subprocess.run(
        ["node", "-e", full_script],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"Node script failed (exit {proc.returncode}):\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise AssertionError(f"Node script produced no stdout. STDERR:\n{proc.stderr}")
    return json.loads(lines[-1])


class TestScoreSyncSelfHealing(unittest.TestCase):
    """Falsifiable verification suite for localStorage-to-DB score synchronization."""

    def test_01_cohort_replay_differential_all_5_evaluators(self):
        """Replay all 5 affected production evaluator/startup pairs against real master_282_rubric.json."""
        res = run_node_script(
            r"""
            const cases = [
              { judge: 'aditya', startup: 'Renovigo_Chemicals', name: 'Renovigo Chemicals', missing: ['F_Q1'] },
              { judge: 'stephanie', startup: 'Foregger_Energy_Solutions', name: 'Foregger Energy Solutions', missing: ['IP_Q13'] },
              { judge: 'brittany', startup: 'CIRQ+', name: 'CIRQ+', missing: ['T_Q21'] },
              { judge: 'vishal', startup: 'ECORECYCLETECH', name: 'ECORECYCLETECH', missing: ['ES_Q5'] },
              { judge: 'suehyun', startup: 'Materium_Technologies', name: 'Materium Technologies', missing: ['IS_Q8', 'TP_Q5', 'TP_Q6'] }
            ];

            (async () => {
              const results = [];
              for (const c of cases) {
                const db = new RelationalDB();
                db.seedStartup(c.startup, c.judge);
                const syncHandler = createSyncScoresHandler(db, { principalId: c.judge, isTest: false });

                const missingSet = new Set(c.missing);
                const localAnswers = {};
                const localJustifications = {
                  BC_Q1: `BC_Q1 note by ${c.judge}`,
                  BC_Q2: `BC_Q2 note by ${c.judge}`,
                  BC_Q4: `BC_Q4 note by ${c.judge}`,
                  BC_Q5: `BC_Q5 note by ${c.judge}`
                };

                for (const q of RUBRIC) {
                  const qid = q.new_q_id || q.q_id;
                  const validVal = Array.isArray(q.options) && q.options.length > 0
                    ? Number(q.options[q.options.length - 1].val)
                    : 1;
                  localAnswers[qid] = validVal;
                  if (!missingSet.has(qid)) {
                    db.upsertRow(c.startup, c.judge, qid, validVal, localJustifications[qid] || '', false);
                  }
                }

                const initialDbCount = db.getAnsweredCount(c.startup, c.judge);
                const storedState = {
                  [`${c.judge}:${c.startup}`]: {
                    humanAnswers: localAnswers,
                    humanJustifications: localJustifications,
                    humanFlags: {}
                  }
                };

                const h = createHarness({
                  localStorage: { cto2025_state: JSON.stringify(storedState) },
                  syncHandler
                });
                const App = h.CTO.App;
                App.currentUser = { id: c.judge, is_test: false };
                App.state.activeStartupId = c.startup;
                App.state.startupsList = [{
                  id: c.startup,
                  name: c.name,
                  answered_count: initialDbCount,
                  is_submitted: false
                }];
                App.state.startups[c.startup] = {
                  startup_id: c.startup,
                  human_questions: RUBRIC,
                  judge_reviews: db.getReviewsForStartup(c.startup, c.judge)
                };

                App.renderStartupPickerOptions(App.state.startupsList);
                App.loadState();
                App.updateStartupStatusPill();

                const pillBeforeFlush = h.getElement('startup-status-pill').innerHTML;
                const queuedBeforeFlush = App._syncMap.size;
                await App.flushSyncQueue();

                const finalDbCount = db.getAnsweredCount(c.startup, c.judge);
                const pillAfterFlush = h.getElement('startup-status-pill').innerHTML;
                const pickerAfterFlush = h.getElement('startup-picker').innerHTML;
                const bcQ1Row = db.getRow(c.startup, c.judge, 'BC_Q1');

                results.push({
                  judge: c.judge,
                  startup: c.startup,
                  expectedMissingCount: c.missing.length,
                  initialDbCount,
                  queuedBeforeFlush,
                  finalDbCount,
                  pillBeforeFlush,
                  pillAfterFlush,
                  pickerHasSubmitted: pickerAfterFlush.includes(`✓ ${c.name} (Submitted)`),
                  bcQ1JustificationPreserved: bcQ1Row && bcQ1Row.justification === `BC_Q1 note by ${c.judge}`
                });
              }
              console.log(JSON.stringify({ results }));
            })();
            """
        )
        for item in res["results"]:
            label = f"{item['judge']} / {item['startup']}"
            self.assertNotEqual(
                item["pillBeforeFlush"],
                "✓ Submitted",
                f"[{label}] Pill must not show Submitted before DB confirms 282",
            )
            self.assertEqual(
                item["queuedBeforeFlush"],
                item["expectedMissingCount"],
                f"[{label}] loadState() must enqueue exactly the {item['expectedMissingCount']} missing question(s)",
            )
            self.assertEqual(
                item["finalDbCount"],
                282,
                f"[{label}] DB must reach 282/282 after 1 flush cycle",
            )
            self.assertEqual(
                item["pillAfterFlush"],
                "✓ Submitted",
                f"[{label}] Pill must update to '✓ Submitted' after DB confirms 282",
            )
            self.assertTrue(
                item["pickerHasSubmitted"],
                f"[{label}] Startup picker option must update to '✓ <Company> (Submitted)'",
            )
            self.assertTrue(
                item["bcQ1JustificationPreserved"],
                f"[{label}] Pre-existing BC_Q1 justification must be preserved intact",
            )

    def test_02_out_of_order_inflight_concurrency_race_no_clobber(self):
        """Stale in-flight Batch 1 failing after newer Batch 2 succeeds must not clobber newer state."""
        res = run_node_script(
            r"""
            (async () => {
              const db = new RelationalDB();
              db.seedStartup('Renovigo_Chemicals', 'aditya');
              const realSync = createSyncScoresHandler(db, { principalId: 'aditya', isTest: false });

              let callIndex = 0;
              let rejectBatch1 = null;
              const batch1Started = new Promise((resolve) => {
                // captured below
              });
              let markBatch1Started;
              const batch1Barrier = new Promise((resolve, reject) => {
                rejectBatch1 = reject;
              });

              const h = createHarness({
                initialNow: 100,
                fetch: async (url, init = {}) => {
                  callIndex++;
                  const body = JSON.parse(init.body);
                  if (callIndex === 1) {
                    // Hold Batch 1 (F_Q1 = 0 at t=100) in flight until Batch 2 finishes
                    await batch1Barrier;
                    return { ok: false, status: 503, async json() { return { error: 'Service Unavailable' }; } };
                  }
                  // Batch 2 (F_Q1 = 1 at t=200) succeeds immediately against DB
                  return realSync(body);
                }
              });

              const App = h.CTO.App;
              App.currentUser = { id: 'aditya', is_test: false };
              App.state.activeStartupId = 'Renovigo_Chemicals';
              App.state.startupsList = [{
                id: 'Renovigo_Chemicals',
                name: 'Renovigo Chemicals',
                answered_count: 0,
                is_submitted: false
              }];
              App.state.startups['Renovigo_Chemicals'] = {
                startup_id: 'Renovigo_Chemicals',
                human_questions: RUBRIC,
                judge_reviews: []
              };
              App.loadState();

              // Step 1: User clicks F_Q1 = 0 at t=100 and Flush #1 starts
              h.setNow(100);
              App.answerHuman('F_Q1', 0);
              const flush1Promise = App.flushSyncQueue();

              // Step 2: While Flush #1 is in flight, user clicks F_Q1 = 1 at t=200 and Flush #2 completes
              h.setNow(200);
              App.answerHuman('F_Q1', 1);
              const flush2Result = await App.flushSyncQueue();

              // Step 3: Now Batch 1 fails with transient 503 error
              rejectBatch1(new Error('503_TRANSIENT'));
              await flush1Promise;

              // Step 4: If anything was requeued into _syncMap, flush it to see if it clobbers DB
              await App.flushSyncQueue();

              const finalLocalVal = App.state.evaluations['Renovigo_Chemicals'].humanAnswers['F_Q1'];
              const finalDbRow = db.getRow('Renovigo_Chemicals', 'aditya', 'F_Q1');
              const syncMapEntry = App._syncMap.get('Renovigo_Chemicals:F_Q1') || null;

              console.log(JSON.stringify({
                flush2Result,
                finalLocalVal,
                finalDbVal: finalDbRow ? finalDbRow.score_value : null,
                syncMapSize: App._syncMap.size,
                syncMapVal: syncMapEntry ? syncMapEntry.value : null
              }));
            })();
            """
        )
        self.assertEqual(
            res["finalLocalVal"],
            1,
            "sEval.humanAnswers['F_Q1'] must remain 1 (newer click at t=200)",
        )
        self.assertEqual(
            res["finalDbVal"],
            1,
            "Database score_value for F_Q1 must NOT be reverted to 0 by stale Batch 1 requeue",
        )
        self.assertEqual(res["syncMapSize"], 0)

    def test_03_cross_startup_justification_and_completed_db_anti_clobber(self):
        """Cross-startup reconciliation must preserve DB justifications; completed DB must not regress from partial local draft."""
        res = run_node_script(
            r"""
            (async () => {
              // Part A: Cross-startup reconciliation with empty localStorage justifications
              const db = new RelationalDB();
              db.seedStartup('Renovigo_Chemicals', 'aditya');
              db.seedStartup('CH4_Microbial_Solutions', 'aditya');
              const syncHandler = createSyncScoresHandler(db, { principalId: 'aditya', isTest: false });

              const localAnswersA = {};
              for (const q of RUBRIC) {
                const qid = q.new_q_id || q.q_id;
                const validVal = Array.isArray(q.options) && q.options.length > 0
                  ? Number(q.options[q.options.length - 1].val)
                  : 1;
                localAnswersA[qid] = validVal;
                if (qid !== 'F_Q1') {
                  const just = qid === 'BC_Q1' ? 'Detailed moat analysis' : '';
                  db.upsertRow('Renovigo_Chemicals', 'aditya', qid, validVal, just, false);
                }
              }

              const storedStateA = {
                'aditya:Renovigo_Chemicals': {
                  humanAnswers: localAnswersA,
                  humanJustifications: {}, // Empty in localStorage!
                  humanFlags: {}
                }
              };

              const hA = createHarness({
                localStorage: { cto2025_state: JSON.stringify(storedStateA) },
                syncHandler
              });
              const AppA = hA.CTO.App;
              AppA.applyBootstrapPayload({
                user: { id: 'aditya', is_test: false },
                active_startup_id: 'CH4_Microbial_Solutions',
                active_startup: {
                  startup_id: 'CH4_Microbial_Solutions',
                  meta: { name: 'CH4 Microbial Solutions' },
                  human_questions: RUBRIC,
                  judge_reviews: []
                },
                startups: [
                  { id: 'CH4_Microbial_Solutions', name: 'CH4 Microbial Solutions', answered_count: 282, is_submitted: true },
                  { id: 'Renovigo_Chemicals', name: 'Renovigo Chemicals', answered_count: 281, is_submitted: false }
                ]
              });

              await AppA.flushSyncQueue();
              const renovigoCountAfterA = db.getAnsweredCount('Renovigo_Chemicals', 'aditya');
              const bcQ1AfterA = db.getRow('Renovigo_Chemicals', 'aditya', 'BC_Q1');

              // Part B: Completed 282/282 DB state vs stale incomplete 270-question localStorage draft
              const fullReviewsB = [];
              const staleLocalAnswersB = {};
              let idx = 0;
              for (const q of RUBRIC) {
                idx++;
                const qid = q.new_q_id || q.q_id;
                const validVal = Array.isArray(q.options) && q.options.length > 0
                  ? Number(q.options[q.options.length - 1].val)
                  : 1;
                const minVal = Array.isArray(q.options) && q.options.length > 0
                  ? Number(q.options[0].val)
                  : 0;
                fullReviewsB.push({
                  question_id: qid,
                  score_value: qid === 'F_Q1' ? 1 : validVal,
                  justification: qid === 'BC_Q1' ? 'Authoritative DB justification' : '',
                  is_flagged: false
                });
                if (idx <= 270) {
                  staleLocalAnswersB[qid] = qid === 'F_Q1' ? 0 : minVal;
                }
              }

              const storedStateB = {
                'aditya:Renovigo_Chemicals': {
                  humanAnswers: staleLocalAnswersB,
                  humanJustifications: {},
                  humanFlags: {}
                }
              };

              const hB = createHarness({
                localStorage: { cto2025_state: JSON.stringify(storedStateB) }
              });
              const AppB = hB.CTO.App;
              AppB.currentUser = { id: 'aditya', is_test: false };
              AppB.state.activeStartupId = 'Renovigo_Chemicals';
              AppB.state.startupsList = [{
                id: 'Renovigo_Chemicals',
                name: 'Renovigo Chemicals',
                answered_count: 282,
                is_submitted: true
              }];
              AppB.state.startups['Renovigo_Chemicals'] = {
                startup_id: 'Renovigo_Chemicals',
                human_questions: RUBRIC,
                judge_reviews: fullReviewsB
              };

              AppB.loadState();

              console.log(JSON.stringify({
                renovigoCountAfterA,
                bcQ1JustificationAfterA: bcQ1AfterA ? bcQ1AfterA.justification : null,
                partBFQ1Answer: AppB.state.evaluations['Renovigo_Chemicals'].humanAnswers['F_Q1'],
                partBBCQ1Justification: AppB.state.evaluations['Renovigo_Chemicals'].humanJustifications['BC_Q1'],
                partBSyncMapSize: AppB._syncMap.size
              }));
            })();
            """
        )
        self.assertEqual(
            res["renovigoCountAfterA"],
            282,
            "Cross-startup reconciliation must sync the missing F_Q1 answer for Renovigo_Chemicals",
        )
        self.assertEqual(
            res["bcQ1JustificationAfterA"],
            "Detailed moat analysis",
            "Cross-startup reconciliation with empty localStorage justifications must NOT erase DB justification on BC_Q1",
        )
        self.assertEqual(
            res["partBFQ1Answer"],
            1,
            "When DB has 282/282 completed answers, stale incomplete 270-answer localStorage draft must NOT overwrite DB score F_Q1=1 with 0",
        )
        self.assertEqual(
            res["partBBCQ1Justification"],
            "Authoritative DB justification",
        )
        self.assertEqual(
            res["partBSyncMapSize"],
            0,
            "Stale incomplete localStorage draft must not enqueue regression updates when DB already has 282/282",
        )

    def test_04_poison_pill_local_storage_quarantine_and_no_400_infinite_loop(self):
        """Poison-pill entries in localStorage must be quarantined so valid answers sync without 400 loops."""
        res = run_node_script(
            r"""
            (async () => {
              const db = new RelationalDB();
              db.seedStartup('Renovigo_Chemicals', 'aditya');
              const syncHandler = createSyncScoresHandler(db, { principalId: 'aditya', isTest: false });

              const localAnswers = {};
              for (const q of RUBRIC) {
                const qid = q.new_q_id || q.q_id;
                const validVal = Array.isArray(q.options) && q.options.length > 0
                  ? Number(q.options[q.options.length - 1].val)
                  : 1;
                localAnswers[qid] = validVal;
                if (qid !== 'F_Q1') {
                  db.upsertRow('Renovigo_Chemicals', 'aditya', qid, validVal, '', false);
                }
              }

              // Inject poison-pill entries into localStorage
              localAnswers['LEGACY_DELETED_Q99'] = 1;
              localAnswers['BC_Q3'] = 0.999;
              localAnswers['ES_Q1'] = 'not_a_number';

              const storedState = {
                'aditya:Renovigo_Chemicals': {
                  humanAnswers: localAnswers,
                  humanJustifications: {},
                  humanFlags: {}
                }
              };

              let status400Count = 0;
              const h = createHarness({
                localStorage: { cto2025_state: JSON.stringify(storedState) },
                syncHandler: async (body, init) => {
                  const resp = await syncHandler(body, init);
                  if (resp.status === 400) status400Count++;
                  return resp;
                }
              });

              const App = h.CTO.App;
              App.currentUser = { id: 'aditya', is_test: false };
              App.state.activeStartupId = 'Renovigo_Chemicals';
              App.state.startupsList = [{
                id: 'Renovigo_Chemicals',
                name: 'Renovigo Chemicals',
                answered_count: 281,
                is_submitted: false
              }];
              App.state.startups['Renovigo_Chemicals'] = {
                startup_id: 'Renovigo_Chemicals',
                human_questions: RUBRIC,
                judge_reviews: db.getReviewsForStartup('Renovigo_Chemicals', 'aditya')
              };

              App.loadState();
              if (typeof App.reconcileAllStartupsFromLocalStorage === 'function') {
                App.reconcileAllStartupsFromLocalStorage();
              }
              const flushOk = await App.flushSyncQueue();
              const dbCountAfterPoison = db.getAnsweredCount('Renovigo_Chemicals', 'aditya');
              const syncMapAfterPoison = App._syncMap.size;

              // Also test direct 400 response from server: flushSyncQueue must drop 400 batch rather than infinite-loop requeue
              const h400 = createHarness({
                fetch: async () => ({
                  ok: false,
                  status: 400,
                  async json() { return { error: 'Invalid score for F_Q1' }; }
                })
              });
              const App400 = h400.CTO.App;
              App400.currentUser = { id: 'aditya', is_test: false };
              App400.state.activeStartupId = 'Renovigo_Chemicals';
              App400.enqueueSync({ startup_id: 'Renovigo_Chemicals', qid: 'F_Q1', value: 1, justification: '' });
              await App400.flushSyncQueue();
              const syncMapAfter400 = App400._syncMap.size;

              console.log(JSON.stringify({
                flushOk,
                status400Count,
                dbCountAfterPoison,
                syncMapAfterPoison,
                syncMapAfter400
              }));
            })();
            """
        )
        self.assertEqual(
            res["status400Count"],
            0,
            "Client must sanitize/quarantine poisoned localStorage entries before sending to /api/sync-scores",
        )
        self.assertEqual(
            res["dbCountAfterPoison"],
            282,
            "Valid F_Q1=1 answer must still be persisted to reach 282/282 despite poisoned siblings in localStorage",
        )
        self.assertEqual(res["syncMapAfterPoison"], 0)
        self.assertEqual(
            res["syncMapAfter400"],
            0,
            "HTTP 400 client validation failure must NOT be infinitely re-queued into _syncMap",
        )

    def test_05_keepalive_64kb_chunking_boundary(self):
        """flushSyncWithKeepalive must chunk large batches so every keepalive request body is <= 60,000 bytes; index.html ?v=32."""
        index_html = INDEX_HTML_PATH.read_text(encoding="utf-8")
        for asset in ("style.css?v=32", "js/scoring.js?v=32", "js/render.js?v=32", "js/app.js?v=32"):
            self.assertTrue(
                asset in index_html,
                f"site/index.html must reference {asset}",
            )

        res = run_node_script(
            r"""
            const h = createHarness();
            const App = h.CTO.App;
            App.currentUser = { id: 'aditya', is_test: false };
            App.state.activeStartupId = 'Renovigo_Chemicals';

            const longText = 'X'.repeat(4500);
            for (let i = 0; i < RUBRIC.length; i++) {
              const q = RUBRIC[i];
              const qid = q.new_q_id || q.q_id;
              const validVal = Array.isArray(q.options) && q.options.length > 0
                ? Number(q.options[q.options.length - 1].val)
                : 1;
              App.enqueueSync({
                startup_id: 'Renovigo_Chemicals',
                qid,
                value: validVal,
                justification: i < 30 ? longText : 'short note'
              });
            }

            const hasKeepaliveFn = typeof App.flushSyncWithKeepalive === 'function';
            if (hasKeepaliveFn) {
              App.flushSyncWithKeepalive();
            }

            const keepaliveCalls = h.fetchCalls.filter(c => c.init && c.init.keepalive === true);
            const byteLengths = keepaliveCalls.map(c => Buffer.byteLength(c.init.body || '', 'utf8'));
            const syncedQids = new Set();
            for (const c of keepaliveCalls) {
              const parsed = JSON.parse(c.init.body);
              for (const s of (parsed.scores || [])) {
                syncedQids.add(s.qid);
              }
            }

            console.log(JSON.stringify({
              hasKeepaliveFn,
              keepaliveCallCount: keepaliveCalls.length,
              maxByteLength: byteLengths.length ? Math.max(...byteLengths) : 0,
              totalBytes: byteLengths.reduce((a, b) => a + b, 0),
              syncedQidCount: syncedQids.size
            }));
            """
        )
        self.assertTrue(res["hasKeepaliveFn"], "CTO.App.flushSyncWithKeepalive must be defined")
        self.assertGreaterEqual(
            res["keepaliveCallCount"],
            3,
            "135KB+ payload must be split across at least 3 keepalive requests",
        )
        self.assertLessEqual(
            res["maxByteLength"],
            60000,
            "Every keepalive request body must be <= 60,000 bytes to stay under the browser 64 KiB keepalive limit",
        )
        self.assertEqual(
            res["syncedQidCount"],
            282,
            "The union of chunked keepalive requests must cover all 282 questions",
        )

    def test_06_stateful_property_fuzzer_50_traces_invariants(self):
        """Run 50 seeded randomized traces verifying UI-DB Lockstep (I_ui) and Convergence (I_conv) invariants."""
        res = run_node_script(
            r"""
            function mulberry32(seed) {
              let a = seed >>> 0;
              return function() {
                a |= 0;
                a = (a + 0x6D2B79F5) | 0;
                let t = Math.imul(a ^ (a >>> 15), 1 | a);
                t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
                return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
              };
            }

            (async () => {
              let uiLockstepViolations = 0;
              let convergenceViolations = 0;
              let firstViolationDetail = null;

              const subsetQs = RUBRIC.slice(0, 10);
              const remainingQs = RUBRIC.slice(10);

              for (let seed = 1; seed <= 50; seed++) {
                const rng = mulberry32(seed);
                const db = new RelationalDB();
                db.seedStartup('Renovigo_Chemicals', 'aditya');
                const realSync = createSyncScoresHandler(db, { principalId: 'aditya', isTest: false });

                // Pre-seed the 272 remaining questions in DB and localStorage so completion boundary (282) is reachable
                const baseAnswers = {};
                for (const q of remainingQs) {
                  const qid = q.new_q_id || q.q_id;
                  const val = Array.isArray(q.options) && q.options.length > 0 ? Number(q.options[0].val) : 0;
                  baseAnswers[qid] = val;
                  db.upsertRow('Renovigo_Chemicals', 'aditya', qid, val, '', false);
                }

                // Ground-truth model of user's latest intent on the 10 active questions
                const modelAnswers = { ...baseAnswers };
                const modelJustifications = {};

                let failNext503 = false;
                const h = createHarness({
                  initialNow: 1000,
                  localStorage: {
                    cto2025_state: JSON.stringify({
                      'aditya:Renovigo_Chemicals': {
                        humanAnswers: { ...baseAnswers },
                        humanJustifications: {},
                        humanFlags: {}
                      }
                    })
                  },
                  syncHandler: async (body, init) => {
                    if (failNext503) {
                      failNext503 = false;
                      return { ok: false, status: 503, async json() { return { error: '503 Transient' }; } };
                    }
                    return realSync(body, init);
                  }
                });

                let App = h.CTO.App;
                App.currentUser = { id: 'aditya', is_test: false };
                App.state.activeStartupId = 'Renovigo_Chemicals';
                App.state.startupsList = [{
                  id: 'Renovigo_Chemicals',
                  name: 'Renovigo Chemicals',
                  answered_count: db.getAnsweredCount('Renovigo_Chemicals', 'aditya'),
                  is_submitted: false
                }];
                App.state.startups['Renovigo_Chemicals'] = {
                  startup_id: 'Renovigo_Chemicals',
                  human_questions: RUBRIC,
                  judge_reviews: db.getReviewsForStartup('Renovigo_Chemicals', 'aditya')
                };
                App.renderStartupPickerOptions(App.state.startupsList);
                App.loadState();
                App.setupListeners();
                App.updateStartupStatusPill();

                for (let step = 0; step < 25; step++) {
                  h.setNow(1000 + step * 10);
                  const actionRoll = Math.floor(rng() * 8);
                  const qObj = subsetQs[Math.floor(rng() * subsetQs.length)];
                  const qid = qObj.new_q_id || qObj.q_id;
                  const opts = Array.isArray(qObj.options) && qObj.options.length > 0
                    ? qObj.options.map(o => Number(o.val))
                    : [0, 0.25, 0.5, 0.75, 1];
                  const chosenVal = opts[Math.floor(rng() * opts.length)];

                  if (actionRoll === 0) {
                    // answer(qid, val)
                    const currentVal = App.state.evaluations['Renovigo_Chemicals'].humanAnswers[qid];
                    if (currentVal !== chosenVal) {
                      App.answerHuman(qid, chosenVal);
                      modelAnswers[qid] = chosenVal;
                    }
                  } else if (actionRoll === 1) {
                    // justify(qid, text)
                    const note = `Note_${seed}_${step}`;
                    App.answerJustification(qid, note);
                    App.commitPendingJustification();
                    modelJustifications[qid] = note;
                  } else if (actionRoll === 2) {
                    // flag(qid)
                    App.toggleFlag(qid);
                  } else if (actionRoll === 3) {
                    // fastSyncFlush()
                    await App.flushSyncQueue();
                  } else if (actionRoll === 4) {
                    // failNextNetworkCall(503) with concurrent newer answer before retry
                    const altVal = opts[(opts.indexOf(chosenVal) + 1) % opts.length];
                    const cur = App.state.evaluations['Renovigo_Chemicals'].humanAnswers[qid];
                    if (cur !== chosenVal) {
                      App.answerHuman(qid, chosenVal);
                      modelAnswers[qid] = chosenVal;
                    }
                    const staleBatch = App.drainSyncMap();
                    h.setNow(1000 + step * 10 + 5);
                    if (App.state.evaluations['Renovigo_Chemicals'].humanAnswers[qid] !== altVal) {
                      App.answerHuman(qid, altVal);
                      modelAnswers[qid] = altVal;
                    }
                    await App.flushSyncQueue();
                    // Simulate delayed 503 failure of staleBatch calling requeueBatch
                    App.requeueBatch(staleBatch);
                  } else if (actionRoll === 5) {
                    // pageHideKeepalive()
                    if (typeof App.flushSyncWithKeepalive === 'function') {
                      App.flushSyncWithKeepalive();
                    }
                  } else if (actionRoll === 6) {
                    // reloadFromBootstrap() (browser fires pagehide keepalive before reload)
                    if (typeof App.flushSyncWithKeepalive === 'function') {
                      App.flushSyncWithKeepalive();
                    }
                    const dbCountNow = db.getAnsweredCount('Renovigo_Chemicals', 'aditya');
                    App.state.startupsList = [{
                      id: 'Renovigo_Chemicals',
                      name: 'Renovigo Chemicals',
                      answered_count: dbCountNow,
                      is_submitted: dbCountNow >= 282
                    }];
                    App.state.startups['Renovigo_Chemicals'] = {
                      startup_id: 'Renovigo_Chemicals',
                      human_questions: RUBRIC,
                      judge_reviews: db.getReviewsForStartup('Renovigo_Chemicals', 'aditya')
                    };
                    App.renderStartupPickerOptions(App.state.startupsList);
                    App.loadState();
                    App.updateStartupStatusPill();
                  } else if (actionRoll === 7) {
                    // clickConfirmSubmit()
                    const confirmBtn = h.getElement('modal-confirm-btn');
                    const clickHandlers = confirmBtn.listeners['click'] || [];
                    if (clickHandlers[0]) {
                      await clickHandlers[0]();
                    }
                  }

                  // Check I_ui after every step
                  const dbConfirmedCount = db.getAnsweredCount('Renovigo_Chemicals', 'aditya');
                  const pillText = h.getElement('startup-status-pill').innerHTML;
                  const pickerHtml = h.getElement('startup-picker').innerHTML;
                  const pillIsSubmitted = pillText === '✓ Submitted';
                  const pickerIsSubmitted = pickerHtml.includes('(Submitted)');
                  const dbIsSubmitted = dbConfirmedCount >= 282;

                  if (pillIsSubmitted !== dbIsSubmitted || pickerIsSubmitted !== dbIsSubmitted) {
                    uiLockstepViolations++;
                    if (!firstViolationDetail) {
                      firstViolationDetail = {
                        type: 'I_ui',
                        seed,
                        step,
                        pillText,
                        pickerHtml,
                        dbConfirmedCount
                      };
                    }
                  }
                }

                // End of trace: run one healthy reconciliation + flushSyncQueue and verify I_conv
                failNext503 = false;
                if (typeof App.reconcileActiveStartupWithDatabase === 'function') {
                  App.reconcileActiveStartupWithDatabase('Renovigo_Chemicals');
                }
                await App.flushSyncQueue();

                if (App._syncMap.size !== 0) {
                  convergenceViolations++;
                  if (!firstViolationDetail) {
                    firstViolationDetail = { type: 'I_conv_syncMap_nonempty', seed, size: App._syncMap.size };
                  }
                }

                for (const qObj of subsetQs) {
                  const qid = qObj.new_q_id || qObj.q_id;
                  const expectedVal = modelAnswers[qid];
                  const dbRow = db.getRow('Renovigo_Chemicals', 'aditya', qid);
                  if (expectedVal !== undefined) {
                    if (!dbRow || dbRow.score_value !== expectedVal) {
                      convergenceViolations++;
                      if (!firstViolationDetail) {
                        firstViolationDetail = {
                          type: 'I_conv_score_mismatch',
                          seed,
                          qid,
                          expectedVal,
                          actualVal: dbRow ? dbRow.score_value : null
                        };
                      }
                    }
                  }
                  const expectedJust = modelJustifications[qid];
                  if (expectedJust && dbRow && dbRow.justification !== expectedJust) {
                    convergenceViolations++;
                    if (!firstViolationDetail) {
                      firstViolationDetail = {
                        type: 'I_conv_just_mismatch',
                        seed,
                        qid,
                        expectedJust,
                        actualJust: dbRow ? dbRow.justification : null
                      };
                    }
                  }
                }
              }

              console.log(JSON.stringify({
                uiLockstepViolations,
                convergenceViolations,
                firstViolationDetail
              }));
            })();
            """
        )
        self.assertEqual(
            res["uiLockstepViolations"],
            0,
            f"UI-Database Lockstep Invariant (I_ui) violated: {res['firstViolationDetail']}",
        )
        self.assertEqual(
            res["convergenceViolations"],
            0,
            f"Convergence Invariant (I_conv) violated: {res['firstViolationDetail']}",
        )


if __name__ == "__main__":
    unittest.main()
