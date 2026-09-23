import os
import shutil
import subprocess
import pymupdf

DOCS_DIR = os.path.abspath("docs")
DESKTOP_DIR = "/Users/geoffrey/Desktop"
os.makedirs(DOCS_DIR, exist_ok=True)

CHROME_PATH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SCREENSHOT_PATH = os.path.join(DOCS_DIR, "scoring_interface_screenshot.png")

# Common styling for both PDF manuals
CSS_BASE = """
@page {
  size: letter;
  margin: 14mm 14mm 16mm 14mm;
  @bottom-right {
    content: counter(page);
  }
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #1b2028;
  background: #ffffff;
  line-height: 1.55;
  font-size: 13px;
}

/* Page Break Controls */
.page-break {
  page-break-before: always;
}

.avoid-break {
  page-break-inside: avoid;
}

/* Header Banner */
.doc-header {
  background: linear-gradient(135deg, #181f2e 0%, #0c6b5d 100%);
  color: #ffffff;
  padding: 24px 28px;
  border-radius: 8px;
  margin-bottom: 24px;
}

.doc-header .badge {
  display: inline-block;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.35);
  color: #a7f3d0;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.doc-header h1 {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.5px;
  margin-bottom: 6px;
}

.doc-header p {
  color: #e2e8f0;
  font-size: 13.5px;
  max-width: 650px;
}

.meta-bar {
  display: flex;
  gap: 20px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.15);
  font-size: 11.5px;
  color: #cbd5e1;
}

/* Section Headings */
h2 {
  font-size: 18px;
  font-weight: 700;
  color: #0c6b5d;
  margin: 24px 0 12px 0;
  padding-bottom: 6px;
  border-bottom: 2px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 8px;
}

h3 {
  font-size: 14.5px;
  font-weight: 700;
  color: #1e293b;
  margin: 16px 0 8px 0;
}

p {
  margin-bottom: 10px;
}

ul, ol {
  margin-left: 20px;
  margin-bottom: 12px;
}

li {
  margin-bottom: 6px;
}

/* Cards & Callouts */
.card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px 18px;
  margin-bottom: 16px;
}

.callout-info {
  background: #ecfdf5;
  border-left: 4px solid #059669;
  border-radius: 0 6px 6px 0;
  padding: 12px 16px;
  margin: 14px 0;
  font-size: 12.5px;
}

.callout-critical {
  background: #fef2f2;
  border-left: 4px solid #dc2626;
  border: 1px solid #fecaca;
  border-left-width: 5px;
  border-left-color: #dc2626;
  border-radius: 6px;
  padding: 14px 18px;
  margin: 16px 0;
  font-size: 13px;
}

.callout-warning {
  background: #fffbeb;
  border-left: 4px solid #d97706;
  border-radius: 0 6px 6px 0;
  padding: 12px 16px;
  margin: 14px 0;
  font-size: 12.5px;
}

.callout-tip {
  background: #eff6ff;
  border-left: 4px solid #2563eb;
  border-radius: 0 6px 6px 0;
  padding: 12px 16px;
  margin: 14px 0;
  font-size: 12.5px;
}

/* Tables */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 14px 0;
  font-size: 12px;
}

th {
  background: #f1f5f9;
  color: #334155;
  font-weight: 700;
  text-align: left;
  padding: 9px 12px;
  border: 1px solid #cbd5e1;
}

td {
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  vertical-align: top;
}

tr:nth-child(even) td {
  background: #f8fafc;
}

/* UI Mockup Blocks */
.ui-mockup {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.05);
  margin: 14px 0;
  overflow: hidden;
}

.ui-mockup-header {
  background: #1e293b;
  color: #f8fafc;
  padding: 8px 14px;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ui-mockup-body {
  padding: 14px;
  background: #f8fafc;
}

.screenshot-img {
  width: 100%;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.08);
  margin: 12px 0 16px 0;
  display: block;
}

/* Badge Styles */
.pill {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 10.5px;
  font-weight: 700;
}

.pill-green {
  background: #dcfce7;
  color: #15803d;
  border: 1px solid #86efac;
}

.pill-orange {
  background: #ffedd5;
  color: #c2410c;
  border: 1px solid #fdba74;
}

.pill-yellow {
  background: #fef9c3;
  color: #854d0e;
  border: 1px solid #fde047;
}

.pill-blue {
  background: #e0f2fe;
  color: #0369a1;
  border: 1px solid #7dd3fc;
}

.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: #0c6b5d;
  color: #ffffff;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  margin-right: 6px;
}

/* Footer note */
.doc-footer {
  margin-top: 30px;
  padding-top: 14px;
  border-top: 1px solid #cbd5e1;
  font-size: 11px;
  color: #64748b;
  display: flex;
  justify-content: space-between;
}
"""

