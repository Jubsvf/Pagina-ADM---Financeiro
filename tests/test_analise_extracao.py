import json
from decimal import Decimal
import datetime
from tests.base import BaseTestCase
from models import (
    Fornecedor, Faturado, TipoDespesa,
    ContaPagar, ParcelaPagar, ClassificacaoContaPagar
)

class TestAnaliseExtracao(BaseTestCase):
    """
    Testes da Segunda Etapa:
    - Análise dos dados extraídos (consulta de fornecedor, faturado e classificação de despesa).
    - Status EXISTE com ID vs NÃO EXISTE com id=None.
    - Processamento pós-análise: criação automática dos cadastros ausentes.
    - Processamento pós-análise: reutilização de cadastros existentes sem duplicação.
    - Transação atômica e prevenção de duplicidade (mesma NF para mesmo fornecedor).
    - Confirmação de lançamento retornando IDs reais criados.
    """

    def setUp(self):
        super().setUp()
        self.seed_initial_data()
        db = self.get_db()
        try:
            self.fornecedor_existente = db.query(Fornecedor).first()
            self.faturado_existente = db.query(Faturado).first()
            self.despesa_existente = db.query(TipoDespesa).filter_by(descricao="Combustíveis e Lubrificantes").first()
            if not self.despesa_existente:
                self.despesa_existente = db.query(TipoDespesa).first()
        finally:
            db.close()

    def test_analise_entidades_existentes(self):
        """Testa análise quando fornecedor, faturado e despesa existem no banco."""
        payload = {
            "fornecedor": {
                "razao_social": self.fornecedor_existente.razao_social,
                "cnpj": self.fornecedor_existente.cnpj
            },
            "faturado": {
                "nome_completo": self.faturado_existente.nome_completo,
                "cpf": self.faturado_existente.cpf
            },
            "classificacao_despesa": {
                "descricao": self.despesa_existente.descricao,
                "categoria": self.despesa_existente.categoria
            }
        }
        res = self.client.post("/api/analisar-dados-extracao", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Fornecedor
        self.assertTrue(data["fornecedor"]["existe"])
        self.assertEqual(data["fornecedor"]["id"], self.fornecedor_existente.id)
        self.assertEqual(data["fornecedor"]["situacao"], f"EXISTE — ID: {self.fornecedor_existente.id}")

        # Faturado
        self.assertTrue(data["faturado"]["existe"])
        self.assertEqual(data["faturado"]["id"], self.faturado_existente.id)
        self.assertEqual(data["faturado"]["situacao"], f"EXISTE — ID: {self.faturado_existente.id}")

        # Classificação de Despesa
        self.assertTrue(data["classificacao"]["existe"])
        self.assertEqual(data["classificacao"]["id"], self.despesa_existente.id)
        self.assertEqual(data["classificacao"]["situacao"], f"EXISTE — ID: {self.despesa_existente.id}")

    def test_analise_entidades_inexistentes(self):
        """Testa análise quando fornecedor, faturado e despesa NÃO existem no banco."""
        payload = {
            "fornecedor": {
                "razao_social": "EMPRESA INEXISTENTE LTDA",
                "cnpj": "99.000.111/0001-99"
            },
            "faturado": {
                "nome_completo": "FULANO DE TAL INEXISTENTE",
                "cpf": "000.111.222-33"
            },
            "classificacao_despesa": {
                "descricao": "Despesa Inexistente Totalmente Nova",
                "categoria": "CATEGORIA NOVA"
            }
        }
        res = self.client.post("/api/analisar-dados-extracao", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertFalse(data["fornecedor"]["existe"])
        self.assertIsNone(data["fornecedor"]["id"])
        self.assertEqual(data["fornecedor"]["situacao"], "NÃO EXISTE")

        self.assertFalse(data["faturado"]["existe"])
        self.assertIsNone(data["faturado"]["id"])
        self.assertEqual(data["faturado"]["situacao"], "NÃO EXISTE")

        self.assertFalse(data["classificacao"]["existe"])
        self.assertIsNone(data["classificacao"]["id"])
        self.assertEqual(data["classificacao"]["situacao"], "NÃO EXISTE")

    def test_processamento_com_criacao_automatica_de_ausentes(self):
        """
        Processamento pós-análise:
        Fornecedor, faturado e classificação não existem previamente.
        O sistema deve criá-los automaticamente e registrar o movimento e suas parcelas.
        """
        payload = {
            "fornecedor": {
                "razao_social": "MÁQUINAS DO CERRADO LTDA",
                "cnpj": "77.666.555/0001-44"
            },
            "faturado": {
                "nome_completo": "PRODUTOR RURAL JOAO",
                "cpf": "555.444.333-22"
            },
            "classificacao": {
                "categoria": "SERVIÇOS DE TERCEIROS",
                "descricao": "Colheita Mecanizada Terceirizada"
            },
            "dados_financeiros": {
                "numero_nf": "NF-8888",
                "valor_total": "5000.00",
                "data_emissao": "2025-05-15",
                "descricao": "Prestação de serviços de colheita safra 2025",
                "parcelas": [
                    {
                        "numero_parcela": 1,
                        "valor": "2500.00",
                        "data_vencimento": "2025-06-15"
                    },
                    {
                        "numero_parcela": 2,
                        "valor": "2500.00",
                        "data_vencimento": "2025-07-15"
                    }
                ]
            }
        }
        res = self.client.post("/api/processar-lancamento-extracao", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()

        self.assertTrue(data["ok"])
        self.assertIsNotNone(data["movimento_id"])
        self.assertEqual(data["parcelas_total"], 2)
        self.assertEqual(data["fornecedor_nome"], "MÁQUINAS DO CERRADO LTDA")
        self.assertEqual(data["faturado_nome"], "PRODUTOR RURAL JOAO")
        self.assertEqual(data["classificacao_nome"], "Colheita Mecanizada Terceirizada")

        # Verificar no banco se entidades foram criadas e movimento persistido
        db = self.get_db()
        try:
            f = db.query(Fornecedor).filter_by(cnpj="77.666.555/0001-44").first()
            self.assertIsNotNone(f)
            self.assertEqual(f.tipo, "FORNECEDOR")

            fat = db.query(Faturado).filter_by(cpf="555.444.333-22").first()
            self.assertIsNotNone(fat)
            self.assertEqual(fat.tipo, "FATURADO")

            td = db.query(TipoDespesa).filter_by(descricao="Colheita Mecanizada Terceirizada").first()
            self.assertIsNotNone(td)
            self.assertEqual(td.tipo, "DESPESA")

            mov = db.query(ContaPagar).filter_by(id=data["movimento_id"]).first()
            self.assertIsNotNone(mov)
            self.assertEqual(mov.tipo, "APAGAR")
            self.assertEqual(mov.fornecedor_id, f.id)
            self.assertEqual(len(mov.parcelas), 2)
            self.assertEqual(len(mov.classificacoes), 1)

            # Verificar unicidade e integridade das parcelas
            for p in mov.parcelas:
                self.assertIsNotNone(p.identificacao)
                self.assertTrue(p.identificacao.startswith("PARC-"))
        finally:
            db.close()

    def test_processamento_reutilizacao_de_cadastros_existentes(self):
        """
        Processamento pós-análise:
        Fornecedor, faturado e classificação JÁ EXISTEM.
        O sistema deve reutilizá-los e não criar duplicatas no banco.
        """
        db = self.get_db()
        count_fornec_antigo = db.query(Fornecedor).count()
        count_faturado_antigo = db.query(Faturado).count()
        count_despesa_antigo = db.query(TipoDespesa).count()
        db.close()

        payload = {
            "fornecedor": {
                "razao_social": self.fornecedor_existente.razao_social,
                "cnpj": self.fornecedor_existente.cnpj
            },
            "faturado": {
                "nome_completo": self.faturado_existente.nome_completo,
                "cpf": self.faturado_existente.cpf
            },
            "classificacao": {
                "categoria": self.despesa_existente.categoria,
                "descricao": self.despesa_existente.descricao
            },
            "dados_financeiros": {
                "numero_nf": "NF-NOVA-REUSO",
                "valor_total": "1200.00",
                "data_emissao": "2025-05-20",
                "descricao": "Compra de insumos",
                "parcelas": [
                    {
                        "numero_parcela": 1,
                        "valor": "1200.00",
                        "data_vencimento": "2025-06-20"
                    }
                ]
            }
        }
        res = self.client.post("/api/processar-lancamento-extracao", json=payload)
        self.assertEqual(res.status_code, 201)

        db = self.get_db()
        try:
            self.assertEqual(db.query(Fornecedor).count(), count_fornec_antigo)
            self.assertEqual(db.query(Faturado).count(), count_faturado_antigo)
            self.assertEqual(db.query(TipoDespesa).count(), count_despesa_antigo)
        finally:
            db.close()

    def test_prevencao_duplicidade_mesma_nf(self):
        """
        Prevenção de duplicidade:
        Se tentar processar a mesma NF para o mesmo fornecedor, deve ser rejeitado com 409 Conflict.
        """
        payload = {
            "fornecedor": {
                "razao_social": self.fornecedor_existente.razao_social,
                "cnpj": self.fornecedor_existente.cnpj
            },
            "faturado": {
                "nome_completo": self.faturado_existente.nome_completo,
                "cpf": self.faturado_existente.cpf
            },
            "classificacao": {
                "categoria": self.despesa_existente.categoria,
                "descricao": self.despesa_existente.descricao
            },
            "dados_financeiros": {
                "numero_nf": "NF-DUPLICADA-TESTE",
                "valor_total": "800.00",
                "data_emissao": "2025-05-10",
                "descricao": "Primeira tentativa",
                "parcelas": [
                    {"numero_parcela": 1, "valor": "800.00", "data_vencimento": "2025-06-10"}
                ]
            }
        }
        # Primeiro envio com sucesso
        res1 = self.client.post("/api/processar-lancamento-extracao", json=payload)
        self.assertEqual(res1.status_code, 201)

        # Segundo envio idêntico deve ser bloqueado
        res2 = self.client.post("/api/processar-lancamento-extracao", json=payload)
        self.assertEqual(res2.status_code, 409)
        self.assertIn("duplicado", res2.get_json()["erro"].lower())
