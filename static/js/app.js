// ============================================================================
// AGROFINANCEIRO N2 - APP.JS
// Extração de Notas Fiscais e Integração com Inteligência Artificial (Gemini)
// ============================================================================

// Base da API (compatível com execução local na porta 5000 ou servidores estáticos)
const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') &&
  window.location.port !== '5000' && window.location.port !== '' ? 'http://127.0.0.1:5000' : '';

// Elementos do DOM - Upload de PDF
const pdfInput = document.getElementById('pdfInput');
const fileStatusText = document.getElementById('fileStatusText');
const fileInfoBox = document.getElementById('fileInfoBox');
const fileNameEl = document.getElementById('fileName');
const fileSizeEl = document.getElementById('fileSize');
const btnRemoveFile = document.getElementById('btnRemoveFile');
const btnExtract = document.getElementById('btnExtract');
const btnText = document.getElementById('btnText');
const extractStatusBox = document.getElementById('extractStatusBox');
const extractStatusText = document.getElementById('extractStatusText');

// Elementos do DOM - Chave da API Gemini
const apiKeyInput = document.getElementById('apiKeyInput');
const btnAplicarChave = document.getElementById('btnAplicarChave');
const btnToggleKey = document.getElementById('btnToggleKey');
const keyStatusBadge = document.getElementById('keyStatusBadge');

// Elementos do DOM - Análise e Resultados
const analysisCard = document.getElementById('analysisCard');
const confirmationCard = document.getElementById('confirmationCard');
const confirmationList = document.getElementById('confirmationList');
const resultCard = document.getElementById('resultCard');
const jsonResult = document.getElementById('jsonResult');
const btnProcessarLancamento = document.getElementById('btnProcessarLancamento');
const btnProcessarText = document.getElementById('btnProcessarText');

// Ícones SVG para alternar visibilidade de chave (sem emojis)
const SVG_EYE = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 18px; height: 18px;"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
const SVG_EYE_OFF = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width: 18px; height: 18px;"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`;

// Estado da Aplicação
let selectedFile = null;
let ultimoResultadoExtracao = null;

// Formatação do tamanho do arquivo (KB/MB)
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  const kb = bytes / 1024;
  if (kb < 1024) return kb.toFixed(2) + ' KB';
  const mb = kb / 1024;
  return mb.toFixed(2) + ' MB';
}

// Formatação monetária BRL
function formatBRL(val) {
  const num = parseFloat(val) || 0;
  return num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

// Disparo de notificações visuais (via toast ou alert fallback)
function notificar(mensagem, tipo = 'info') {
  if (typeof window.mostrarNotificacao === 'function') {
    window.mostrarNotificacao(mensagem, tipo);
  } else if (window.toast && typeof window.toast[tipo] === 'function') {
    window.toast[tipo](mensagem);
  } else {
    alert(mensagem);
  }
}

// Feedback visual do status da extração
function setStatusExtracao(ativo, mensagem = '') {
  if (extractStatusBox) {
    if (ativo) {
      extractStatusBox.classList.remove('hidden');
      if (extractStatusText) extractStatusText.textContent = mensagem;
    } else {
      extractStatusBox.classList.add('hidden');
    }
  }
}

// Reset da seleção de arquivo
function resetFileSelection() {
  selectedFile = null;
  ultimoResultadoExtracao = null;
  if (pdfInput) pdfInput.value = '';
  if (fileInfoBox) fileInfoBox.classList.add('hidden');
  if (fileStatusText) fileStatusText.textContent = 'Nenhum arquivo escolhido';
  if (btnExtract) btnExtract.disabled = true;
  if (analysisCard) analysisCard.classList.add('hidden');
  if (confirmationCard) confirmationCard.classList.add('hidden');
  if (resultCard) resultCard.classList.add('hidden');
  if (btnText) btnText.textContent = 'Extrair Dados';
  setStatusExtracao(false);
}

// Manipulação da seleção de arquivo PDF
if (pdfInput) {
  pdfInput.addEventListener('change', (e) => {
    const file = e.target.files && e.target.files[0];
    if (file) {
      if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
        notificar('Por favor, selecione um arquivo no formato PDF.', 'aviso');
        resetFileSelection();
        return;
      }

      selectedFile = file;
      if (fileNameEl) fileNameEl.textContent = file.name;
      if (fileSizeEl) fileSizeEl.textContent = formatFileSize(file.size);

      if (fileInfoBox) fileInfoBox.classList.remove('hidden');
      if (fileStatusText) fileStatusText.textContent = '';
      if (btnExtract) btnExtract.disabled = false;
    } else {
      resetFileSelection();
    }
  });
}

