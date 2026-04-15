import os
import psycopg2
from psycopg2 import pool
import streamlit as st
from datetime import datetime

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
    """Return a connection to the pool, ensuring it's in a clean state"""
    try:
        conn.rollback()  # Garante que não há transação pendente/abortada
    except Exception:
        pass
    pool = get_connection_pool()
    pool.putconn(conn)


def adicionar_coluna_se_nao_existe(cursor, tabela, coluna, tipo, valor_padrao=None):
    """Adiciona uma coluna se ela não existir na tabela"""
    try:
        cursor.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s AND column_name = %s
        """, (tabela, coluna))
        
        if not cursor.fetchone():
            sql = f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}"
            if valor_padrao:
                sql += f" DEFAULT {valor_padrao}"
            cursor.execute(sql)
            print(f"Coluna {coluna} adicionada à tabela {tabela}")
            return True
        return False
    except Exception as e:
        print(f"Erro ao adicionar coluna {coluna}: {e}")
        return False


def init_db():
    """Initialize database tables with migrations"""
    conn = get_connection()
    cursor = conn.cursor()

    print("Criando/verificando tabelas no PostgreSQL...")

    # ===== TABELA PROCESSOS =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processos (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        area TEXT,
        senioridade TEXT,
        job_title TEXT,
        admission_category TEXT,
        local TEXT,
        status TEXT DEFAULT 'Aberto',
        data_inicio TIMESTAMP DEFAULT NOW()
    )
    """)
    
    # Adicionar colunas que podem estar faltando
    adicionar_coluna_se_nao_existe(cursor, 'processos', 'tipo', 'TEXT', "''")
    adicionar_coluna_se_nao_existe(cursor, 'processos', 'descricao', 'TEXT', "''")

    # ===== TABELA CANDIDATOS =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidatos (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        email TEXT UNIQUE,
        linkedin TEXT,
        greenhouse_id TEXT,
        pbix_file TEXT,
        optional_file TEXT,
        data_cadastro TIMESTAMP DEFAULT NOW()
    )
    """)
    
    # Adicionar colunas extras se necessário
    adicionar_coluna_se_nao_existe(cursor, 'candidatos', 'pais', 'TEXT', "''")
    adicionar_coluna_se_nao_existe(cursor, 'candidatos', 'nivel', 'TEXT', "''")

    # ===== TABELA APLICACOES =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS aplicacoes (
        id SERIAL PRIMARY KEY,
        candidato_id INTEGER REFERENCES candidatos(id) ON DELETE CASCADE,
        processo_id INTEGER REFERENCES processos(id) ON DELETE CASCADE,
        greenhouse_id TEXT,
        pbix_file TEXT,
        optional_file TEXT,
        timestamp_aplicacao TIMESTAMP DEFAULT NOW(),
        data_importacao TIMESTAMP DEFAULT NOW(),
        UNIQUE(candidato_id, processo_id)
    )
    """)

    # ===== TABELA AVALIACOES =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS avaliacoes (
        id SERIAL PRIMARY KEY,
        aplicacao_id INTEGER REFERENCES aplicacoes(id) ON DELETE CASCADE,
        nota_final NUMERIC,
        avaliador TEXT,
        comentario_final TEXT,
        priorizacao TEXT DEFAULT 'Não priorizar',
        gh_atualizada BOOLEAN DEFAULT FALSE,
        data_avaliacao TIMESTAMP DEFAULT NOW()
    )
    """)

    # Migração: adicionar colunas que podem estar faltando em bancos antigos
    adicionar_coluna_se_nao_existe(cursor, 'avaliacoes', 'aplicacao_id', 'INTEGER REFERENCES aplicacoes(id) ON DELETE CASCADE')
    adicionar_coluna_se_nao_existe(cursor, 'avaliacoes', 'priorizacao', 'TEXT', "'Não priorizar'")
    adicionar_coluna_se_nao_existe(cursor, 'avaliacoes', 'gh_atualizada', 'BOOLEAN', 'FALSE')
    adicionar_coluna_se_nao_existe(cursor, 'avaliacoes', 'data_avaliacao', 'TIMESTAMP')
    conn.commit()

    # ===== TABELA AVALIACOES_CRITERIOS =====
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

    # ===== TABELA ALLOWED_EMAILS =====
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

    # Inserir admin padrão
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
    print("✅ Banco de dados inicializado com sucesso!")


# ===== FUNÇÕES DE PROCESSOS =====

def get_processos_ativos():
    """Busca todos os processos"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nome, job_title, admission_category 
            FROM processos 
            ORDER BY nome
        """)
        processos = cursor.fetchall()
        cursor.close()
        return processos
    except Exception as e:
        st.warning(f"⚠️ Erro ao buscar processos: {e}")
        return []
    finally:
        if conn:
            return_connection(conn)


def get_processo_info(processo_id):
    """Get processo info by id"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nome, job_title, admission_category, status 
            FROM processos WHERE id = %s
        """, (processo_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar processo: {e}")
        return None
    finally:
        if conn:
            return_connection(conn)


def criar_processo(nome, area, senioridade, job_title, admission_category, local):
    """Cria um novo processo manualmente"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO processos (nome, area, senioridade, job_title, admission_category, local, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (nome, area, senioridade, job_title, admission_category, local, 'Aberto'))
        processo_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        return processo_id
    except Exception as e:
        print(f"Erro ao criar processo: {e}")
        return None
    finally:
        if conn:
            return_connection(conn)


