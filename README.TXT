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
Commit Hash: 536663c84bc4ad3613cd9a54abfff81235219688
Commit Curto: 536663c
Data/Hora: Mon Oct 26 23:40:52 2026 -0300
Link Direto: https://github.com/Jubsvf/Pagina-ADM---Financeiro/commit/536663c84bc4ad3613cd9a54abfff81235219688

HISTORICO DE VERSOES (COMMITS)
-------------------------------
7859711 - Mon Oct 26 23:32:54 2026 - fix: configurar deploy para Vercel e remover arquivos do Render
a384c88 - Mon Oct 26 23:26:39 2026 - docs: atualizar README com detalhes do projeto e criadores
4408dde - Mon Sep 28 21:45:47 2026 - fix: correcao na extracao dos dados das notas fiscais em PDF
e2193af - Sun Sep 27 17:33:57 2026 - docs: atualizar hash de versionamento no README.TXT
5e08c2f - Sun Sep 27 17:32:56 2026 - fix: ajustar chamadas de API relativas para producao

DADOS DE LOGIN / SENHA
-----------------------
URL de Acesso: /login
Usuario: admin
Senha:   fintrack2025

GESTAO DA CHAVE DE API (Gemini)
---------------------------------
A chave pode ser fornecida de duas formas:
  1. Em tempo real: na pagina de extracao, campo "Chave da API Gemini"
     (enviada apenas na requisicao, nao armazenada em codigo)
  2. Via arquivo .env: definir GEMINI_API_KEY=sua_chave_aqui
     (arquivo excluido do repositorio pelo .gitignore)
Obtencao da chave: https://aistudio.google.com/

COMO EXECUTAR LOCALMENTE
-------------------------
1. Clonar o repositorio:
   git clone https://github.com/Jubsvf/Pagina-ADM---Financeiro.git

2. Instalar dependencias:
   pip install -r requirements.txt

3. Configurar o .env (copiar de .env.example):
   GEMINI_API_KEY=sua_chave_aqui

4. Iniciar o servidor:
   python app.py

5. Acessar no navegador:
   http://127.0.0.1:5000/login

DEPLOY / HOSPEDAGEM
--------------------
- Configurado para Vercel Serverless via vercel.json e app.py.

TECNOLOGIAS UTILIZADAS
-----------------------
- Python 3 / Flask
- SQLAlchemy + SQLite / PostgreSQL
- Google Gemini API (google-genai) & pypdf
- HTML, CSS, JavaScript Vanilla
- Flasgger (Swagger UI na rota /apidocs)

=============================================================