// Remover arquivo selecionado
if (btnRemoveFile) {
  btnRemoveFile.addEventListener('click', () => {
    resetFileSelection();
  });
}

// Renderização dos resultados da Segunda Etapa (Entidades e Relacionamento no Banco)
function renderizarAnalise(analise) {
  if (!analise || !analysisCard) return;

  const forn = analise.fornecedor || {};
  const fat = analise.faturado || {};
  const desp = analise.classificacao || {};
  const extraidos = analise.dados_extraidos || {};

  // Resumo de Metadados da Nota Fiscal
  const elNumNf = document.getElementById('metaNumeroNf') || document.getElementById('summaryNumeroNf');
  if (elNumNf) elNumNf.textContent = extraidos.numero_nf || 'S/N';

  const elDtEmissao = document.getElementById('metaDataEmissao') || document.getElementById('summaryDataEmissao');
  if (elDtEmissao) elDtEmissao.textContent = extraidos.data_emissao || '-';

  const elValTotal = document.getElementById('metaValorTotal') || document.getElementById('summaryValorTotal');
  if (elValTotal) elValTotal.textContent = formatBRL(extraidos.valor_total);

  const elParcelas = document.getElementById('metaParcelas') || document.getElementById('summaryDataVencimento');
  if (elParcelas) {
    elParcelas.textContent = extraidos.data_vencimento ? `Venc: ${extraidos.data_vencimento}` : (extraidos.data_emissao || '1x à vista');
  }

  // 1. Fornecedor (Emitente)
  const elStatusForn = document.getElementById('statusFornecedor') || document.getElementById('fornecedorStatusBadge');
  if (elStatusForn) {
    if (forn.existe) {
      elStatusForn.className = 'status-badge-exists';
      elStatusForn.textContent = forn.situacao || `EXISTE — ID: ${forn.id}`;
    } else {
      elStatusForn.className = 'status-badge-missing';
      elStatusForn.textContent = 'NÃO EXISTE (SERÁ CRIADO)';
    }
  }
  const elDetForn = document.getElementById('detalhesFornecedor') || document.getElementById('analysisFornecedorNome');
  if (elDetForn) {
    elDetForn.innerHTML = `<strong>${forn.nome || 'Não identificado'}</strong><br><span style="font-family: monospace; font-size: 11px;">${forn.documento ? `CNPJ: ${forn.documento}` : 'CNPJ não informado'}</span>`;
  }

  // 2. Faturado (Destinatário)
  const elStatusFat = document.getElementById('statusFaturado') || document.getElementById('faturadoStatusBadge');
  if (elStatusFat) {
    if (fat.existe) {
      elStatusFat.className = 'status-badge-exists';
      elStatusFat.textContent = fat.situacao || `EXISTE — ID: ${fat.id}`;
    } else {
      elStatusFat.className = 'status-badge-missing';
      elStatusFat.textContent = 'NÃO EXISTE (SERÁ CRIADO)';
    }
  }
  const elDetFat = document.getElementById('detalhesFaturado') || document.getElementById('analysisFaturadoNome');
  if (elDetFat) {
    elDetFat.innerHTML = `<strong>${fat.nome || 'Não identificado'}</strong><br><span style="font-family: monospace; font-size: 11px;">${fat.documento ? `CPF/CNPJ: ${fat.documento}` : 'Documento não informado'}</span>`;
  }

  // 3. Classificação da Despesa
  const elStatusDesp = document.getElementById('statusClassificacao') || document.getElementById('despesaStatusBadge');
  if (elStatusDesp) {
    if (desp.existe) {
      elStatusDesp.className = 'status-badge-exists';
      elStatusDesp.textContent = desp.situacao || `EXISTE — ID: ${desp.id}`;
    } else {
      elStatusDesp.className = 'status-badge-missing';
      elStatusDesp.textContent = 'NÃO EXISTE (SERÁ CRIADA)';
    }
  }
  const elDetDesp = document.getElementById('detalhesClassificacao') || document.getElementById('analysisDespesaNome');
  if (elDetDesp) {
    elDetDesp.innerHTML = `<strong>${desp.descricao || 'MANUTENÇÃO E OPERAÇÃO'}</strong>`;
  }

  // Badge no cabeçalho do card
  const analysisBadge = document.getElementById('analysisBadge');
  if (analysisBadge) analysisBadge.style.display = 'inline-block';

  analysisCard.classList.remove('hidden');
  if (confirmationCard) confirmationCard.classList.add('hidden');
  analysisCard.scrollIntoView({ behavior: 'smooth' });
}

