from database import engine, Base, SessionLocal
from models import TipoDespesa, TipoReceita, Fornecedor, Faturado, Cliente
from migrations import run_migrations

CATEGORIAS_DESPESA = [
    {
        "categoria": "INSUMOS AGRÍCOLAS",
        "subcategorias": [
            "Sementes",
            "Fertilizantes",
            "Defensivos Agrícolas",
            "Corretivos",
        ],
    },
    {
        "categoria": "MANUTENÇÃO E OPERAÇÃO",
        "subcategorias": [
            "Combustíveis e Lubrificantes",
            "Peças, Parafusos, Componentes Mecânicos",
            "Manutenção de Máquinas e Equipamentos",
            "Pneus, Filtros, Correias",
            "Ferramentas e Utensílios",
        ],
    },
    {
        "categoria": "RECURSOS HUMANOS",
        "subcategorias": [
            "Mão de Obra Temporária",
            "Salários e Encargos",
        ],
    },
    {
        "categoria": "SERVIÇOS OPERACIONAIS",
        "subcategorias": [
            "Frete e Transporte",
            "Colheita Terceirizada",
            "Secagem e Armazenagem",
            "Pulverização e Aplicação",
        ],
    },
    {
        "categoria": "INFRAESTRUTURA E UTILIDADES",
        "subcategorias": [
            "Energia Elétrica",
            "Arrendamento de Terras",
            "Construções e Reformas",
            "Materiais de Construção",
        ],
    },
    {
        "categoria": "ADMINISTRATIVAS",
        "subcategorias": [
            "Honorários (Contábeis, Advocatícios, Agronômicos)",
            "Despesas Bancárias e Financeiras",
        ],
    },
    {
        "categoria": "SEGUROS E PROTEÇÃO",
        "subcategorias": [
            "Seguro Agrícola",
            "Seguro de Ativos (Máquinas/Veículos)",
            "Seguro Prestamista",
        ],
    },
    {
        "categoria": "IMPOSTOS E TAXAS",
        "subcategorias": [
            "ITR, IPTU, IPVA, INCRA-CCIR",
        ],
    },
    {
        "categoria": "INVESTIMENTOS",
        "subcategorias": [
            "Aquisição de Máquinas e Implementos",
            "Aquisição de Veículos",
            "Aquisição de Imóveis",
            "Infraestrutura Rural",
        ],
    },
]

TIPOS_RECEITA = [
    "Venda de Grãos (Soja, Milho, Trigo)",
    "Venda de Algodão e Fibras",
    "Prestação de Serviços de Plantio e Colheita",
    "Prestação de Serviços de Frete e Transporte",
    "Arrendamento e Aluguel de Pastagens/Terras",
    "Rendimentos Financeiros e Aplicações",
    "Venda de Ativos e Equipamentos Usados",
    "Outras Receitas Operacionais",
]


def init_database():
    print("Criando tabelas no PostgreSQL/SQLite...")
    Base.metadata.create_all(bind=engine)
    run_migrations()
    print("Tabelas e migrações aplicadas com sucesso.")

    db = SessionLocal()
    try:
        # Seed Tipos de Despesa
        existing_td = db.query(TipoDespesa).count()
        if existing_td == 0:
            print("Populando Tipos de Despesa padrão...")
            for cat_item in CATEGORIAS_DESPESA:
                cat_name = cat_item["categoria"]
                for sub in cat_item["subcategorias"]:
                    td = TipoDespesa(categoria=cat_name, descricao=sub, ativo=True)
                    db.add(td)
            db.commit()
            print(f"Tipos de Despesa populados com sucesso.")

        # Seed Tipos de Receita
        existing_tr = db.query(TipoReceita).count()
        if existing_tr == 0:
            print("Populando Tipos de Receita padrão...")
            for rec_desc in TIPOS_RECEITA:
                tr = TipoReceita(descricao=rec_desc, ativo=True)
                db.add(tr)
            db.commit()
            print("Tipos de Receita populados com sucesso.")

        # Exemplo de fornecedor e faturado padrão para facilitar testes
        if db.query(Fornecedor).count() == 0:
            f = Fornecedor(
                razao_social="IGUAÇU MÁQUINAS AGRÍCOLAS LTDA",
                nome_fantasia="Iguaçu Máquinas",
                cnpj="33.656.729/0023-85",
                ativo=True,
            )
            db.add(f)
            db.commit()

        if db.query(Faturado).count() == 0:
            fat = Faturado(
                nome_completo="CICLANO DA SILVA",
                cpf="999.999.999-99",
                ativo=True,
            )
            db.add(fat)
            db.commit()

        if db.query(Cliente).count() == 0:
            cli = Cliente(
                razao_social="COOPERATIVA AGRÍCOLA CENTRAL",
                nome_fantasia="CoopCentral",
                cpf_cnpj="12.345.678/0001-90",
                ativo=True,
            )
            db.add(cli)
            db.commit()

        print("Seed finalizado com sucesso!")
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
