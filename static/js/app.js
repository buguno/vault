// Let HTMX swap validation (422) and domain-rule (409) responses into the page.
document.addEventListener('htmx:beforeSwap', (event) => {
  const status = event.detail.xhr.status;
  if (status === 409 || status === 422) {
    event.detail.shouldSwap = true;
    event.detail.isError = false;
  }
});

// Modals use the native <dialog> element.
document.addEventListener('click', (event) => {
  const opener = event.target.closest('[data-modal-open]');
  if (opener) {
    document.getElementById(opener.dataset.modalOpen).showModal();
    return;
  }
  if (event.target.closest('[data-modal-close]')) {
    event.target.closest('dialog').close();
    return;
  }
  // A click on the backdrop targets the <dialog> itself.
  if (event.target.matches('dialog.modal')) event.target.close();
});

// Reopen dialogs that came back with validation errors.
function openPendingModals() {
  document.querySelectorAll('dialog[data-open]').forEach((dialog) => {
    dialog.removeAttribute('data-open');
    dialog.showModal();
  });
}
document.addEventListener('DOMContentLoaded', openPendingModals);
document.addEventListener('htmx:afterSettle', openPendingModals);

// Selects marked data-autosubmit submit their form on change (language picker).
document.addEventListener('change', (event) => {
  if (event.target.matches('[data-autosubmit]')) event.target.form.submit();
});

// Sidebar (mobile drawer): the menu button opens it, the overlay, Esc or a link closes it.
// Closed on a small screen it is inert, so Tab never lands on links nobody can see.
const wideScreen = matchMedia('(min-width: 1024px)');

function syncSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;
  const open = sidebar.hasAttribute('data-open');
  sidebar.toggleAttribute('inert', !wideScreen.matches && !open);
  document
    .querySelector('[data-sidebar-toggle]')
    ?.setAttribute('aria-expanded', String(open));
}

function setSidebar(open) {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;
  const wasOpen = sidebar.hasAttribute('data-open');
  sidebar.toggleAttribute('data-open', open);
  document.getElementById('sidebar-overlay')?.toggleAttribute('data-open', open);
  syncSidebar();
  if (open) sidebar.querySelector('a, button')?.focus();
  else if (wasOpen) document.querySelector('[data-sidebar-toggle]')?.focus();
}
document.addEventListener('click', (event) => {
  if (event.target.closest('[data-sidebar-toggle]')) setSidebar(true);
  else if (event.target.closest('[data-sidebar-close]')) setSidebar(false);
  else if (event.target.closest('#sidebar a')) setSidebar(false);
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') setSidebar(false);
});
wideScreen.addEventListener('change', syncSidebar);
document.addEventListener('DOMContentLoaded', syncSidebar);

// A form that was sent cannot be sent again while the page loads: no double entries.
document.addEventListener('submit', (event) => {
  const form = event.target;
  if (event.defaultPrevented || form.method !== 'post') return;
  if (form.hasAttribute('hx-post')) return;
  requestAnimationFrame(() => {
    form.querySelectorAll('button[type="submit"]').forEach((button) => {
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
    });
  });
});
window.addEventListener('pageshow', (event) => {
  if (!event.persisted) return;
  document.querySelectorAll('button[aria-busy="true"]').forEach((button) => {
    button.disabled = false;
    button.removeAttribute('aria-busy');
  });
});

// Dropdown menus built on <details data-menu> close when you click elsewhere.
document.addEventListener('click', (event) => {
  document.querySelectorAll('details[data-menu][open]').forEach((menu) => {
    if (!menu.contains(event.target)) menu.removeAttribute('open');
  });
});
