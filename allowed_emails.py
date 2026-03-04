# Lista de emails autorizados a acessar o sistema
# Apenas emails @artefact.com podem fazer login

ALLOWED_EMAILS = [
    "raissa.azevedo@artefact.com",
    "brenda.antunes@artefact.com",
    "henrique.toledo@artefact.com",
    # Adicione mais emails conforme necessário
]

def is_email_allowed(email):
    """
    Verifica se o email está autorizado a acessar o sistema.
    Aceita qualquer email @artefact.com ou emails específicos na lista.
    """
    if not email:
        return False
    
    email = email.lower().strip()
    
    # Verifica se o email termina com @artefact.com
    if email.endswith("@artefact.com"):
        return True
    
    # Verifica se o email está na lista de permitidos
    if email in [e.lower() for e in ALLOWED_EMAILS]:
        return True
    
    return False
