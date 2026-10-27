// Elementos do DOM
const pdfInput = document.getElementById('pdfInput');
const fileStatusText = document.getElementById('fileStatusText');
const fileInfoBox = document.getElementById('fileInfoBox');
const fileNameEl = document.getElementById('fileName');
const fileSizeEl = document.getElementById('fileSize');
const btnRemoveFile = document.getElementById('btnRemoveFile');
const btnExtract = document.getElementById('btnExtract');

// Elementos da Chave API Gemini
const apiKeyInput = document.getElementById('apiKeyInput');
const btnAplicarChave = document.getElementById('btnAplicarChave');
const btnToggleKey = document.getElementById('btnToggleKey');
const keyStatusBadge = document.getElementById('keyStatusBadge');

// Estado da Aplicação
let selectedFile = null;

// Formatação do tamanho do arquivo (KB/MB)
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  const kb = bytes / 1024;
  if (kb < 1024) return kb.toFixed(2) + ' KB';
  const mb = kb / 1024;
  return mb.toFixed(2) + ' MB';
}

function notificar(mensagem, tipo = 'info') {
  if (typeof window.mostrarNotificacao === 'function') {
    window.mostrarNotificacao(mensagem, tipo);
  } else {
    alert(mensagem);
  }
}

// Manipulação da seleção de arquivo PDF
if (pdfInput) {
  pdfInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
        notificar('Por favor, selecione um arquivo no formato PDF.', 'aviso');
        resetFileSelection();
        return;
      }

    selectedFile = file;
    fileNameEl.textContent = file.name;
    fileSizeEl.textContent = formatFileSize(file.size);

    fileInfoBox.classList.remove('hidden');
    fileStatusText.textContent = '';
    btnExtract.disabled = false;
  } else {
    resetFileSelection();
  }
});

// Remover arquivo selecionado
btnRemoveFile.addEventListener('click', () => {
  resetFileSelection();
});

const resultCard = document.getElementById('resultCard');
const jsonResult = document.getElementById('jsonResult');
const btnSalvarConta = document.getElementById('btnSalvarConta');
const btnText = document.getElementById('btnText');

// Aponta para o backend Flask (porta 5000) caso aberto via Live Server (porta 5500) localmente
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && window.location.port !== '5000' ? 'http://127.0.0.1:5000' : '';

let ultimoResultadoExtracao = null;

// Elementos da Segunda Etapa (Análise no Banco)
const analysisCard = document.getElementById('analysisCard');
const summaryNumeroNf = document.getElementById('summaryNumeroNf');
const summaryDataEmissao = document.getElementById('summaryDataEmissao');
const summaryDataVencimento = document.getElementById('summaryDataVencimento');
const summaryValorTotal = document.getElementById('summaryValorTotal');

const analysisFornecedorNome = document.getElementById('analysisFornecedorNome');
const analysisFornecedorDoc = document.getElementById('analysisFornecedorDoc');
const fornecedorStatusBadge = document.getElementById('fornecedorStatusBadge');

const analysisFaturadoNome = document.getElementById('analysisFaturadoNome');
const analysisFaturadoDoc = document.getElementById('analysisFaturadoDoc');
const faturadoStatusBadge = document.getElementById('faturadoStatusBadge');

const analysisDespesaNome = document.getElementById('analysisDespesaNome');
const despesaStatusBadge = document.getElementById('despesaStatusBadge');

const btnProcessarLancamento = document.getElementById('btnProcessarLancamento');
const btnProcessarText = document.getElementById('btnProcessarText');

const confirmationCard = document.getElementById('confirmationCard');
const confirmationList = document.getElementById('confirmationList');

