// Injected into every tool page by build.py.
const REPO = 'https://github.com/aceofaces/tools';
const slug = location.pathname.split('/').pop().replace(/\.html$/, '') || 'index';

const footer = document.createElement('footer');
footer.className = 'tools-footer';
footer.innerHTML = `
  <a href="./">All tools</a>
  <span aria-hidden="true">·</span>
  <a href="${REPO}/blob/main/${slug}.html">Source</a>
  <span aria-hidden="true">·</span>
  <a href="colophon.html#${slug}">History</a>
`;

const style = document.createElement('style');
style.textContent = `
  .tools-footer { max-width: 760px; margin: 48px auto 24px; padding: 12px 16px 0;
    border-top: 1px solid rgba(128,128,128,.3); font: 14px/1.4 system-ui, sans-serif;
    color: #777; display: flex; gap: 8px; flex-wrap: wrap; }
  .tools-footer a { color: inherit; }
  @media print { .tools-footer { display: none; } }
`;
document.head.appendChild(style);
document.body.appendChild(footer);
