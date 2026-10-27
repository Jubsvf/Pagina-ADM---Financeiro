/**
 * Sistema Moderno de Notificações Toast
 * Suporta tipos: 'sucesso', 'erro', 'aviso', 'info'
 */
(function() {
  function getOrCreateContainer() {
    let container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  const ICON_SVGS = {
    sucesso: '<svg class="toast-icon text-success" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
    erro: '<svg class="toast-icon text-error" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>',
    aviso: '<svg class="toast-icon text-warning" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
    info: '<svg class="toast-icon text-info" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>'
  };

  const DEFAULT_TITLES = {
    sucesso: 'Sucesso',
    erro: 'Erro',
    aviso: 'Atenção',
    info: 'Informação'
  };

  function mostrarNotificacao(mensagem, tipo = 'sucesso', titulo = '') {
    const container = getOrCreateContainer();
    const tipoNormalizado = (tipo || 'info').toLowerCase();
    const tipoValido = ['sucesso', 'erro', 'aviso', 'info'].includes(tipoNormalizado) ? tipoNormalizado : 'info';
    const tituloFinal = titulo || DEFAULT_TITLES[tipoValido];

    const toast = document.createElement('div');
    toast.className = `toast toast-${tipoValido}`;

    toast.innerHTML = `
      <div class="toast-icon-wrapper">
        ${ICON_SVGS[tipoValido]}
      </div>
      <div class="toast-body">
        <div class="toast-title">${tituloFinal}</div>
        <div class="toast-message">${mensagem}</div>
      </div>
      <button type="button" class="toast-close" aria-label="Fechar">&times;</button>
    `;

    const closeBtn = toast.querySelector('.toast-close');
    const fechar = () => {
      toast.classList.add('toast-leaving');
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 250);
    };

    closeBtn.addEventListener('click', fechar);

    // Auto-dismiss após 4.5 segundos
    const timer = setTimeout(fechar, 4500);
    toast.addEventListener('mouseenter', () => clearTimeout(timer));

    container.appendChild(toast);
  }

  // Exportar globalmente
  window.mostrarNotificacao = mostrarNotificacao;
  window.toast = {
    sucesso: (msg, tit) => mostrarNotificacao(msg, 'sucesso', tit),
    erro: (msg, tit) => mostrarNotificacao(msg, 'erro', tit),
    aviso: (msg, tit) => mostrarNotificacao(msg, 'aviso', tit),
    info: (msg, tit) => mostrarNotificacao(msg, 'info', tit)
  };

  // Inicialização Automática da Sidebar
  document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname.replace(/\/$/, '') || '/';
    document.querySelectorAll('.sidebar-link').forEach(link => {
      const href = link.getAttribute('href');
      const dataRoute = link.getAttribute('data-route');
      if (href === path || dataRoute === path || (path === '' && href === '/')) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });

    // Logout
    const btnLogout = document.getElementById('btnLogoutSidebar');
    if (btnLogout) {
      btnLogout.addEventListener('click', async () => {
        try {
          await fetch('/api/logout', { method: 'POST' });
          window.location.href = '/login';
        } catch (_) {
          window.location.href = '/login';
        }
      });
    }

    // Versão Git no Rodapé da Sidebar
    const gitBadge = document.getElementById('sidebarGitHash');
    if (gitBadge) {
      fetch('/api/version')
        .then(r => r.json())
        .then(d => {
          if (d && d.commit_short && d.commit_short !== 'N/A') {
            gitBadge.textContent = d.commit_short;
          }
        })
        .catch(() => {});
    }
  });
})();
