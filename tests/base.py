import os
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import server
from database import Base
from seed import CATEGORIAS_DESPESA, TIPOS_RECEITA
from models import (
    Fornecedor, Cliente, Faturado, TipoDespesa, TipoReceita,
    ContaPagar, ParcelaPagar, ClassificacaoContaPagar,
    ContaReceber, ParcelaReceber, ClassificacaoContaReceber
)

TEST_DB_PATH = "test_fintrack.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

class BaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Remove any existing test db file
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except OSError:
                pass

        cls.engine = create_engine(TEST_DB_URL, echo=False)
        Base.metadata.create_all(bind=cls.engine)
        cls.TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        # Patch server SessionLocal and engine
        cls._orig_session_local = server.SessionLocal
        cls._orig_engine = server.engine
        server.SessionLocal = cls.TestSessionLocal
        server.engine = cls.engine

        server.app.config["TESTING"] = True
        cls.app = server.app
        cls.client = server.app.test_client()

    @classmethod
    def tearDownClass(cls):
        server.SessionLocal = cls._orig_session_local
        server.engine = cls._orig_engine
        cls.engine.dispose()
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except OSError:
                pass

    def setUp(self):
        # Clean all tables before each test
        db = self.TestSessionLocal()
        try:
            db.query(ClassificacaoContaPagar).delete()
            db.query(ClassificacaoContaReceber).delete()
            db.query(ParcelaPagar).delete()
            db.query(ParcelaReceber).delete()
            db.query(ContaPagar).delete()
            db.query(ContaReceber).delete()
            db.query(Fornecedor).delete()
            db.query(Cliente).delete()
            db.query(Faturado).delete()
            db.query(TipoDespesa).delete()
            db.query(TipoReceita).delete()
            db.commit()
        finally:
            db.close()

    def get_db(self):
        return self.TestSessionLocal()

    def seed_initial_data(self):
        db = self.get_db()
        try:
            # Seed tipos de despesa
            for cat in CATEGORIAS_DESPESA:
                for sub in cat["subcategorias"]:
                    td = TipoDespesa(categoria=cat["categoria"], descricao=sub, ativo=True)
                    db.add(td)
            # Seed tipos de receita
            for rec in TIPOS_RECEITA:
                tr = TipoReceita(descricao=rec, ativo=True)
                db.add(tr)
            
            # Seed um fornecedor, faturado e cliente
            f = Fornecedor(
                razao_social="IGUAÇU MÁQUINAS AGRÍCOLAS LTDA",
                nome_fantasia="Iguaçu Máquinas",
                cnpj="33.656.729/0023-85",
                ativo=True
            )
            fat = Faturado(
                nome_completo="CICLANO DA SILVA",
                cpf="999.999.999-99",
                ativo=True
            )
            cli = Cliente(
                razao_social="COOPERATIVA CENTRAL",
                cpf_cnpj="12.345.678/0001-90",
                ativo=True
            )
            db.add_all([f, fat, cli])
            db.commit()
        finally:
            db.close()