# ===== FUNÇÕES DE CANDIDATOS =====

def adicionar_candidato_processo(processo_id, nome, email, linkedin, greenhouse_id, pbix_file, optional_file):
    """Adiciona ou atualiza um candidato em um processo manualmente"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        nome = (nome or "").strip()
        email = (email or "").strip().lower()
        linkedin = (linkedin or "").strip()
        greenhouse_id = (greenhouse_id or "").strip()
        pbix_file = (pbix_file or "").strip()
        optional_file = (optional_file or "").strip()

        if not nome or not email:
            return {"sucesso": False, "erro": "Nome e email são obrigatórios."}

        # Criar ou atualizar candidato pelo email
        cursor.execute("""
            INSERT INTO candidatos (nome, email, linkedin, greenhouse_id, pbix_file, optional_file)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET 
                nome = EXCLUDED.nome,
                linkedin = EXCLUDED.linkedin,
                greenhouse_id = EXCLUDED.greenhouse_id,
                pbix_file = EXCLUDED.pbix_file,
                optional_file = EXCLUDED.optional_file
            RETURNING id
        """, (nome, email, linkedin, greenhouse_id, pbix_file, optional_file))
        candidato_id = cursor.fetchone()[0]

        # Alguns bancos antigos não possuem UNIQUE(candidato_id, processo_id).
        # Então buscamos primeiro e atualizamos se já existir.
        cursor.execute("""
            SELECT id
            FROM aplicacoes
            WHERE candidato_id = %s AND processo_id = %s
            ORDER BY id
            LIMIT 1
        """, (candidato_id, processo_id))
        aplicacao_existente = cursor.fetchone()

        if aplicacao_existente:
            cursor.execute("""
                UPDATE aplicacoes
                SET greenhouse_id = %s,
                    pbix_file = %s,
                    optional_file = %s
                WHERE id = %s
                RETURNING id
            """, (greenhouse_id, pbix_file, optional_file, aplicacao_existente[0]))
            aplicacao_id = cursor.fetchone()[0]
            acao = "atualizado"
        else:
            cursor.execute("""
                INSERT INTO aplicacoes (candidato_id, processo_id, greenhouse_id, pbix_file, optional_file, timestamp_aplicacao)
                VALUES (%s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (candidato_id, processo_id, greenhouse_id, pbix_file, optional_file))
            aplicacao_id = cursor.fetchone()[0]
            acao = "adicionado"

        conn.commit()
        cursor.close()
        return {"sucesso": True, "aplicacao_id": aplicacao_id, "acao": acao}
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Erro ao adicionar candidato: {e}")
        return {"sucesso": False, "erro": str(e)}
    finally:
        if conn:
            return_connection(conn)


# ===== FUNÇÕES DE APLICAÇÕES =====

