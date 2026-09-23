const fs = require('fs');
let html = fs.readFileSync('site/index.html', 'utf8');

const rubricModal = `
  <!-- Rubric Modal -->
  <div class="modal-overlay" id="rubric-modal" style="display:none; z-index: 999; backdrop-filter: blur(4px);">
    <div class="modal-content" style="max-width: 600px; max-height: 80vh; overflow-y: auto; padding: 32px; border-radius: 12px; background: #fff; box-shadow: var(--shadow-lg);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h2 style="font-size: 20px; font-weight: 700; color: var(--text-main);" id="rubric-modal-title">Rubric Examples</h2>
        <button id="rubric-modal-close" style="background: none; border: none; font-size: 24px; cursor: pointer; color: var(--text-muted);">&times;</button>
      </div>
      <div id="rubric-modal-body" style="font-size: 14px; color: var(--text-main); line-height: 1.6;">
        <!-- Content injected via JS -->
      </div>
    </div>
  </div>
`;

if (!html.includes('id="rubric-modal"')) {
  html = html.replace('</body>', rubricModal + '\n</body>');
  fs.writeFileSync('site/index.html', html);
  console.log("Added rubric-modal to index.html");
} else {
  console.log("rubric-modal already exists");
}