// Acionamento do Agente de IA para Extração dos Dados + Execução da Segunda Etapa
if (btnExtract) {
  btnExtract.addEventListener('click', async () => {
    if (!selectedFile) {
      notificar('Por favor, selecione um arquivo PDF antes de extrair.', 'aviso');
      return;
    }

    const originalText = btnText ? btnText.textContent : 'Extrair Dados';
    if (btnText) btnText.textContent = 'PROCESSANDO COM IA...';
    btnExtract.disabled = true;
    setStatusExtracao(true, 'Lendo páginas do PDF e extraindo com IA Gemini...');

    try {
      const formData = new FormData();
      formData.append('pdf', selectedFile);

      // Envia a chave atual informada no input ou gravada em sessionStorage
      const chaveAtual = (apiKeyInput && apiKeyInput.value.trim()) || sessionStorage.getItem('gemini_api_key') || '';
      if (chaveAtual) {
        formData.append('api_key', chaveAtual);
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
      setStatusExtracao(true, 'Consultando banco de dados para Fornecedor, Faturado e Classificação...');

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
      notificar('Dados extraídos e analisados com sucesso!', 'sucesso');

    } catch (error) {
      console.error('Erro na extração/análise:', error);
      notificar('Erro ao processar dados da nota fiscal: ' + error.message, 'erro');
    } finally {
      if (btnText) btnText.textContent = originalText;
      btnExtract.disabled = false;
      setStatusExtracao(false);
    }
  });
}

// Ação do Botão: Processar e Registrar Lançamento pós-análise
if (btnProcessarLancamento) {
  btnProcessarLancamento.addEventListener('click', async () => {
    if (!ultimoResultadoExtracao) {
      notificar('Nenhum dado extraído para processar.', 'aviso');
      return;
    }

    const origTxt = btnProcessarText ? btnProcessarText.textContent : 'Confirmar e Processar Lançamento';
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
      notificar('Lançamento e parcelas persistidos no banco de dados com sucesso!', 'sucesso');

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
    keyStatusBadge.textContent = 'Não ativa';
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

// Botão Visualizar / Esconder Chave (Ícones SVG profissionais, sem emojis)
if (btnToggleKey && apiKeyInput) {
  btnToggleKey.addEventListener('click', () => {
    const isPassword = apiKeyInput.type === 'password';
    apiKeyInput.type = isPassword ? 'text' : 'password';
    btnToggleKey.title = isPassword ? 'Ocultar chave' : 'Mostrar chave';
    btnToggleKey.innerHTML = isPassword ? SVG_EYE_OFF : SVG_EYE;
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

// Carregar versão no rodapé da sidebar
async function carregarVersao() {
  const versionLink = document.getElementById('sidebarGitHash');
  if (!versionLink) return;
  try {
    const res = await fetch(`${API_BASE}/api/version`);
    if (res.ok) {
      const data = await res.json();
      versionLink.textContent = data.commit_short || '12c68a';
    }
  } catch (e) {
    // Silencioso em caso de falha de rede
  }
}

// Inicializações ao carregar o script
verificarStatusChave();
carregarVersao();