// Formatação monetária BRL
function formatBRL(val) {
  const num = parseFloat(val) || 0;
  return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

// Reset da seleção
function resetFileSelection() {
  selectedFile = null;
  ultimoResultadoExtracao = null;
  pdfInput.value = '';
  fileInfoBox.classList.add('hidden');
  fileStatusText.textContent = 'Nenhum arquivo escolhido';
  btnExtract.disabled = true;
  if (analysisCard) analysisCard.classList.add('hidden');
  if (confirmationCard) confirmationCard.classList.add('hidden');
  if (resultCard) resultCard.classList.add('hidden');
  if (btnText) btnText.textContent = 'EXTRAIR DADOS';
}

// Renderização dos resultados da Segunda Etapa
function renderizarAnalise(analise) {
  if (!analise || !analysisCard) return;

  const forn = analise.fornecedor || {};
  const fat = analise.faturado || {};
  const desp = analise.classificacao || {};
  const extraidos = analise.dados_extraidos || {};

  // Resumo
  if (summaryNumeroNf) summaryNumeroNf.textContent = extraidos.numero_nf || 'S/N';
  if (summaryDataEmissao) summaryDataEmissao.textContent = extraidos.data_emissao || '-';
  if (summaryDataVencimento) summaryDataVencimento.textContent = extraidos.data_vencimento || extraidos.data_emissao || '-';
  if (summaryValorTotal) summaryValorTotal.textContent = formatBRL(extraidos.valor_total);

  // 1. Fornecedor
  if (analysisFornecedorNome) analysisFornecedorNome.textContent = forn.nome || 'Não identificado';
  if (analysisFornecedorDoc) analysisFornecedorDoc.textContent = forn.documento ? `CNPJ: ${forn.documento}` : 'CNPJ não informado';
  if (fornecedorStatusBadge) {
    if (forn.existe) {
      fornecedorStatusBadge.className = 'status-badge-exists';
      fornecedorStatusBadge.textContent = forn.situacao || `EXISTE — ID: ${forn.id}`;
    } else {
      fornecedorStatusBadge.className = 'status-badge-missing';
      fornecedorStatusBadge.textContent = 'NÃO EXISTE';
    }
  }

  // 2. Faturado
  if (analysisFaturadoNome) analysisFaturadoNome.textContent = fat.nome || 'Não identificado';
  if (analysisFaturadoDoc) analysisFaturadoDoc.textContent = fat.documento ? `CPF/CNPJ: ${fat.documento}` : 'Documento não informado';
  if (faturadoStatusBadge) {
    if (fat.existe) {
      faturadoStatusBadge.className = 'status-badge-exists';
      faturadoStatusBadge.textContent = fat.situacao || `EXISTE — ID: ${fat.id}`;
    } else {
      faturadoStatusBadge.className = 'status-badge-missing';
      faturadoStatusBadge.textContent = 'NÃO EXISTE';
    }
  }

  // 3. Despesa
  if (analysisDespesaNome) analysisDespesaNome.textContent = desp.descricao || 'MANUTENÇÃO E OPERAÇÃO';
  if (despesaStatusBadge) {
    if (desp.existe) {
      despesaStatusBadge.className = 'status-badge-exists';
      despesaStatusBadge.textContent = desp.situacao || `EXISTE — ID: ${desp.id}`;
    } else {
      despesaStatusBadge.className = 'status-badge-missing';
      despesaStatusBadge.textContent = 'NÃO EXISTE';
    }
  }

  analysisCard.classList.remove('hidden');
  if (confirmationCard) confirmationCard.classList.add('hidden');
  analysisCard.scrollIntoView({ behavior: 'smooth' });
}

// Acionamento do Agente de IA para Extração dos Dados + Execução da Segunda Etapa
btnExtract.addEventListener('click', async () => {
  if (!selectedFile) return;

  const originalText = btnText ? btnText.textContent : 'EXTRAIR DADOS';
  if (btnText) btnText.textContent = 'PROCESSANDO COM IA...';
  btnExtract.disabled = true;

  try {
    const formData = new FormData();
    formData.append('pdf', selectedFile);
    if (apiKeyInput && apiKeyInput.value.trim()) {
      formData.append('api_key', apiKeyInput.value.trim());
    }

    // Etapa 1: Extrair dados da NF em PDF
    const response = await fetch(`${API_BASE}/api/extrair-pdf`, {
      method: 'POST',
      body: formData,
    });

    const responseText = await response.text();
    let dados;
    try {
      dados = JSON.parse(responseText);
    } catch (parseErr) {
      throw new Error(`Resposta do servidor não é um JSON válido: ${responseText.substring(0, 100)}`);
    }

    if (!response.ok) {
      throw new Error(dados.erro || `Falha na requisição (Status ${response.status}).`);
    }

    ultimoResultadoExtracao = dados;

    if (jsonResult) {
      jsonResult.textContent = JSON.stringify(dados, null, 2);
    }
    if (resultCard) {
      resultCard.classList.remove('hidden');
    }

    // Etapa 2: Análise dos dados extraídos no banco de dados
    if (btnText) btnText.textContent = 'ANALISANDO NO BANCO...';
    const analiseRes = await fetch(`${API_BASE}/api/analisar-dados-extracao`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(dados),
    });

    if (!analiseRes.ok) {
      const errData = await analiseRes.json();
      throw new Error(errData.erro || 'Falha ao analisar dados no banco.');
    }

    const analiseData = await analiseRes.json();
    renderizarAnalise(analiseData);

  } catch (error) {
    console.error('Erro na extração/análise:', error);
    notificar('Erro ao processar dados da nota fiscal: ' + error.message, 'erro');
  } finally {
    if (btnText) btnText.textContent = originalText;
    btnExtract.disabled = false;
  }
});