def get_aplicacoes_pendentes(processo_id):
    """Busca aplicações pendentes de avaliação"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                a.id as aplicacao_id,
                c.id as candidato_id,
                c.nome,
                c.email,
                c.linkedin,
                a.timestamp_aplicacao,
                a.greenhouse_id,
                a.pbix_file,
                a.optional_file
            FROM aplicacoes a
            JOIN candidatos c ON a.candidato_id = c.id
            LEFT JOIN avaliacoes av ON a.id = av.aplicacao_id
            WHERE a.processo_id = %s AND av.id IS NULL
            ORDER BY a.timestamp_aplicacao DESC
        """, (processo_id,))
        
        result = cursor.fetchall()
        cursor.close()
        return result
    except Exception as e:
        st.warning(f"⚠️ Erro ao buscar candidatos pendentes: {e}")
        return []
    finally:
        if conn:
            return_connection(conn)


def get_aplicacoes_avaliadas(processo_id):
    """Busca aplicações já avaliadas"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                a.id as aplicacao_id,
                c.id as candidato_id,
                c.nome,
                c.email,
                a.timestamp_aplicacao,
                av.nota_final,
                av.priorizacao,
                av.gh_atualizada,
                av.data_avaliacao,
                av.avaliador
            FROM aplicacoes a
            JOIN candidatos c ON a.candidato_id = c.id
            JOIN avaliacoes av ON a.id = av.aplicacao_id
            WHERE a.processo_id = %s
            ORDER BY av.data_avaliacao DESC
        """, (processo_id,))
        
        result = cursor.fetchall()
        cursor.close()
        return result
    except Exception as e:
        st.warning(f"⚠️ Erro ao buscar candidatos avaliados: {e}")
        return []
    finally:
        if conn:
            return_connection(conn)


def get_stats(processo_id):
    """Estatísticas do processo"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN av.id IS NULL THEN 1 END) as pendentes,
                COUNT(CASE WHEN av.id IS NOT NULL THEN 1 END) as avaliados,
                COALESCE(AVG(CASE WHEN av.id IS NOT NULL THEN av.nota_final END), 0) as media_avaliados,
                COUNT(CASE WHEN av.gh_atualizada = true THEN 1 END) as gh_atualizados
            FROM aplicacoes a
            LEFT JOIN avaliacoes av ON a.id = av.aplicacao_id
            WHERE a.processo_id = %s
        """, (processo_id,))
        
        result = cursor.fetchone()
        cursor.close()
        
        if result:
            return (result[0] or 0, result[1] or 0, result[2] or 0, result[3] or 0)
        return (0, 0, 0, 0)
    except Exception as e:
        st.warning(f"⚠️ Erro ao buscar estatísticas: {e}")
        return (0, 0, 0, 0)
    finally:
        if conn:
            return_connection(conn)


