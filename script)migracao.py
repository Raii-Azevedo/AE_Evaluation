# script_migracao.py - Execute uma vez
from database import init_db, get_connection, return_connection

print("Iniciando migração do banco...")
init_db()

# Verificar se as colunas foram adicionadas
conn = get_connection()
cursor = conn.cursor()

cursor.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'processos'
""")
colunas = cursor.fetchall()
print("Colunas na tabela processos:", [c[0] for c in colunas])

cursor.close()
return_connection(conn)
print("Migração concluída!")