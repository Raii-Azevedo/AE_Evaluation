import os
import psycopg2


def get_connection():
    return psycopg2.connect(
        os.environ["DATABASE_URL"]
    )


def init_db():
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

    # RESET: Dropar e recriar tabela allowed_emails com estrutura limpa
    print("Recriando tabela allowed_emails...")
    
    try:
        cursor.execute("DROP TABLE IF EXISTS allowed_emails CASCADE")
        conn.commit()
        print("Tabela antiga removida.")
    except Exception as e:
        conn.rollback()
        print(f"Erro ao dropar tabela: {e}")
    
    # Criar tabela allowed_emails com estrutura nova e limpa
    cursor.execute("""
    CREATE TABLE allowed_emails (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'user', 'viewer')),
        added_by TEXT,
        added_at TIMESTAMP DEFAULT NOW()
    )
    """)
    conn.commit()
    print("Tabela allowed_emails criada com sucesso.")

    # Inserir apenas admin padrão
    cursor.execute("""
    INSERT INTO allowed_emails (email, role, added_by)
    VALUES ('admin@artefact.com', 'admin', 'system')
    """)
    conn.commit()
    print("Admin padrão criado: admin@artefact.com")

    cursor.close()
    conn.close()