def get_aplicacao_info(aplicacao_id):
    """Busca informações de uma aplicação específica"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.id, c.id, c.nome, c.email, c.linkedin,
                   a.greenhouse_id, a.pbix_file, a.optional_file, a.timestamp_aplicacao
            FROM aplicacoes a
            JOIN candidatos c ON a.candidato_id = c.id
            WHERE a.id = %s
        """, (aplicacao_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar aplicação: {e}")
        return None
    finally:
        if conn:
            return_connection(conn)


# ===== FUNÇÕES DE AVALIAÇÕES =====

def salvar_avaliacao(aplicacao_id, nota_final, avaliador, comentario, priorizacao, gh_atualizada=True):
    """Salva uma nova avaliação para uma aplicação"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO avaliacoes 
            (aplicacao_id, nota_final, avaliador, comentario_final, priorizacao, gh_atualizada, data_avaliacao)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (aplicacao_id, nota_final, avaliador, comentario, priorizacao, gh_atualizada, datetime.now()))
        
        avaliacao_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        return avaliacao_id
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Erro ao salvar avaliação: {e}")
        return None
    finally:
        if conn:
            return_connection(conn)


def salvar_criterios_avaliacao(avaliacao_id, bloco, criterio, nota, justificativa):
    """Salva um critério/justificativa de avaliação"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO avaliacoes_criterios (avaliacao_id, bloco, criterio, nota, justificativa)
            VALUES (%s, %s, %s, %s, %s)
        """, (avaliacao_id, bloco, criterio, nota, justificativa))
        
        conn.commit()
        cursor.close()
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Erro ao salvar critério: {e}")
        return False
    finally:
        if conn:
            return_connection(conn)


def get_ultima_avaliacao_por_aplicacao(aplicacao_id):
    """Busca a última avaliação para uma aplicação"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, nota_final, avaliador, comentario_final, priorizacao, gh_atualizada, data_avaliacao
            FROM avaliacoes 
            WHERE aplicacao_id = %s 
            ORDER BY data_avaliacao DESC LIMIT 1
        """, (aplicacao_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar avaliação: {e}")
        return None
    finally:
        if conn:
            return_connection(conn)


def get_avaliacao_completa(aplicacao_id):
    """Busca avaliação completa com informações da aplicação e candidato"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT av.nota_final, av.avaliador, av.comentario_final, av.data_avaliacao, 
                   av.priorizacao, av.gh_atualizada,
                   c.nome, c.email, c.linkedin,
                   a.greenhouse_id, a.pbix_file, a.optional_file, a.timestamp_aplicacao,
                   p.nome as processo_nome,
                   av.id
            FROM avaliacoes av
            JOIN aplicacoes a ON av.aplicacao_id = a.id
            JOIN candidatos c ON a.candidato_id = c.id
            JOIN processos p ON a.processo_id = p.id
            WHERE av.aplicacao_id = %s
            ORDER BY av.data_avaliacao DESC
            LIMIT 1
        """, (aplicacao_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar avaliação completa: {e}")
        return None
    finally:
        if conn:
            return_connection(conn)


def get_criterios_avaliacao(avaliacao_id):
    """Busca os critérios/justificativas de uma avaliação"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT bloco, criterio, nota, justificativa 
            FROM avaliacoes_criterios 
            WHERE avaliacao_id = %s
            ORDER BY bloco, criterio
        """, (avaliacao_id,))
        result = cursor.fetchall()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar critérios: {e}")
        return []
    finally:
        if conn:
            return_connection(conn)


def atualizar_gh_status_aplicacao(aplicacao_id, gh_atualizada):
    """Atualiza o status Greenhouse de uma aplicação específica"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE avaliacoes 
            SET gh_atualizada = %s
            WHERE aplicacao_id = %s
        """, (gh_atualizada, aplicacao_id))
        
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Erro ao atualizar GH status: {e}")
        return False
    finally:
        if conn:
            return_connection(conn)


# ===== FUNÇÕES DE ESTATÍSTICAS =====

def get_estatisticas_gerais():
    """Busca estatísticas gerais do sistema"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM processos) as total_processos,
                (SELECT COUNT(*) FROM candidatos) as total_candidatos,
                (SELECT COUNT(*) FROM aplicacoes) as total_aplicacoes,
                (SELECT COUNT(*) FROM avaliacoes) as total_avaliacoes,
                (SELECT COUNT(*) FROM avaliacoes WHERE gh_atualizada = true) as gh_atualizados,
                (SELECT COUNT(*) FROM allowed_emails) as total_usuarios
        """)
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar estatísticas: {e}")
        return (0, 0, 0, 0, 0, 0)
    finally:
        if conn:
            return_connection(conn)


def get_avaliacoes_recentes(limite=10):
    """Busca avaliações recentes"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                av.data_avaliacao,
                p.nome as processo,
                c.nome as candidato,
                av.nota_final,
                av.avaliador,
                av.gh_atualizada
            FROM avaliacoes av
            JOIN aplicacoes a ON av.aplicacao_id = a.id
            JOIN processos p ON a.processo_id = p.id
            JOIN candidatos c ON a.candidato_id = c.id
            ORDER BY av.data_avaliacao DESC
            LIMIT %s
        """, (limite,))
        
        result = cursor.fetchall()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar avaliações recentes: {e}")
        return []
    finally:
        if conn:
            return_connection(conn)