// Ação do Botão: Processar e Registrar Lançamento pós-análise
if (btnProcessarLancamento) {
  btnProcessarLancamento.addEventListener('click', async () => {
    if (!ultimoResultadoExtracao) {
      notificar('Nenhum dado extraído para processar.', 'aviso');
      return;
    }

    const origTxt = btnProcessarText ? btnProcessarText.textContent : 'CONFIRMAR E PROCESSAR LANÇAMENTO';
    try {
      btnProcessarLancamento.disabled = true;
      if (btnProcessarText) btnProcessarText.textContent = 'PERSISTINDO NO BANCO...';

      const res = await fetch(`${API_BASE}/api/processar-lancamento-extracao`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ultimoResultadoExtracao),
      });

      const resData = await res.json();
      if (!res.ok) {
        throw new Error(resData.erro || `Erro HTTP ${res.status}`);
      }

      // Exibir card de confirmação com dados reais do banco
      if (confirmationList && resData.resumo) {
        const r = resData.resumo;
        confirmationList.innerHTML = `
          <li><strong>Fornecedor:</strong> ${r.fornecedor.razao_social} (ID: ${r.fornecedor.id}) ${r.fornecedor.criado ? '<span class="badge badge-active" style="font-size:10px;">Cadastrado</span>' : '<span class="badge badge-active" style="font-size:10px;">Existente</span>'}</li>
          <li><strong>Faturado:</strong> ${r.faturado.nome} (ID: ${r.faturado.id}) ${r.faturado.criado ? '<span class="badge badge-active" style="font-size:10px;">Cadastrado</span>' : '<span class="badge badge-active" style="font-size:10px;">Existente</span>'}</li>
          <li><strong>Classificação:</strong> ${r.classificacao.categoria} (ID: ${r.classificacao.id}) ${r.classificacao.criado ? '<span class="badge badge-active" style="font-size:10px;">Cadastrada</span>' : '<span class="badge badge-active" style="font-size:10px;">Existente</span>'}</li>
          <li><strong>Movimento Financeiro:</strong> ID real ${r.movimento.id} (Tipo: ${r.movimento.tipo}, NF: ${r.movimento.numero_nf}, Total: ${formatBRL(r.movimento.valor_total)})</li>
          <li><strong>Parcelas:</strong> ${r.quantidade_parcelas} parcela(s) registrada(s) ${r.parcelas && r.parcelas[0] ? `[ID: ${r.parcelas[0].id}, Identificação: ${r.parcelas[0].identificacao}, Vencimento: ${r.parcelas[0].data_vencimento}]` : ''}</li>
        `;
      }

      if (analysisCard) analysisCard.classList.add('hidden');
      if (confirmationCard) {
        confirmationCard.classList.remove('hidden');
        confirmationCard.scrollIntoView({ behavior: 'smooth' });
      }

    } catch (err) {
      console.error('Erro ao processar lançamento:', err);
      notificar('Não foi possível concluir o lançamento: ' + err.message, 'erro');
    } finally {
      btnProcessarLancamento.disabled = false;
      if (btnProcessarText) btnProcessarText.textContent = origTxt;
    }
  });
}

// ============================================================================
// GERENCIAMENTO DA CHAVE DE API GEMINI (ATIVAR / VISUALIZAR / STATUS)
// ============================================================================

