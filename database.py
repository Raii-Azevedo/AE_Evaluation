import os
import psycopg2
from psycopg2 import pool
import streamlit as st

# Connection pool for better performance
_connection_pool = None

def get_connection_pool():
    """Get or create a connection pool (singleton pattern)"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = psycopg2.pool.SimpleConnectionPool(
            1,  # minconn
            10,  # maxconn
            os.environ["DATABASE_URL"]
        )
    return _connection_pool

def get_connection():
    """Get a connection from the pool"""
    pool = get_connection_pool()
    return pool.getconn()

def return_connection(conn):
    """Return a connection to the pool"""
    pool = get_connection_pool()
    pool.putconn(conn)


def init_db():
    """Initialize database tables - cached to avoid repeated calls"""
    conn = get_connection()
    cursor = conn.cursor()

    print("Criando/verificando tabelas no PostgreSQL...")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processos (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        area TEXT,
        tipo TEXT,
        senioridade TEXT,
        status TEXT,
        local TEXT,
        data_inicio TIMESTAMP DEFAULT NOW()
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidatos (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        email TEXT UNIQUE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processos_candidatos (
        id SERIAL PRIMARY KEY,
        processo_id INTEGER REFERENCES processos(id) ON DELETE CASCADE,
        candidato_id INTEGER REFERENCES candidatos(id) ON DELETE CASCADE,
        data_vinculo TIMESTAMP DEFAULT NOW(),
        UNIQUE(processo_id, candidato_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS avaliacoes (
        id SERIAL PRIMARY KEY,
        processo_id INTEGER REFERENCES processos(id) ON DELETE CASCADE,
        candidato_id INTEGER REFERENCES candidatos(id) ON DELETE CASCADE,
        nota_final NUMERIC,
        avaliador TEXT,
        comentario_final TEXT,
        data TIMESTAMP DEFAULT NOW()
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS avaliacoes_criterios (
        id SERIAL PRIMARY KEY,
        avaliacao_id INTEGER REFERENCES avaliacoes(id) ON DELETE CASCADE,
        bloco TEXT,
        criterio TEXT,
        nota NUMERIC,
        justificativa TEXT
    )
    """)

    # Criar tabela allowed_emails se não existir
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS allowed_emails (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        role TEXT DEFAULT 'user',
        added_by TEXT,
        added_at TIMESTAMP DEFAULT NOW()
    )
    """)
    conn.commit()

    # Inserir admin padrão se não existir (não trunca mais)
    try:
        cursor.execute("""
        INSERT INTO allowed_emails (email, role, added_by)
        VALUES ('admin@artefact.com', 'admin', 'system')
        ON CONFLICT (email) DO UPDATE SET role = 'admin'
        """)
        conn.commit()
        print("Admin padrão garantido: admin@artefact.com")
    except Exception as e:
        conn.rollback()
        print(f"Erro ao criar admin: {e}")

    cursor.close()
    return_connection(conn)