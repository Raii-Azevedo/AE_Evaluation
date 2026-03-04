# Sistema de gerenciamento de emails autorizados
# Agora usando banco de dados para armazenar emails permitidos

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
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM allowed_emails WHERE LOWER(email) = %s", (email,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result is not None
    except:
        return False

def is_admin(email):
    """
    Verifica se o email tem privilégios de administrador.
    """
    if not email:
        return False
    
    email = email.lower().strip()
    
    try:
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_admin FROM allowed_emails WHERE LOWER(email) = %s", (email,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result and result[0]
    except:
        return False

def add_allowed_email(email, is_admin_user=False, added_by=None):
    """
    Adiciona um email à lista de permitidos.
    """
    try:
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO allowed_emails (email, is_admin, added_by)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET is_admin = EXCLUDED.is_admin
        """, (email.lower().strip(), is_admin_user, added_by))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao adicionar email: {e}")
        return False

def remove_allowed_email(email):
    """
    Remove um email da lista de permitidos.
    """
    try:
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM allowed_emails WHERE LOWER(email) = %s", (email.lower().strip(),))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Erro ao remover email: {e}")
        return False

def get_all_allowed_emails():
    """
    Retorna todos os emails permitidos.
    """
    try:
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email, is_admin, added_by, added_at FROM allowed_emails ORDER BY added_at DESC")
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        print(f"Erro ao buscar emails: {e}")
        return []