# -------------------------------------------------------------
# ADMIN TUTORIAL HTML CONTENT (No updated date)
# -------------------------------------------------------------
HTML_ADMIN = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>CleanTech Open 2025 - Administrator Operations Manual</title>
  <style>
    {CSS_BASE}
  </style>
</head>
<body>

  <!-- Header Banner -->
  <div class="doc-header">
    <span class="badge">Operations & Admin Guide</span>
    <h1>CleanTech Open 2025: Administrator Operations Manual</h1>
    <p>Complete guide to managing judge accounts, overseeing startup assignments, and monitoring evaluation progress across the 2025 cohort.</p>
    <div class="meta-bar">
      <span><strong>Target:</strong> Program Directors & Diligence Leads</span>
      <span><strong>Portal URL:</strong> <code>/admin.html</code></span>
      <span><strong>Version:</strong> 2.4 (Clean AI Release)</span>
    </div>
  </div>

  <!-- Section 1 -->
  <h2><span class="step-num">1</span> Overview & Diligence Architecture</h2>
  <p>The CleanTech Open Diligence Platform coordinates the multi-judge evaluation of 92 cleantech startups across 10 evaluation categories (282 standardized criteria). The platform features an AI Due Diligence Copilot and live PDF viewer with auto-citation indexing to accelerate judge reviews while enforcing strict accountability.</p>

  <div class="card avoid-break">
    <h3 style="margin-top: 0;">Platform Key Components</h3>
    <ul style="margin-bottom: 0;">
      <li><strong>Admin Portal (<code>/admin.html</code>):</strong> Dedicated dashboard for operations leads to create judges, assign companies, and monitor completion rates in real time.</li>
      <li><strong>Scorer Portal (<code>/index.html</code>):</strong> Focused side-by-side workspace where judges examine company deliverables on the left and enter scores with AI guidance on the right.</li>
      <li><strong>PostgreSQL Database (Supabase):</strong> Stores judge rosters, encrypted passcodes, assignment mappings, and question reviews with instant transactional auto-saving.</li>
      <li><strong>Clean AI Copilot Engine:</strong> Advanced reasoning model (Qwen 35B) running on sanitized founder text with 0% competition scaffolding and 92.7% PDF page-indexed citations.</li>
    </ul>
  </div>

  <!-- Section 2 -->
  <h2><span class="step-num">2</span> Accessing the Admin Dashboard</h2>
  <p>To access the administrative tools:</p>
  <ol>
    <li>Navigate to <code>/admin.html</code> in any modern desktop browser (Google Chrome, Safari, or Microsoft Edge recommended).</li>
    <li>When prompted by the modal overlay, enter the administrator credentials:
      <ul>
        <li><strong>Admin Username:</strong> <code>admin</code> (or designated admin handle)</li>
        <li><strong>Passcode:</strong> Your secure administrator passcode</li>
      </ul>
    </li>
    <li>Click <strong>Log In</strong>. The session will persist automatically in local storage until you click <strong>Log Out</strong>.</li>
  </ol>

  <div class="ui-mockup avoid-break">
    <div class="ui-mockup-header">
      <span>ADMIN PORTAL LOGIN</span>
      <span>RESTRICTED ACCESS</span>
    </div>
    <div class="ui-mockup-body" style="text-align: center; padding: 20px;">
      <div style="font-size: 15px; font-weight: 700; margin-bottom: 6px;">CleanTech Open - Admin Portal</div>
      <div style="color: #64748b; font-size: 12px; margin-bottom: 14px;">Enter administrator credentials to manage judge assignments</div>
      <div style="display: inline-block; text-align: left; width: 260px;">
        <label style="font-size: 11px; font-weight: 600; color: #475569;">Admin Username</label>
        <div style="background:#fff; border:1px solid #cbd5e1; padding:6px 10px; border-radius:4px; font-family:monospace; margin-bottom:10px;">admin</div>
        <label style="font-size: 11px; font-weight: 600; color: #475569;">Passcode</label>
        <div style="background:#fff; border:1px solid #cbd5e1; padding:6px 10px; border-radius:4px; font-family:monospace; margin-bottom:12px;">••••••••••••</div>
        <div style="background:#0c6b5d; color:#fff; padding:7px; border-radius:4px; text-align:center; font-weight:600; font-size:12px;">Log In</div>
      </div>
    </div>
  </div>

  <div class="page-break"></div>

  <!-- Section 3 -->
  <h2><span class="step-num">3</span> Managing Judges & Reviewers</h2>
  <p>Judges only have access to startups explicitly assigned to them. Administrators can quickly onboard new judges and view active reviewer credentials on the left side of the dashboard.</p>

  <div class="card avoid-break">
    <h3 style="margin-top: 0;">How to Create a New Judge</h3>
    <ol>
      <li>Locate the <strong>Create New Scorer</strong> card on the left panel.</li>
      <li>Enter a memorable, unique <strong>Scorer ID</strong>. Recommended convention:
        <ul>
          <li><code>judge_smith</code> or <code>judge_chen</code> (Named judges)</li>
          <li><code>J-001</code>, <code>J-002</code>, <code>J-003</code> (Numbered panel IDs)</li>
        </ul>
      </li>
      <li>Enter a secure <strong>Passcode</strong> (e.g., 4-digit code or memorable passphrase).</li>
      <li>Click <strong>Create Scorer</strong>. The judge is instantly registered in Supabase and appears in the <strong>Existing Scorers</strong> roster below.</li>
      <li>Provide the judge with the portal URL (<code>/index.html</code>), their Scorer ID, and their passcode.</li>
    </ol>
  </div>

  <div class="callout-info avoid-break">
    <strong>Security & Credential Recovery:</strong> All active judge IDs and their passcodes are displayed in the "Existing Scorers" scrollable box. If a judge misplaces their passcode, you can read it directly from this panel without needing to reset their database account.
  </div>

  <!-- Section 4 -->
  <h2><span class="step-num">4</span> Assigning Startups to Judges</h2>
  <p>The assignment workflow gives administrators full control over distribution, ensuring dual-reviewer consensus and preventing accidental assignment of incomplete applications.</p>

  <div class="ui-mockup avoid-break">
    <div class="ui-mockup-header">
      <span>COMPANY ASSIGNMENTS DASHBOARD</span>
      <span>REAL-TIME COHORT SYNC</span>
    </div>
    <div class="ui-mockup-body">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <span style="font-weight: 700; font-size: 13px;">Selected Judge: <span style="color:#0c6b5d;">judge_smith</span></span>
        <span style="font-size: 11px; background:#dcfce7; color:#15803d; padding:2px 8px; border-radius:12px; font-weight:700;">74 / 92 Ready for Assignment</span>
      </div>

      <!-- Filters -->
      <div style="display:flex; gap:8px; margin-bottom:12px;">
        <span style="background:#059669; color:#fff; padding:4px 12px; border-radius:14px; font-size:11px; font-weight:600;">✓ Ready for Assignment</span>
        <span style="background:#f1f5f9; color:#64748b; padding:4px 12px; border-radius:14px; font-size:11px; border:1px solid #cbd5e1;">Show All (92)</span>
      </div>

      <!-- Mock list items -->
      <div style="background:#fff; border:1px solid #e2e8f0; border-radius:6px; font-size:12px;">
        <div style="display:flex; align-items:center; gap:8px; padding:8px 12px; border-bottom:1px solid #f1f5f9; background:#f8fafc;">
          <input type="checkbox" checked>
          <span style="font-weight:600;">17</span>
          <span class="pill pill-green">✓ Clean AI Ready</span>
          <span class="pill pill-blue">142 Answers</span>
          <span class="pill pill-orange" style="margin-left:auto;">1 Assigned</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px; padding:8px 12px; border-bottom:1px solid #f1f5f9;">
          <input type="checkbox">
          <span style="font-weight:600;">Calectra</span>
          <span class="pill pill-green">✓ Clean AI Ready</span>
          <span class="pill pill-yellow" style="margin-left:auto;">0 Assigned</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px; padding:8px 12px;">
          <input type="checkbox" checked>
          <span style="font-weight:600;">Novagrid</span>
          <span class="pill pill-green">✓ Clean AI Ready</span>
          <span style="color:#ef4444; font-size:11px; font-weight:600; border:1px solid #fca5a5; padding:1px 5px; border-radius:3px; background:#fef2f2;">Not Started</span>
          <span class="pill pill-green" style="margin-left:auto;">2 Assigned</span>
        </div>
      </div>
    </div>
  </div>

  <h3>Step-by-Step Assignment Protocol</h3>
  <ol>
    <li><strong>Select a Scorer:</strong> Choose the target judge from the <em>"Select Scorer to Assign Companies"</em> dropdown. The list immediately refreshes to reflect that judge's assignments.</li>
    <li><strong>Use the "✓ Ready for Assignment" Filter:</strong> Always keep this filter active. It restricts the visible list to startups that have 100% completed clean AI extraction and PDF citation reverse-indexing.</li>
    <li><strong>Assign or Unassign Companies:</strong> Check the box next to any startup to immediately assign it to the selected judge. Unchecking removes the assignment. Every toggle commits to the database instantly.</li>
    <li><strong>Track Cohort Progress:</strong> Next to each assigned company, observe the judge's completion status:
      <ul>
        <li><span style="color:#ef4444; font-weight:700;">Not Started:</span> The judge has not answered any questions yet.</li>
        <li><span style="color:#0369a1; font-weight:700;">X Answers:</span> Number of rubric questions answered so far (out of 282).</li>
      </ul>
    </li>
  </ol>

  <div class="page-break"></div>

  <!-- Section 5 -->
  <h2><span class="step-num">5</span> Understanding Assignment Badges & Distribution</h2>
  <p>To ensure high statistical validity, each startup should ideally receive two independent evaluations. The admin dashboard provides visual cues to guide assignment balancing:</p>

  <table>
    <thead>
      <tr>
        <th style="width: 25%;">Badge</th>
        <th style="width: 20%;">Cohort Status</th>
        <th>Administrative Meaning & Action Required</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><span class="pill pill-yellow">0 Assigned</span></td>
        <td>Unassigned</td>
        <td>No judge is currently assigned to this startup. <strong>Action:</strong> Assign to an available reviewer.</td>
      </tr>
      <tr>
        <td><span class="pill pill-orange">1 Assigned</span></td>
        <td>Partially Assigned</td>
        <td>One judge has been assigned. <strong>Action:</strong> Assign a second independent judge for dual-review consensus.</td>
      </tr>
      <tr>
        <td><span class="pill pill-green">2+ Assigned</span></td>
        <td>Fully Assigned</td>
        <td>Two or more judges have been assigned. Dual-blind consensus requirement is satisfied.</td>
      </tr>
      <tr>
        <td><span class="pill pill-green">✓ Clean AI Ready</span></td>
        <td>Pipeline Complete</td>
        <td>The startup has completed 282/282 clean AI extractions and all citations are reverse-indexed to PDF pages.</td>
      </tr>
      <tr>
        <td><span style="background:#f1f5f9; color:#64748b; padding:2px 7px; border-radius:4px; font-size:10px; font-weight:600;">⏳ Extracting AI</span></td>
        <td>In Progress</td>
        <td>Clean AI extraction is currently executing on the remote GPU server. <strong>Do not assign until extraction completes.</strong></td>
      </tr>
    </tbody>
  </table>

  <h3>The Assignment Distribution Bar Chart</h3>
  <p>Directly beneath the scorer roster, the dashboard renders a real-time bar chart illustrating the overall state of the cohort:</p>
  <ul>
    <li><strong>Yellow Bar (Unassigned):</strong> Count of startups with zero reviewers. Aim to reduce this to 0.</li>
    <li><strong>Orange Bar (1 Assigned):</strong> Count of startups with only 1 reviewer. These require a second assignment.</li>
    <li><strong>Green Bar (Fully Assigned 2+):</strong> Count of startups with two or more assigned judges.</li>
  </ul>

  <!-- Section 6 -->
  <h2><span class="step-num">6</span> Administrative FAQ & Operational Rules</h2>

  <div class="avoid-break">
    <h3>Recommended Reviewer Workload</h3>
    <p>We recommend assigning <strong>3 to 5 startups per judge</strong>. Each startup evaluation requires careful diligence. Overloading reviewers beyond 6 startups increases fatigue and decreases qualitative justification quality.</p>

    <h3>How Do I Reset a Scorer's Password or Delete an Account?</h3>
    <p>In the <em>Existing Scorers</em> panel, each reviewer has two administrative actions:
      <ul>
        <li><strong>Reset:</strong> Click <strong>Reset</strong> to set a new password for the judge. This immediately invalidates active sessions and requires the judge to log in with the new credential.</li>
        <li><strong>Delete:</strong> Click <strong>Delete</strong> to permanently remove a test or decommissioned reviewer. Deleting a scorer cleanly removes their assignments and review sessions.</li>
      </ul>
    </p>

    <h3>How Do I Export Scored Cohort Data?</h3>
    <p>Click the green <strong>📥 Export Scored Data (CSV)</strong> button in the top navigation header of the Admin Portal. Your browser will download a complete CSV containing applicant names, judge IDs, rubric categories, question prompts, human scores, qualitative justifications, AI suggestions, confidence ratings, concordance flags, and citation source files.</p>

    <h3>Can Judges See Other Judges' Scores?</h3>
    <p><strong>No.</strong> The scoring portal is strictly double-blind. Judges only see the AI suggestions, founder deliverables, and their own scoring answers. They cannot view who else is reviewing the startup or what other judges have scored.</p>
  </div>

  <div class="doc-footer">
    <span>CleanTech Open 2025 Diligence Engine</span>
    <span>Confidential — For Internal Operations Use Only</span>
  </div>