function atualizarBadgeStatusChave(configurada) {
  if (!keyStatusBadge) return;
  if (configurada) {
    keyStatusBadge.style.background = '#dcfce7';
    keyStatusBadge.style.color = '#166534';
    keyStatusBadge.textContent = 'Ativa';
    if (apiKeyInput && !apiKeyInput.value) {
      const salva = sessionStorage.getItem('gemini_api_key');
      if (salva) apiKeyInput.value = salva;
    }
  } else {
    keyStatusBadge.style.background = '#fee2e2';
    keyStatusBadge.style.color = '#991b1b';
    keyStatusBadge.textContent = 'Não configurada';
    if (apiKeyInput && !apiKeyInput.value) {
      apiKeyInput.placeholder = 'Cole sua chave Gemini aqui e clique em Aplicar';
    }
  }
}

async function verificarStatusChave() {
  if (!keyStatusBadge) return;
  
  // 1. Restaurar chave salva no sessionStorage se existir
  const salva = sessionStorage.getItem('gemini_api_key');
  if (salva && apiKeyInput && !apiKeyInput.value) {
    apiKeyInput.value = salva;
  }

  try {
    const res = await fetch(`${API_BASE}/api/status-chave`);
    if (res.ok) {
      const data = await res.json();
      if (data.configurada) {
        atualizarBadgeStatusChave(true);
      } else if (salva) {
        // Se temos chave no sessionStorage mas o servidor reiniciou, re-aplicar automaticamente
        try {
          const autoRes = await fetch(`${API_BASE}/api/configurar-chave`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: salva }),
          });
          if (autoRes.ok) {
            atualizarBadgeStatusChave(true);
            return;
          }
        } catch (_) {}
        atualizarBadgeStatusChave(false);
      } else {
        atualizarBadgeStatusChave(false);
      }
    } else {
      atualizarBadgeStatusChave(false);
    }
  } catch (err) {
    console.warn('Não foi possível verificar status da chave:', err);
    atualizarBadgeStatusChave(false);
  }
}

// Botão Ativar / Aplicar Chave
if (btnAplicarChave) {
  btnAplicarChave.addEventListener('click', async () => {
    if (!apiKeyInput) return;
    const chave = apiKeyInput.value.trim();
    if (!chave) {
      notificar('Por favor, informe a chave da API antes de aplicar.', 'aviso');
      apiKeyInput.focus();
      return;
    }

    const textoOriginal = btnAplicarChave.textContent;
    btnAplicarChave.disabled = true;
    btnAplicarChave.textContent = 'Aplicando...';

    try {
      const res = await fetch(`${API_BASE}/api/configurar-chave`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: chave }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.erro || `Erro HTTP ${res.status}`);
      }

      // Salvar no sessionStorage para persistir enquanto o site estiver aberto
      sessionStorage.setItem('gemini_api_key', chave);
      atualizarBadgeStatusChave(true);
      notificar(data.mensagem || 'Chave da API Gemini configurada com sucesso.', 'sucesso');
    } catch (err) {
      console.error('Erro ao configurar chave da API:', err);
      notificar('Falha ao aplicar chave: ' + err.message, 'erro');
    } finally {
      btnAplicarChave.disabled = false;
      btnAplicarChave.textContent = textoOriginal;
    }
  });
}

// Botão Visualizar / Esconder Chave
if (btnToggleKey && apiKeyInput) {
  btnToggleKey.addEventListener('click', () => {
    if (apiKeyInput.type === 'password') {
      apiKeyInput.type = 'text';
      btnToggleKey.textContent = '🙈';
      btnToggleKey.title = 'Esconder chave';
    } else {
      apiKeyInput.type = 'password';
      btnToggleKey.textContent = '👁';
      btnToggleKey.title = 'Mostrar chave';
    }
  });
}

// Pressionar Enter no campo da chave aplica automaticamente
if (apiKeyInput && btnAplicarChave) {
  apiKeyInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      btnAplicarChave.click();
    }
  });
}

// Carregar versão no rodapé
async function carregarVersao() {
  const versionLink = document.getElementById('versionLink');
  if (!versionLink) return;
  try {
    const res = await fetch(`${API_BASE}/api/version`);
    if (res.ok) {
      const data = await res.json();
      versionLink.textContent = data.commit_short || data.commit || 'v2.0.0';
      if (data.link_commit) {
        versionLink.href = data.link_commit;
      }
    } else {
      versionLink.textContent = 'v2.0.0';
    }
  } catch (e) {
    versionLink.textContent = 'v2.0.0';
  }
}

// Inicializações ao carregar a página
verificarStatusChave();
carregarVersao();
