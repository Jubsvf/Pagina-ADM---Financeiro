import json
from decimal import Decimal
import datetime
from tests.base import BaseTestCase
from models import (
    Fornecedor, Cliente, Faturado, TipoDespesa, TipoReceita,
    ContaPagar, ParcelaPagar, ClassificacaoContaPagar,
    ContaReceber, ParcelaReceber, ClassificacaoContaReceber
)

class TestMovimentosFinanceiros(BaseTestCase):
    """
    Testes de Movimentos Financeiros:
    - Registro de conta a pagar com 1 classificação e 1 parcela.
    - Registro de conta a pagar com múltiplas classificações e parcelas.
    - Registro de conta a receber com uma ou mais classificações de receita.
    - Parcelas com datas de vencimento distintas.
    - Rejeição de classificações incompatíveis com o tipo de movimento.
    - Validação da unicidade de identificacao em parcelas.
    - Rejeição de dados inválidos ou incompletos (inativos, soma incorreta, etc).
    """

    def setUp(self):
        super().setUp()
        self.seed_initial_data()
        db = self.get_db()
        try:
            self.fornecedor = db.query(Fornecedor).first()
            self.cliente = db.query(Cliente).first()
            self.despesas = db.query(TipoDespesa).limit(3).all()
            self.receitas = db.query(TipoReceita).limit(3).all()
        finally:
            db.close()

    def test_conta_pagar_uma_classificacao_uma_parcela(self):
        """Registro de uma conta a pagar com uma classificação e uma parcela."""
        payload = {
            "fornecedor_id": self.fornecedor.id,
            "descricao": "Aquisição de Filtros",
            "valor_total": "250.00",
            "numero_nf": "NF-1001",
            "data_emissao": "2025-05-10",
            "classificacoes": [self.despesas[0].id],
            "parcelas": [
                {
                    "numero_parcela": 1,
                    "valor": "250.00",
                    "data_vencimento": "2025-06-10"
                }
            ]
        }
        res = self.client.post("/api/contas-pagar", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["tipo"], "APAGAR")
        self.assertEqual(len(data["parcelas"]), 1)
        self.assertEqual(len(data["classificacoes"]), 1)
        self.assertTrue(data["parcelas"][0]["identificacao"].startswith("PARC-PAGAR-"))

    def test_conta_pagar_multiplas_classificacoes_e_parcelas(self):
        """Registro de conta a pagar com várias classificações e várias parcelas com vencimentos distintos."""
        payload = {
            "fornecedor_id": self.fornecedor.id,
            "descricao": "Peças e Manutenção Geral",
            "valor_total": "3000.00",
            "numero_nf": "NF-1002",
            "data_emissao": "2025-06-01",
            "classificacoes": [self.despesas[0].id, self.despesas[1].id],
            "parcelas": [
                {
                    "numero_parcela": 1,
                    "valor": "1000.00",
                    "data_vencimento": "2025-07-01",
                    "identificacao": "NF-1002/01"
                },
                {
                    "numero_parcela": 2,
                    "valor": "1000.00",
                    "data_vencimento": "2025-08-01",
                    "identificacao": "NF-1002/02"
                },
                {
                    "numero_parcela": 3,
                    "valor": "1000.00",
                    "data_vencimento": "2025-09-01",
                    "identificacao": "NF-1002/03"
                }
            ]
        }
        res = self.client.post("/api/contas-pagar", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(len(data["parcelas"]), 3)
        self.assertEqual(len(data["classificacoes"]), 2)

        # Verificar vencimentos diferentes
        vencimentos = [p["data_vencimento"] for p in data["parcelas"]]
        self.assertEqual(len(set(vencimentos)), 3)
        self.assertEqual(data["parcelas"][0]["identificacao"], "NF-1002/01")
        self.assertEqual(data["parcelas"][1]["identificacao"], "NF-1002/02")
        self.assertEqual(data["parcelas"][2]["identificacao"], "NF-1002/03")

    def test_conta_receber_com_classificacoes_e_parcelas(self):
        """Registro de conta a receber com classificações de receita e parcelas."""
        payload = {
            "cliente_id": self.cliente.id,
            "descricao": "Venda de Grãos Safra Verão",
            "valor_total": "15000.00",
            "numero_documento": "CONTRATO-881",
            "data_emissao": "2025-04-01",
            "classificacoes": [self.receitas[0].id],
            "parcelas": [
                {
                    "numero_parcela": 1,
                    "valor": "7500.00",
                    "data_vencimento": "2025-05-01"
                },
                {
                    "numero_parcela": 2,
                    "valor": "7500.00",
                    "data_vencimento": "2025-06-01"
                }
            ]
        }
        res = self.client.post("/api/contas-receber", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["tipo"], "ARECEBER")
        self.assertEqual(len(data["parcelas"]), 2)
        self.assertEqual(len(data["classificacoes"]), 1)
        self.assertEqual(data["cliente_id"], self.cliente.id)

    def test_rejeicao_classificacoes_incompativeis(self):
        """
        Rejeição de classificações incompatíveis:
        - Tentar usar despesa inativa em conta a pagar.
        - Tentar usar ID inexistente de classificação.
        """
        # Inativar uma despesa
        despesa_inativa = self.despesas[2]
        res_inativar = self.client.post(f"/api/tipos-despesa/{despesa_inativa.id}/inativar")
        self.assertEqual(res_inativar.status_code, 200)

        # 1. Tentar vincular despesa inativa em novo lançamento
        payload_inativa = {
            "fornecedor_id": self.fornecedor.id,
            "descricao": "Tentativa Invalida",
            "valor_total": "100.00",
            "numero_nf": "NF-INATIVA-1",
            "classificacoes": [despesa_inativa.id],
            "parcelas": [{"numero_parcela": 1, "valor": "100.00", "data_vencimento": "2025-07-01"}]
        }
        res_inativa = self.client.post("/api/contas-pagar", json=payload_inativa)
        self.assertEqual(res_inativa.status_code, 400)
        self.assertIn("inativ", res_inativa.get_json()["erro"].lower())

        # 2. Tentar vincular ID que não existe (ex: 99999)
        payload_inexistente = {
            "fornecedor_id": self.fornecedor.id,
            "descricao": "Tentativa Inexistente",
            "valor_total": "100.00",
            "numero_nf": "NF-INEXISTENTE-1",
            "classificacoes": [99999],
            "parcelas": [{"numero_parcela": 1, "valor": "100.00", "data_vencimento": "2025-07-01"}]
        }
        res_inexistente = self.client.post("/api/contas-pagar", json=payload_inexistente)
        self.assertEqual(res_inexistente.status_code, 400)

    def test_rejeicao_lancamento_com_fornecedor_inativo(self):
        """Regra: Registros inativos não deverão ser utilizados em novos lançamentos."""
        # Inativar fornecedor
        self.client.post(f"/api/fornecedores/{self.fornecedor.id}/inativar")

        payload = {
            "fornecedor_id": self.fornecedor.id,
            "descricao": "Tentativa Fornecedor Inativo",
            "valor_total": "100.00",
            "numero_nf": "NF-FORN-INATIVO",
            "classificacoes": [self.despesas[0].id],
            "parcelas": [{"numero_parcela": 1, "valor": "100.00", "data_vencimento": "2025-07-01"}]
        }
        res = self.client.post("/api/contas-pagar", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("inativo", res.get_json()["erro"].lower())

    def test_validacao_soma_parcelas_divergente(self):
        """Rejeita se a soma das parcelas divergir do valor_total."""
        payload = {
            "fornecedor_id": self.fornecedor.id,
            "descricao": "Erro na Soma",
            "valor_total": "500.00",
            "numero_nf": "NF-SOMA-ERR",
            "classificacoes": [self.despesas[0].id],
            "parcelas": [
                {"numero_parcela": 1, "valor": "200.00", "data_vencimento": "2025-07-01"},
                {"numero_parcela": 2, "valor": "200.00", "data_vencimento": "2025-08-01"}
            ]
        }
        res = self.client.post("/api/contas-pagar", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("soma", res.get_json()["erro"].lower())

    def test_unicidade_identificacao_parcelas(self):
        """Validação da unicidade de identificação de parcelas."""
        # Cria primeira conta com identificação específica
        payload1 = {
            "fornecedor_id": self.fornecedor.id,
            "descricao": "Primeira Conta",
            "valor_total": "100.00",
            "numero_nf": "NF-UNICA-1",
            "classificacoes": [self.despesas[0].id],
            "parcelas": [
                {"numero_parcela": 1, "valor": "100.00", "data_vencimento": "2025-07-01", "identificacao": "ID-UNICA-123"}
            ]
        }
        res1 = self.client.post("/api/contas-pagar", json=payload1)
        self.assertEqual(res1.status_code, 201)

        # Tenta criar segunda conta com a mesma identificação de parcela
        payload2 = {
            "fornecedor_id": self.fornecedor.id,
            "descricao": "Segunda Conta Repetida",
            "valor_total": "100.00",
            "numero_nf": "NF-UNICA-2",
            "classificacoes": [self.despesas[0].id],
            "parcelas": [
                {"numero_parcela": 1, "valor": "100.00", "data_vencimento": "2025-07-01", "identificacao": "ID-UNICA-123"}
            ]
        }
        res2 = self.client.post("/api/contas-pagar", json=payload2)
        self.assertEqual(res2.status_code, 400)
        self.assertIn("identificação", res2.get_json()["erro"].lower())
