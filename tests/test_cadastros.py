import json
from decimal import Decimal
import datetime
from tests.base import BaseTestCase
from models import (
    Fornecedor, Cliente, Faturado, TipoDespesa, TipoReceita,
    ContaPagar, ParcelaPagar, ClassificacaoContaPagar
)

class TestCadastros(BaseTestCase):
    """
    Testes de Cadastros e Manutenção:
    - Cadastro de fornecedor, cliente e faturado.
    - Cadastro de classificações de receita e despesa.
    - Edição de cadastros.
    - Inativação de cadastros.
    - Reativação de cadastros.
    - Bloqueio de exclusão física pelos fluxos normais da aplicação.
    - Preservação dos movimentos históricos após inativação.
    """

    def test_cadastro_fornecedor(self):
        """Testa o cadastro de um novo fornecedor via API."""
        payload = {
            "razao_social": "FORNECEDOR TESTE LTDA",
            "nome_fantasia": "Teste Fornec",
            "cnpj": "11.222.333/0001-44",
            "email": "contato@teste.com"
        }
        res = self.client.post("/api/fornecedores", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["razao_social"], "FORNECEDOR TESTE LTDA")
        self.assertTrue(data["ativo"])
        self.assertEqual(data["tipo"], "FORNECEDOR")
        self.assertIsNotNone(data["id"])

        # Verificar no banco
        db = self.get_db()
        try:
            f = db.query(Fornecedor).filter_by(cnpj="11.222.333/0001-44").first()
            self.assertIsNotNone(f)
            self.assertEqual(f.razao_social, "FORNECEDOR TESTE LTDA")
        finally:
            db.close()

    def test_cadastro_cliente(self):
        """Testa o cadastro de um novo cliente via API."""
        payload = {
            "razao_social": "AGRO CLIENTE S.A.",
            "nome_fantasia": "AgroCliente",
            "cpf_cnpj": "44.555.666/0001-77"
        }
        res = self.client.post("/api/clientes", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["razao_social"], "AGRO CLIENTE S.A.")
        self.assertTrue(data["ativo"])
        self.assertEqual(data["tipo"], "CLIENTE")

    def test_cadastro_faturado(self):
        """Testa o cadastro de faturado via API."""
        payload = {
            "nome_completo": "BELTRANO DA SILVA",
            "cpf": "123.456.789-00"
        }
        res = self.client.post("/api/faturados", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data["nome_completo"], "BELTRANO DA SILVA")
        self.assertTrue(data["ativo"])
        self.assertEqual(data["tipo"], "FATURADO")

    def test_cadastro_classificacoes(self):
        """Testa o cadastro de tipos de receita e tipos de despesa."""
        # Despesa
        res_d = self.client.post("/api/tipos-despesa", json={
            "categoria": "MANUTENÇÃO E OPERAÇÃO",
            "descricao": "Peças e Reparos Emergenciais"
        })
        self.assertEqual(res_d.status_code, 201)
        data_d = res_d.get_json()
        self.assertEqual(data_d["categoria"], "MANUTENÇÃO E OPERAÇÃO")
        self.assertEqual(data_d["descricao"], "Peças e Reparos Emergenciais")
        self.assertEqual(data_d["tipo"], "DESPESA")

        # Receita
        res_r = self.client.post("/api/tipos-receita", json={
            "descricao": "Venda de Grãos Safra Nova"
        })
        self.assertEqual(res_r.status_code, 201)
        data_r = res_r.get_json()
        self.assertEqual(data_r["descricao"], "Venda de Grãos Safra Nova")
        self.assertEqual(data_r["tipo"], "RECEITA")

    def test_edicao_cadastros(self):
        """Testa a edição de cadastros existentes via PUT."""
        # Cadastrar fornecedor
        res = self.client.post("/api/fornecedores", json={
            "razao_social": "NOME ANTIGO LTDA",
            "cnpj": "99.888.777/0001-11"
        })
        forn_id = res.get_json()["id"]

        # Editar fornecedor
        res_edit = self.client.put(f"/api/fornecedores/{forn_id}", json={
            "razao_social": "NOME ATUALIZADO S.A.",
            "nome_fantasia": "Atualizado",
            "cnpj": "99.888.777/0001-11"
        })
        self.assertEqual(res_edit.status_code, 200)
        self.assertEqual(res_edit.get_json()["razao_social"], "NOME ATUALIZADO S.A.")

        # Editar tipo de despesa
        res_td = self.client.post("/api/tipos-despesa", json={
            "categoria": "OPERACIONAL",
            "descricao": "Combustivel Antigo"
        })
        td_id = res_td.get_json()["id"]

        res_td_edit = self.client.put(f"/api/tipos-despesa/{td_id}", json={
            "categoria": "OPERACIONAL",
            "descricao": "Diesel S10 e Lubrificantes"
        })
        self.assertEqual(res_td_edit.status_code, 200)
        self.assertEqual(res_td_edit.get_json()["descricao"], "Diesel S10 e Lubrificantes")

    def test_inativacao_e_reativacao_cadastros(self):
        """Testa a inativação e posterior reativação de cadastros."""
        # Cadastrar fornecedor
        res = self.client.post("/api/fornecedores", json={
            "razao_social": "FORNECEDOR CICLO LTDA",
            "cnpj": "55.444.333/0001-22"
        })
        forn_id = res.get_json()["id"]
        self.assertTrue(res.get_json()["ativo"])

        # Inativar fornecedor
        res_inativar = self.client.post(f"/api/fornecedores/{forn_id}/inativar")
        self.assertEqual(res_inativar.status_code, 200)
        self.assertFalse(res_inativar.get_json()["fornecedor"]["ativo"])

        # Verificar se consulta com apenas_ativos=true não retorna ele
        res_list_ativos = self.client.get("/api/fornecedores?apenas_ativos=true")
        ids_ativos = [f["id"] for f in res_list_ativos.get_json()]
        self.assertNotIn(forn_id, ids_ativos)

        # Verificar se consulta geral (todos) retorna ele como inativo
        res_list_todos = self.client.get("/api/fornecedores")
        item = next(f for f in res_list_todos.get_json() if f["id"] == forn_id)
        self.assertFalse(item["ativo"])

        # Reativar fornecedor
        res_reativar = self.client.post(f"/api/fornecedores/{forn_id}/reativar")
        self.assertEqual(res_reativar.status_code, 200)
        self.assertTrue(res_reativar.get_json()["fornecedor"]["ativo"])

        # Verificar se voltou a aparecer nos ativos
        res_list_ativos_pos = self.client.get("/api/fornecedores?apenas_ativos=true")
        ids_ativos_pos = [f["id"] for f in res_list_ativos_pos.get_json()]
        self.assertIn(forn_id, ids_ativos_pos)

    def test_bloqueio_exclusao_fisica(self):
        """
        Regra: Nenhum cadastro poderá ser excluído fisicamente pelo fluxo normal da aplicação.
        Verifica que DELETE converte para inativação lógica, mantendo o registro no banco.
        """
        res_post = self.client.post("/api/fornecedores", json={
            "razao_social": "FORNECEDOR INDELETAVEL LTDA",
            "cnpj": "77.888.999/0001-00"
        })
        forn_id = res_post.get_json()["id"]

        # Tentativa de DELETE
        res_del = self.client.delete(f"/api/fornecedores/{forn_id}")
        self.assertEqual(res_del.status_code, 200)
        self.assertIn("exclusão física não permitida", res_del.get_json()["mensagem"].lower())
        self.assertFalse(res_del.get_json()["fornecedor"]["ativo"])

        # Verificar que o registro continua existindo no banco intacto
        db = self.get_db()
        try:
            f = db.query(Fornecedor).filter_by(id=forn_id).first()
            self.assertIsNotNone(f)
            self.assertFalse(f.ativo)
        finally:
            db.close()

    def test_preservacao_movimentos_apos_inativacao(self):
        """
        Regra: A inativação de um cadastro não poderá apagar, invalidar ou modificar
        indevidamente movimentos financeiros históricos já registrados.
        """
        db = self.get_db()
        try:
            # Criar fornecedor, faturado e despesa
            forn = Fornecedor(razao_social="FORNECEDOR HISTORICO", cnpj="11.111.111/0001-99", ativo=True)
            fat = Faturado(nome_completo="FATURADO HISTORICO", cpf="111.222.333-44", ativo=True)
            td = TipoDespesa(categoria="SERVIÇOS", descricao="Frete de Carga", ativo=True)
            db.add_all([forn, fat, td])
            db.commit()
            db.refresh(forn)
            db.refresh(fat)
            db.refresh(td)

            # Criar movimento de conta a pagar histórico
            conta = ContaPagar(
                fornecedor_id=forn.id,
                faturado_id=fat.id,
                descricao_produtos="Frete Safra 2024",
                valor_total=Decimal("1500.00"),
                numero_nf="NF-9999",
                data_emissao=datetime.date(2024, 1, 15),
                tipo="APAGAR"
            )
            db.add(conta)
            db.commit()
            db.refresh(conta)

            parc = ParcelaPagar(
                conta_pagar_id=conta.id,
                numero_parcela=1,
                valor=Decimal("1500.00"),
                data_vencimento=datetime.date(2024, 2, 15),
                identificacao="PARC-TESTE-HIST-1"
            )
            classif = ClassificacaoContaPagar(
                conta_pagar_id=conta.id,
                tipo_despesa_id=td.id
            )
            db.add_all([parc, classif])
            db.commit()
            conta_id = conta.id
            forn_id = forn.id
        finally:
            db.close()

        # Inativar o fornecedor via API
        res_inativar = self.client.post(f"/api/fornecedores/{forn_id}/inativar")
        self.assertEqual(res_inativar.status_code, 200)
        self.assertFalse(res_inativar.get_json()["fornecedor"]["ativo"])

        # Verificar se a conta histórica permanece intacta
        res_conta = self.client.get(f"/api/contas-pagar/{conta_id}")
        self.assertEqual(res_conta.status_code, 200)
        data_conta = res_conta.get_json()
        self.assertEqual(data_conta["id"], conta_id)
        self.assertEqual(data_conta["fornecedor_id"], forn_id)
        self.assertEqual(float(data_conta["valor_total"]), 1500.0)
        self.assertEqual(len(data_conta["parcelas"]), 1)
        self.assertEqual(data_conta["parcelas"][0]["identificacao"], "PARC-TESTE-HIST-1")
