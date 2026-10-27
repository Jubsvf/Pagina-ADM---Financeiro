=============================================================
 LEITOR DE NOTA FISCAL - SISTEMA DE EXTRACAO COM IA
 Atividade Pratica Academica - Gestao Financeira & IA
=============================================================

REPOSITORIOS GITHUB
-------------------
URL Principal: https://github.com/Jubsvf/Pagina-ADM---Financeiro
URL Original:  https://github.com/Jubsvf/Leitor-de-PDF

AUTORES / DESENVOLVEDORES
-------------------------
- Julia Favieira (GitHub: @Jubsvf)
- Felipe Martins (GitHub: @felipemartinsgithub)

CODIGO DE VERSIONAMENTO (COMMIT ATUAL)
---------------------------------------
Commit Hash: 807bd2e3c7b0f4c81aefea1bc09c808b1c8a6972
Commit Curto: 807bd2e
Data/Hora: Tue Oct 27 2026 -0300
Link Direto: https://github.com/Jubsvf/Pagina-ADM---Financeiro/commit/807bd2e3c7b0f4c81aefea1bc09c808b1c8a6972

HISTORICO DE VERSOES (COMMITS)
-------------------------------
807bd2e - Tue Oct 27 2026 - correcao dos erros de extracao
04578d8 - Mon Oct 27 2026 - fix: compatibilizar criacao e fallback do sqlite para /tmp na Vercel
17d0d76 - Mon Oct 27 2026 - feat: organizar templates, estaticos, testes e documentacao de versao
7859711 - Mon Oct 26 2026 - fix: configurar deploy para Vercel e remover arquivos do Render
a384c88 - Mon Oct 26 2026 - docs: atualizar README com detalhes do projeto e criadores

DADOS DE LOGIN / SENHA
-----------------------
URL de Acesso: /login
Usuario: admin
Senha:   fintrack2025

CHAVE DE API GEMINI (DIVIDIDA EM DUAS PARTES)
----------------------------------------------
IMPORTANTE: Concatene as duas partes abaixo para obter a chave completa.
NAO compartilhe esta chave publicamente.

  Parte 1: AQ.Ab8RN6I-OCiMN
  Parte 2: vUr5T8R1AKK_nBStkAqYO9YEc7WAXhJix9Few

Como usar a chave:
  1. Em tempo real: na pagina de extracao, campo "Chave da API Gemini"
     (enviada apenas na requisicao, nao armazenada em codigo)
  2. Via arquivo .env: definir GEMINI_API_KEY=chave_completa_aqui
     (arquivo excluido do repositorio pelo .gitignore)
  3. Via variavel de ambiente no Render: no painel > Environment > GEMINI_API_KEY
Obtencao de nova chave: https://aistudio.google.com/

COMO EXECUTAR LOCALMENTE
-------------------------
1. Clonar o repositorio:
   git clone https://github.com/Jubsvf/Pagina-ADM---Financeiro.git

2. Instalar dependencias:
   pip install -r requirements.txt

3. Configurar o .env (copiar de .env.example):
   GEMINI_API_KEY=chave_completa_aqui

4. Iniciar o servidor:
   python app.py

5. Acessar no navegador:
   http://127.0.0.1:5000/login

DEPLOY / HOSPEDAGEM
--------------------
- Configurado para Render via render.yaml e gunicorn.
- Comando de inicializacao: gunicorn --chdir . server:app
- Banco de dados: PostgreSQL persistente configurado no Render.
- Variaveis de ambiente necessarias no Render:
    DATABASE_URL  -> URL do PostgreSQL do Render
    GEMINI_API_KEY -> Chave da API (ver secao acima)
    SECRET_KEY    -> Chave secreta para sessoes Flask

TECNOLOGIAS UTILIZADAS
-----------------------
- Python 3.11 / Flask
- SQLAlchemy + SQLite (local) / PostgreSQL (Render)
- Google Gemini API (google-genai) & pypdf
- HTML, CSS, JavaScript Vanilla
- Flasgger (Swagger UI na rota /apidocs)
- Gunicorn (servidor WSGI para producao)

=============================================================

