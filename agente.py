import os
import io
import re
import json
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()


CATEGORIAS_SINAIS = {
    "MANUTENÇÃO E OPERAÇÃO": [
        "GRAXA", "ÓLEO", "OLEO", "DIESEL", "LUBRIFICANTE", "PEÇAS", "PECAS",
        "PARAFUSO", "ANEL", "BUCHA", "ROLAMENTO", "PNEU", "FILTRO", "CORREIA",
        "FERRAMENTA", "MÁQUINAS AGRÍCOLAS", "MAQUINAS AGRICOLAS", "ESTOPA",
        "PANO PARA LIMPEZA", "LIMPADOR", "VEDAÇÃO", "RETENTOR", "BATERIA",
        "SOLDA", "MANGUEIRA", "DISCO DE CORTE", "CABO", "PORCA", "ARRUELA"
    ],
    "INSUMOS AGRÍCOLAS": [
        "SEMENTE", "SEMENTES", "FERTILIZANTE", "FERTILIZANTES", "ADUBO",
        "DEFENSIVO", "DEFENSIVOS", "HERBICIDA", "FUNGICIDA", "INSETICIDA",
        "CORRETIVO", "CALCÁRIO", "CALCARIO", "GESSO AGRÍCOLA", "INOCULANTE",
        "NUTRIÇÃO FOLIAR"
    ],
    "RECURSOS HUMANOS": [
        "MÃO DE OBRA", "MAO DE OBRA", "DIÁRIA", "DIARIA", "SALÁRIO", "SALARIO",
        "ENCARGO", "FOLHA DE PAGAMENTO", "FGTS", "INSS", "HONORÁRIO TRABALHISTA",
        "SERVIÇO TEMPORÁRIO"
    ],
    "SERVIÇOS OPERACIONAIS": [
        "FRETE", "TRANSPORTE", "COLHEITA", "SECAGEM", "ARMAZENAGEM",
        "PULVERIZAÇÃO", "PULVERIZACAO", "APLICAÇÃO AÉREA", "TRANSBORDO",
        "SILAGEM"
    ],
    "INFRAESTRUTURA E UTILIDADES": [
        "ENERGIA ELÉTRICA", "ENERGIA ELETRICA", "LUZ", "ÁGUA", "AGUA",
        "ARRENDAMENTO", "CONSTRUÇÃO", "CONSTRUCAO", "REFORMA", "MATERIAL HIDRÁULICO",
        "HIDRAULICO", "CIMENTO", "TIJOLO", "AREIA", "BRITA", "MADEIRA",
        "CERCA", "ARAME", "TUBO", "CANO PVC"
    ],
    "ADMINISTRATIVAS": [
        "HONORÁRIOS CONTÁBEIS", "HONORARIOS", "CONTABILIDADE", "ADVOCACIA",
        "AGRONÔMICO", "CONSULTORIA", "DESPESA BANCÁRIA", "TARIFA BANCÁRIA",
        "TAXA BANCÁRIA", "INTERNET", "TELEFONE", "SOFTWARE", "LICENÇA"
    ],
    "SEGUROS E PROTEÇÃO": [
        "SEGURO AGRÍCOLA", "SEGURO AGRICOLA", "APÓLICE", "APOLICE", "SINISTRO",
        "SEGURO DE MÁQUINA", "SEGURO PRESTAMISTA", "SEGURO PATRIMONIAL"
    ],
    "IMPOSTOS E TAXAS": [
        "ITR", "IPTU", "IPVA", "INCRA", "CCIR", "TAXA DE FISCALIZAÇÃO", "DARF",
        "GUIA DE RECOLHIMENTO"
    ],
    "INVESTIMENTOS": [
        "AQUISIÇÃO DE MÁQUINAS", "TRATOR", "COLHEITADEIRA", "PLANTADEIRA",
        "PULVERIZADOR AUTOPROPELIDO", "VEÍCULO", "CAMINHONETE", "CAMINHÃO",
        "IMÓVEL", "TERRA", "INFRAESTRUTURA RURAL", "SILO", "BARRACÃO", "PIVÔ CENTRAL"
    ]
}