</body>
</html>
"""

# -------------------------------------------------------------
# SCORER TUTORIAL HTML CONTENT (Updated for 2-panel view, strong human emphasis, no date)
# -------------------------------------------------------------
HTML_SCORER = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>CleanTech Open 2025 - Judge & Scorer Manual</title>
  <style>
    {CSS_BASE}
  </style>
</head>
<body>

  <!-- Header Banner -->
  <div class="doc-header">
    <span class="badge">Judge & Reviewer Guide</span>
    <h1>CleanTech Open 2025: Scorer & Evaluation Manual</h1>
    <p>Step-by-step instructions for evaluating startup applications, utilizing the AI Due Diligence Copilot, and navigating founder deliverables with auto-citation jumping.</p>
    <div class="meta-bar">
      <span><strong>Target:</strong> Expert Judges, Mentors & Investors</span>
      <span><strong>Portal URL:</strong> <code>/index.html</code></span>
      <span><strong>Evaluation Framework:</strong> 10 Categories (282 Criteria)</span>
    </div>
  </div>

  <!-- Section 1 -->
  <h2><span class="step-num">1</span> Getting Started & Logging In</h2>
  <p>As a CleanTech Open judge, you have been assigned specific cleantech startups to evaluate. Your evaluations determine accelerator cohort admissions, awards, and investment readiness.</p>

  <ol>
    <li>Navigate to the scoring portal at <strong><code>/index.html</code></strong>.</li>
    <li>In the <strong>Judge Authentication</strong> modal, enter:
      <ul>
        <li><strong>Scorer ID:</strong> Your assigned username (e.g., <code>judge_smith</code> or <code>J-001</code>).</li>
        <li><strong>Passcode:</strong> Your individual access passcode provided by the administrator.</li>
      </ul>
    </li>
    <li>Click <strong>Sign In</strong>.</li>
    <li>In the top dark navigation bar, click the <strong>Company Dropdown</strong> to view the startups assigned to you. Select the startup you wish to evaluate to load its application workspace.</li>
  </ol>

  <div class="callout-tip avoid-break">
    <strong>Cloud Auto-Save:</strong> Every score selection and justification note is <strong>automatically saved to the Supabase database</strong> the moment you click a score or pause typing. You can safely reload the page or return on another device without losing work.
  </div>

  <!-- Section 2: Updated 2-Panel Side-by-Side Workspace -->
  <h2><span class="step-num">2</span> The Split-Screen Evaluation Workspace</h2>
  <p>The CleanTech Open scoring interface features a high-velocity <strong>Side-by-Side Split Workspace</strong> designed to eliminate window tab flipping. The left panel is dedicated to original founder deliverables, while the right panel displays your active scoring rubric and AI guidance.</p>

  <!-- Real Screenshot Insertion -->
  <img class="screenshot-img avoid-break" src="file://{SCREENSHOT_PATH}" alt="CleanTech Open Scoring Interface">

  <div class="card avoid-break">
    <h3 style="margin-top: 0;">Workspace Layout Overview</h3>
    
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 10px;">
      <div>
        <h4 style="color: #0c6b5d; font-size: 13px; margin-bottom: 6px;">LEFT PANEL: Source vs. AI Extraction Viewer</h4>
        <ul style="margin-left: 16px; font-size: 12px;">
          <li><strong>Deliverable Selector Dropdown:</strong> Switch between any uploaded PDF for the active evaluation module (e.g., <em>05 2DaLoop - Business Model Canvas</em>).</li>
          <li><strong>Module Tag:</strong> Displays current category context (e.g. <code>Business Canvas</code>).</li>
          <li><strong>Integrated PDF Viewer:</strong> Complete in-browser document reader with zoom (<code>+</code>/<code>-</code>), page jump, rotation, pan, print, and local download.</li>
          <li><strong>Auto-Jumping Canvas:</strong> Automatically snaps to the exact page when an AI citation is clicked on the right!</li>
        </ul>
      </div>

      <div>
        <h4 style="color: #0c6b5d; font-size: 13px; margin-bottom: 6px;">RIGHT PANEL: Step-by-Step Scoring & Rubric</h4>
        <ul style="margin-left: 16px; font-size: 12px;">
          <li><strong>Module Step Indicator:</strong> Shows current section (e.g., <code>STEP 1 OF 10</code>) and live progress (e.g., <code>0 / 5 answered</code>).</li>
          <li><strong>Overall Assessment Progress Bar:</strong> Visual progress tracking completion across all 282 criteria.</li>
          <li><strong>Evaluation Cards:</strong> Scrollable criteria cards containing rubric text, AI suggestion pills, and point selectors.</li>
          <li><strong>Section Footer:</strong> <em>← Previous</em> and <em>Next Section →</em> buttons to transition between modules.</li>
        </ul>
      </div>
    </div>
  </div>

  <div class="page-break"></div>

  <!-- Section 3: Strongly Emphasized Human Review -->
  <h2><span class="step-num">3</span> The AI Copilot & The Mandatory Human Review Rule</h2>

  <!-- CRITICAL PROTOCOL BOX -->
  <div class="callout-critical avoid-break">
    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
      <span style="font-size: 18px;">⚠️</span>
      <strong style="font-size: 14px; color: #991b1b; text-transform: uppercase; letter-spacing: 0.5px;">CRITICAL PROTOCOL: Human Review is Mandatory Regardless of AI Confidence</strong>
    </div>
    <p style="color: #7f1d1d; font-size: 12.5px; margin-bottom: 8px; line-height: 1.5;">
      <strong>Never rubber-stamp high-confidence AI suggestions.</strong> An AI confidence rating of <code>90%</code>, <code>95%</code>, or <code>100%</code> does <strong>NOT</strong> mean the startup's claim is commercially viable, technically sound, or factually true in the real world.
    </p>
    <ul style="color: #991b1b; font-size: 12px; margin-left: 18px; margin-bottom: 0;">
      <li><strong>What AI Confidence Actually Measures:</strong> The AI confidence score solely reflects <em>how clearly an explicit textual statement was found</em> in the founder's uploaded text. If a founder writes <em>"Our technology has zero competitors and 100% customer retention"</em>, the AI will extract a high-confidence match (<code>1.0 PT | 95% Conf</code>).</li>
      <li><strong>What the AI Cannot Do:</strong> The AI cannot verify whether the founder's claim is realistic, whether lab data supports it, whether customer interviews were genuine, or whether the competitive analysis is superficial.</li>
      <li><strong>Your Role as an Expert Judge:</strong> You <strong>must click the citation link</strong>, review the cited passage in the PDF viewer on the left, inspect the surrounding context, and determine whether the startup genuinely satisfied the standard. <strong>You have full authority to override the AI whenever founder evidence lacks depth or credibility.</strong></li>
    </ul>
  </div>

  <h3>Anatomy of an Interactive Evaluation Card</h3>
  <p>Each evaluation card in the right panel is structured for rapid diligence and transparent accountability:</p>

  <div class="ui-mockup avoid-break">
    <div class="ui-mockup-header">
      <span>EVALUATION CARD BREAKDOWN</span>
      <span>MODULE: BUSINESS CANVAS (BC)</span>
    </div>
    <div class="ui-mockup-body">
      
      <!-- Top Tag Row -->
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px;">👤 HUMAN REVIEW REQUIRED</span>
        <span style="background: #fef9c3; color: #854d0e; border: 1px solid #fde047; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 700;">⚡ 0.5 PTS | 60% Conf</span>
      </div>

      <div style="font-size: 11px; color: #64748b; font-weight: 600; margin-bottom: 4px;">BC &nbsp; BC_Q3</div>
      <div style="font-size: 14px; font-weight: 700; color: #1e293b; margin-bottom: 10px;">
        Has the company interviewed at least 5 customers?
      </div>

      <!-- Justification Box -->
      <div style="margin-bottom: 12px;">
        <label style="display: flex; justify-content: space-between; align-items: center; font-size: 11.5px; font-weight: 600; color: #475569; margin-bottom: 4px;">
          <span>Justification</span>
          <span style="color: #0284c7; font-weight: 600; font-size: 11px;">📄 View Examples</span>
        </label>
        <div style="background: #fff; border: 1px solid #cbd5e1; border-radius: 4px; padding: 8px 10px; font-size: 12px; color: #94a3b8; font-style: italic;">
          Provide justification based on the markdown rubrics...
        </div>
      </div>

      <!-- Citation Block -->
      <div style="background: #fff8e1; border-left: 4px solid #b0761c; padding: 10px 12px; border-radius: 4px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          <a href="#" style="color: #0c6b5d; font-weight: 700; font-size: 12px; text-decoration: none;">🔗 View AI Citation (p. 1)</a>
          <span style="font-family: monospace; font-size: 10.5px; background: rgba(0,0,0,0.06); padding: 1px 5px; border-radius: 3px;">05_2DaLoop_Business_Model_Canvas.pdf</span>
        </div>
        <p style="font-size: 11.5px; font-style: italic; color: #334155; margin-bottom: 4px;">
          "Interviews we've completed before (NSF I-Corps) indicates that enterprise IT managers require standardized SLA guarantees..."
        </p>
        <span style="font-size: 10.5px; color: #64748b;">Switched viewer to Page 1. Use <strong>Cmd+F</strong> / <strong>Ctrl+F</strong> in the viewer to locate exact text.</span>
      </div>

      <!-- Point Options Row -->
      <div style="display: flex; gap: 8px;">
        <span style="flex: 1; text-align: center; border: 1px solid #cbd5e1; padding: 7px; border-radius: 4px; font-weight: 600; background: #fff;">1 PT</span>
        <span style="flex: 1; text-align: center; border: 1px solid #cbd5e1; padding: 7px; border-radius: 4px; font-weight: 600; background: #fff;">0.75 PTS</span>
        <span style="flex: 1; text-align: center; border: 1px solid #0c6b5d; padding: 7px; border-radius: 4px; font-weight: 700; background: #0c6b5d; color: #fff;">0.5 PTS</span>
        <span style="flex: 1; text-align: center; border: 1px solid #cbd5e1; padding: 7px; border-radius: 4px; font-weight: 600; background: #fff;">0.25 PTS</span>
        <span style="flex: 1; text-align: center; border: 1px solid #cbd5e1; padding: 7px; border-radius: 4px; font-weight: 600; background: #fff;">0 PTS</span>
      </div>

    </div>
  </div>

  <div class="page-break"></div>

  <!-- Section 4 -->
  <h2><span class="step-num">4</span> The 10 Evaluation Categories</h2>
  <p>Judges evaluate startups across 10 standardized modules. Use the <em>Next Section →</em> and <em>← Previous</em> buttons at the bottom of the right panel to move sequentially through each section:</p>

  <table>
    <thead>
      <tr>
        <th style="width: 10%;">Code</th>
        <th style="width: 25%;">Module Title</th>
        <th style="width: 15%;">Questions</th>
        <th>Primary Deliverable(s) Reviewed in Left Panel</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>BC</strong></td>
        <td>Business Canvas</td>
        <td>5 Questions (BC_Q1–Q5)</td>
        <td>Business Model Canvas (EBD1) & Customer Discovery capture</td>
      </tr>
      <tr>
        <td><strong>ES</strong></td>
        <td>Environmental & Social</td>
        <td>10 Questions (ES_Q1–Q10)</td>
        <td>Impact Statement (EBD2) & Sustainability module questions</td>
      </tr>
      <tr>
        <td><strong>F</strong></td>
        <td>Financials</td>
        <td>29 Questions (F_Q1–Q29)</td>
        <td>3-Year Financial Projections (EBD5) & unit economics model</td>
      </tr>
      <tr>
        <td><strong>IP</strong></td>
        <td>Investor Pitch</td>
        <td>58 Questions (IP_Q1–Q58)</td>
        <td>Investor Pitch Deck (EBD8) & full diligence slide presentation</td>
      </tr>
      <tr>
        <td><strong>IS</strong></td>
        <td>Executive Summary</td>
        <td>34 Questions (IS_Q1–Q34)</td>
        <td>1-Page Executive Summary (EBD6) & core company narrative</td>
      </tr>
      <tr>
        <td><strong>L</strong></td>
        <td>Legal & Governance</td>
        <td>53 Questions (L_Q1–Q53)</td>
        <td>IP filings, corporate formation, governance & legal review</td>
      </tr>
      <tr>
        <td><strong>M</strong></td>
        <td>Market & Customers</td>
        <td>12 Questions (M_Q1–Q12)</td>
        <td>Customer Segmentation & Competitive Matrix (EBD3)</td>
      </tr>
      <tr>
        <td><strong>PMF</strong></td>
        <td>Product Market Fit</td>
        <td>34 Questions (PMF_Q1–Q34)</td>
        <td>Customer interviews, discovery log & target customer segments</td>
      </tr>
      <tr>
        <td><strong>T</strong></td>
        <td>Team Targets</td>
        <td>31 Questions (T_Q1–Q31)</td>
        <td>Team hiring plans, targets & milestones</td>
      </tr>
      <tr>
        <td><strong>TP</strong></td>
        <td>Tech / Product</td>
        <td>16 Questions (TP_Q1–Q16)</td>
        <td>Technology Validation (EBD4) & Technical testimonials</td>
      </tr>
      <tr style="background: #f1f5f9; font-weight: 700;">
        <td><strong>TOTAL</strong></td>
        <td><strong>10 Evaluation Categories</strong></td>
        <td><strong>282 Questions Total</strong></td>
        <td><strong>Standardized CleanTech Open Diligence Rubric</strong></td>
      </tr>
    </tbody>
  </table>

  <!-- Section 5 -->
  <h2><span class="step-num">5</span> Step-by-Step Diligence Checklist</h2>
  <p>Follow this standardized 5-step workflow for every startup assigned to you:</p>

  <table>
    <thead>
      <tr>
        <th style="width: 15%;">Step</th>
        <th style="width: 25%;">Action</th>
        <th>Description & Best Practice</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Step 1</strong></td>
        <td>Executive Summary</td>
        <td>Start in the <strong>Executive Summary (IS)</strong> category to read the founder's 1-page overview and understand the core thesis.</td>
      </tr>
      <tr>
        <td><strong>Step 2</strong></td>
        <td>Category Progression</td>
        <td>Progress systematically through the 10 categories using the bottom navigation buttons. Watch the overall progress bar fill.</td>
      </tr>
      <tr>
        <td><strong>Step 3</strong></td>
        <td>Inspect Citations</td>
        <td>On each question, click <strong>"View AI Citation"</strong> to verify the founder's claim against the embedded PDF deliverable on the left.</td>
      </tr>
      <tr>
        <td><strong>Step 4</strong></td>
        <td>Record Score & Notes</td>
        <td>Select your point verdict. If the question requires justification or if you disagree with the AI, type your brief explanation.</td>
      </tr>
      <tr>
        <td><strong>Step 5</strong></td>
        <td>Final Verification</td>
        <td>Click <strong>"Confirm & Submit"</strong> when prompted to finalize and flush all scores to the database.</td>
      </tr>
    </tbody>
  </table>

  <!-- Section 6: Scorer FAQ (Duration removed) -->
  <h2><span class="step-num">6</span> Scorer FAQs & Pro-Tips</h2>

  <div class="card avoid-break">
    <h3 style="margin-top: 0;">Frequently Asked Questions</h3>
    
    <p><strong>Q: What if the AI Citation says "No direct evidence exists"?</strong><br>
    <strong>A:</strong> This means the startup's submitted deliverables did not address this specific criterion. If you independently search the document and cannot locate evidence, award <strong>0 PTS</strong>.</p>

    <p><strong>Q: Can I view the official rubric scoring guidelines?</strong><br>
    <strong>A:</strong> Yes! On questions with official rubric guidelines (e.g. Business Canvas), click the <strong>"📄 View Examples"</strong> link in the question card to view rubric thresholds and real-world grading examples calibrated directly to the <strong>0 – 1 point scale</strong> (0, 0.25, 0.5, 0.75, 1.0 PTS).</p>

    <p><strong>Q: How do I zoom or download a startup PDF?</strong><br>
    <strong>A:</strong> The live PDF viewer on the left includes full browser controls in the top toolbar: zoom in/out (<code>+</code>/<code>-</code>), page jump, and a direct download icon to inspect the file in your preferred PDF reader.</p>

    <p><strong>Q: What if I notice a document misclassification?</strong><br>
    <strong>A:</strong> The deliverable dropdown above the PDF viewer allows you to switch between all documents attached to that category. If you need to view a deliverable from another category, navigate to that category section.</p>

    <p><strong>Q: What happens if I close my browser before clicking Submit?</strong><br>
    <strong>A:</strong> All scores and justifications are continuously saved to the Supabase database in real time. When you reopen the portal, all your answers will automatically reload from the database.</p>
  </div>

  <div class="doc-footer">
    <span>CleanTech Open 2025 Diligence Engine</span>
    <span>Scorer & Judge Guidance Manual</span>
  </div>

</body>
</html>
"""

