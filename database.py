import os
import tempfile
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv(override=True)

# Detecta se está rodando em ambiente Vercel Serverless
IS_VERCEL = bool(os.getenv("VERCEL"))

default_db = (
    f"sqlite:///{os.path.join(tempfile.gettempdir(), 'fintrack.db')}"
    if IS_VERCEL
    else "sqlite:///fintrack.db"
)

DATABASE_URL = os.getenv("DATABASE_URL", default_db)

# Normaliza postgres:// para postgresql:// caso use URLs de bancos em nuvem (Neon/Supabase)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def _make_engine(url):
    is_postgres = url.startswith("postgresql")
    kwargs = {"echo": False, "pool_pre_ping": True}
    if is_postgres:
        kwargs["connect_args"] = {"connect_timeout": 5}
    return create_engine(url, **kwargs)

try:
    engine = _make_engine(DATABASE_URL)
    with engine.connect() as _:
        pass
except Exception:
    # Fallback seguro para SQLite no diretório temporário (caso Vercel) ou local
    if IS_VERCEL:
        temp_db_path = os.path.join(tempfile.gettempdir(), "fintrack.db")
        fallback_url = f"sqlite:///{temp_db_path}"
    else:
        fallback_url = "sqlite:///fintrack.db"
    engine = create_engine(fallback_url, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
