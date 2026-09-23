const fs = require('fs');

let renderJs = fs.readFileSync('site/js/render.js', 'utf8');

const renderLeftPaneRegex = /renderLeftPane\(stepCat, documentData\) \{[\s\S]*?(?=\n  renderRightPane)/;

const newRenderLeftPane = `renderLeftPane(stepCat, documentData) {
    const container = document.getElementById('extraction-viewer');
    const pill = document.getElementById('left-step-pill');
    pill.textContent = this.categoryNames[stepCat] || stepCat;

    if (!documentData || !documentData.sections) {
      container.innerHTML = \`<div class="pane-empty"><div class="pane-empty-mark">\${this.icons.doc}</div><strong>No document loaded</strong><p>The source record for this applicant has not been ingested yet.</p></div>\`;
      return;
    }

    // 1. Extract ALL unique PDFs grouped by category
    const allCategories = [];
    let firstAvailablePdfUrl = null;
    let defaultPdfUrl = null;
    
    documentData.sections.forEach(sec => {
        if (sec.pdfs && sec.pdfs.length > 0) {
            const catName = this.categoryNames[sec.cat_code] || sec.heading || sec.cat_code;
            const pdfs = [];
            sec.pdfs.forEach(pdf => {
                if (!firstAvailablePdfUrl) firstAvailablePdfUrl = pdf.url;
                if (sec.cat_code === stepCat && !defaultPdfUrl) defaultPdfUrl = pdf.url;
                pdfs.push({ label: pdf.label || pdf.filename, url: pdf.url });
            });
            allCategories.push({ catName, pdfs });
        }
    });

    if (allCategories.length === 0) {
      container.innerHTML = \`<div class="pane-empty"><div class="pane-empty-mark">\${this.icons.doc}</div><strong>No Documents Found</strong><p>This applicant has no documents available.</p></div>\`;
      return;
    }
    
    // Set default selection
    const activePdfUrl = defaultPdfUrl || firstAvailablePdfUrl;
    
    // 2. Build the Universal Dropdown
    let dropdownHtml = \`<select id="universal-pdf-selector" style="width: 100%; padding: 8px 12px; margin-bottom: 16px; border-radius: 6px; border: 1px solid var(--border); font-size: 14px; background-color: var(--surface-sunk); color: var(--text-main); cursor: pointer;" onchange="window.CTO.Render.switchPDF(this.value)">\`;
    
    allCategories.forEach(cat => {
        dropdownHtml += \`<optgroup label="\${cat.catName}">\`;
        cat.pdfs.forEach(pdf => {
            const selected = (pdf.url === activePdfUrl) ? 'selected' : '';
            dropdownHtml += \`<option value="\${pdf.url}" \${selected}>\${pdf.label}</option>\`;
        });
        dropdownHtml += \`</optgroup>\`;
    });
    dropdownHtml += \`</select>\`;
    
    // Optional Notice if category has no explicitly mapped PDF
    let noticeHtml = '';
    if (!defaultPdfUrl) {
        noticeHtml = \`<div style="padding: 10px 14px; background: #fff8e1; border-left: 3px solid var(--accent-yellow); margin-bottom: 16px; border-radius: 4px; font-size: 13px; color: #744210;">
          <strong>No specific document mapped.</strong> Displaying alternative application documents.
        </div>\`;
    }

    // 3. Render the single Viewer
    let html = \`<div class="pdf-viewer-container" style="display:flex; flex-direction:column; height:100%; width:100%;">
      \${dropdownHtml}
      \${noticeHtml}
      <div class="pdf-wrapper" style="flex: 1; display: flex; flex-direction: column; min-height: 600px; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; background: #fff;">
        <iframe id="primary-pdf-viewer" src="\${activePdfUrl}#navpanes=0&pagemode=none" width="100%" height="100%" style="border: none; flex: 1;"></iframe>
      </div>
    </div>\`;

    container.innerHTML = html;
  },`;

renderJs = renderJs.replace(renderLeftPaneRegex, newRenderLeftPane);

const addSwitchPdf = `
  switchPDF(url) {
    const iframe = document.getElementById('primary-pdf-viewer');
    if (iframe) {
        iframe.src = url + '#navpanes=0&pagemode=none';
    }
  },

  renderRightPane`;

renderJs = renderJs.replace('renderRightPane', addSwitchPdf);
fs.writeFileSync('site/js/render.js', renderJs);
