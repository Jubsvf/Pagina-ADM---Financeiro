import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Date,
    DateTime,
    Numeric,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from database import Base


class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id = Column(Integer, primary_key=True, index=True)
    razao_social = Column(String(255), nullable=False)
    nome_fantasia = Column(String(255), nullable=True)
    cnpj = Column(String(20), nullable=False, unique=True, index=True)
    tipo = Column(String(20), default="FORNECEDOR", nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.datetime.utcnow)
    atualizado_em = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    contas_a_pagar = relationship("ContaPagar", back_populates="fornecedor")

    def to_dict(self):
        return {
            "id": self.id,
            "razao_social": self.razao_social,
            "nome_fantasia": self.nome_fantasia or "",
            "cnpj": self.cnpj,
            "tipo": self.tipo or "FORNECEDOR",
            "ativo": self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    razao_social = Column(String(255), nullable=False)
    nome_fantasia = Column(String(255), nullable=True)
    cpf_cnpj = Column(String(20), nullable=False, unique=True, index=True)
    tipo = Column(String(20), default="CLIENTE", nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.datetime.utcnow)
    atualizado_em = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    contas_a_receber = relationship("ContaReceber", back_populates="cliente")

    def to_dict(self):
        return {
            "id": self.id,
            "razao_social": self.razao_social,
            "nome_fantasia": self.nome_fantasia or "",
            "cpf_cnpj": self.cpf_cnpj,
            "tipo": self.tipo or "CLIENTE",
            "ativo": self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }


class Faturado(Base):
    __tablename__ = "faturados"

    id = Column(Integer, primary_key=True, index=True)
    nome_completo = Column(String(255), nullable=False)
    cpf = Column(String(20), nullable=False, unique=True, index=True)
    tipo = Column(String(20), default="FATURADO", nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.datetime.utcnow)
    atualizado_em = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    contas_a_pagar = relationship("ContaPagar", back_populates="faturado")
    contas_a_receber = relationship("ContaReceber", back_populates="faturado")

    @property
    def razao_social(self):
        return self.nome_completo

    def to_dict(self):
        return {
            "id": self.id,
            "nome_completo": self.nome_completo,
            "razao_social": self.nome_completo,
            "cpf": self.cpf,
            "tipo": self.tipo or "FATURADO",
            "ativo": self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }


class TipoReceita(Base):
    __tablename__ = "tipos_receita"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String(255), nullable=False, unique=True)
    tipo = Column(String(20), default="RECEITA", nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.datetime.utcnow)
    atualizado_em = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    classificacoes = relationship(
        "ClassificacaoContaReceber", back_populates="tipo_receita"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "descricao": self.descricao,
            "tipo": self.tipo or "RECEITA",
            "ativo": self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }


class TipoDespesa(Base):
    __tablename__ = "tipos_despesa"

    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(String(100), nullable=False, index=True)
    descricao = Column(String(255), nullable=False)
    tipo = Column(String(20), default="DESPESA", nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.datetime.utcnow)
    atualizado_em = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    classificacoes = relationship(
        "ClassificacaoContaPagar", back_populates="tipo_despesa"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "categoria": self.categoria,
            "descricao": self.descricao,
            "tipo": self.tipo or "DESPESA",
            "ativo": self.ativo,
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }


class ContaPagar(Base):
    __tablename__ = "contas_a_pagar"

    id = Column(Integer, primary_key=True, index=True)
    fornecedor_id = Column(Integer, ForeignKey("fornecedores.id"), nullable=False)
    faturado_id = Column(Integer, ForeignKey("faturados.id"), nullable=False)
    numero_nf = Column(String(50), nullable=False)
    data_emissao = Column(Date, nullable=False)
    descricao_produtos = Column(Text, nullable=True)
    valor_total = Column(Numeric(15, 2), nullable=False)
    quantidade_parcelas = Column(Integer, default=1, nullable=False)
    tipo = Column(String(20), default="APAGAR", nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.datetime.utcnow)
    atualizado_em = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    fornecedor = relationship("Fornecedor", back_populates="contas_a_pagar")
    faturado = relationship("Faturado", back_populates="contas_a_pagar")
    parcelas = relationship(
        "ParcelaPagar", back_populates="conta_pagar", cascade="all, delete-orphan"
    )
    classificacoes = relationship(
        "ClassificacaoContaPagar",
        back_populates="conta_pagar",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "fornecedor_id": self.fornecedor_id,
            "fornecedor": self.fornecedor.to_dict() if self.fornecedor else None,
            "faturado_id": self.faturado_id,
            "faturado": self.faturado.to_dict() if self.faturado else None,
            "numero_nf": self.numero_nf,
            "data_emissao": self.data_emissao.isoformat() if self.data_emissao else None,
            "descricao_produtos": self.descricao_produtos or "",
            "valor_total": float(self.valor_total) if self.valor_total is not None else 0.0,
            "quantidade_parcelas": self.quantidade_parcelas,
            "tipo": self.tipo or "APAGAR",
            "ativo": self.ativo,
            "parcelas": [p.to_dict() for p in self.parcelas],
            "classificacoes": [c.to_dict() for c in self.classificacoes],
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }


