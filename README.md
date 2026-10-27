# AgroFinanceiro N2 - Sistema de Gestão Financeira & Leitor de Nota Fiscal com IA

Sistema web completo para gestão financeira e processamento inteligente de documentos fiscais em PDF, integrando Inteligência Artificial (Google Gemini) para leitura automática, classificação de despesas e rotinas financeiras completas (Contas a Pagar e a Receber).

---

## 📌 Sobre o Projeto

O **AgroFinanceiro** une a administração financeira operacional ao poder da IA generativa. Além de permitir a extração e estruturação automática de dados de faturas/notas fiscais a partir de arquivos PDF, o sistema oferece um painel administrativo completo para controle de fornecedores, clientes, faturados, categorias orçamentárias e lançamentos parcelados.

---

## 👥 Criadores e Autores

- **Júlia Favieira** ([@Jubsvf](https://github.com/Jubsvf))
- **Felipe Martins** ([@felipemartinsgithub](https://github.com/felipemartinsgithub))

---

## 🚀 Principais Módulos e Funcionalidades

### 1. 🤖 Leitor de Nota Fiscal & Extração com IA
- Upload intuitivo com visualização de metadados do PDF (tamanho, formato e validações).
- Integração com **Google Gemini API** (`google-genai`) para reconhecimento de campos cruciais (Número da NF, CNPJ do Fornecedor, Data de Emissão, Valor Total, Itens/Produtos e Vencimentos).
- **Mecanismo de Fallback**: Parsing local estruturado com `pypdf` para contingência.
- **Classificação Automática de Despesas**: A IA deduz inteligentemente o centro/tipo de despesa de acordo com a descrição dos itens faturados.
- Integração em um clique para persistir diretamente em **Contas a Pagar**.

### 2. 👥 Cadastros Gerais (CRUDs Administrativos)
- **Manter Fornecedor**: Cadastro com Razão Social, Nome Fantasia, CNPJ e controle de status (Ativo/Inativo com exclusão lógica).
- **Manter Cliente**: Cadastro corporativo ou pessoa física com CPF/CNPJ e gerenciamento de status.
- **Manter Faturado**: Cadastro de Pessoa Física / Destinatário final com CPF e controle de atividade.
- **Classificação Orçamentária**:
  - **Tipos de Despesa**: Categorias macro (Insumos Agrícolas, Manutenção e Operação, Recursos Humanos, Serviços Operacionais, Infraestrutura, Administrativas, etc.) e subcategorias.
  - **Tipos de Receita**: Categorias de receitas operacionais e agrícolas com vinculação direta.

### 3. 💳 Gestão Financeira
- **Contas a Pagar**:
  - Vínculo com Fornecedor, Faturado, Documento/NF, Data de Emissão, Valor Total e Detalhamento de Itens.
  - Rateio e classificação de despesas por percentual/valor.
  - Parcelamento com identificador único de parcela, datas de vencimento customizadas e status (Pendente/Pago/Cancelado).
  - Validação estrita da integridade financeira (soma das parcelas vs valor total).
- **Contas a Receber**:
  - Vínculo com Cliente, Faturado, Documento, Emissão e Valor Total.
  - Rateio de receitas operacionais.
  - Gestão de parcelas a receber com vencimentos e status.

### 4. 📖 Documentação da API
- Documentação interativa **Swagger / OpenAPI** disponível via **Flasgger** na rota `/apidocs`.

---

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python 3.11+, Flask, Flask-CORS, Flasgger
- **Banco de Dados**: SQLAlchemy ORM (PostgreSQL em produção via Render, SQLite em desenvolvimento local)
- **Driver de Conexão**: `psycopg` (v3) e `psycopg2-binary`
- **Inteligência Artificial**: Google Gemini API (`google-genai`) & `pypdf`
- **Frontend**: HTML5 Semântico, CSS3 Moderno (Glassmorphism, responsividade), JavaScript Vanilla
- **Deploy**: Configurado para **Render** (`render.yaml`) com PostgreSQL persistente

---

## ⚙️ Como Executar Localmente

### 1. Clonar o repositório
```bash
git clone https://github.com/Jubsvf/Pagina-ADM---Financeiro.git
cd Pagina-ADM---Financeiro
```

### 2. Criar e ativar o ambiente virtual (opcional, recomendado)
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente
Crie um arquivo `.env` na raiz do projeto (baseando-se no `.env.example`):
```env
GEMINI_API_KEY=sua_chave_do_google_gemini_aqui
DATABASE_URL=sqlite:///fintrack.db
SECRET_KEY=sua_chave_secreta
```

### 5. Iniciar o servidor
```bash
python app.py
```

O sistema inicializará as tabelas e o seed padrão automaticamente, ficando disponível em:
👉 **http://127.0.0.1:5000**

---

## 🔑 Credenciais Padrão de Acesso

- **URL de Login**: [http://127.0.0.1:5000/login](http://127.0.0.1:5000/login)
- **Usuário**: `admin`
- **Senha**: `fintrack2025`

---

## ☁️ Deploy no Render

O projeto está configurado para deploy no **Render** com banco de dados PostgreSQL persistente:

1. Crie um serviço **Web Service** no [Render.com](https://render.com) apontando para este repositório.
2. O comando de inicialização é: `gunicorn --chdir . server:app`
3. Configure as variáveis de ambiente no painel do Render:
   - `DATABASE_URL` — URL de conexão do PostgreSQL (gerado automaticamente pelo Render PostgreSQL)
   - `GEMINI_API_KEY` — Chave da API do Google Gemini
   - `SECRET_KEY` — Chave secreta para sessões Flask

---

## 📁 Rotas Principais

| Rota | Descrição |
| :--- | :--- |
| `/login` | Tela de autenticação |
| `/` ou `/dashboard` | Painel inicial e métricas |
| `/extracao` | Leitor de Nota Fiscal com IA |
| `/fornecedores` | Cadastro e gestão de Fornecedores |
| `/clientes` | Cadastro e gestão de Clientes |
| `/faturados` | Cadastro e gestão de Faturados |
| `/tipos-despesa` | Categorias e subcategorias de despesa |
| `/tipos-receita` | Categorias de receitas |
| `/contas-pagar` | Movimentação e parcelamento de Contas a Pagar |
| `/contas-receber` | Movimentação e parcelamento de Contas a Receber |
| `/apidocs` | Documentação interativa Swagger/OpenAPI |
