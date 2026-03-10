# Sistema de gerenciamento de emails autorizados
# Agora usando banco de dados para armazenar emails permitidos
# Suporta 3 roles: admin, user, viewer

import streamlit as st

@st.cache_data(ttl=300)  # Cache for 5 minutes
def is_email_allowed(email):
    """
    Verifica se o email está autorizado a acessar o sistema.
    Apenas emails cadastrados no banco de dados têm acesso.
    """
    if not email:
        return False
    
    email = email.lower().strip()
    
    # Verifica se o email está na lista de permitidos no banco
    try:
        from database import get_connection, return_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM allowed_emails WHERE LOWER(email) = %s", (email,))
        result = cursor.fetchone()
        cursor.close()
        return_connection(conn)
        return result is not None
    except:
        return False

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_user_role(email):
    """
    Retorna o role do usuário: 'admin', 'user', 'viewer' ou None.
    """
    if not email:
        return None
    
    email = email.lower().strip()
    
    try:
        from database import get_connection, return_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM allowed_emails WHERE LOWER(email) = %s", (email,))
        result = cursor.fetchone()
        cursor.close()
        return_connection(conn)
        return result[0] if result else None
    except:
        return None

def is_admin(email):
    """
    Verifica se o email tem privilégios de administrador.
    """
    return get_user_role(email) == 'admin'

def is_viewer(email):
    """
    Verifica se o email é apenas visualizador (read-only).
    """
    return get_user_role(email) == 'viewer'

def can_edit(email):
    """
    Verifica se o usuário pode editar (criar processos, avaliar, etc).
    Apenas admin e user podem editar. Viewer não pode.
    """
    role = get_user_role(email)
    return role in ['admin', 'user']

def add_allowed_email(email, role='user', added_by=None):
    """
    Adiciona um email à lista de permitidos.
    role: 'admin', 'user', ou 'viewer'
    """
    if role not in ['admin', 'user', 'viewer']:
        role = 'user'
    
    try:
        from database import get_connection, return_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO allowed_emails (email, role, added_by)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET role = EXCLUDED.role
        """, (email.lower().strip(), role, added_by))
        conn.commit()
        cursor.close()
        return_connection(conn)
        # Clear cache after modification
        is_email_allowed.clear()
        get_user_role.clear()
        get_all_allowed_emails.clear()
        return True
    except Exception as e:
        print(f"Erro ao adicionar email: {e}")
        return False

def remove_allowed_email(email):
    """
    Remove um email da lista de permitidos.
    """
    try:
        from database import get_connection, return_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM allowed_emails WHERE LOWER(email) = %s", (email.lower().strip(),))
        conn.commit()
        cursor.close()
        return_connection(conn)
        # Clear cache after modification
        is_email_allowed.clear()
        get_user_role.clear()
        get_all_allowed_emails.clear()
        return True
    except Exception as e:
        print(f"Erro ao remover email: {e}")
        return False

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_all_allowed_emails():
    """
    Retorna todos os emails permitidos.
    """
    try:
        from database import get_connection, return_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email, role, added_by, added_at FROM allowed_emails ORDER BY added_at DESC")
        results = cursor.fetchall()
        cursor.close()
        return_connection(conn)
        return results
    except Exception as e:
        print(f"Erro ao buscar emails: {e}")
        return []
