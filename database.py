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

    # Tabela candidatos atualizada com novos campos do Google Sheets
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidatos (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        email TEXT UNIQUE,
        email_application TEXT,  -- Email usado na candidatura (pode ser diferente)
        linkedin TEXT,           -- Perfil do LinkedIn
        greenhouse_id TEXT,      -- ID do Greenhouse (URL)
        pbix_file TEXT,          -- Link do arquivo PBIX
        optional_file TEXT,      -- Link do arquivo opcional
        status TEXT,             -- Status do candidato (da planilha)
        pais TEXT,               -- País do candidato
        nivel TEXT,              -- Nível do candidato
        priorizacao TEXT,        -- Priorização (Prioridade 1, Não priorize, etc)
        gh_atualizada BOOLEAN DEFAULT FALSE,  -- Se já foi atualizado no Greenhouse
        timestamp TIMESTAMP,     -- Data/hora de entrada no sistema (da planilha)
        data_importacao TIMESTAMP DEFAULT NOW()  -- Quando foi importado para o sistema
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

    # Tabela avaliacoes atualizada com os novos campos da avaliação técnica
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS avaliacoes (
        id SERIAL PRIMARY KEY,
        processo_id INTEGER REFERENCES processos(id) ON DELETE CASCADE,
        candidato_id INTEGER REFERENCES candidatos(id) ON DELETE CASCADE,
        nota_final NUMERIC,
        avaliador TEXT,
        comentario_final TEXT,
        -- Novos campos da avaliação técnica (do Google Sheets)
        treatment_part NUMERIC,   -- Nota da parte de Tratamento
        analytics_part NUMERIC,   -- Nota da parte de Analytics
        visual_part NUMERIC,      -- Nota da parte Visual
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

    # Criar tabela para controle de importação do Google Sheets
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS importacoes_sheets (
        id SERIAL PRIMARY KEY,
        data_importacao TIMESTAMP DEFAULT NOW(),
        total_linhas_processadas INTEGER,
        novos_candidatos INTEGER,
        candidatos_atualizados INTEGER,
        status TEXT,
        detalhes TEXT,
        importado_por TEXT
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


# ===== NOVAS FUNÇÕES PARA INTEGRAÇÃO COM GOOGLE SHEETS =====

def importar_candidatos_sheets(dados_sheets, processo_id, importado_por):
    """
    Importa candidatos do Google Sheets para o banco de dados
    
    Args:
        dados_sheets: Lista de dicionários com os dados da planilha
        processo_id: ID do processo ao qual os candidatos serão vinculados
        importado_por: Email do usuário que realizou a importação
    
    Returns:
        dict: Estatísticas da importação
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        novos_candidatos = 0
        candidatos_atualizados = 0
        
        for linha in dados_sheets:
            # Extrair dados relevantes
            timestamp = linha.get('Timestamp')
            email = linha.get('Email address', '').strip()
            nome = linha.get('Full name', '').strip()
            email_application = linha.get('Email used on application', '').strip()
            linkedin = linha.get('LinkedIn', '').strip()
            greenhouse_id = linha.get('Greenhouse ID', '').strip()
            pbix_file = linha.get('Pbix file', '').strip()
            optional_file = linha.get('Optional file', '').strip()
            status_sheets = linha.get('Status', '').strip()
            pais = linha.get('Pais', '').strip()
            nivel = linha.get('Nível', '').strip()
            priorizacao = linha.get('Priorização', '').strip()
            
            # Verificar se o candidato já existe
            cursor.execute("SELECT id FROM candidatos WHERE email = %s", (email,))
            existe = cursor.fetchone()
            
            if not existe:
                # Inserir novo candidato
                cursor.execute("""
                    INSERT INTO candidatos 
                    (nome, email, email_application, linkedin, greenhouse_id, pbix_file, 
                     optional_file, status, pais, nivel, priorizacao, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (nome, email, email_application, linkedin, greenhouse_id, pbix_file, 
                      optional_file, status_sheets, pais, nivel, priorizacao, timestamp))
                candidato_id = cursor.lastrowid
                novos_candidatos += 1
            else:
                # Atualizar dados do candidato existente
                candidato_id = existe[0]
                cursor.execute("""
                    UPDATE candidatos 
                    SET nome = %s, email_application = %s, linkedin = %s, greenhouse_id = %s,
                        pbix_file = %s, optional_file = %s, status = %s, pais = %s,
                        nivel = %s, priorizacao = %s, timestamp = %s
                    WHERE id = %s
                """, (nome, email_application, linkedin, greenhouse_id, pbix_file, 
                      optional_file, status_sheets, pais, nivel, priorizacao, timestamp, candidato_id))
                candidatos_atualizados += 1
            
            # Vincular candidato ao processo
            cursor.execute("""
                INSERT INTO processos_candidatos (processo_id, candidato_id)
                VALUES (%s, %s)
                ON CONFLICT (processo_id, candidato_id) DO NOTHING
            """, (processo_id, candidato_id))
        
        # Registrar a importação
        cursor.execute("""
            INSERT INTO importacoes_sheets 
            (total_linhas_processadas, novos_candidatos, candidatos_atualizados, status, importado_por)
            VALUES (%s, %s, %s, %s, %s)
        """, (len(dados_sheets), novos_candidatos, candidatos_atualizados, 'sucesso', importado_por))
        
        conn.commit()
        cursor.close()
        
        return {
            'sucesso': True,
            'total': len(dados_sheets),
            'novos': novos_candidatos,
            'atualizados': candidatos_atualizados
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        return {
            'sucesso': False,
            'erro': str(e)
        }
    finally:
        if conn:
            return_connection(conn)


def atualizar_gh_status(candidato_id, gh_atualizada):
    """Atualiza o status de movimentação no Greenhouse"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE candidatos 
            SET gh_atualizada = %s
            WHERE id = %s
        """, (gh_atualizada, candidato_id))
        
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Erro ao atualizar GH status: {e}")
        return False
    finally:
        if conn:
            return_connection(conn)


def get_candidatos_com_gh_status(processo_id):
    """Busca candidatos com informações de status do Greenhouse"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                c.id, 
                c.nome, 
                c.email,
                c.greenhouse_id,
                c.gh_atualizada,
                c.priorizacao,
                c.status as candidato_status,
                COUNT(a.id) as total_avaliacoes,
                MAX(a.nota_final) as ultima_nota
            FROM processos_candidatos pc
            JOIN candidatos c ON pc.candidato_id = c.id
            LEFT JOIN avaliacoes a
                ON c.id = a.candidato_id AND a.processo_id = %s
            WHERE pc.processo_id = %s
            GROUP BY c.id
            ORDER BY 
                CASE 
                    WHEN c.priorizacao = 'Prioridade 1' THEN 1
                    WHEN c.priorizacao = 'Prioridade 2' THEN 2
                    WHEN c.priorizacao = 'Prioridade 3' THEN 3
                    ELSE 4
                END,
                c.nome
        """, (processo_id, processo_id))
        
        candidatos = cursor.fetchall()
        cursor.close()
        return candidatos
    except Exception as e:
        st.error(f"Erro ao buscar candidatos: {str(e)}")
        return []
    finally:
        if conn:
            return_connection(conn)


def get_ultima_avaliacao_completa(processo_id, candidato_id):
    """Busca a última avaliação completa com todos os novos campos"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nota_final, id, avaliador, treatment_part, analytics_part, 
                   visual_part, comentario_final, data
            FROM avaliacoes 
            WHERE processo_id = %s AND candidato_id = %s 
            ORDER BY data DESC LIMIT 1
        """, (processo_id, candidato_id))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        return None
    finally:
        if conn:
            return_connection(conn)