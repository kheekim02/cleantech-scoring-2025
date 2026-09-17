window.CTO = window.CTO || {};

window.CTO.Export = {
  exportPDF() {
    // Make sure all cards are visible for print (ensure both tabs display)
    const viewAi = document.getElementById('view-ai');
    const viewHuman = document.getElementById('view-human');
    
    // Temporarily remove hidden classes to force render everything in print
    const aiWasHidden = viewAi.classList.contains('hidden');
    const humanWasHidden = viewHuman.classList.contains('hidden');
    
    viewAi.classList.remove('hidden');
    viewHuman.classList.remove('hidden');
    
    // Trigger print
    window.print();
    
    // Restore tab state after print dialogue closes
    if (aiWasHidden) viewAi.classList.add('hidden');
    if (humanWasHidden) viewHuman.classList.add('hidden');
  }
};