class ParcelaPagar(Base):
    __tablename__ = "parcelas_pagar"

    id = Column(Integer, primary_key=True, index=True)
    conta_pagar_id = Column(Integer, ForeignKey("contas_a_pagar.id"), nullable=False)
    numero_parcela = Column(Integer, default=1, nullable=False)
    identificacao = Column(String(100), unique=True, index=True, nullable=False)
    data_vencimento = Column(Date, nullable=False)
    valor = Column(Numeric(15, 2), nullable=False)
    status = Column(String(30), default="PENDENTE", nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)

    conta_pagar = relationship("ContaPagar", back_populates="parcelas")

    def to_dict(self):
        return {
            "id": self.id,
            "conta_pagar_id": self.conta_pagar_id,
            "numero_parcela": self.numero_parcela,
            "identificacao": self.identificacao,
            "data_vencimento": self.data_vencimento.isoformat() if self.data_vencimento else None,
            "valor": float(self.valor) if self.valor is not None else 0.0,
            "status": self.status,
            "ativo": self.ativo,
        }


class ClassificacaoContaPagar(Base):
    __tablename__ = "classificacoes_conta_pagar"

    id = Column(Integer, primary_key=True, index=True)
    conta_pagar_id = Column(Integer, ForeignKey("contas_a_pagar.id"), nullable=False)
    tipo_despesa_id = Column(Integer, ForeignKey("tipos_despesa.id"), nullable=False)
    percentual = Column(Numeric(5, 2), default=100.0, nullable=True)
    valor = Column(Numeric(15, 2), nullable=True)

    conta_pagar = relationship("ContaPagar", back_populates="classificacoes")
    tipo_despesa = relationship("TipoDespesa", back_populates="classificacoes")

    def to_dict(self):
        return {
            "id": self.id,
            "conta_pagar_id": self.conta_pagar_id,
            "tipo_despesa_id": self.tipo_despesa_id,
            "tipo_despesa": self.tipo_despesa.to_dict() if self.tipo_despesa else None,
            "percentual": float(self.percentual) if self.percentual is not None else 100.0,
            "valor": float(self.valor) if self.valor is not None else None,
        }


class ContaReceber(Base):
    __tablename__ = "contas_a_receber"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    faturado_id = Column(Integer, ForeignKey("faturados.id"), nullable=False)
    numero_documento = Column(String(50), nullable=False)
    data_emissao = Column(Date, nullable=False)
    descricao = Column(Text, nullable=True)
    valor_total = Column(Numeric(15, 2), nullable=False)
    quantidade_parcelas = Column(Integer, default=1, nullable=False)
    tipo = Column(String(20), default="ARECEBER", nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime, default=datetime.datetime.utcnow)
    atualizado_em = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    cliente = relationship("Cliente", back_populates="contas_a_receber")
    faturado = relationship("Faturado", back_populates="contas_a_receber")
    parcelas = relationship(
        "ParcelaReceber", back_populates="conta_receber", cascade="all, delete-orphan"
    )
    classificacoes = relationship(
        "ClassificacaoContaReceber",
        back_populates="conta_receber",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "cliente_id": self.cliente_id,
            "cliente": self.cliente.to_dict() if self.cliente else None,
            "faturado_id": self.faturado_id,
            "faturado": self.faturado.to_dict() if self.faturado else None,
            "numero_documento": self.numero_documento,
            "data_emissao": self.data_emissao.isoformat() if self.data_emissao else None,
            "descricao": self.descricao or "",
            "valor_total": float(self.valor_total) if self.valor_total is not None else 0.0,
            "quantidade_parcelas": self.quantidade_parcelas,
            "tipo": self.tipo or "ARECEBER",
            "ativo": self.ativo,
            "parcelas": [p.to_dict() for p in self.parcelas],
            "classificacoes": [c.to_dict() for c in self.classificacoes],
            "criado_em": self.criado_em.isoformat() if self.criado_em else None,
            "atualizado_em": self.atualizado_em.isoformat() if self.atualizado_em else None,
        }


class ParcelaReceber(Base):
    __tablename__ = "parcelas_receber"

    id = Column(Integer, primary_key=True, index=True)
    conta_receber_id = Column(Integer, ForeignKey("contas_a_receber.id"), nullable=False)
    numero_parcela = Column(Integer, default=1, nullable=False)
    identificacao = Column(String(100), unique=True, index=True, nullable=False)
    data_vencimento = Column(Date, nullable=False)
    valor = Column(Numeric(15, 2), nullable=False)
    status = Column(String(30), default="PENDENTE", nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)

    conta_receber = relationship("ContaReceber", back_populates="parcelas")

    def to_dict(self):
        return {
            "id": self.id,
            "conta_receber_id": self.conta_receber_id,
            "numero_parcela": self.numero_parcela,
            "identificacao": self.identificacao,
            "data_vencimento": self.data_vencimento.isoformat() if self.data_vencimento else None,
            "valor": float(self.valor) if self.valor is not None else 0.0,
            "status": self.status,
            "ativo": self.ativo,
        }


class ClassificacaoContaReceber(Base):
    __tablename__ = "classificacoes_conta_receber"

    id = Column(Integer, primary_key=True, index=True)
    conta_receber_id = Column(Integer, ForeignKey("contas_a_receber.id"), nullable=False)
    tipo_receita_id = Column(Integer, ForeignKey("tipos_receita.id"), nullable=False)
    percentual = Column(Numeric(5, 2), default=100.0, nullable=True)
    valor = Column(Numeric(15, 2), nullable=True)

    conta_receber = relationship("ContaReceber", back_populates="classificacoes")
    tipo_receita = relationship("TipoReceita", back_populates="classificacoes")

    def to_dict(self):
        return {
            "id": self.id,
            "conta_receber_id": self.conta_receber_id,
            "tipo_receita_id": self.tipo_receita_id,
            "tipo_receita": self.tipo_receita.to_dict() if self.tipo_receita else None,
            "percentual": float(self.percentual) if self.percentual is not None else 100.0,
            "valor": float(self.valor) if self.valor is not None else None,
        }

