const fs = require('fs');

let renderJs = fs.readFileSync('site/js/render.js', 'utf8');

// Replace the empty pane logic
const emptyPaneLogic = `if (sections.length === 0) {
      container.innerHTML = \`<div class="pane-empty"><div class="pane-empty-mark">\${this.icons.scan}</div><strong>Nothing mapped here</strong><p>No passages from the source application were mapped to this rubric section.</p></div>\`;
      return;
    }`;

const fallbackLogic = `if (sections.length === 0) {
      // Fallback: If no specific PDF is mapped, show all available PDFs so the scorer can still search for answers
      let fallbackHtml = \`<div style="padding: 16px; background: #fff8e1; border-left: 4px solid var(--accent-yellow); margin-bottom: 24px; border-radius: 4px;">
        <h4 style="margin: 0 0 8px 0; color: #b7791f; font-size: 15px;">No Specific Document Mapped</h4>
        <p style="margin: 0; font-size: 13px; color: #744210;">The applicant did not provide a dedicated document for this category. The remaining application documents are displayed below for your reference.</p>
      </div>\`;
      
      fallbackHtml += '<div class="pdf-viewer-container" style="display:flex; flex-direction:column; gap:24px; height:100%; width:100%;">';
      
      // Collect all unique PDFs across all sections
      const allPdfs = [];
      const seenUrls = new Set();
      if (documentData.sections) {
          documentData.sections.forEach(sec => {
              if (sec.pdfs) {
                  sec.pdfs.forEach(pdf => {
                      if (!seenUrls.has(pdf.url)) {
                          seenUrls.add(pdf.url);
                          allPdfs.push(pdf);
                      }
                  });
              }
          });
      }
      
      if (allPdfs.length === 0) {
          container.innerHTML = \`<div class="pane-empty"><div class="pane-empty-mark">\${this.icons.doc}</div><strong>No Documents Found</strong><p>This applicant has no documents available.</p></div>\`;
          return;
      }
      
      allPdfs.forEach((pdf, idx) => {
          fallbackHtml += \`
            <div class="pdf-wrapper" style="flex: 1; display: flex; flex-direction: column; min-height: 600px; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; animation-delay: \${idx * 40}ms; background: #fff;">
              <div class="pdf-header" style="background: var(--surface-sunk); padding: 12px 16px; border-bottom: 1px solid var(--border); font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                \${this.icons.doc} <span>\${pdf.label || pdf.filename || 'Application Document'}</span>
              </div>
              <iframe src="\${pdf.url}#navpanes=0&pagemode=none" width="100%" height="100%" style="border: none; flex: 1;"></iframe>
            </div>
          \`;
      });
      fallbackHtml += '</div>';
      container.innerHTML = fallbackHtml;
      return;
    }`;

renderJs = renderJs.replace(emptyPaneLogic, fallbackLogic);
fs.writeFileSync('site/js/render.js', renderJs);
console.log("Patched render.js to include fallback PDF viewer!");
