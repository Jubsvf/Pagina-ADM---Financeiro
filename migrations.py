"""
Módulo de migrações automáticas e compatíveis para evolução do esquema do banco de dados.
Preserva integralmente os dados existentes em SQLite ou PostgreSQL.
"""
from sqlalchemy import text
from database import engine

def run_migrations():
    """Aplica colunas necessárias caso ainda não existam, sem perda de dados."""
    columns_to_add = [
        ("fornecedores", "tipo", "VARCHAR(20) DEFAULT 'FORNECEDOR'"),
        ("clientes", "tipo", "VARCHAR(20) DEFAULT 'CLIENTE'"),
        ("faturados", "tipo", "VARCHAR(20) DEFAULT 'FATURADO'"),
        ("tipos_despesa", "tipo", "VARCHAR(20) DEFAULT 'DESPESA'"),
        ("tipos_receita", "tipo", "VARCHAR(20) DEFAULT 'RECEITA'"),
        ("contas_a_pagar", "tipo", "VARCHAR(20) DEFAULT 'APAGAR'"),
        ("contas_a_receber", "tipo", "VARCHAR(20) DEFAULT 'ARECEBER'"),
        ("parcelas_pagar", "identificacao", "VARCHAR(100)"),
        ("parcelas_receber", "identificacao", "VARCHAR(100)"),
    ]

    is_sqlite = engine.url.drivername.startswith("sqlite")

    with engine.connect() as conn:
        for table, col_name, col_def in columns_to_add:
            try:
                # Verificar se a coluna já existe
                if is_sqlite:
                    check_sql = text(f"PRAGMA table_info({table});")
                    cols = [row[1] for row in conn.execute(check_sql).fetchall()]
                    col_exists = col_name in cols
                else:
                    check_sql = text(
                        f"SELECT column_name FROM information_schema.columns "
                        f"WHERE table_name = '{table}' AND column_name = '{col_name}';"
                    )
                    col_exists = conn.execute(check_sql).fetchone() is not None

                if not col_exists:
                    print(f"[MIGRATION] Adicionando coluna '{col_name}' na tabela '{table}'...")
                    alter_sql = text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def};")
                    conn.execute(alter_sql)
                    conn.commit()
            except Exception as e:
                print(f"[MIGRATION] Aviso ao migrar {table}.{col_name}: {e}")

        # Preencher identificacoes vazias em parcelas existentes para garantir integridade e unicidade
        try:
            if is_sqlite:
                # Preencher parcelas_pagar vazias
                conn.execute(text(
                    "UPDATE parcelas_pagar SET identificacao = 'PARC-PAGAR-' || conta_pagar_id || '-' || numero_parcela || '-' || id "
                    "WHERE identificacao IS NULL OR identificacao = '';"
                ))
                # Preencher parcelas_receber vazias
                conn.execute(text(
                    "UPDATE parcelas_receber SET identificacao = 'PARC-RECEBER-' || conta_receber_id || '-' || numero_parcela || '-' || id "
                    "WHERE identificacao IS NULL OR identificacao = '';"
                ))
            else:
                conn.execute(text(
                    "UPDATE parcelas_pagar SET identificacao = 'PARC-PAGAR-' || conta_pagar_id || '-' || numero_parcela || '-' || id "
                    "WHERE identificacao IS NULL OR identificacao = '';"
                ))
                conn.execute(text(
                    "UPDATE parcelas_receber SET identificacao = 'PARC-RECEBER-' || conta_receber_id || '-' || numero_parcela || '-' || id "
                    "WHERE identificacao IS NULL OR identificacao = '';"
                ))
            conn.commit()
        except Exception as e:
            print(f"[MIGRATION] Aviso ao preencher identificacoes legadas: {e}")

if __name__ == "__main__":
    run_migrations()