class Agente:
    def __init__(self, api_key=None):
        load_dotenv(override=True)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()

    def _extrair_texto_pdf(self, pdf_file):
        """Extrai todo o texto legível das páginas do arquivo PDF preservando o layout visual de tabelas."""
        try:
            if isinstance(pdf_file, (str, os.PathLike)):
                reader = PdfReader(pdf_file)
            elif hasattr(pdf_file, "read"):
                # Arquivo em stream ou FileStorage do Flask
                pdf_file.seek(0)
                reader = PdfReader(pdf_file)
            elif isinstance(pdf_file, (bytes, bytearray)):
                reader = PdfReader(io.BytesIO(pdf_file))
            else:
                raise ValueError("Tipo de arquivo PDF não suportado.")

            text_parts = []
            for i, page in enumerate(reader.pages):
                # Tenta extração em modo layout para preservar o alinhamento de colunas em tabelas
                try:
                    t = page.extract_text(extraction_mode="layout")
                except Exception:
                    t = page.extract_text()
                
                if t:
                    text_parts.append(f"--- PÁGINA {i+1} ---\n{t}")
            return "\n\n".join(text_parts)
        except Exception as e:
            print(f"Aviso ao extrair texto do PDF: {e}")
            return ""

    def _classificar_por_regras(self, texto_completo, descricao_produtos=""):
        """Classifica os produtos da NF detectando termos e aplicando as regras definidas."""
        conteudo_busca = f"{descricao_produtos} {texto_completo}".upper()
        
        melhor_categoria = "classificação"
        melhores_termos = []
        maior_pontuacao = 0

        for categoria, termos in CATEGORIAS_SINAIS.items():
            encontrados = []
            for termo in termos:
                if re.search(r'\b' + re.escape(termo) + r'\b', conteudo_busca) or termo in conteudo_busca:
                    if termo not in encontrados:
                        encontrados.append(termo)
            if len(encontrados) > maior_pontuacao:
                maior_pontuacao = len(encontrados)
                melhor_categoria = categoria
                melhores_termos = encontrados

        if maior_pontuacao == 0:
            melhor_categoria = "classificação"
            melhores_termos = []

        return melhor_categoria, melhores_termos

    def _extrair_fallback_heuristico(self, texto_pdf):
        """
        Parser heurístico robusto para extrair os campos principais caso a chave
        do Gemini não esteja configurada ou a chamada à LLM falhe temporariamente.
        """
        # Número da Nota Fiscal (ex: No. 000126981 ou Nº 000.084.682)
        nf_match = re.search(r'(?:Nº|Nº\.|No\.|Nº\s*|No\s*|NF-e\s*N[ºo°\.]\s*)(\d{3}(?:\.\d{3})+|\d{6,9})', texto_pdf, re.IGNORECASE)
        if not nf_match:
            nf_match = re.search(r'N[ºo°\.\s]*[:\.\s]*(\d{6,9}|\d{3}\.\d{3}\.\d{3})', texto_pdf, re.IGNORECASE)
        numero_nf = nf_match.group(1) if nf_match else None

        # Datas (formato DD/MM/AAAA ou DD.MM.AAAA)
        datas = re.findall(r'\b(\d{2}[/\.]\d{2}[/\.]\d{4})\b', texto_pdf)
        datas_formatadas = [d.replace(".", "/") for d in datas]
        data_emissao = datas_formatadas[0] if len(datas_formatadas) > 0 else None
        data_vencimento = datas_formatadas[1] if len(datas_formatadas) > 1 else data_emissao

        # Bloco Destinatário
        dest_block = re.search(r'DESTINATÁRIO/REMETENTE[\s\S]*?(?=INFORMAÇÕES|CÁLCULO DO IMPOSTO|DADOS DOS PRODUTOS|$)', texto_pdf, re.IGNORECASE)
        texto_destinatario = dest_block.group(0) if dest_block else ""

        # Bloco Emitente (tudo antes do Destinatário)
        idx_dest = texto_pdf.find('DESTINATÁRIO/REMETENTE')
        texto_emitente = texto_pdf[:idx_dest] if idx_dest != -1 else texto_pdf

        # CNPJs / CPFs do Emitente e Destinatário
        cnpjs_emit = re.findall(r'\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b', texto_emitente)
        cnpjs_dest = re.findall(r'\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b', texto_destinatario)
        cpfs_dest = re.findall(r'\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b', texto_destinatario)

        cnpj_emitente = cnpjs_emit[0] if cnpjs_emit else None
        cnpj_destinatario = cnpjs_dest[0] if cnpjs_dest else (cpfs_dest[0] if cpfs_dest else None)

        # Nomes de Emitente
        nome_emitente = None
        emit_match = re.search(r'RECEB[EI]MOS DE\s+(?:[\d\./\-]+\s+)?([A-Z0-9\s\.\-LTDA/S\.A\.]+?)\s+OS PRODUTOS', texto_emitente, re.IGNORECASE)
        if not emit_match:
            emit_match = re.search(r'(\b[A-Z0-9\s\.\-]+\b(?:S\.A\.|LTDA))\s*\n\s*(?:Rodovia|Rua|Av|Setor)', texto_emitente, re.IGNORECASE)
        if emit_match and len(emit_match.group(1).strip()) > 3:
            nome_emitente = emit_match.group(1).strip()

        # Nomes de Destinatário
        nome_destinatario = None
        if texto_destinatario:
            lines = [l.strip() for l in texto_destinatario.split('\n') if l.strip()]
            for i, l in enumerate(lines):
                if 'NOME/RAZÃO SOCIAL' in l.upper():
                    if i + 1 < len(lines):
                        nome_destinatario = re.split(r'\s{2,}|\b\d{2}\.\d{3}', lines[i+1])[0].strip()
                        break

        # Valor Total da NF (V.TOT. DA NF ou VALOR TOTAL DA NOTA)
        valor_total = None
        vtot_block = re.search(r'V\.TOT\. DA NF[^\n]*\n([^\n]+)', texto_pdf)
        if not vtot_block:
            vtot_block = re.search(r'VALOR TOTAL DA NOTA[^\n]*\n([^\n]+)', texto_pdf)
        
        if vtot_block:
            linha_valores = vtot_block.group(1)
            valores_encontrados = re.findall(r'\b(\d{1,3}(?:\.\d{3})*,\d{2})\b', linha_valores)
            if valores_encontrados:
                valor_total = valores_encontrados[-1]

        if not valor_total:
            valores_gerais = re.findall(r'\b(\d{1,3}(?:\.\d{3})*,\d{2})\b', texto_pdf)
            valor_total = valores_gerais[-1] if valores_gerais else None

        # Extração heurística de produtos linha a linha
        produtos = []
        linhas_pdf = texto_pdf.split("\n")
        em_produtos = False
        for linha in linhas_pdf:
            if "DADOS DOS PRODUTOS" in linha.upper() or ("CÓDIGO" in linha.upper() and "DESCRIÇÃO" in linha.upper()):
                em_produtos = True
                continue
            if em_produtos and ("DADOS ADICIONAIS" in linha.upper() or "CÁLCULO DO ISSQN" in linha.upper() or "INFORMAÇÕES COMPLEMENTARES" in linha.upper()):
                em_produtos = False
                break
            if em_produtos and linha.strip():
                # Padrão flexível: CÓDIGO | DESCRIÇÃO | NCM | (CST + CFOP) | UNIDADE | QTD | V.UNIT | V.TOTAL
                match_prod = re.search(r'([A-Z0-9/\-]+)\s+([A-Z0-9\s\./\-\(\)]+?)\s+(\d{8})\s+(\d{3})(\d{4})\s+([A-Z]{1,3})\s+([\d,\.]+)\s+([\d,\.]+)\s+([\d,\.]+)', linha)
                if not match_prod:
                    match_prod = re.search(r'([A-Z0-9/\-]+)\s+([A-Z0-9\s\./\-\(\)]+?)\s+(\d{8})\s+(\d{3,4})\s+(\d{4})\s+([A-Z]{1,3})\s+([\d,\.]+)\s+([\d,\.]+)\s+([\d,\.]+)', linha)
                
                if match_prod:
                    produtos.append({
                        "codigo": match_prod.group(1).strip(),
                        "descricao": match_prod.group(2).strip(),
                        "ncm": match_prod.group(3).strip(),
                        "cst": match_prod.group(4).strip(),
                        "cfop": match_prod.group(5).strip(),
                        "unidade": match_prod.group(6).strip(),
                        "quantidade": match_prod.group(7).strip(),
                        "valor_unitario": match_prod.group(8).strip(),
                        "valor_total": match_prod.group(9).strip()
                    })

        descricoes_lista = [p["descricao"] for p in produtos if p.get("descricao")]
        descricao_produtos = ", ".join(descricoes_lista) if descricoes_lista else "ITENS DA NOTA FISCAL"

        # Classificação
        categoria, termos = self._classificar_por_regras(texto_pdf, descricao_produtos)

        return {
            "Número da Nota Fiscal": numero_nf,
            "Data de Emissão": data_emissao,
            "Data de Vencimento": data_vencimento,
            "Descrição dos Produtos": descricao_produtos,
            "Valor Total": valor_total,
            "Nome do Emitente": nome_emitente,
            "CNPJ do Emitente": cnpj_emitente,
            "Nome do Destinatário": nome_destinatario,
            "CNPJ do Destinatário": cnpj_destinatario,
            "CLASSIFICAÇÃO": {
                "categoria": categoria,
                "termos_detectados": termos
            }
        }

    def extrair_dados(self, pdf_file, prompt=None):
        """
        Extrai informações de notas fiscais utilizando Gemini ou fallback heurístico.
        Retorna estritamente o JSON com as chaves padronizadas.
        """
        pdf_bytes = None
        try:
            if hasattr(pdf_file, "read"):
                pdf_file.seek(0)
                pdf_bytes = pdf_file.read()
                pdf_file.seek(0)
            elif isinstance(pdf_file, (bytes, bytearray)):
                pdf_bytes = bytes(pdf_file)
            elif isinstance(pdf_file, (str, os.PathLike)) and os.path.exists(pdf_file):
                with open(pdf_file, "rb") as f:
                    pdf_bytes = f.read()
        except Exception:
            pdf_bytes = None

        texto_pdf = self._extrair_texto_pdf(pdf_file)

        if not prompt:
            prompt = """
        Você é um especialista em análise de Notas Fiscais Eletrônicas (DANFE) e documentos fiscais.
        Sua tarefa é analisar rigorosamente o texto do documento fornecido (que abrange TODAS as páginas) e extrair os dados em formato JSON.

        INSTRUÇÕES DE EXTRAÇÃO:
        1. "Número da Nota Fiscal": número sequencial da nota fiscal (ex: "000126981" ou "000.084.682").
        2. "Data de Emissão": no formato DD/MM/AAAA. Se a data estiver no formato DD.MM.AAAA, converta para DD/MM/AAAA.
        3. "Data de Vencimento": no formato DD/MM/AAAA. Se não encontrar uma data de vencimento ou fatura explícita, retorne a mesma data de emissão.
        4. "Nome do Emitente": Razão social ou nome completo do EMITENTE/REMETENTE/VENDEDOR no topo da nota (ex: "LOUIS DREYFUS COMPANY BRASIL S.A."). Não confunda com o destinatário!
        5. "CNPJ do Emitente": CNPJ do emitente/vendedor no formato XX.XXX.XXX/XXXX-XX localizado na seção do emitente/cabeçalho.
        6. "Nome do Destinatário": Razão social ou nome completo localizado estritamente dentro da seção "DESTINATÁRIO/REMETENTE".
        7. "CNPJ do Destinatário": CNPJ ou CPF do comprador localizado na seção "DESTINATÁRIO/REMETENTE".
        8. "Valor Total": valor total final da nota fiscal localizado em "V.TOT. DA NF" ou "VALOR TOTAL DA NOTA" (ex: "6.478,76" ou "3.086,75"). Não retorne 0,00 se houver um valor em V.TOT. DA NF ou V. TOT. PROD.
        9. "Descrição dos Produtos": uma string concatenada com os nomes/descrições de TODOS os produtos/serviços de TODAS as páginas, separados por vírgula.

        REGRAS DE CLASSIFICAÇÃO:
        Classifique a Nota Fiscal em uma das categorias abaixo com base nas descrições dos produtos e serviços:
        - INSUMOS AGRÍCOLAS: Sementes, Fertilizantes, Adubos, Defensivos Agrícolas, Corretivos, Calcário, Herbicida, Fungicida, Inseticida.
        - MANUTENÇÃO E OPERAÇÃO: Combustíveis e Lubrificantes (Diesel, Graxa, Óleo), Peças, Parafusos, Anel, Bucha, Rolamento, Componentes Mecânicos, Manutenção de máquinas, Pneus, Filtros, Correias, Estopa, Pano de limpeza, Limpador.
        - RECURSOS HUMANOS: Mão de Obra Temporária, Salários e Encargos, Diárias.
        - SERVIÇOS OPERACIONAIS: Frete e Transporte, Colheita Terceirizada, Secagem e Armazenagem, Pulverização e aplicação aérea.
        - INFRAESTRUTURA E UTILIDADES: Energia Elétrica, Água, Arrendamento, Material de Construção, Cimento, Madeira, Arame.
        - ADMINISTRATIVAS: Honorários Contábeis, Advocacia, Consultoria, Tarifas Bancárias, Internet, Software.
        - SEGUROS E PROTEÇÃO: Seguro Agrícola, Apólice, Seguro de Máquinas.
        - IMPOSTOS E TAXAS: ITR, IPTU, IPVA, INCRA, DARF.
        - INVESTIMENTOS: Aquisição de Máquinas e Implementos, Trator, Colheitadeira, Veículos, Imóveis.

        Retorne também um objeto "CLASSIFICAÇÃO" com as chaves:
        - "categoria": string com o nome exato da categoria identificada (ou "classificação" se indeferido).
        - "termos_detectados": lista de strings com os termos encontrados no texto que motivaram a classificação.

        REGRAS DE INTEGRIDADE:
        - Não invente nem alucine informações. Se um campo individual não estiver no documento, retorne null.
        - Leia TODAS as páginas do PDF enviado.

        Retorne estritamente o JSON válido correspondente, sem textos explicativos antes ou depois.
        """

        # Se houver GEMINI_API_KEY configurada, tentar chamada via SDK Gemini
        if self.api_key:
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=self.api_key)
                
                conteudo_prompt = f"{prompt}\n\n--- TEXTO EXTRAÍDO DA NOTA FISCAL (TODAS AS PÁGINAS) ---\n{texto_pdf}"
                
                # Se o texto extraído for muito curto (ex: PDF digitalizado/escaneado), tenta enviar os bytes do PDF
                contents = [conteudo_prompt]
                if pdf_bytes and len(texto_pdf.strip()) < 50:
                    try:
                        contents = [
                            prompt,
                            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
                        ]
                    except Exception:
                        contents = [conteudo_prompt]

                # Lista de modelos por ordem de preferência, velocidade e resiliência
                modelos_tentativa = [
                    "gemini-flash-lite-latest",
                    "gemini-3.5-flash-lite",
                    "gemini-flash-latest",
                    "gemini-3.8-flash",
                    "gemini-3.7-flash",
                ]
                response = None
                ultimo_erro = None

                for mod in modelos_tentativa:
                    try:
                        response = client.models.generate_content(
                            model=mod,
                            contents=contents,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json"
                            )
                        )
                        if response and response.text:
                            break
                    except Exception as err_mod:
                        ultimo_erro = err_mod
                        continue

                if not response or not response.text:
                    raise ultimo_erro or Exception("Não foi possível obter resposta da API Gemini.")

                resposta_texto = response.text.strip()
                # Remover possíveis marcadores ```json ... ```
                if resposta_texto.startswith("```"):
                    resposta_texto = re.sub(r"^```[a-zA-Z]*\n?", "", resposta_texto)
                    resposta_texto = re.sub(r"\n?```$", "", resposta_texto).strip()
                elif "```" in resposta_texto:
                    match_fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", resposta_texto)
                    if match_fence:
                        resposta_texto = match_fence.group(1).strip()

                try:
                    dados = json.loads(resposta_texto)
                except Exception:
                    match_json = re.search(r"\{[\s\S]*\}", resposta_texto)
                    if match_json:
                        dados = json.loads(match_json.group(0))
                    else:
                        raise

                return self._normalizar_json(dados, texto_pdf)
            except Exception as e:
                print(f"Aviso: Erro ao chamar API Gemini ({e}). Utilizando motor de contingência.")

        # Fallback heurístico inteligente
        return self._extrair_fallback_heuristico(texto_pdf)

    def _normalizar_json(self, dados, texto_pdf=""):
        """
        Garante conformidade estrita com a estrutura esperada no projeto,
        removendo a chave 'produtos' e normalizando os campos principais.
        """
        def get_val(chaves, default=None):
            for k in chaves:
                if k in dados and dados[k] is not None:
                    v = str(dados[k]).strip()
                    if v and v.lower() != "null":
                        return v
            return default

        num_nf = get_val(["Número da Nota Fiscal", "numero_nota_fiscal", "numero_nf", "numero da nota fiscal", "numero"])
        dt_emissao = get_val(["Data de Emissão", "data_emissao", "data de emissao", "emissao"])
        dt_venc = get_val(["Data de Vencimento", "data_vencimento", "data de vencimento", "vencimento"], dt_emissao)
        val_total = get_val(["Valor Total", "valor_total", "valor total", "valor"])
        nome_emit = get_val(["Nome do Emitente", "nome_emitente", "nome do emitente", "emitente", "razao_social_emitente"])
        cnpj_emit = get_val(["CNPJ do Emitente", "cnpj_emitente", "cnpj do emitente"])
        nome_dest = get_val(["Nome do Destinatário", "nome_destinatario", "nome do destinatario", "destinatario"])
        cnpj_dest = get_val(["CNPJ do Destinatário", "cnpj_destinatario", "cnpj do destinatario", "cpf_destinatario", "CPF do Destinatário"])

        # Tratar a 'Descrição dos Produtos' caso a LLM tenha retornado os produtos em forma de lista ou texto
        desc_prod_val = dados.get("Descrição dos Produtos") or dados.get("descricao_produtos")
        if not desc_prod_val:
            prods_list = dados.get("produtos") or dados.get("itens")
            if isinstance(prods_list, list):
                nomes = [p.get("descricao") or p.get("description") or str(p) for p in prods_list if isinstance(p, dict)]
                desc_prod = ", ".join(filter(None, nomes))
            else:
                desc_prod = str(prods_list) if prods_list else ""
        else:
            desc_prod = str(desc_prod_val).strip()

        # Classificação
        classificacao_obj = dados.get("CLASSIFICAÇÃO") or dados.get("classificacao") or dados.get("classificação") or {}
        if isinstance(classificacao_obj, dict):
            categoria = classificacao_obj.get("categoria", "classificação")
            termos = classificacao_obj.get("termos_detectados", [])
        else:
            categoria = str(classificacao_obj)
            termos = []

        if not categoria or categoria.lower() == "desconhecida":
            categoria, termos_fallback = self._classificar_por_regras(texto_pdf, desc_prod)
            if not termos:
                termos = termos_fallback

        return {
            "Número da Nota Fiscal": num_nf,
            "Data de Emissão": dt_emissao,
            "Data de Vencimento": dt_venc,
            "Descrição dos Produtos": desc_prod,
            "Valor Total": val_total,
            "Nome do Emitente": nome_emit,
            "CNPJ do Emitente": cnpj_emit,
            "Nome do Destinatário": nome_dest,
            "CNPJ do Destinatário": cnpj_dest,
            "CLASSIFICAÇÃO": {
                "categoria": categoria,
                "termos_detectados": termos if isinstance(termos, list) else ([termos] if termos else [])
            }
        }

