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
    """Return a connection to the pool"""
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

    # Tabela candidatos (dados demográficos únicos por email)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidatos (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        email TEXT UNIQUE,
        linkedin TEXT,
        data_cadastro TIMESTAMP DEFAULT NOW()
    )
    """)

    # Adicionar colunas que podem estar faltando na tabela candidatos
    adicionar_coluna_se_nao_existe(cursor, 'candidatos', 'gh_atualizada', 'BOOLEAN', 'false')
    adicionar_coluna_se_nao_existe(cursor, 'candidatos', 'priorizacao', 'TEXT', "'Não priorizar'")

    # NOVA TABELA: Aplicações (cada vez que o candidato se inscreve)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS aplicacoes (
        id SERIAL PRIMARY KEY,
        candidato_id INTEGER REFERENCES candidatos(id) ON DELETE CASCADE,
        processo_id INTEGER REFERENCES processos(id) ON DELETE CASCADE,
        greenhouse_id TEXT,
        pbix_file TEXT,
        optional_file TEXT,
        timestamp_aplicacao TIMESTAMP,
        data_importacao TIMESTAMP DEFAULT NOW(),
        UNIQUE(candidato_id, processo_id, timestamp_aplicacao)
    )
    """)

    # Tabela avaliacoes (vinculada à aplicação específica)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS avaliacoes (
        id SERIAL PRIMARY KEY,
        aplicacao_id INTEGER REFERENCES aplicacoes(id) ON DELETE CASCADE,
        nota_final NUMERIC,
        avaliador TEXT,
        comentario_final TEXT,
        priorizacao TEXT,
        gh_atualizada BOOLEAN DEFAULT FALSE,
        data_avaliacao TIMESTAMP DEFAULT NOW()
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

    # Tabela importacoes_sheets (atualizada)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS importacoes_sheets (
        id SERIAL PRIMARY KEY,
        data_importacao TIMESTAMP DEFAULT NOW(),
        total_linhas_processadas INTEGER,
        novos_candidatos INTEGER,
        novas_aplicacoes INTEGER,
        candidatos_ignorados INTEGER,
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
    print("✅ Banco de dados inicializado com sucesso!")


# ===== FUNÇÕES DE PROCESSOS =====

def get_ou_criar_processo(nome_processo, job_title, admission_category):
    """Obtém ou cria um processo baseado no Job Title + Admission Category"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id FROM processos 
            WHERE job_title = %s AND admission_category = %s
        """, (job_title, admission_category))
        
        result = cursor.fetchone()
        
        if result:
            processo_id = result[0]
        else:
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


# ===== FUNÇÕES DE IMPORTAÇÃO (APENAS 2026 E PRIORIZAÇÃO EM BRANCO) =====