def compile_html_to_pdf(html_content, output_pdf_path):
    temp_html = output_pdf_path.replace(".pdf", ".html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Compiling {os.path.basename(temp_html)} -> {os.path.basename(output_pdf_path)} via Chrome Headless...")
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        "--allow-file-access-from-files",
        f"--print-to-pdf={output_pdf_path}",
        temp_html
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error compiling {output_pdf_path}: {res.stderr}")
        raise RuntimeError(f"Chrome PDF generation failed: {res.stderr}")

    # Verify with pymupdf
    doc = pymupdf.open(output_pdf_path)
    page_count = len(doc)
    doc.close()
    file_size_kb = os.path.getsize(output_pdf_path) / 1024
    print(f"  ✓ Success: {os.path.basename(output_pdf_path)} ({page_count} pages, {file_size_kb:.1f} KB)")
    return page_count

def main():
    print("==================================================")
    print("UPDATING CLEANTECH OPEN 2025 TUTORIAL MANUALS")
    print("==================================================")

    # 1. Admin Tutorial
    admin_pdf_local = os.path.join(DOCS_DIR, "CleanTech_Open_Admin_Tutorial.pdf")
    compile_html_to_pdf(HTML_ADMIN, admin_pdf_local)

    # 2. Scorer Tutorial
    scorer_pdf_local = os.path.join(DOCS_DIR, "CleanTech_Open_Scorer_Tutorial.pdf")
    compile_html_to_pdf(HTML_SCORER, scorer_pdf_local)

    # 3. Sync to Desktop
    print("\nSyncing updated PDF manuals to Desktop (/Users/geoffrey/Desktop)...")
    admin_pdf_desktop = os.path.join(DESKTOP_DIR, "CleanTech_Open_Admin_Tutorial.pdf")
    scorer_pdf_desktop = os.path.join(DESKTOP_DIR, "CleanTech_Open_Scorer_Tutorial.pdf")

    shutil.copy2(admin_pdf_local, admin_pdf_desktop)
    shutil.copy2(scorer_pdf_local, scorer_pdf_desktop)

    print(f"  ✓ Synced: {admin_pdf_desktop} ({os.path.getsize(admin_pdf_desktop)/1024:.1f} KB)")
    print(f"  ✓ Synced: {scorer_pdf_desktop} ({os.path.getsize(scorer_pdf_desktop)/1024:.1f} KB)")
    print("\nUpdated tutorial generation & desktop synchronization complete!")

if __name__ == "__main__":
    main()
