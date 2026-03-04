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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS allowed_emails (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        role TEXT DEFAULT 'user',  -- 'admin', 'user', 'viewer'
        added_by TEXT,
        added_at TIMESTAMP DEFAULT NOW()
    )
    """)

    # Migrar dados existentes de is_admin para role
    cursor.execute("""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='allowed_emails' AND column_name='is_admin') THEN
            UPDATE allowed_emails SET role = CASE
                WHEN is_admin = TRUE THEN 'admin'
                ELSE 'user'
            END;
            ALTER TABLE allowed_emails DROP COLUMN IF EXISTS is_admin;
        END IF;
    END $$;
    """)

    # Inserir admin padrão se não existir
    cursor.execute("""
    INSERT INTO allowed_emails (email, role, added_by)
    VALUES ('admin@artefact.com', 'admin', 'system')
    ON CONFLICT (email) DO UPDATE SET role = 'admin'
    """)

    conn.commit()
    cursor.close()
    conn.close()