def importar_candidatos_sheets(dados_candidatos, processo_id, importado_por):
    """
    Importa APENAS candidatos com:
    - Timestamp em 2026
    - Priorização em branco (não avaliados)
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        novos_candidatos = 0
        novas_aplicacoes = 0
        candidatos_ignorados = 0
        
        for candidato in dados_candidatos:
            email = candidato.get('email', '').strip()
            if not email:
                continue
            
            timestamp_aplicacao = candidato.get('timestamp')
            priorizacao_sheets = candidato.get('priorizacao', '').strip()
            
            # REGRA 1: Verificar se é de 2026
            ano_aplicacao = None
            if timestamp_aplicacao:
                try:
                    if isinstance(timestamp_aplicacao, str):
                        # Formato: "21/01/2026 20:08:01"
                        partes = timestamp_aplicacao.split('/')
                        if len(partes) >= 3:
                            ano_aplicacao = int(partes[2].split(' ')[0])
                    elif isinstance(timestamp_aplicacao, datetime):
                        ano_aplicacao = timestamp_aplicacao.year
                except:
                    pass
            
            # Se não for 2026, ignora
            if ano_aplicacao != 2026:
                candidatos_ignorados += 1
                continue
            
            # REGRA 2: Se já tem priorização preenchida, está avaliado - IGNORA
            if priorizacao_sheets and priorizacao_sheets not in ['', 'Não priorizar']:
                candidatos_ignorados += 1
                continue
            
            # REGRA 3: É de 2026 e não tem priorização -> IMPORTAR
            greenhouse_id = candidato.get('greenhouse_id', '').strip()
            pbix_file = candidato.get('pbix_file', '').strip()
            optional_file = candidato.get('optional_file', '').strip()
            linkedin = candidato.get('linkedin', '').strip()
            nome = candidato.get('nome', '').strip()
            
            # Buscar ou criar candidato (dados demográficos)
            cursor.execute("SELECT id FROM candidatos WHERE email = %s", (email,))
            existe = cursor.fetchone()
            
            if not existe:
                cursor.execute("""
                    INSERT INTO candidatos (nome, email, linkedin)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (nome, email, linkedin))
                candidato_id = cursor.fetchone()[0]
                novos_candidatos += 1
            else:
                candidato_id = existe[0]
                # Atualizar dados demográficos
                cursor.execute("""
                    UPDATE candidatos 
                    SET nome = %s, linkedin = %s
                    WHERE id = %s
                """, (nome, linkedin, candidato_id))
            
            # Verificar se já existe aplicação para este candidato em 2026
            cursor.execute("""
                SELECT id FROM aplicacoes 
                WHERE candidato_id = %s AND processo_id = %s 
                AND EXTRACT(YEAR FROM timestamp_aplicacao) = 2026
            """, (candidato_id, processo_id))
            
            aplicacao_existente = cursor.fetchone()
            
            if not aplicacao_existente:
                # Nova aplicação para 2026
                cursor.execute("""
                    INSERT INTO aplicacoes 
                    (candidato_id, processo_id, greenhouse_id, pbix_file, optional_file, timestamp_aplicacao)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (candidato_id, processo_id, greenhouse_id, pbix_file, optional_file, timestamp_aplicacao))
                novas_aplicacoes += 1
            else:
                # Atualizar dados da aplicação existente
                cursor.execute("""
                    UPDATE aplicacoes 
                    SET greenhouse_id = %s, pbix_file = %s, optional_file = %s
                    WHERE id = %s
                """, (greenhouse_id, pbix_file, optional_file, aplicacao_existente[0]))
        
        conn.commit()
        
        # Registrar importação
        cursor.execute("""
            INSERT INTO importacoes_sheets 
            (total_linhas_processadas, novos_candidatos, novas_aplicacoes, 
             candidatos_ignorados, status, importado_por)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (len(dados_candidatos), novos_candidatos, novas_aplicacoes, 
              candidatos_ignorados, 'sucesso', importado_por))
        conn.commit()
        
        cursor.close()
        
        return {
            'sucesso': True,
            'novos_candidatos': novos_candidatos,
            'novas_aplicacoes': novas_aplicacoes,
            'candidatos_ignorados': candidatos_ignorados,
            'total_processados': len(dados_candidatos)
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


# ===== FUNÇÕES DE APLICAÇÕES =====

def get_aplicacoes_pendentes_2026(processo_id):
    """
    Busca aplicações pendentes de avaliação que são:
    - De 2026
    - Sem avaliação
    """
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
            WHERE a.processo_id = %s 
                AND av.id IS NULL
                AND EXTRACT(YEAR FROM a.timestamp_aplicacao) = 2026
            ORDER BY a.timestamp_aplicacao DESC
        """, (processo_id,))
        
        result = cursor.fetchall()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar aplicações pendentes: {e}")
        return []
    finally:
        if conn:
            return_connection(conn)


def get_aplicacoes_avaliadas_2026(processo_id):
    """
    Busca aplicações já avaliadas em 2026
    """
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
                AND EXTRACT(YEAR FROM a.timestamp_aplicacao) = 2026
            ORDER BY av.data_avaliacao DESC
        """, (processo_id,))
        
        result = cursor.fetchall()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar aplicações avaliadas: {e}")
        return []
    finally:
        if conn:
            return_connection(conn)


def get_stats_2026(processo_id):
    """
    Estatísticas específicas para 2026
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN av.id IS NULL THEN 1 END) as pendentes,
                COUNT(CASE WHEN av.id IS NOT NULL THEN 1 END) as avaliados,
                COALESCE(AVG(CASE WHEN av.id IS NOT NULL THEN av.nota_final END), 0) as media_avaliados,
                SUM(CASE WHEN av.priorizacao = 'Prioridade 1' THEN 1 ELSE 0 END) as prioridade_1,
                SUM(CASE WHEN av.priorizacao = 'Prioridade 2' THEN 1 ELSE 0 END) as prioridade_2,
                SUM(CASE WHEN av.priorizacao = 'Prioridade 3' THEN 1 ELSE 0 END) as prioridade_3,
                SUM(CASE WHEN av.gh_atualizada = true THEN 1 ELSE 0 END) as gh_atualizados
            FROM aplicacoes a
            LEFT JOIN avaliacoes av ON a.id = av.aplicacao_id
            WHERE a.processo_id = %s 
                AND EXTRACT(YEAR FROM a.timestamp_aplicacao) = 2026
        """, (processo_id,))
        
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        print(f"Erro ao buscar stats 2026: {e}")
        return (0, 0, 0, 0, 0, 0, 0)
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

def salvar_avaliacao(aplicacao_id, nota_final, avaliador, comentario, priorizacao, gh_atualizada=False):
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


def get_avaliacao_completa(avaliacao_id):
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
                   p.nome as processo_nome
            FROM avaliacoes av
            JOIN aplicacoes a ON av.aplicacao_id = a.id
            JOIN candidatos c ON a.candidato_id = c.id
            JOIN processos p ON a.processo_id = p.id
            WHERE av.id = %s
        """, (avaliacao_id,))
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
    """Busca os critérios de uma avaliação"""
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
                (SELECT COUNT(*) FROM aplicacoes WHERE EXTRACT(YEAR FROM timestamp_aplicacao) = 2026) as total_aplicacoes_2026,
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