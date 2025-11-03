document.addEventListener('click', function(e){
  if(e.target && e.target.id==='add-line'){
    const items = document.getElementById('items');
    const first = items.querySelector('.sale-line');
    const clone = first.cloneNode(true);
    clone.querySelectorAll('input').forEach(i=>{ if(i.type==='number') i.value='1'; else i.value=''; });
    items.appendChild(clone);
  }
  if(e.target && e.target.classList.contains('remove-line')){
    const line = e.target.closest('.sale-line');
    const parent = document.getElementById('items');
    if(parent.querySelectorAll('.sale-line').length>1) line.remove();
  }
});

// Loading / double-submit protection
(function(){
  const overlay = document.getElementById('loading-overlay');

  function showLoading(message, submitter){
    if(!overlay) return;
    const msgEl = overlay.querySelector('.loading-message');
    msgEl.textContent = message || 'Loading…';
    overlay.style.display = 'flex';

    // disable all submit controls to avoid double submissions
    document.querySelectorAll('button, input[type="submit"]').forEach(b=>{
      // remember previous state
      if(b.dataset.__disabledByLoading===undefined) b.dataset.__disabledByLoading = b.disabled ? '1' : '0';
      b.disabled = true;
    });

    if(submitter){
      try{
        if(submitter.tagName === 'BUTTON'){
          submitter.dataset.__origHtml = submitter.innerHTML;
          submitter.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> ' + (message || 'Loading…');
        }
      }catch(err){/* ignore */}
    }
  }

  function hideLoading(){
    if(!overlay) return;
    overlay.style.display = 'none';
    document.querySelectorAll('button, input[type="submit"]').forEach(b=>{
      if(b.dataset.__disabledByLoading==='0') b.disabled = false;
      // cleanup stored props
      delete b.dataset.__disabledByLoading;
      if(b.dataset.__origHtml){ b.innerHTML = b.dataset.__origHtml; delete b.dataset.__origHtml; }
    });
  }

  // Expose for manual use if needed
  window.showLoading = showLoading;
  window.hideLoading = hideLoading;

  document.addEventListener('submit', function(e){
    // if overlay already visible, prevent additional submits
    if(overlay && overlay.style.display !== 'none'){
      e.preventDefault();
      return;
    }

    // try to get the submitter (modern browsers) and a contextual message
    const submitter = e.submitter || document.activeElement;
    let message = 'Loading…';
    try{
      if(submitter && submitter.getAttribute){
        message = submitter.getAttribute('data-loading') || submitter.dataset.loading || message;
      }
    }catch(err){}

    // show loading UI; allow normal submit to proceed
    showLoading(message, submitter);
  }, true);

  // If there are forms submitted via AJAX, callers can manually call hideLoading() on completion.
})();
