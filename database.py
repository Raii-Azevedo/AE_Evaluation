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
    """Initialize database tables"""
    conn = get_connection()
    cursor = conn.cursor()

    print("Criando/verificando tabelas no PostgreSQL...")

    # Tabela processos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processos (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        job_title TEXT,
        admission_category TEXT,
        area TEXT,
        data_inicio TIMESTAMP DEFAULT NOW()
    )
    """)

    # Tabela candidatos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidatos (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        email TEXT UNIQUE,
        linkedin TEXT,
        greenhouse_id TEXT,
        pbix_file TEXT,
        optional_file TEXT,
        gh_atualizada BOOLEAN DEFAULT FALSE,
        timestamp TIMESTAMP,
        data_importacao TIMESTAMP DEFAULT NOW()
    )
    """)

    # Tabela processos_candidatos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processos_candidatos (
        id SERIAL PRIMARY KEY,
        processo_id INTEGER REFERENCES processos(id) ON DELETE CASCADE,
        candidato_id INTEGER REFERENCES candidatos(id) ON DELETE CASCADE,
        data_vinculo TIMESTAMP DEFAULT NOW(),
        UNIQUE(processo_id, candidato_id)
    )
    """)

    # Tabela avaliacoes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS avaliacoes (
        id SERIAL PRIMARY KEY,
        processo_id INTEGER REFERENCES processos(id) ON DELETE CASCADE,
        candidato_id INTEGER REFERENCES candidatos(id) ON DELETE CASCADE,
        nota_final NUMERIC,
        avaliador TEXT,
        comentario_final TEXT,
        priorizacao TEXT,
        data TIMESTAMP DEFAULT NOW()
    )
    """)

    # Tabela avaliacoes_criterios
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

    # Tabela allowed_emails
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS allowed_emails (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        role TEXT DEFAULT 'user',
        added_by TEXT,
        added_at TIMESTAMP DEFAULT NOW()
    )
    """)

    # Tabela importacoes_sheets
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


# ===== FUNÇÕES DE PROCESSOS =====

def get_ou_criar_processo(nome_processo, job_title, admission_category):
    """Obtém ou cria um processo baseado no Job Title + Admission Category"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Buscar processo existente
        cursor.execute("""
            SELECT id FROM processos 
            WHERE job_title = %s AND admission_category = %s
        """, (job_title, admission_category))
        
        result = cursor.fetchone()
        
        if result:
            processo_id = result[0]
        else:
            # Criar novo processo
            cursor.execute("""
                INSERT INTO processos (nome, job_title, admission_category)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (nome_processo, job_title, admission_category))
            
            processo_id = cursor.fetchone()[0]
            conn.commit()
        
        cursor.close()
        return processo_id
        
    except Exception as e:
        print(f"Erro em get_ou_criar_processo: {e}")
        return None
    finally:
        if conn:
            return_connection(conn)


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
        print(f"Erro ao buscar processos: {e}")
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
            SELECT nome, job_title, admission_category 
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


def get_stats_processo(processo_id):
    """Get statistics for a processo"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT c.id) as total_candidatos,
                COUNT(a.id) as total_avaliacoes,
                AVG(a.nota_final) as media_geral,
                SUM(CASE WHEN a.nota_final >= 8 THEN 1 ELSE 0 END) as aprovados,
                SUM(CASE WHEN c.gh_atualizada THEN 1 ELSE 0 END) as gh_atualizados
            FROM processos_candidatos pc
            JOIN candidatos c ON pc.candidato_id = c.id
            LEFT JOIN avaliacoes a ON c.id = a.candidato_id AND a.processo_id = %s
            WHERE pc.processo_id = %s
        """, (processo_id, processo_id))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar stats: {e}")
        return None
    finally:
        if conn:
            return_connection(conn)


# ===== FUNÇÕES DE CANDIDATOS =====

def importar_candidatos_sheets(dados_candidatos, processo_id, importado_por):
    """
    Importa candidatos do Google Sheets para o banco de dados
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        novos_candidatos = 0
        candidatos_atualizados = 0
        
        for candidato in dados_candidatos:
            # Extrair dados
            timestamp = candidato.get('timestamp')
            email = candidato.get('email', '').strip()
            nome = candidato.get('nome', '').strip()
            linkedin = candidato.get('linkedin', '').strip()
            greenhouse_id = candidato.get('greenhouse_id', '').strip()
            pbix_file = candidato.get('pbix_file', '').strip()
            optional_file = candidato.get('optional_file', '').strip()
            
            if not email:
                continue
            
            # Verificar se o candidato já existe
            cursor.execute("SELECT id FROM candidatos WHERE email = %s", (email,))
            existe = cursor.fetchone()
            
            if not existe:
                # Inserir novo candidato
                cursor.execute("""
                    INSERT INTO candidatos 
                    (nome, email, linkedin, greenhouse_id, pbix_file, optional_file, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (nome, email, linkedin, greenhouse_id, pbix_file, optional_file, timestamp))
                candidato_id = cursor.fetchone()[0]
                novos_candidatos += 1
            else:
                # Atualizar dados do candidato existente
                candidato_id = existe[0]
                cursor.execute("""
                    UPDATE candidatos 
                    SET nome = %s, linkedin = %s, greenhouse_id = %s,
                        pbix_file = %s, optional_file = %s, timestamp = %s
                    WHERE id = %s
                """, (nome, linkedin, greenhouse_id, pbix_file, optional_file, timestamp, candidato_id))
                candidatos_atualizados += 1
            
            # Vincular candidato ao processo
            cursor.execute("""
                INSERT INTO processos_candidatos (processo_id, candidato_id)
                VALUES (%s, %s)
                ON CONFLICT (processo_id, candidato_id) DO NOTHING
            """, (processo_id, candidato_id))
        
        conn.commit()
        
        # Registrar importação
        cursor.execute("""
            INSERT INTO importacoes_sheets 
            (total_linhas_processadas, novos_candidatos, candidatos_atualizados, status, importado_por)
            VALUES (%s, %s, %s, %s, %s)
        """, (len(dados_candidatos), novos_candidatos, candidatos_atualizados, 'sucesso', importado_por))
        conn.commit()
        
        cursor.close()
        
        return {
            'sucesso': True,
            'novos': novos_candidatos,
            'atualizados': candidatos_atualizados
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Erro ao importar candidatos: {e}")
        return {
            'sucesso': False,
            'erro': str(e)
        }
    finally:
        if conn:
            return_connection(conn)


def get_candidatos_processo_completo(processo_id):
    """Busca candidatos de um processo com todas as informações"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                c.id, 
                c.nome, 
                c.email,
                c.linkedin,
                c.greenhouse_id,
                c.gh_atualizada,
                c.pbix_file,
                c.optional_file,
                c.timestamp as data_entrada,
                COUNT(a.id) as total_avaliacoes,
                MAX(a.id) as ultima_avaliacao_id
            FROM processos_candidatos pc
            JOIN candidatos c ON pc.candidato_id = c.id
            LEFT JOIN avaliacoes a ON c.id = a.candidato_id AND a.processo_id = %s
            WHERE pc.processo_id = %s
            GROUP BY c.id
            ORDER BY c.nome
        """, (processo_id, processo_id))
        
        candidatos = cursor.fetchall()
        cursor.close()
        return candidatos
    except Exception as e:
        print(f"Erro ao buscar candidatos: {e}")
        return []
    finally:
        if conn:
            return_connection(conn)


def get_candidato_info(candidato_id):
    """Busca informações de um candidato específico"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nome, email, linkedin, greenhouse_id, pbix_file, optional_file 
            FROM candidatos WHERE id = %s
        """, (candidato_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar candidato: {e}")
        return None
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


# ===== FUNÇÕES DE AVALIAÇÕES =====

def get_ultima_avaliacao_completa(processo_id, candidato_id):
    """Busca a última avaliação completa"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nota_final, id, avaliador, comentario_final, data, priorizacao
            FROM avaliacoes 
            WHERE processo_id = %s AND candidato_id = %s 
            ORDER BY data DESC LIMIT 1
        """, (processo_id, candidato_id))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar avaliação: {e}")
        return None
    finally:
        if conn:
            return_connection(conn)


def salvar_avaliacao(processo_id, candidato_id, nota_final, avaliador, comentario, priorizacao):
    """Salva uma nova avaliação no banco (apenas cabeçalho, sem critérios)"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO avaliacoes 
            (processo_id, candidato_id, nota_final, avaliador, comentario_final, priorizacao, data)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (processo_id, candidato_id, nota_final, avaliador, comentario, priorizacao, datetime.now()))
        
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
    """Salva um critério de avaliação"""
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


def get_avaliacao_info_completa(avaliacao_id):
    """Get avaliação info with all fields"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.nota_final, a.avaliador, a.comentario_final, a.data, 
                   a.priorizacao, c.nome, c.email, c.greenhouse_id, p.nome
            FROM avaliacoes a
            JOIN candidatos c ON a.candidato_id = c.id
            JOIN processos p ON a.processo_id = p.id
            WHERE a.id = %s
        """, (avaliacao_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar avaliação: {e}")
        return None
    finally:
        if conn:
            return_connection(conn)


def get_avaliacao_criterios(avaliacao_id):
    """Get criteria for an evaluation"""
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
                (SELECT COUNT(*) FROM avaliacoes) as total_avaliacoes,
                (SELECT COUNT(*) FROM candidatos WHERE gh_atualizada = true) as gh_atualizados,
                (SELECT COUNT(*) FROM allowed_emails) as total_usuarios
        """)
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar estatísticas: {e}")
        return (0, 0, 0, 0, 0)
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
                a.data,
                p.nome as processo,
                c.nome as candidato,
                a.nota_final,
                a.avaliador,
                c.gh_atualizada
            FROM avaliacoes a
            JOIN processos p ON a.processo_id = p.id
            JOIN candidatos c ON a.candidato_id = c.id
            ORDER BY a.data DESC
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