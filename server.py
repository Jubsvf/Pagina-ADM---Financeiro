import os
import datetime
from decimal import Decimal
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for
from flask_cors import CORS
from flasgger import Swagger
from dotenv import load_dotenv

from database import SessionLocal, engine, Base
from models import (
    Fornecedor,
    Cliente,
    Faturado,
    TipoReceita,
    TipoDespesa,
    ContaPagar,
    ParcelaPagar,
    ClassificacaoContaPagar,
    ContaReceber,
    ParcelaReceber,
    ClassificacaoContaReceber,
)
from agente import Agente
from seed import init_database

import re
import uuid
import unicodedata

load_dotenv()

# Inicializar tabelas e migrações no banco
init_database()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("SECRET_KEY", "fintrack-secret-2025")
CORS(app, supports_credentials=True)

# Credenciais de acesso (demonstração acadêmica)
APP_USERS = {
    "admin": "fintrack2025"
}


def login_required(f):
    """Decorator que exige login para acessar rotas de página."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

# Configuração do Swagger
app.config["SWAGGER"] = {
    "title": "API de Gestão Financeira e Extração de PDF",
    "uiversion": 3,
    "description": "Documentação OpenAPI/Swagger para o sistema de gestão financeira e extração de notas fiscais com IA (Gemini).",
    "version": "2.0.0",
}
swagger = Swagger(app)


# Utilitários para normalização, datas e decimais
def parse_date(date_str):
    if not date_str:
        return datetime.date.today()
    if isinstance(date_str, datetime.date):
        return date_str
    # Tenta DD/MM/AAAA ou AAAA-MM-DD
    if "/" in date_str:
        parts = date_str.split("/")
        if len(parts) == 3:
            d, m, y = parts
            return datetime.date(int(y), int(m), int(d))
    return datetime.datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()


def parse_decimal(val):
    if val is None or val == "":
        return Decimal("0.00")
    if isinstance(val, (int, float, Decimal)):
        return Decimal(str(val))
    # Tratar formato brasileiro 1.234,56
    clean_val = str(val).replace("R$", "").strip()
    if "," in clean_val and "." in clean_val:
        clean_val = clean_val.replace(".", "").replace(",", ".")
    elif "," in clean_val:
        clean_val = clean_val.replace(",", ".")
    try:
        return Decimal(clean_val)
    except Exception:
        return Decimal("0.00")


def normalizar_doc(doc):
    """Remove caracteres não numéricos para comparação confiável de CPF/CNPJ."""
    if not doc:
        return ""
    return re.sub(r"\D", "", str(doc))


def normalizar_texto(txt):
    """Remove acentuações e padroniza espaços em maiúsculo."""
    if not txt:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(txt))
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return " ".join(sem_acento.upper().split())


def consultar_fornecedor_db(db, nome_emitente, cnpj_emitente):
    """Consulta Fornecedor no banco usando CNPJ e/ou Razão Social normalizados."""
    cnpj_limpo = normalizar_doc(cnpj_emitente)
    nome_norm = normalizar_texto(nome_emitente)
    forn = None
    if cnpj_limpo:
        for f in db.query(Fornecedor).all():
            if normalizar_doc(f.cnpj) == cnpj_limpo:
                forn = f
                break
    if not forn and nome_norm:
        for f in db.query(Fornecedor).all():
            if normalizar_texto(f.razao_social) == nome_norm or (f.nome_fantasia and normalizar_texto(f.nome_fantasia) == nome_norm):
                forn = f
                break
    if forn:
        return {
            "tipo": "FORNECEDOR",
            "nome": forn.razao_social,
            "documento": forn.cnpj,
            "existe": True,
            "id": forn.id,
            "situacao": f"EXISTE — ID: {forn.id}",
            "ativo": forn.ativo
        }
    return {
        "tipo": "FORNECEDOR",
        "nome": nome_emitente or "Não identificado",
        "documento": cnpj_emitente or "Não identificado",
        "existe": False,
        "id": None,
        "situacao": "NÃO EXISTE",
        "ativo": None
    }


def consultar_faturado_db(db, nome_destinatario, cpf_destinatario):
    """Consulta Faturado no banco usando CPF/CNPJ e/ou Nome normalizados."""
    doc_limpo = normalizar_doc(cpf_destinatario)
    nome_norm = normalizar_texto(nome_destinatario)
    fat = None
    if doc_limpo:
        for f in db.query(Faturado).all():
            if normalizar_doc(f.cpf) == doc_limpo:
                fat = f
                break
    if not fat and nome_norm:
        for f in db.query(Faturado).all():
            if normalizar_texto(f.nome_completo) == nome_norm:
                fat = f
                break
    if fat:
        return {
            "tipo": "FATURADO",
            "nome": fat.nome_completo,
            "documento": fat.cpf,
            "existe": True,
            "id": fat.id,
            "situacao": f"EXISTE — ID: {fat.id}",
            "ativo": fat.ativo
        }
    return {
        "tipo": "FATURADO",
        "nome": nome_destinatario or "Não identificado",
        "documento": cpf_destinatario or "Não identificado",
        "existe": False,
        "id": None,
        "situacao": "NÃO EXISTE",
        "ativo": None
    }


def consultar_despesa_db(db, categoria_ou_desc):
    """Consulta Classificação de Despesa no banco (apenas do tipo DESPESA)."""
    cat_norm = normalizar_texto(categoria_ou_desc)
    td = None
    if cat_norm:
        for item in db.query(TipoDespesa).filter(TipoDespesa.tipo == "DESPESA").all():
            if normalizar_texto(item.categoria) == cat_norm or normalizar_texto(item.descricao) == cat_norm:
                td = item
                break
    if td:
        return {
            "tipo": "DESPESA",
            "descricao": td.categoria,
            "existe": True,
            "id": td.id,
            "situacao": f"EXISTE — ID: {td.id}",
            "ativo": td.ativo
        }
    return {
        "tipo": "DESPESA",
        "descricao": categoria_ou_desc or "MANUTENÇÃO E OPERAÇÃO",
        "existe": False,
        "id": None,
        "situacao": "NÃO EXISTE",
        "ativo": None
    }


# ============================================================================
# ROTAS DE PÁGINAS WEB (VIEWS)
# ============================================================================

@app.route("/login")
def login_page():
    """Página de Login."""
    if session.get("logged_in"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    """Realiza o login do usuário."""
    dados = request.get_json() or {}
    username = (dados.get("username") or "").strip()
    password = dados.get("password") or ""
    if APP_USERS.get(username) == password:
        session["logged_in"] = True
        session["username"] = username
        return jsonify({"ok": True, "mensagem": "Login realizado com sucesso."})
    return jsonify({"ok": False, "erro": "Usuário ou senha inválidos."}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """Encerra a sessão do usuário."""
    session.clear()
    return jsonify({"ok": True, "mensagem": "Logout realizado com sucesso."})


@app.route("/")
@app.route("/index.html")
@app.route("/dashboard")
@app.route("/dashboard.html")
@login_required
def index():
    """Dashboard de Gestão de Lançamentos & Contas (Tela Inicial)."""
    return render_template("index.html")


@app.route("/extracao")
@app.route("/extracao.html")
@login_required
def view_extracao():
    """Página de Upload e Extração de PDF com IA Gemini."""
    return render_template("extracao.html")


@app.route("/style.css")
def serve_css():
    """Compatibilidade para style.css."""
    return send_from_directory("static/css", "style.css")


@app.route("/app.js")
def serve_js():
    """Compatibilidade para app.js."""
    return send_from_directory("static/js", "app.js")


@app.route("/toast.js")
def serve_toast_js():
    """Compatibilidade para toast.js."""
    return send_from_directory("static/js", "toast.js")


@app.route("/dashboard.js")
def serve_dashboard_js():
    """Compatibilidade para dashboard.js."""
    return send_from_directory("static/js", "dashboard.js")


@app.route("/fornecedores")
@app.route("/fornecedores.html")
@login_required
def view_fornecedores():
    return render_template("fornecedores.html")


@app.route("/clientes")
@app.route("/clientes.html")
@login_required
def view_clientes():
    return render_template("clientes.html")


@app.route("/faturados")
@app.route("/faturados.html")
@login_required
def view_faturados():
    return render_template("faturados.html")


@app.route("/tipos-receita")
@app.route("/tipos-receita.html")
@login_required
def view_tipos_receita():
    return render_template("tipos-receita.html")


@app.route("/tipos-despesa")
@app.route("/tipos-despesa.html")
@login_required
def view_tipos_despesa():
    return render_template("tipos-despesa.html")


@app.route("/contas-pagar")
@app.route("/contas-pagar.html")
@login_required
def view_contas_pagar():
    return render_template("contas-pagar.html")


@app.route("/contas-receber")
@app.route("/contas-receber.html")
@login_required
def view_contas_receber():
    return render_template("contas-receber.html")




# ============================================================================
# INFORMAÇÕES DE VERSÃO E CONFIGURAÇÃO EM TEMPO REAL
# ============================================================================

# Hash do commit atual (carregado uma única vez na inicialização)
def _get_git_hash():
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))
        )
        return result.stdout.strip() if result.returncode == 0 else "N/A"
    except Exception:
        return "N/A"

GIT_COMMIT_HASH = _get_git_hash()
GIT_REPO_URL = "https://github.com/Jubsvf/Leitor-de-PDF"

# Chave em memória (pode ser sobrescrita em tempo real via /api/configurar-chave)
_runtime_api_key = None


@app.route("/api/lancamentos", methods=["GET"])
def api_listar_lancamentos():
    """
    Retorna KPIs consolidados e lista unificada de lançamentos (Contas a Pagar e a Receber).
    Suporta filtros: 'q' (busca textual), 'tipo' (todos, pagar, receber) e 'status' (ativos, inativos, todos).
    ---
    tags:
      - Movimento Financeiro
    parameters:
      - name: q
        in: query
        type: string
        description: Termo de busca textual
      - name: tipo
        in: query
        type: string
        enum: [todos, pagar, receber]
      - name: status
        in: query
        type: string
        enum: [ativos, inativos, todos]
    responses:
      200:
        description: Métricas e lançamentos unificados
    """
    termo = (request.args.get("q") or "").strip().lower()
    filtro_tipo = (request.args.get("tipo") or "todos").lower()
    filtro_status = (request.args.get("status") or "todos").lower()

    db = SessionLocal()
    try:
        contas_pagar = db.query(ContaPagar).all()
        contas_receber = db.query(ContaReceber).all()

        total_lancamentos_ativos = sum(1 for c in contas_pagar if c.ativo) + sum(1 for c in contas_receber if c.ativo)
        total_despesas = sum(float(c.valor_total or 0) for c in contas_pagar if c.ativo)
        total_receitas = sum(float(c.valor_total or 0) for c in contas_receber if c.ativo)

        parcelas_pagar_abertas = [
            p for c in contas_pagar if c.ativo for p in c.parcelas if p.ativo and (p.status or "").upper() != "PAGO"
        ]
        parcelas_receber_abertas = [
            p for c in contas_receber if c.ativo for p in c.parcelas if p.ativo and (p.status or "").upper() != "PAGO"
        ]
        total_parcelas_aberto = len(parcelas_pagar_abertas) + len(parcelas_receber_abertas)
        saldo_pendente = sum(float(p.valor or 0) for p in parcelas_pagar_abertas) + sum(float(p.valor or 0) for p in parcelas_receber_abertas)

        itens = []

        if filtro_tipo in ("todos", "pagar", "despesa"):
            for c in contas_pagar:
                if filtro_status == "ativos" and not c.ativo:
                    continue
                if filtro_status == "inativos" and c.ativo:
                    continue

                forn_nome = c.fornecedor.razao_social if c.fornecedor else "N/A"
                forn_doc = c.fornecedor.cnpj if c.fornecedor else ""
                fat_nome = c.faturado.nome_completo if c.faturado else "N/A"
                fat_doc = c.faturado.cpf if c.faturado else ""

                if termo:
                    conteudo = f"{c.id} {c.numero_nf or ''} {forn_nome} {forn_doc} {fat_nome} {fat_doc} {c.descricao_produtos or ''}".lower()
                    if termo not in conteudo:
                        continue

                itens.append({
                    "id": c.id,
                    "numero_nf": c.numero_nf or "S/N",
                    "tipo": "DESPESA",
                    "origem": "pagar",
                    "pessoa": forn_nome,
                    "pessoa_doc": forn_doc,
                    "faturado": fat_nome,
                    "faturado_doc": fat_doc,
                    "data_emissao": c.data_emissao.isoformat() if c.data_emissao else "",
                    "valor_total": float(c.valor_total or 0),
                    "quantidade_parcelas": c.quantidade_parcelas or len(c.parcelas),
                    "ativo": c.ativo,
                    "url_modulo": "/contas-pagar"
                })

        if filtro_tipo in ("todos", "receber", "receita"):
            for c in contas_receber:
                if filtro_status == "ativos" and not c.ativo:
                    continue
                if filtro_status == "inativos" and c.ativo:
                    continue

                cli_nome = c.cliente.razao_social if c.cliente else "N/A"
                cli_doc = c.cliente.cpf_cnpj if c.cliente else ""
                fat_nome = c.faturado.nome_completo if c.faturado else "N/A"
                fat_doc = c.faturado.cpf if c.faturado else ""

                if termo:
                    conteudo = f"{c.id} {c.numero_nf or ''} {cli_nome} {cli_doc} {fat_nome} {fat_doc} {c.descricao_servicos or ''}".lower()
                    if termo not in conteudo:
                        continue

                itens.append({
                    "id": c.id,
                    "numero_nf": c.numero_nf or "S/N",
                    "tipo": "RECEITA",
                    "origem": "receber",
                    "pessoa": cli_nome,
                    "pessoa_doc": cli_doc,
                    "faturado": fat_nome,
                    "faturado_doc": fat_doc,
                    "data_emissao": c.data_emissao.isoformat() if c.data_emissao else "",
                    "valor_total": float(c.valor_total or 0),
                    "quantidade_parcelas": c.quantidade_parcelas or len(c.parcelas),
                    "ativo": c.ativo,
                    "url_modulo": "/contas-receber"
                })

        itens.sort(key=lambda x: (x["data_emissao"] or "", x["id"]), reverse=True)

        return jsonify({
            "kpis": {
                "total_lancamentos_ativos": total_lancamentos_ativos,
                "total_despesas": total_despesas,
                "total_receitas": total_receitas,
                "total_parcelas_aberto": total_parcelas_aberto,
                "saldo_pendente": saldo_pendente,
            },
            "total_filtrado": len(itens),
            "itens": itens,
        })
    finally:
        db.close()


@app.route("/api/version", methods=["GET"])
def api_version():
    """
    Retorna informações de versão do sistema (hash do commit GitHub).
    ---
    tags:
      - Sistema
    responses:
      200:
        description: Dados de versionamento
    """
    return jsonify({
        "commit": GIT_COMMIT_HASH,
        "commit_short": GIT_COMMIT_HASH[:7] if GIT_COMMIT_HASH != "N/A" else "N/A",
        "repositorio": GIT_REPO_URL,
        "link_commit": f"{GIT_REPO_URL}/commit/{GIT_COMMIT_HASH}" if GIT_COMMIT_HASH != "N/A" else GIT_REPO_URL,
    })


@app.route("/api/configurar-chave", methods=["POST"])
def configurar_chave():
    """
    Configura a chave da API Gemini em tempo real (sem reiniciar o servidor).
    ---
    tags:
      - Sistema
    parameters:
      - name: body
        in: body
        required: true
        schema:
          properties:
            api_key:
              type: string
              description: Chave da API do Google Gemini
    responses:
      200:
        description: Chave configurada com sucesso
      400:
        description: Chave não informada
    """
    global _runtime_api_key
    dados = request.get_json() or {}
    chave = (dados.get("api_key") or "").strip()
    if not chave:
        return jsonify({"erro": "Campo 'api_key' não informado ou vazio."}), 400
    _runtime_api_key = chave
    os.environ["GEMINI_API_KEY"] = chave
    try:
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "GEMINI_API_KEY=" in content:
                content = re.sub(r"GEMINI_API_KEY=.*", f"GEMINI_API_KEY={chave}", content)
            else:
                content += f"\nGEMINI_API_KEY={chave}\n"
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(f"GEMINI_API_KEY={chave}\n")
    except Exception as e:
        print(f"Aviso ao persistir chave no .env: {e}")
    return jsonify({"mensagem": "Chave da API Gemini configurada com sucesso.", "status": "ok"})


@app.route("/api/status-chave", methods=["GET"])
def status_chave():
    """
    Verifica se a chave da API Gemini está configurada.
    ---
    tags:
      - Sistema
    responses:
      200:
        description: Status da chave
    """
    chave = _runtime_api_key or os.getenv("GEMINI_API_KEY", "")
    configurada = bool(chave and chave.strip())
    return jsonify({
        "configurada": configurada,
        "origem": "runtime" if _runtime_api_key else ("env" if configurada else "nenhuma"),
        "preview": (chave[:8] + "...") if configurada else None,
    })


# ============================================================================
# PROCESSADOR DE PDF COM IA (GEMINI)
# ============================================================================


@app.route("/api/extrair-pdf", methods=["POST"])
def extrair_pdf():
    """
    Processa uma nota fiscal em PDF e retorna os dados extraídos em formato JSON.
    ---
    tags:
      - Processador de PDF
    consumes:
      - multipart/form-data
    parameters:
      - name: pdf
        in: formData
        type: file
        required: true
        description: Arquivo PDF da nota fiscal
      - name: api_key
        in: formData
        type: string
        required: false
        description: Chave da API Gemini (opcional; substitui a configurada no servidor)
    responses:
      200:
        description: JSON estruturado com os dados extraídos e a classificação
      400:
        description: Nenhum arquivo enviado ou formato inválido
    """
    if "pdf" not in request.files and "file" not in request.files:
        return jsonify({"erro": "Nenhum arquivo PDF foi enviado no campo 'pdf'."}), 400

    pdf_file = request.files.get("pdf") or request.files.get("file")
    if not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"erro": "O arquivo deve ser um documento PDF válido."}), 400

    # A chave pode vir do form, da memória runtime ou do .env
    chave_form = (request.form.get("api_key") or "").strip()
    chave_efetiva = chave_form or _runtime_api_key or os.getenv("GEMINI_API_KEY", "")

    agente = Agente(api_key=chave_efetiva if chave_efetiva else None)
    resultado = agente.extrair_dados(pdf_file)
    return jsonify(resultado)


@app.route("/api/analisar-dados-extracao", methods=["POST"])
def api_analisar_dados_extracao():
    """
    Segunda etapa: analisa os dados extraídos da NF e verifica correspondência com o banco.
    ---
    tags:
      - Processador de PDF
    consumes:
      - application/json
    responses:
      200:
        description: Resultados da consulta para Fornecedor, Faturado e Classificação de Despesa.
    """
    dados = request.get_json() or {}
    forn_dict = dados.get("fornecedor") if isinstance(dados.get("fornecedor"), dict) else {}
    fat_dict = dados.get("faturado") if isinstance(dados.get("faturado"), dict) else {}
    classif_raw = dados.get("classificacao") or dados.get("classificacao_despesa") or dados.get("CLASSIFICAÇÃO") or {}
    fin_dict = dados.get("dados_financeiros") if isinstance(dados.get("dados_financeiros"), dict) else {}

    nome_emitente = (forn_dict.get("razao_social") or forn_dict.get("nome") or dados.get("Nome do Emitente") or dados.get("razao_social") or "").strip()
    cnpj_emitente = (forn_dict.get("cnpj") or forn_dict.get("documento") or dados.get("CNPJ do Emitente") or dados.get("cnpj") or "").strip()
    nome_destinatario = (fat_dict.get("nome_completo") or fat_dict.get("nome") or dados.get("Nome do Destinatário") or dados.get("nome_destinatario") or "").strip()
    cnpj_destinatario = (fat_dict.get("cpf") or fat_dict.get("documento") or dados.get("CNPJ do Destinatário") or dados.get("cpf") or "").strip()

    categoria_nome = ""
    if isinstance(classif_raw, dict):
        categoria_nome = classif_raw.get("descricao") or classif_raw.get("categoria") or ""
    elif classif_raw:
        categoria_nome = str(classif_raw)
    if not categoria_nome:
        categoria_nome = "MANUTENÇÃO E OPERAÇÃO"

    db = SessionLocal()
    try:
        res_forn = consultar_fornecedor_db(db, nome_emitente, cnpj_emitente)
        res_fat = consultar_faturado_db(db, nome_destinatario, cnpj_destinatario)
        res_desp = consultar_despesa_db(db, categoria_nome)

        return jsonify({
            "ok": True,
            "fornecedor": res_forn,
            "faturado": res_fat,
            "classificacao": res_desp,
            "dados_extraidos": {
                "numero_nf": fin_dict.get("numero_nf") or dados.get("Número da Nota Fiscal") or dados.get("numero_nf") or "S/N",
                "data_emissao": fin_dict.get("data_emissao") or dados.get("Data de Emissão"),
                "data_vencimento": fin_dict.get("data_vencimento") or dados.get("Data de Vencimento"),
                "valor_total": float(parse_decimal(fin_dict.get("valor_total") or dados.get("Valor Total") or dados.get("valor_total") or 0)),
                "descricao_produtos": fin_dict.get("descricao") or dados.get("Descrição dos Produtos") or ""
            }
        })
    finally:
        db.close()


@app.route("/api/processar-lancamento-extracao", methods=["POST"])
def api_processar_lancamento_extracao():
    """
    Processamento após a análise: persiste o movimento financeiro e parcelas dentro de uma transação.
    Cria os cadastros necessários (Fornecedor, Faturado, Classificação) se ausentes ou reaproveita existentes.
    Evita duplicidade de lançamento e garante atomicidade com rollback em caso de falha.
    ---
    tags:
      - Processador de PDF
    consumes:
      - application/json
    responses:
      201:
        description: Lançamento registrado com sucesso
      400:
        description: Erro de validação ou integridade
      409:
        description: Movimento duplicado
    """
    dados = request.get_json() or {}
    db = SessionLocal()
    try:
        # Etapa 1 - Validar os dados extraídos
        forn_dict = dados.get("fornecedor") if isinstance(dados.get("fornecedor"), dict) else {}
        fat_dict = dados.get("faturado") if isinstance(dados.get("faturado"), dict) else {}
        classif_raw = dados.get("classificacao") or dados.get("classificacao_despesa") or dados.get("CLASSIFICAÇÃO") or {}
        fin_dict = dados.get("dados_financeiros") if isinstance(dados.get("dados_financeiros"), dict) else {}

        nome_emitente = (forn_dict.get("razao_social") or forn_dict.get("nome") or dados.get("Nome do Emitente") or dados.get("razao_social") or "").strip()
        cnpj_emitente = (forn_dict.get("cnpj") or forn_dict.get("documento") or dados.get("CNPJ do Emitente") or dados.get("cnpj") or "").strip()
        nome_destinatario = (fat_dict.get("nome_completo") or fat_dict.get("nome") or dados.get("Nome do Destinatário") or dados.get("nome_destinatario") or "").strip()
        cnpj_destinatario = (fat_dict.get("cpf") or fat_dict.get("documento") or dados.get("CNPJ do Destinatário") or dados.get("cpf") or "").strip()

        numero_nf = (fin_dict.get("numero_nf") or dados.get("Número da Nota Fiscal") or dados.get("numero_nf") or "").strip()
        descricao_produtos = (fin_dict.get("descricao") or fin_dict.get("descricao_produtos") or dados.get("Descrição dos Produtos") or "").strip()
        data_emissao_raw = fin_dict.get("data_emissao") or dados.get("Data de Emissão")
        data_venc_raw = fin_dict.get("data_vencimento") or dados.get("Data de Vencimento")
        valor_total = parse_decimal(fin_dict.get("valor_total") or dados.get("Valor Total") or dados.get("valor_total") or 0)
        parcelas_input = fin_dict.get("parcelas") or dados.get("parcelas") or []

        if not numero_nf:
            return jsonify({"erro": "Número da Nota Fiscal é obrigatório para registrar o movimento."}), 400
        if valor_total <= Decimal("0.00"):
            return jsonify({"erro": "Valor total deve ser maior que zero."}), 400

        data_emissao = parse_date(data_emissao_raw)
        data_vencimento = parse_date(data_venc_raw or data_emissao_raw)

        # Etapa 2 - Criar o fornecedor quando necessário ou reaproveitar existente
        res_forn = consultar_fornecedor_db(db, nome_emitente, cnpj_emitente)
        criado_forn = False
        if res_forn["existe"]:
            fornecedor = db.query(Fornecedor).filter(Fornecedor.id == res_forn["id"]).first()
            if not fornecedor.ativo:
                return jsonify({"erro": f"O fornecedor '{fornecedor.razao_social}' (ID: {fornecedor.id}) está inativo e não pode ser utilizado em novos lançamentos."}), 400
        else:
            razao = nome_emitente or "FORNECEDOR DA NF"
            cnpj_f = cnpj_emitente or f"00.{uuid.uuid4().hex[:3]}.{uuid.uuid4().hex[:3]}/0001-00"
            fornecedor = Fornecedor(
                razao_social=razao,
                nome_fantasia=razao,
                cnpj=cnpj_f,
                tipo="FORNECEDOR",
                ativo=True
            )
            db.add(fornecedor)
            db.flush()
            criado_forn = True

        # Prevenção de duplicidade: verificar se já existe a mesma NF para este fornecedor
        conta_existente = db.query(ContaPagar).filter(
            ContaPagar.fornecedor_id == fornecedor.id,
            ContaPagar.numero_nf == numero_nf
        ).first()
        if conta_existente:
            return jsonify({
                "erro": f"Movimento duplicado: a NF {numero_nf} já está registrada para este fornecedor (ID da Conta: {conta_existente.id})."
            }), 409

        # Etapa 3 - Criar o faturado quando necessário ou reaproveitar existente
        res_fat = consultar_faturado_db(db, nome_destinatario, cnpj_destinatario)
        criado_fat = False
        if res_fat["existe"]:
            faturado = db.query(Faturado).filter(Faturado.id == res_fat["id"]).first()
            if not faturado.ativo:
                return jsonify({"erro": f"O faturado '{faturado.nome_completo}' (ID: {faturado.id}) está inativo e não pode ser utilizado em novos lançamentos."}), 400
        else:
            nome_f = nome_destinatario or "DESTINATÁRIO NF"
            cpf_f = cnpj_destinatario or f"000.{uuid.uuid4().hex[:3]}.{uuid.uuid4().hex[:3]}-00"
            faturado = Faturado(
                nome_completo=nome_f,
                cpf=cpf_f,
                tipo="FATURADO",
                ativo=True
            )
            db.add(faturado)
            db.flush()
            criado_fat = True

        # Etapa 4 - Criar a classificação da despesa quando necessário ou reaproveitar existente
        categoria_nome = ""
        descricao_nome = ""
        if isinstance(classif_raw, dict):
            categoria_nome = classif_raw.get("categoria") or classif_raw.get("descricao") or ""
            descricao_nome = classif_raw.get("descricao") or classif_raw.get("categoria") or ""
        elif classif_raw:
            categoria_nome = str(classif_raw)
            descricao_nome = str(classif_raw)
        if not categoria_nome:
            categoria_nome = "MANUTENÇÃO E OPERAÇÃO"
            descricao_nome = "MANUTENÇÃO E OPERAÇÃO"

        res_desp = consultar_despesa_db(db, categoria_nome)
        criado_classif = False
        if res_desp["existe"]:
            tipo_despesa = db.query(TipoDespesa).filter(TipoDespesa.id == res_desp["id"]).first()
            if not tipo_despesa.ativo:
                return jsonify({"erro": f"A classificação de despesa '{tipo_despesa.categoria}' está inativa."}), 400
        else:
            cat_upper = categoria_nome.strip().upper()
            tipo_despesa = TipoDespesa(
                categoria=cat_upper,
                descricao=descricao_nome.strip() if descricao_nome else cat_upper,
                tipo="DESPESA",
                ativo=True
            )
            db.add(tipo_despesa)
            db.flush()
            criado_classif = True

        # Etapa 5 - Criar o movimento financeiro (Conta a Pagar com tipo APAGAR)
        conta = ContaPagar(
            fornecedor_id=fornecedor.id,
            faturado_id=faturado.id,
            numero_nf=numero_nf,
            data_emissao=data_emissao,
            descricao_produtos=descricao_produtos,
            valor_total=valor_total,
            quantidade_parcelas=len(parcelas_input) if parcelas_input else 1,
            tipo="APAGAR",
            ativo=True
        )
        db.add(conta)
        db.flush()

        # Etapa 6 - Criar as parcelas com identificacao única
        parcelas_adicionadas = []
        if parcelas_input:
            for idx, p_item in enumerate(parcelas_input, 1):
                p_venc = parse_date(p_item.get("data_vencimento") or data_vencimento)
                p_val = parse_decimal(p_item.get("valor", valor_total / len(parcelas_input)))
                p_ident = (p_item.get("identificacao") or "").strip()
                if not p_ident:
                    p_ident = f"PARC-NF-{numero_nf}-P{idx}-{uuid.uuid4().hex[:6].upper()}"

                parcela = ParcelaPagar(
                    conta_pagar_id=conta.id,
                    numero_parcela=p_item.get("numero_parcela", idx),
                    identificacao=p_ident,
                    data_vencimento=p_venc,
                    valor=p_val,
                    status="PENDENTE",
                    ativo=True
                )
                db.add(parcela)
                parcelas_adicionadas.append(parcela)
        else:
            ident_parcela = f"PARC-NF-{numero_nf}-P1-{uuid.uuid4().hex[:6].upper()}"
            parcela = ParcelaPagar(
                conta_pagar_id=conta.id,
                numero_parcela=1,
                identificacao=ident_parcela,
                data_vencimento=data_vencimento,
                valor=valor_total,
                status="PENDENTE",
                ativo=True
            )
            db.add(parcela)
            parcelas_adicionadas.append(parcela)

        # Vincular classificação da despesa
        classif_item = ClassificacaoContaPagar(
            conta_pagar_id=conta.id,
            tipo_despesa_id=tipo_despesa.id,
            percentual=Decimal("100.00"),
            valor=valor_total
        )
        db.add(classif_item)

        # Etapa 7 - Confirmar o lançamento atômico
        db.commit()
        db.refresh(conta)

        return jsonify({
            "ok": True,
            "mensagem": "Lançamento realizado com sucesso!",
            "movimento_id": conta.id,
            "fornecedor_nome": fornecedor.razao_social,
            "faturado_nome": faturado.nome_completo,
            "classificacao_nome": tipo_despesa.descricao or tipo_despesa.categoria,
            "parcelas_total": len(parcelas_adicionadas),
            "resumo": {
                "fornecedor": {
                    "id": fornecedor.id,
                    "razao_social": fornecedor.razao_social,
                    "cnpj": fornecedor.cnpj,
                    "criado": criado_forn
                },
                "faturado": {
                    "id": faturado.id,
                    "nome": faturado.nome_completo,
                    "cpf": faturado.cpf,
                    "criado": criado_fat
                },
                "classificacao": {
                    "id": tipo_despesa.id,
                    "categoria": tipo_despesa.categoria,
                    "criado": criado_classif
                },
                "movimento": {
                    "id": conta.id,
                    "tipo": conta.tipo,
                    "numero_nf": conta.numero_nf,
                    "valor_total": float(conta.valor_total),
                    "data_emissao": conta.data_emissao.isoformat()
                },
                "quantidade_parcelas": len(parcelas_adicionadas),
                "parcelas": [
                    {
                        "id": p.id,
                        "identificacao": p.identificacao,
                        "numero_parcela": p.numero_parcela,
                        "data_vencimento": p.data_vencimento.isoformat(),
                        "valor": float(p.valor)
                    }
                    for p in parcelas_adicionadas
                ]
            }
        }), 201
    except Exception as e:
        db.rollback()
        return jsonify({"erro": f"Falha ao processar lançamento: {str(e)}"}), 400
    finally:
        db.close()


@app.route("/api/salvar-conta-pagar-pdf", methods=["POST"])
def salvar_conta_pagar_pdf():
    """
    Salva uma Conta a Pagar diretamente a partir do JSON extraído da nota fiscal.
    Encaminha para api_processar_lancamento_extracao mantendo compatibilidade.
    """
    return api_processar_lancamento_extracao()



# ============================================================================
# CRUD: MANTER FORNECEDOR
# ============================================================================

def get_ativo_param(req):
    apenas_ativos = req.args.get("apenas_ativos")
    if apenas_ativos is not None:
        return "true" if apenas_ativos.lower() in ("true", "1") else "all"
    ativo_val = req.args.get("ativo")
    if ativo_val:
        return ativo_val.lower()
    return "all"


@app.route("/api/fornecedores", methods=["GET"])
def listar_fornecedores():
    """
    Lista todos os fornecedores cadastrados.
    ---
    tags:
      - Fornecedores
    parameters:
      - name: ativo
        in: query
        type: string
        description: Filtrar por ativo (true, false ou all)
    responses:
      200:
        description: Lista de fornecedores
    """
    ativo_param = get_ativo_param(request)
    db = SessionLocal()
    try:
        query = db.query(Fornecedor)
        if ativo_param == "true":
            query = query.filter(Fornecedor.ativo == True)
        elif ativo_param == "false":
            query = query.filter(Fornecedor.ativo == False)
        fornecedores = query.order_by(Fornecedor.razao_social).all()
        return jsonify([f.to_dict() for f in fornecedores])
    finally:
        db.close()


@app.route("/api/fornecedores", methods=["POST"])
def criar_fornecedor():
    """
    Cadastra um novo fornecedor.
    ---
    tags:
      - Fornecedores
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - razao_social
            - cnpj
          properties:
            razao_social:
              type: string
            nome_fantasia:
              type: string
            cnpj:
              type: string
    responses:
      201:
        description: Fornecedor criado
    """
    dados = request.get_json() or {}
    razao = dados.get("razao_social", "").strip()
    cnpj = dados.get("cnpj", "").strip()
    fantasia = dados.get("nome_fantasia", "").strip()

    if not razao or not cnpj:
        return jsonify({"erro": "Razão Social e CNPJ são obrigatórios."}), 400

    db = SessionLocal()
    try:
        existente = db.query(Fornecedor).filter(Fornecedor.cnpj == cnpj).first()
        if existente:
            return jsonify({"erro": f"Já existe um fornecedor cadastrado com o CNPJ {cnpj}."}), 409

        forn = Fornecedor(razao_social=razao, nome_fantasia=fantasia, cnpj=cnpj, ativo=True)
        db.add(forn)
        db.commit()
        db.refresh(forn)
        return jsonify(forn.to_dict()), 201
    finally:
        db.close()


@app.route("/api/fornecedores/<int:id>", methods=["GET"])
def obter_fornecedor(id):
    """Obtém detalhes de um fornecedor pelo ID."""
    db = SessionLocal()
    try:
        forn = db.query(Fornecedor).filter(Fornecedor.id == id).first()
        if not forn:
            return jsonify({"erro": "Fornecedor não encontrado."}), 404
        return jsonify(forn.to_dict())
    finally:
        db.close()


@app.route("/api/fornecedores/<int:id>", methods=["PUT"])
def atualizar_fornecedor(id):
    """Atualiza dados de um fornecedor."""
    dados = request.get_json() or {}
    db = SessionLocal()
    try:
        forn = db.query(Fornecedor).filter(Fornecedor.id == id).first()
        if not forn:
            return jsonify({"erro": "Fornecedor não encontrado."}), 404

        if "razao_social" in dados and dados["razao_social"].strip():
            forn.razao_social = dados["razao_social"].strip()
        if "nome_fantasia" in dados:
            forn.nome_fantasia = dados["nome_fantasia"].strip()
        if "cnpj" in dados and dados["cnpj"].strip():
            # Verificar duplicidade
            outro = db.query(Fornecedor).filter(Fornecedor.cnpj == dados["cnpj"].strip(), Fornecedor.id != id).first()
            if outro:
                return jsonify({"erro": "CNPJ já utilizado por outro fornecedor."}), 409
            forn.cnpj = dados["cnpj"].strip()

        db.commit()
        db.refresh(forn)
        return jsonify(forn.to_dict())
    finally:
        db.close()


@app.route("/api/fornecedores/<int:id>/inativar", methods=["POST"])
@app.route("/api/fornecedores/<int:id>", methods=["DELETE"])
def inativar_fornecedor(id):
    """
    Regra de negócio: Cadastros NÃO podem ser excluídos, apenas INATIVADOS.
    """
    db = SessionLocal()
    try:
        forn = db.query(Fornecedor).filter(Fornecedor.id == id).first()
        if not forn:
            return jsonify({"erro": "Fornecedor não encontrado."}), 404

        forn.ativo = False
        db.commit()
        return jsonify({"mensagem": "Fornecedor inativado com sucesso (exclusão física não permitida por regra de negócio).", "fornecedor": forn.to_dict()})
    finally:
        db.close()


@app.route("/api/fornecedores/<int:id>/reativar", methods=["POST"])
def reativar_fornecedor(id):
    """Regra de negócio: Registros inativos devem poder ser REATIVADOS."""
    db = SessionLocal()
    try:
        forn = db.query(Fornecedor).filter(Fornecedor.id == id).first()
        if not forn:
            return jsonify({"erro": "Fornecedor não encontrado."}), 404

        forn.ativo = True
        db.commit()
        return jsonify({"mensagem": "Fornecedor reativado com sucesso!", "fornecedor": forn.to_dict()})
    finally:
        db.close()


# ============================================================================
# CRUD: MANTER CLIENTE
# ============================================================================

@app.route("/api/clientes", methods=["GET"])
def listar_clientes():
    """Lista todos os clientes."""
    ativo_param = request.args.get("ativo", "all").lower()
    db = SessionLocal()
    try:
        query = db.query(Cliente)
        if ativo_param == "true":
            query = query.filter(Cliente.ativo == True)
        elif ativo_param == "false":
            query = query.filter(Cliente.ativo == False)
        clientes = query.order_by(Cliente.razao_social).all()
        return jsonify([c.to_dict() for c in clientes])
    finally:
        db.close()


@app.route("/api/clientes", methods=["POST"])
def criar_cliente():
    """Cadastra um novo cliente."""
    dados = request.get_json() or {}
    razao = dados.get("razao_social", "").strip()
    cpf_cnpj = dados.get("cpf_cnpj", "").strip()
    fantasia = dados.get("nome_fantasia", "").strip()

    if not razao or not cpf_cnpj:
        return jsonify({"erro": "Razão Social / Nome e CPF/CNPJ são obrigatórios."}), 400

    db = SessionLocal()
    try:
        existente = db.query(Cliente).filter(Cliente.cpf_cnpj == cpf_cnpj).first()
        if existente:
            return jsonify({"erro": f"Já existe um cliente cadastrado com o CPF/CNPJ {cpf_cnpj}."}), 409

        cli = Cliente(razao_social=razao, nome_fantasia=fantasia, cpf_cnpj=cpf_cnpj, ativo=True)
        db.add(cli)
        db.commit()
        db.refresh(cli)
        return jsonify(cli.to_dict()), 201
    finally:
        db.close()


@app.route("/api/clientes/<int:id>", methods=["GET"])
def obter_cliente(id):
    db = SessionLocal()
    try:
        cli = db.query(Cliente).filter(Cliente.id == id).first()
        if not cli:
            return jsonify({"erro": "Cliente não encontrado."}), 404
        return jsonify(cli.to_dict())
    finally:
        db.close()


@app.route("/api/clientes/<int:id>", methods=["PUT"])
def atualizar_cliente(id):
    dados = request.get_json() or {}
    db = SessionLocal()
    try:
        cli = db.query(Cliente).filter(Cliente.id == id).first()
        if not cli:
            return jsonify({"erro": "Cliente não encontrado."}), 404

        if "razao_social" in dados and dados["razao_social"].strip():
            cli.razao_social = dados["razao_social"].strip()
        if "nome_fantasia" in dados:
            cli.nome_fantasia = dados["nome_fantasia"].strip()
        if "cpf_cnpj" in dados and dados["cpf_cnpj"].strip():
            outro = db.query(Cliente).filter(Cliente.cpf_cnpj == dados["cpf_cnpj"].strip(), Cliente.id != id).first()
            if outro:
                return jsonify({"erro": "CPF/CNPJ já utilizado por outro cliente."}), 409
            cli.cpf_cnpj = dados["cpf_cnpj"].strip()

        db.commit()
        db.refresh(cli)
        return jsonify(cli.to_dict())
    finally:
        db.close()


@app.route("/api/clientes/<int:id>/inativar", methods=["POST"])
@app.route("/api/clientes/<int:id>", methods=["DELETE"])
def inativar_cliente(id):
    db = SessionLocal()
    try:
        cli = db.query(Cliente).filter(Cliente.id == id).first()
        if not cli:
            return jsonify({"erro": "Cliente não encontrado."}), 404

        cli.ativo = False
        db.commit()
        return jsonify({"mensagem": "Cliente inativado com sucesso.", "cliente": cli.to_dict()})
    finally:
        db.close()


@app.route("/api/clientes/<int:id>/reativar", methods=["POST"])
def reativar_cliente(id):
    db = SessionLocal()
    try:
        cli = db.query(Cliente).filter(Cliente.id == id).first()
        if not cli:
            return jsonify({"erro": "Cliente não encontrado."}), 404

        cli.ativo = True
        db.commit()
        return jsonify({"mensagem": "Cliente reativado com sucesso.", "cliente": cli.to_dict()})
    finally:
        db.close()


# ============================================================================
# CRUD: MANTER FATURADO
# ============================================================================

@app.route("/api/faturados", methods=["GET"])
def listar_faturados():
    """Lista todos os faturados."""
    ativo_param = request.args.get("ativo", "all").lower()
    db = SessionLocal()
    try:
        query = db.query(Faturado)
        if ativo_param == "true":
            query = query.filter(Faturado.ativo == True)
        elif ativo_param == "false":
            query = query.filter(Faturado.ativo == False)
        faturados = query.order_by(Faturado.nome_completo).all()
        return jsonify([f.to_dict() for f in faturados])
    finally:
        db.close()


@app.route("/api/faturados", methods=["POST"])
def criar_faturado():
    """Cadastra um novo faturado."""
    dados = request.get_json() or {}
    nome = dados.get("nome_completo", "").strip()
    cpf = dados.get("cpf", "").strip()

    if not nome or not cpf:
        return jsonify({"erro": "Nome Completo e CPF são obrigatórios."}), 400

    db = SessionLocal()
    try:
        existente = db.query(Faturado).filter(Faturado.cpf == cpf).first()
        if existente:
            return jsonify({"erro": f"Já existe um faturado cadastrado com o CPF {cpf}."}), 409

        fat = Faturado(nome_completo=nome, cpf=cpf, ativo=True)
        db.add(fat)
        db.commit()
        db.refresh(fat)
        return jsonify(fat.to_dict()), 201
    finally:
        db.close()


@app.route("/api/faturados/<int:id>", methods=["GET"])
def obter_faturado(id):
    db = SessionLocal()
    try:
        fat = db.query(Faturado).filter(Faturado.id == id).first()
        if not fat:
            return jsonify({"erro": "Faturado não encontrado."}), 404
        return jsonify(fat.to_dict())
    finally:
        db.close()


@app.route("/api/faturados/<int:id>", methods=["PUT"])
def atualizar_faturado(id):
    dados = request.get_json() or {}
    db = SessionLocal()
    try:
        fat = db.query(Faturado).filter(Faturado.id == id).first()
        if not fat:
            return jsonify({"erro": "Faturado não encontrado."}), 404

        if "nome_completo" in dados and dados["nome_completo"].strip():
            fat.nome_completo = dados["nome_completo"].strip()
        if "cpf" in dados and dados["cpf"].strip():
            outro = db.query(Faturado).filter(Faturado.cpf == dados["cpf"].strip(), Faturado.id != id).first()
            if outro:
                return jsonify({"erro": "CPF já utilizado por outro faturado."}), 409
            fat.cpf = dados["cpf"].strip()

        db.commit()
        db.refresh(fat)
        return jsonify(fat.to_dict())
    finally:
        db.close()


@app.route("/api/faturados/<int:id>/inativar", methods=["POST"])
@app.route("/api/faturados/<int:id>", methods=["DELETE"])
def inativar_faturado(id):
    db = SessionLocal()
    try:
        fat = db.query(Faturado).filter(Faturado.id == id).first()
        if not fat:
            return jsonify({"erro": "Faturado não encontrado."}), 404

        fat.ativo = False
        db.commit()
        return jsonify({"mensagem": "Faturado inativado com sucesso.", "faturado": fat.to_dict()})
    finally:
        db.close()


@app.route("/api/faturados/<int:id>/reativar", methods=["POST"])
def reativar_faturado(id):
    db = SessionLocal()
    try:
        fat = db.query(Faturado).filter(Faturado.id == id).first()
        if not fat:
            return jsonify({"erro": "Faturado não encontrado."}), 404

        fat.ativo = True
        db.commit()
        return jsonify({"mensagem": "Faturado reativado com sucesso.", "faturado": fat.to_dict()})
    finally:
        db.close()


# ============================================================================
# CRUD: MANTER TIPO DE RECEITA
# ============================================================================

@app.route("/api/tipos-receita", methods=["GET"])
def listar_tipos_receita():
    ativo_param = request.args.get("ativo", "all").lower()
    db = SessionLocal()
    try:
        query = db.query(TipoReceita)
        if ativo_param == "true":
            query = query.filter(TipoReceita.ativo == True)
        elif ativo_param == "false":
            query = query.filter(TipoReceita.ativo == False)
        tipos = query.order_by(TipoReceita.descricao).all()
        return jsonify([t.to_dict() for t in tipos])
    finally:
        db.close()


@app.route("/api/tipos-receita", methods=["POST"])
def criar_tipo_receita():
    dados = request.get_json() or {}
    desc = dados.get("descricao", "").strip()
    if not desc:
        return jsonify({"erro": "Descrição do tipo de receita é obrigatória."}), 400

    db = SessionLocal()
    try:
        existente = db.query(TipoReceita).filter(TipoReceita.descricao.ilike(desc)).first()
        if existente:
            return jsonify({"erro": "Tipo de receita já cadastrado com esta descrição."}), 409

        tr = TipoReceita(descricao=desc, ativo=True)
        db.add(tr)
        db.commit()
        db.refresh(tr)
        return jsonify(tr.to_dict()), 201
    finally:
        db.close()


@app.route("/api/tipos-receita/<int:id>", methods=["PUT"])
def atualizar_tipo_receita(id):
    dados = request.get_json() or {}
    db = SessionLocal()
    try:
        tr = db.query(TipoReceita).filter(TipoReceita.id == id).first()
        if not tr:
            return jsonify({"erro": "Tipo de receita não encontrado."}), 404

        if "descricao" in dados and dados["descricao"].strip():
            tr.descricao = dados["descricao"].strip()

        db.commit()
        db.refresh(tr)
        return jsonify(tr.to_dict())
    finally:
        db.close()


@app.route("/api/tipos-receita/<int:id>/inativar", methods=["POST"])
@app.route("/api/tipos-receita/<int:id>", methods=["DELETE"])
def inativar_tipo_receita(id):
    db = SessionLocal()
    try:
        tr = db.query(TipoReceita).filter(TipoReceita.id == id).first()
        if not tr:
            return jsonify({"erro": "Tipo de receita não encontrado."}), 404

        tr.ativo = False
        db.commit()
        return jsonify({"mensagem": "Tipo de receita inativado com sucesso.", "tipo_receita": tr.to_dict()})
    finally:
        db.close()


@app.route("/api/tipos-receita/<int:id>/reativar", methods=["POST"])
def reativar_tipo_receita(id):
    db = SessionLocal()
    try:
        tr = db.query(TipoReceita).filter(TipoReceita.id == id).first()
        if not tr:
            return jsonify({"erro": "Tipo de receita não encontrado."}), 404

        tr.ativo = True
        db.commit()
        return jsonify({"mensagem": "Tipo de receita reativado com sucesso.", "tipo_receita": tr.to_dict()})
    finally:
        db.close()


# ============================================================================
# CRUD: MANTER TIPO DE DESPESA
# ============================================================================

@app.route("/api/tipos-despesa", methods=["GET"])
def listar_tipos_despesa():
    ativo_param = request.args.get("ativo", "all").lower()
    categoria_param = request.args.get("categoria", "").strip()
    db = SessionLocal()
    try:
        query = db.query(TipoDespesa)
        if ativo_param == "true":
            query = query.filter(TipoDespesa.ativo == True)
        elif ativo_param == "false":
            query = query.filter(TipoDespesa.ativo == False)
        if categoria_param:
            query = query.filter(TipoDespesa.categoria == categoria_param)
        tipos = query.order_by(TipoDespesa.categoria, TipoDespesa.descricao).all()
        return jsonify([t.to_dict() for t in tipos])
    finally:
        db.close()


@app.route("/api/tipos-despesa", methods=["POST"])
def criar_tipo_despesa():
    dados = request.get_json() or {}
    categoria = dados.get("categoria", "").strip()
    descricao = dados.get("descricao", "").strip()

    if not categoria or not descricao:
        return jsonify({"erro": "Categoria e Descrição são obrigatórias."}), 400

    db = SessionLocal()
    try:
        td = TipoDespesa(categoria=categoria, descricao=descricao, ativo=True)
        db.add(td)
        db.commit()
        db.refresh(td)
        return jsonify(td.to_dict()), 201
    finally:
        db.close()


@app.route("/api/tipos-despesa/<int:id>", methods=["PUT"])
def atualizar_tipo_despesa(id):
    dados = request.get_json() or {}
    db = SessionLocal()
    try:
        td = db.query(TipoDespesa).filter(TipoDespesa.id == id).first()
        if not td:
            return jsonify({"erro": "Tipo de despesa não encontrado."}), 404

        if "categoria" in dados and dados["categoria"].strip():
            td.categoria = dados["categoria"].strip()
        if "descricao" in dados and dados["descricao"].strip():
            td.descricao = dados["descricao"].strip()

        db.commit()
        db.refresh(td)
        return jsonify(td.to_dict())
    finally:
        db.close()


@app.route("/api/tipos-despesa/<int:id>/inativar", methods=["POST"])
@app.route("/api/tipos-despesa/<int:id>", methods=["DELETE"])
def inativar_tipo_despesa(id):
    db = SessionLocal()
    try:
        td = db.query(TipoDespesa).filter(TipoDespesa.id == id).first()
        if not td:
            return jsonify({"erro": "Tipo de despesa não encontrado."}), 404

        td.ativo = False
        db.commit()
        return jsonify({"mensagem": "Tipo de despesa inativado com sucesso.", "tipo_despesa": td.to_dict()})
    finally:
        db.close()


@app.route("/api/tipos-despesa/<int:id>/reativar", methods=["POST"])
def reativar_tipo_despesa(id):
    db = SessionLocal()
    try:
        td = db.query(TipoDespesa).filter(TipoDespesa.id == id).first()
        if not td:
            return jsonify({"erro": "Tipo de despesa não encontrado."}), 404

        td.ativo = True
        db.commit()
        return jsonify({"mensagem": "Tipo de despesa reativado com sucesso.", "tipo_despesa": td.to_dict()})
    finally:
        db.close()


# ============================================================================
# REGISTRAR CONTAS A PAGAR
# ============================================================================

@app.route("/api/contas-pagar", methods=["GET"])
def listar_contas_pagar():
    """Lista todas as contas a pagar."""
    ativo_param = request.args.get("ativo", "all").lower()
    db = SessionLocal()
    try:
        query = db.query(ContaPagar)
        if ativo_param == "true":
            query = query.filter(ContaPagar.ativo == True)
        elif ativo_param == "false":
            query = query.filter(ContaPagar.ativo == False)
        contas = query.order_by(ContaPagar.data_emissao.desc()).all()
        return jsonify([c.to_dict() for c in contas])
    finally:
        db.close()


@app.route("/api/contas-pagar", methods=["POST"])
def criar_conta_pagar():
    """
    Registra uma nova Conta a Pagar com parcelas e classificações de despesa.
    Suporta 1 ou múltiplas parcelas e 1 ou múltiplas classificações de despesa compatíveis.
    Valida unicidade de identificação da parcela, status ativo e soma de valores.
    """
    dados = request.get_json() or {}
    fornecedor_id = dados.get("fornecedor_id")
    faturado_id = dados.get("faturado_id")
    numero_nf = (dados.get("numero_nf") or "S/N").strip()
    data_emissao = parse_date(dados.get("data_emissao"))
    descricao = (dados.get("descricao") or dados.get("descricao_produtos") or "").strip()
    valor_total = parse_decimal(dados.get("valor_total", 0))

    if not fornecedor_id:
        return jsonify({"erro": "Fornecedor é obrigatório."}), 400

    if valor_total <= Decimal("0.00"):
        return jsonify({"erro": "O valor total do movimento deve ser maior que zero."}), 400

    db = SessionLocal()
    try:
        forn = db.query(Fornecedor).filter(Fornecedor.id == fornecedor_id).first()
        if not forn:
            return jsonify({"erro": "Fornecedor não encontrado."}), 400
        if not forn.ativo:
            return jsonify({"erro": "Fornecedor inativo não pode ser utilizado em novos lançamentos."}), 400

        fat = None
        if faturado_id:
            fat = db.query(Faturado).filter(Faturado.id == faturado_id).first()
            if not fat:
                return jsonify({"erro": "Faturado não encontrado."}), 400
            if not fat.ativo:
                return jsonify({"erro": "Faturado inativo não pode ser utilizado em novos lançamentos."}), 400
        else:
            fat = db.query(Faturado).filter(Faturado.ativo == True).first()
            if fat:
                faturado_id = fat.id
            else:
                return jsonify({"erro": "Nenhum faturado ativo cadastrado no sistema."}), 400

        parcelas_input = dados.get("parcelas") or []
        if not parcelas_input:
            venc = parse_date(dados.get("data_vencimento") or data_emissao)
            parcelas_input = [{"numero_parcela": 1, "data_vencimento": venc, "valor": valor_total}]

        # Validação financeira: a soma das parcelas deve coincidir com o valor total
        soma_parcelas = Decimal("0.00")
        for p_item in parcelas_input:
            p_val = parse_decimal(p_item.get("valor", 0))
            if p_val <= Decimal("0.00"):
                return jsonify({"erro": "O valor de cada parcela deve ser maior que zero."}), 400
            soma_parcelas += p_val

        if abs(soma_parcelas - valor_total) > Decimal("0.05"):
            return jsonify({
                "erro": f"A soma das parcelas (R$ {soma_parcelas:.2f}) não confere com o valor total do movimento (R$ {valor_total:.2f})."
            }), 400

        # Classificações de Despesa compatíveis
        raw_classif = dados.get("classificacoes") or []
        norm_classif = []
        if raw_classif:
            for c in raw_classif:
                if isinstance(c, (int, str)):
                    norm_classif.append({"tipo_despesa_id": int(c), "percentual": Decimal("100.00"), "valor": valor_total})
                elif isinstance(c, dict):
                    norm_classif.append({
                        "tipo_despesa_id": int(c.get("tipo_despesa_id") or c.get("id")),
                        "percentual": parse_decimal(c.get("percentual", 100.0)),
                        "valor": parse_decimal(c.get("valor", valor_total))
                    })
        else:
            td_id = dados.get("tipo_despesa_id")
            if td_id:
                norm_classif = [{"tipo_despesa_id": int(td_id), "percentual": Decimal("100.00"), "valor": valor_total}]
            else:
                primeiro_td = db.query(TipoDespesa).filter(TipoDespesa.ativo == True).first()
                if primeiro_td:
                    norm_classif = [{"tipo_despesa_id": primeiro_td.id, "percentual": Decimal("100.00"), "valor": valor_total}]
                else:
                    return jsonify({"erro": "Nenhum tipo de despesa ativo disponível no sistema."}), 400

        # Validar cada classificação
        for c_item in norm_classif:
            c_td_id = c_item["tipo_despesa_id"]
            td = db.query(TipoDespesa).filter(TipoDespesa.id == c_td_id).first()
            if not td:
                return jsonify({"erro": f"Tipo de despesa ID {c_td_id} não encontrado."}), 400
            if td.tipo != "DESPESA":
                return jsonify({"erro": f"Classificação incompatível: '{td.categoria}' não é uma despesa."}), 400
            if not td.ativo:
                return jsonify({"erro": f"A classificação de despesa '{td.categoria}' está inativa e não pode ser utilizada."}), 400

        # Validar unicidade de identificacao das parcelas
        identificacoes_geradas = []
        for idx, p_item in enumerate(parcelas_input, 1):
            p_ident = (p_item.get("identificacao") or "").strip()
            if not p_ident:
                p_ident = f"PARC-PAGAR-NF-{numero_nf}-P{idx}-{uuid.uuid4().hex[:6].upper()}"

            conflito = db.query(ParcelaPagar).filter(ParcelaPagar.identificacao == p_ident).first()
            if conflito:
                return jsonify({"erro": f"A identificação de parcela '{p_ident}' já existe no sistema. Deve ser única."}), 400

            if p_ident in identificacoes_geradas:
                return jsonify({"erro": f"Identificação duplicada encontrada no mesmo lote de parcelas: '{p_ident}'."}), 400

            identificacoes_geradas.append(p_ident)

        # Criar movimento financeiro
        conta = ContaPagar(
            fornecedor_id=fornecedor_id,
            faturado_id=faturado_id,
            numero_nf=numero_nf,
            data_emissao=data_emissao,
            descricao_produtos=descricao,
            valor_total=valor_total,
            quantidade_parcelas=len(parcelas_input),
            tipo="APAGAR",
            ativo=True
        )
        db.add(conta)
        db.flush()

        # Criar parcelas
        for idx, p_item in enumerate(parcelas_input, 1):
            p_venc = parse_date(p_item.get("data_vencimento"))
            p_val = parse_decimal(p_item.get("valor", valor_total / len(parcelas_input)))
            parcela = ParcelaPagar(
                conta_pagar_id=conta.id,
                numero_parcela=p_item.get("numero_parcela", idx),
                identificacao=identificacoes_geradas[idx - 1],
                data_vencimento=p_venc,
                valor=p_val,
                status=p_item.get("status", "PENDENTE"),
                ativo=True
            )
            db.add(parcela)

        # Criar vínculos com classificações
        for c_item in norm_classif:
            c_td_id = c_item["tipo_despesa_id"]
            c_perc = c_item["percentual"]
            c_val = c_item["valor"]
            classif = ClassificacaoContaPagar(
                conta_pagar_id=conta.id,
                tipo_despesa_id=c_td_id,
                percentual=c_perc,
                valor=c_val
            )
            db.add(classif)

        db.commit()
        db.refresh(conta)
        return jsonify(conta.to_dict()), 201
    except Exception as e:
        db.rollback()
        return jsonify({"erro": str(e)}), 400
    finally:
        db.close()


@app.route("/api/contas-pagar/<int:id>", methods=["GET"])
def obter_conta_pagar(id):
    db = SessionLocal()
    try:
        conta = db.query(ContaPagar).filter(ContaPagar.id == id).first()
        if not conta:
            return jsonify({"erro": "Conta a pagar não encontrada."}), 404
        return jsonify(conta.to_dict())
    finally:
        db.close()


@app.route("/api/contas-pagar/<int:id>/inativar", methods=["POST"])
@app.route("/api/contas-pagar/<int:id>", methods=["DELETE"])
def inativar_conta_pagar(id):
    db = SessionLocal()
    try:
        conta = db.query(ContaPagar).filter(ContaPagar.id == id).first()
        if not conta:
            return jsonify({"erro": "Conta a pagar não encontrada."}), 404

        conta.ativo = False
        for p in conta.parcelas:
            p.ativo = False
        db.commit()
        return jsonify({"mensagem": "Conta a pagar inativada com sucesso.", "conta": conta.to_dict()})
    finally:
        db.close()


@app.route("/api/contas-pagar/<int:id>/reativar", methods=["POST"])
def reativar_conta_pagar(id):
    db = SessionLocal()
    try:
        conta = db.query(ContaPagar).filter(ContaPagar.id == id).first()
        if not conta:
            return jsonify({"erro": "Conta a pagar não encontrada."}), 404

        conta.ativo = True
        for p in conta.parcelas:
            p.ativo = True
        db.commit()
        return jsonify({"mensagem": "Conta a pagar reativada com sucesso.", "conta": conta.to_dict()})
    finally:
        db.close()


# ============================================================================
# REGISTRAR CONTAS A RECEBER
# ============================================================================

@app.route("/api/contas-receber", methods=["GET"])
def listar_contas_receber():
    ativo_param = request.args.get("ativo", "all").lower()
    db = SessionLocal()
    try:
        query = db.query(ContaReceber)
        if ativo_param == "true":
            query = query.filter(ContaReceber.ativo == True)
        elif ativo_param == "false":
            query = query.filter(ContaReceber.ativo == False)
        contas = query.order_by(ContaReceber.data_emissao.desc()).all()
        return jsonify([c.to_dict() for c in contas])
    finally:
        db.close()


@app.route("/api/contas-receber", methods=["POST"])
def criar_conta_receber():
    """
    Registra uma nova Conta a Receber com parcelas e classificações de receita.
    Suporta 1 ou múltiplas parcelas e 1 ou múltiplas classificações de receita compatíveis.
    Valida unicidade de identificação da parcela, status ativo e soma de valores.
    """
    dados = request.get_json() or {}
    cliente_id = dados.get("cliente_id")
    faturado_id = dados.get("faturado_id")
    numero_doc = (dados.get("numero_documento") or "S/D").strip()
    data_emissao = parse_date(dados.get("data_emissao"))
    descricao = (dados.get("descricao") or "").strip()
    valor_total = parse_decimal(dados.get("valor_total", 0))

    if not cliente_id:
        return jsonify({"erro": "Cliente é obrigatório."}), 400

    if valor_total <= Decimal("0.00"):
        return jsonify({"erro": "O valor total do movimento deve ser maior que zero."}), 400

    db = SessionLocal()
    try:
        cli = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cli:
            return jsonify({"erro": "Cliente não encontrado."}), 400
        if not cli.ativo:
            return jsonify({"erro": "Cliente inativo não pode ser utilizado em novos lançamentos."}), 400

        fat = None
        if faturado_id:
            fat = db.query(Faturado).filter(Faturado.id == faturado_id).first()
            if not fat:
                return jsonify({"erro": "Faturado não encontrado."}), 400
            if not fat.ativo:
                return jsonify({"erro": "Faturado inativo não pode ser utilizado em novos lançamentos."}), 400
        else:
            fat = db.query(Faturado).filter(Faturado.ativo == True).first()
            if fat:
                faturado_id = fat.id
            else:
                return jsonify({"erro": "Nenhum faturado ativo cadastrado no sistema."}), 400

        parcelas_input = dados.get("parcelas") or []
        if not parcelas_input:
            venc = parse_date(dados.get("data_vencimento") or data_emissao)
            parcelas_input = [{"numero_parcela": 1, "data_vencimento": venc, "valor": valor_total}]

        # Validação financeira: a soma das parcelas deve coincidir com o valor total
        soma_parcelas = Decimal("0.00")
        for p_item in parcelas_input:
            p_val = parse_decimal(p_item.get("valor", 0))
            if p_val <= Decimal("0.00"):
                return jsonify({"erro": "O valor de cada parcela deve ser maior que zero."}), 400
            soma_parcelas += p_val

        if abs(soma_parcelas - valor_total) > Decimal("0.05"):
            return jsonify({
                "erro": f"A soma das parcelas (R$ {soma_parcelas:.2f}) não confere com o valor total do movimento (R$ {valor_total:.2f})."
            }), 400

        # Classificações de Receita compatíveis
        raw_classif = dados.get("classificacoes") or []
        norm_classif = []
        if raw_classif:
            for c in raw_classif:
                if isinstance(c, (int, str)):
                    norm_classif.append({"tipo_receita_id": int(c), "percentual": Decimal("100.00"), "valor": valor_total})
                elif isinstance(c, dict):
                    norm_classif.append({
                        "tipo_receita_id": int(c.get("tipo_receita_id") or c.get("id")),
                        "percentual": parse_decimal(c.get("percentual", 100.0)),
                        "valor": parse_decimal(c.get("valor", valor_total))
                    })
        else:
            tr_id = dados.get("tipo_receita_id")
            if tr_id:
                norm_classif = [{"tipo_receita_id": int(tr_id), "percentual": Decimal("100.00"), "valor": valor_total}]
            else:
                primeiro_tr = db.query(TipoReceita).filter(TipoReceita.ativo == True).first()
                if primeiro_tr:
                    norm_classif = [{"tipo_receita_id": primeiro_tr.id, "percentual": Decimal("100.00"), "valor": valor_total}]
                else:
                    return jsonify({"erro": "Nenhum tipo de receita ativo disponível no sistema."}), 400

        # Validar cada classificação
        for c_item in norm_classif:
            c_tr_id = c_item["tipo_receita_id"]
            tr = db.query(TipoReceita).filter(TipoReceita.id == c_tr_id).first()
            if not tr:
                return jsonify({"erro": f"Tipo de receita ID {c_tr_id} não encontrado."}), 400
            if tr.tipo != "RECEITA":
                return jsonify({"erro": f"Classificação incompatível: '{tr.descricao}' não é uma receita."}), 400
            if not tr.ativo:
                return jsonify({"erro": f"O tipo de receita '{tr.descricao}' está inativo e não pode ser utilizado."}), 400

        # Validar unicidade de identificacao das parcelas
        identificacoes_geradas = []
        for idx, p_item in enumerate(parcelas_input, 1):
            p_ident = (p_item.get("identificacao") or "").strip()
            if not p_ident:
                p_ident = f"PARC-RECEBER-DOC-{numero_doc}-P{idx}-{uuid.uuid4().hex[:6].upper()}"

            conflito = db.query(ParcelaReceber).filter(ParcelaReceber.identificacao == p_ident).first()
            if conflito:
                return jsonify({"erro": f"A identificação de parcela '{p_ident}' já existe no sistema. Deve ser única."}), 400

            if p_ident in identificacoes_geradas:
                return jsonify({"erro": f"Identificação duplicada encontrada no mesmo lote de parcelas: '{p_ident}'."}), 400

            identificacoes_geradas.append(p_ident)

        # Criar movimento financeiro
        conta = ContaReceber(
            cliente_id=cliente_id,
            faturado_id=faturado_id,
            numero_documento=numero_doc,
            data_emissao=data_emissao,
            descricao=descricao,
            valor_total=valor_total,
            quantidade_parcelas=len(parcelas_input),
            tipo="ARECEBER",
            ativo=True
        )
        db.add(conta)
        db.flush()

        # Criar parcelas
        for idx, p_item in enumerate(parcelas_input, 1):
            p_venc = parse_date(p_item.get("data_vencimento"))
            p_val = parse_decimal(p_item.get("valor", valor_total / len(parcelas_input)))
            parcela = ParcelaReceber(
                conta_receber_id=conta.id,
                numero_parcela=p_item.get("numero_parcela", idx),
                identificacao=identificacoes_geradas[idx - 1],
                data_vencimento=p_venc,
                valor=p_val,
                status=p_item.get("status", "PENDENTE"),
                ativo=True
            )
            db.add(parcela)

        # Criar vínculos com classificações
        for c_item in norm_classif:
            c_tr_id = c_item["tipo_receita_id"]
            c_perc = c_item["percentual"]
            c_val = c_item["valor"]
            classif = ClassificacaoContaReceber(
                conta_receber_id=conta.id,
                tipo_receita_id=c_tr_id,
                percentual=c_perc,
                valor=c_val
            )
            db.add(classif)

        db.commit()
        db.refresh(conta)
        return jsonify(conta.to_dict()), 201
    except Exception as e:
        db.rollback()
        return jsonify({"erro": str(e)}), 400
    finally:
        db.close()



@app.route("/api/contas-receber/<int:id>", methods=["GET"])
def obter_conta_receber(id):
    db = SessionLocal()
    try:
        conta = db.query(ContaReceber).filter(ContaReceber.id == id).first()
        if not conta:
            return jsonify({"erro": "Conta a receber não encontrada."}), 404
        return jsonify(conta.to_dict())
    finally:
        db.close()


@app.route("/api/contas-receber/<int:id>/inativar", methods=["POST"])
@app.route("/api/contas-receber/<int:id>", methods=["DELETE"])
def inativar_conta_receber(id):
    db = SessionLocal()
    try:
        conta = db.query(ContaReceber).filter(ContaReceber.id == id).first()
        if not conta:
            return jsonify({"erro": "Conta a receber não encontrada."}), 404

        conta.ativo = False
        for p in conta.parcelas:
            p.ativo = False
        db.commit()
        return jsonify({"mensagem": "Conta a receber inativada com sucesso.", "conta": conta.to_dict()})
    finally:
        db.close()


@app.route("/api/contas-receber/<int:id>/reativar", methods=["POST"])
def reativar_conta_receber(id):
    db = SessionLocal()
    try:
        conta = db.query(ContaReceber).filter(ContaReceber.id == id).first()
        if not conta:
            return jsonify({"erro": "Conta a receber não encontrada."}), 404

        conta.ativo = True
        for p in conta.parcelas:
            p.ativo = True
        db.commit()
        return jsonify({"mensagem": "Conta a receber reativada com sucesso.", "conta": conta.to_dict()})
    finally:
        db.close()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Iniciando servidor Flask na porta {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
