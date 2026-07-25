(() => {
  'use strict';

  const el = (sel) => document.querySelector(sel);
  const log = (...args) => console.log('[stock-dashboard]', ...args);

  const init = () => {
    log('static scaffold loaded');
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
