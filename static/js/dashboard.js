/**
 * Lógica do Dashboard - Gestão de Lançamentos & Contas
 */

const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") && window.location.port !== "5000" ? "http://127.0.0.1:5000" : "";

let dadosLancamentos = [];
let ordenacaoAtual = { coluna: 'data_emissao', desc: true };

function formatarBRL(valor) {
  const num = Number(valor) || 0;
  return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function formatarData(isoStr) {
  if (!isoStr) return '-';
  const partes = isoStr.split('T')[0].split('-');
  if (partes.length === 3) {
    return `${partes[2]}/${partes[1]}/${partes[0]}`;
  }
  return isoStr;
}

// Carregar versão git no rodapé da sidebar
async function carregarVersaoSidebar() {
  try {
    const res = await fetch(`${API_BASE}/api/version`);
    if (res.ok) {
      const data = await res.json();
      const el = document.getElementById('sidebarGitHash');
      if (el) el.textContent = data.commit_short || '12c68a';
    }
  } catch (_) {
    const el = document.getElementById('sidebarGitHash');
    if (el) el.textContent = '12c68a';
  }
}

// Carregar Métricas e Lançamentos
async function carregarLancamentos(params = {}) {
  const queryParams = new URLSearchParams(params);
  try {
    const res = await fetch(`${API_BASE}/api/lancamentos?${queryParams.toString()}`);
    if (!res.ok) throw new Error(`Erro HTTP ${res.status}`);
    const data = await res.json();

    // Atualizar KPIs
    if (data.kpis) {
      const elTotal = document.getElementById('kpiTotalLancamentos');
      const elDesp = document.getElementById('kpiTotalDespesas');
      const elRec = document.getElementById('kpiTotalReceitas');
      const elParc = document.getElementById('kpiParcelasAberto');
      const elSaldo = document.getElementById('kpiSaldoPendente');

      if (elTotal) elTotal.textContent = data.kpis.total_lancamentos_ativos;
      if (elDesp) elDesp.textContent = formatarBRL(data.kpis.total_despesas);
      if (elRec) elRec.textContent = formatarBRL(data.kpis.total_receitas);
      if (elParc) elParc.textContent = data.kpis.total_parcelas_aberto;
      if (elSaldo) elSaldo.textContent = `Saldo pendente: ${formatarBRL(data.kpis.saldo_pendente)}`;
    }

    dadosLancamentos = data.itens || [];
    renderizarTabela(dadosLancamentos);

  } catch (err) {
    console.error('Erro ao carregar lançamentos:', err);
    if (typeof window.mostrarNotificacao === 'function') {
      window.mostrarNotificacao('Falha ao carregar dados dos lançamentos: ' + err.message, 'erro');
    }
  }
}

function renderizarTabela(itens) {
  const emptyState = document.getElementById('emptyStateLancamentos');
  const tableContainer = document.getElementById('tableContainerLancamentos');
  const tbody = document.getElementById('tbodyLancamentos');

  if (!itens || itens.length === 0) {
    if (emptyState) emptyState.classList.remove('hidden');
    if (tableContainer) tableContainer.classList.add('hidden');
    return;
  }

  if (emptyState) emptyState.classList.add('hidden');
  if (tableContainer) tableContainer.classList.remove('hidden');

  tbody.innerHTML = '';
  itens.forEach(item => {
    const tr = document.createElement('tr');
    const isDespesa = item.tipo === 'DESPESA';
    const badgeClass = isDespesa ? 'badge badge-inactive' : 'badge badge-active';
    const statusBadge = item.ativo ? '<span class="badge badge-active">Ativo</span>' : '<span class="badge badge-inactive">Inativo</span>';

    tr.innerHTML = `
      <td style="font-weight: 600; color: #475569;">#${item.id}</td>
      <td style="font-weight: 600;">${item.numero_nf || 'S/N'}</td>
      <td><span class="${badgeClass}">${item.tipo}</span></td>
      <td>
        <div style="font-weight: 600; color: #0f172a;">${item.pessoa}</div>
        <div style="font-size: 11px; color: #64748b;">${item.pessoa_doc || ''}</div>
      </td>
      <td>
        <div style="color: #334155;">${item.faturado}</div>
        <div style="font-size: 11px; color: #64748b;">${item.faturado_doc || ''}</div>
      </td>
      <td>${formatarData(item.data_emissao)}</td>
      <td style="font-weight: 700; color: ${isDespesa ? '#dc2626' : '#16a34a'};">${formatarBRL(item.valor_total)}</td>
      <td style="text-align: center;">${item.quantidade_parcelas}</td>
      <td>
        <div style="display: flex; gap: 6px; align-items: center;">
          <a href="${item.url_modulo}" class="btn-sm" title="Acessar Módulo">Ver Detalhes</a>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// Configurar Eventos do Dashboard
document.addEventListener('DOMContentLoaded', () => {
  carregarVersaoSidebar();
  
  // Carrega inicialmente os KPIs e dados
  carregarLancamentos({ tipo: 'todos', status: 'ativos' });

  const btnBuscar = document.getElementById('btnBuscarLancamentos');
  const btnTodos = document.getElementById('btnTodosLancamentos');
  const btnEmptyCarregar = document.getElementById('btnEmptyCarregar');
  const btnRefresh = document.getElementById('btnRefreshDashboard');
  const inputBusca = document.getElementById('searchQuery');
  const selectTipo = document.getElementById('filterTipo');
  const selectStatus = document.getElementById('filterStatus');

  function executarBusca() {
    const q = inputBusca ? inputBusca.value.trim() : '';
    const tipo = selectTipo ? selectTipo.value : 'todos';
    const status = selectStatus ? selectStatus.value : 'ativos';
    carregarLancamentos({ q, tipo, status });
  }

  if (btnBuscar) btnBuscar.addEventListener('click', executarBusca);
  if (inputBusca) {
    inputBusca.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        executarBusca();
      }
    });
  }

  if (btnTodos) {
    btnTodos.addEventListener('click', () => {
      if (inputBusca) inputBusca.value = '';
      if (selectTipo) selectTipo.value = 'todos';
      if (selectStatus) selectStatus.value = 'todos';
      carregarLancamentos({ tipo: 'todos', status: 'todos' });
    });
  }

  if (btnEmptyCarregar) {
    btnEmptyCarregar.addEventListener('click', () => {
      if (inputBusca) inputBusca.value = '';
      if (selectTipo) selectTipo.value = 'todos';
      if (selectStatus) selectStatus.value = 'ativos';
      carregarLancamentos({ tipo: 'todos', status: 'ativos' });
    });
  }

  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => {
      executarBusca();
      if (typeof window.mostrarNotificacao === 'function') {
        window.mostrarNotificacao('Dados atualizados com sucesso.', 'info');
      }
    });
  }

  // Logout no Sidebar
  const btnLogout = document.getElementById('btnLogoutSidebar');
  if (btnLogout) {
    btnLogout.addEventListener('click', async () => {
      try {
        await fetch(`${API_BASE}/api/logout`, { method: 'POST' });
        window.location.href = '/login';
      } catch (_) {
        window.location.href = '/login';
      }
    });
  }
});
