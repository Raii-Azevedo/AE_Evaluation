import streamlit as st
import pandas as pd
import time
from datetime import datetime
from database import (
    init_db, get_connection, return_connection,
    importar_candidatos_sheets, 
    get_aplicacoes_pendentes_2026, get_aplicacoes_avaliadas_2026, get_stats_2026,
    get_aplicacao_info, salvar_avaliacao, salvar_criterios_avaliacao,
    get_ultima_avaliacao_por_aplicacao, get_avaliacao_completa, get_criterios_avaliacao,
    atualizar_gh_status_aplicacao,
    get_ou_criar_processo, get_processos_ativos, get_processo_info,
    get_estatisticas_gerais, get_avaliacoes_recentes
)
from criterios_areas import get_criterios_por_area, get_areas_disponiveis
from allowed_emails import (
    is_email_allowed, get_user_role, is_admin, is_viewer, can_edit,
    add_allowed_email, remove_allowed_email, get_all_allowed_emails
)
import gspread
from google.oauth2.service_account import Credentials
from functools import wraps

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="Sistema de Avaliação Técnica",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== DATABASE INITIALIZATION =====
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# ===== SESSION STATE INITIALIZATION =====
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "view": "home",
        "processo_id": None,
        "aplicacao_id": None,
        "avaliacao_id": None,
        "dark_mode": True,
        "auto_save_enabled": True,
        "last_save_time": 0,
        "draft_data": {},
        "notifications": [],
        "logged_in": False,
        "user_email": None,
        "user_name": None,
        "user_role": None,
        "admin_view": "dashboard",
        "candidato_filter": "todos",
        "search_term": "",
        "dados_sheets_cache": None,
        "ultima_sincronizacao": None
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ===== HELPER FUNCTIONS =====
def add_notification(message, type="info"):
    st.session_state.notifications.append({
        "message": message,
        "type": type,
        "timestamp": datetime.now()
    })

def show_notifications():
    for notif in st.session_state.notifications[-5:]:
        if notif["type"] == "success":
            st.success(notif["message"])
        elif notif["type"] == "error":
            st.error(notif["message"])
        elif notif["type"] == "warning":
            st.warning(notif["message"])
        else:
            st.info(notif["message"])
    st.session_state.notifications = []

def show_progress_bar(current, total, label=""):
    if total > 0:
        progress = current / total
        st.progress(progress)
        st.caption(f"{label} {current}/{total} itens avaliados")

def extract_name_from_email(email):
    """Extrai nome do email para exibição"""
    if email:
        name_part = email.split('@')[0]
        name = name_part.replace('.', ' ').replace('_', ' ').title()
        return name
    return "Avaliador"

# ===== GOOGLE SHEETS INTEGRATION =====
@st.cache_data(ttl=300)
def carregar_google_sheets():
    """Carrega dados do Google Sheets com cache"""
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        if 'google_credentials' in st.secrets:
            creds_dict = st.secrets["google_credentials"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        else:
            try:
                creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
            except FileNotFoundError:
                return carregar_google_sheets_demo()
        
        client = gspread.authorize(creds)
        sheet_id = "1ZYJjoZDQAZEIthzNfB5gl4DJ3zkwvQdHhkaeBXDorcg"
        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.get_worksheet(0)
        data = worksheet.get_all_records()
        
        return data
        
    except Exception as e:
        st.error(f"Erro ao carregar Google Sheets: {str(e)}")
        return None

def carregar_google_sheets_demo():
    """Dados de demonstração"""
    return [
        {
            'Timestamp': '21/01/2026 20:08:01',
            'Email address': 'felipecadavez2912@gmail.com',
            'Full name': 'Felipe Cadavez Oliveira',
            'Email used on application': 'felipecadavez2912@gmail.com',
            'Job title': 'Entry Analytics Engineer - Brazil',
            'Admission Category': 'Ampla Concorrência',
            'LinkedIn': 'linkedin.com/in/fecadavez',
            'Greenhouse ID': 'https://app2.greenhouse.io/people/259096501002?application_id=273686618002',
            'Pbix file': 'https://drive.google.com/open?id=1zM8VKEPme0qYA1a5Omaqr2pcr88Ro8gD',
            'Optional file': 'https://drive.google.com/open?id=1nto_OpoyBrJyYe0BvE42k0kCp0ay68TW',
            'Priorização': ''
        },
        {
            'Timestamp': '03/02/2026 12:01:27',
            'Email address': 'luiz.h.augusto13@gmail.com',
            'Full name': 'Luiz Henrique Alves Augusto',
            'Email used on application': 'luiz.h.augusto13@gmail.com',
            'Job title': 'Entry Analytics Engineer - Brazil',
            'Admission Category': 'Ampla Concorrência',
            'LinkedIn': 'https://www.linkedin.com/in/luizhenriqueaaugusto/',
            'Greenhouse ID': 'https://app2.greenhouse.io/people/254659019002?application_id=272421166002',
            'Pbix file': 'https://drive.google.com/open?id=1tkzyYUH8AVRd0CBea-k3B_dPns77hDQP',
            'Optional file': 'https://drive.google.com/open?id=1CYOAjTRHygmX0BClGO-uhJ8iBfJSkXi5',
            'Priorização': ''
        }
    ]

def sincronizar_dados_google_sheets():
    """Sincroniza APENAS candidatos de 2026 com priorização em branco"""
    
    dados = carregar_google_sheets()
    
    if not dados:
        st.error("❌ Não foi possível carregar dados do Google Sheets")
        return False
    
    # Analisar dados
    total_linhas = len(dados)
    candidatos_2026 = 0
    candidatos_com_priorizacao = 0
    candidatos_para_importar = []
    
    for linha in dados:
        timestamp = linha.get('Timestamp', '')
        priorizacao = linha.get('Priorização', '').strip()
        job_title = linha.get('Job title', '').strip()
        admission_category = linha.get('Admission Category', '').strip()
        
        ano = None
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    partes = timestamp.split('/')
                    if len(partes) >= 3:
                        ano = int(partes[2].split(' ')[0])
            except:
                pass
        
        if ano == 2026:
            candidatos_2026 += 1
            if priorizacao and priorizacao not in ['', 'Não priorizar']:
                candidatos_com_priorizacao += 1
            else:
                if job_title and admission_category:
                    candidatos_para_importar.append({
                        'timestamp': timestamp,
                        'email': linha.get('Email address', '').strip(),
                        'nome': linha.get('Full name', '').strip(),
                        'linkedin': linha.get('LinkedIn', '').strip(),
                        'greenhouse_id': linha.get('Greenhouse ID', '').strip(),
                        'pbix_file': linha.get('Pbix file', '').strip(),
                        'optional_file': linha.get('Optional file', '').strip(),
                        'job_title': job_title,
                        'admission_category': admission_category,
                        'priorizacao': priorizacao
                    })
    
    # Mostrar análise
    st.info(f"""
    📊 **Análise dos dados:**
    - Total de registros: {total_linhas}
    - Registros de 2026: {candidatos_2026}
    - Destes, já avaliados (com priorização): {candidatos_com_priorizacao}
    - **A serem importados:** {len(candidatos_para_importar)}
    """)
    
    if len(candidatos_para_importar) == 0:
        st.warning("⚠️ Nenhum candidato para importar.")
        return False
    
    # Mostrar preview
    with st.expander("📋 Preview dos candidatos a serem importados", expanded=True):
        preview_df = pd.DataFrame(candidatos_para_importar)
        st.dataframe(preview_df[['nome', 'email', 'job_title', 'admission_category']], use_container_width=True)
    
    # Armazenar no session state para usar depois
    st.session_state.candidatos_para_importar = candidatos_para_importar
    
    # Botão para confirmar importação
    if st.button("✅ Confirmar Importação", type="primary", use_container_width=True):
        st.session_state.executar_importacao = True
        st.rerun()
    
    return False


def executar_importacao():
    """Executa a importação dos candidatos"""
    if not st.session_state.get('executar_importacao', False):
        return False
    
    candidatos_para_importar = st.session_state.get('candidatos_para_importar', [])
    if not candidatos_para_importar:
        st.warning("⚠️ Nenhum candidato para importar.")
        st.session_state.executar_importacao = False
        return False
    
    st.write("### 🚀 Iniciando importação...")
    
    # Agrupar por Job Title + Admission Category
    processos_data = {}
    for candidato in candidatos_para_importar:
        chave = f"{candidato['job_title']}||{candidato['admission_category']}"
        
        if chave not in processos_data:
            processos_data[chave] = {
                'nome': f"{candidato['job_title']} - {candidato['admission_category']}",
                'job_title': candidato['job_title'],
                'admission_category': candidato['admission_category'],
                'candidatos': []
            }
        
        processos_data[chave]['candidatos'].append({
            'timestamp': candidato['timestamp'],
            'email': candidato['email'],
            'nome': candidato['nome'],
            'linkedin': candidato['linkedin'],
            'greenhouse_id': candidato['greenhouse_id'],
            'pbix_file': candidato['pbix_file'],
            'optional_file': candidato['optional_file'],
            'priorizacao': candidato['priorizacao']
        })
    
    st.write(f"📁 Serão criados/atualizados {len(processos_data)} processo(s):")
    for chave, processo in processos_data.items():
        st.write(f"   - **{processo['nome']}** ({len(processo['candidatos'])} candidatos)")
    
    total_importados = 0
    processos_criados = 0
    
    # Barra de progresso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for idx, (chave, processo) in enumerate(processos_data.items()):
        status_text.text(f"Processando: {processo['nome']}...")
        
        # Criar ou obter processo
        processo_id = get_ou_criar_processo(
            processo['nome'],
            processo['job_title'],
            processo['admission_category']
        )
        
        if processo_id:
            processos_criados += 1
            st.write(f"✅ Processo **{processo['nome']}** criado/obtido (ID: {processo_id})")
            
            # Importar candidatos
            resultado = importar_candidatos_sheets(
                processo['candidatos'],
                processo_id,
                st.session_state.user_email
            )
            
            if resultado.get('sucesso'):
                novas = resultado.get('novas_aplicacoes', 0)
                total_importados += novas
                st.success(f"   ✅ {novas} candidatos importados para este processo")
            else:
                st.error(f"   ❌ Erro: {resultado.get('erro', 'Erro desconhecido')}")
        else:
            st.error(f"❌ Falha ao criar/obter processo {processo['nome']}")
        
        # Atualizar progresso
        progress_bar.progress((idx + 1) / len(processos_data))
    
    status_text.text("Importação concluída!")
    
    if total_importados > 0:
        st.success(f"""
        ✅ **Sincronização concluída!**
        - Processos criados/atualizados: {processos_criados}
        - Novas aplicações criadas: {total_importados}
        """)
        st.session_state.ultima_sincronizacao = datetime.now()
        st.session_state.executar_importacao = False
        st.session_state.candidatos_para_importar = []
        
        # Botão para recarregar
        if st.button("🔄 Recarregar página para ver os novos dados", use_container_width=True):
            st.rerun()
        return True
    else:
        st.warning("⚠️ Nenhum candidato foi importado.")
        st.session_state.executar_importacao = False
        return False

# ===== STYLES =====
def get_styles(dark_mode=False):
    if dark_mode:
        return """
        <style>
        .stApp { background: linear-gradient(135deg, #0B1E3D 0%, #1E1E2F 40%, #2D1B3A 100%); }
        .card {
            background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03));
            backdrop-filter: blur(12px);
            padding: 28px;
            border-radius: 20px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0px 10px 30px rgba(0,0,0,0.35);
            transition: all 0.3s ease;
        }
        .card:hover {
            transform: translateY(-6px);
            box-shadow: 0px 20px 40px rgba(0,0,0,0.5);
            border-color: rgba(255,255,255,0.2);
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }
        .badge-success { background: rgba(34,197,94,0.2); color: #22c55e; }
        .badge-warning { background: rgba(250,204,21,0.2); color: #facc15; }
        .badge-danger { background: rgba(239,68,68,0.2); color: #ef4444; }
        .badge-info { background: rgba(59,130,246,0.2); color: #60a5fa; }
        .badge-gh-done { background: rgba(34,197,94,0.3); color: #22c55e; }
        .badge-gh-pending { background: rgba(239,68,68,0.3); color: #ef4444; }
        .gh-link { color: #60a5fa; text-decoration: none; }
        .gh-link:hover { text-decoration: underline; }
        h1, h2, h3, h4, h5, h6, p, span, label { color: #f3f4f6; }
        .stButton>button {
            border-radius: 12px;
            height: 44px;
            font-weight: 600;
            border: none;
            background: linear-gradient(135deg, #3B82F6, #EC4899);
            color: white;
            transition: all 0.25s ease;
        }
        .stButton>button:hover {
            transform: translateY(-3px);
            box-shadow: 0px 10px 20px rgba(236,72,153,0.5);
        }
        .stTextInput>div>div>input, .stTextArea textarea, .stSelectbox>div>div {
            border-radius: 12px !important;
            background-color: rgba(255,255,255,0.08) !important;
            color: white !important;
            border: 1px solid rgba(255,255,255,0.15) !important;
        }
        .stMetric { background: rgba(255,255,255,0.05); border-radius: 12px; padding: 15px; }
        hr { border-color: rgba(255,255,255,0.1); }
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 40px;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        .search-box { margin-bottom: 20px; }
        </style>
        """
    else:
        return """
        <style>
        .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #e8edf5 100%); }
        .card {
            background: white;
            padding: 28px;
            border-radius: 20px;
            margin-bottom: 25px;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.08);
            transition: all 0.3s ease;
            border: 1px solid #e5e7eb;
        }
        .card:hover {
            transform: translateY(-6px);
            box-shadow: 0px 12px 30px rgba(0,0,0,0.12);
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }
        .badge-success { background: #d1fae5; color: #065f46; }
        .badge-warning { background: #fed7aa; color: #92400e; }
        .badge-danger { background: #fee2e2; color: #991b1b; }
        .badge-info { background: #dbeafe; color: #1e40af; }
        .badge-gh-done { background: #d1fae5; color: #065f46; }
        .badge-gh-pending { background: #fee2e2; color: #991b1b; }
        .gh-link { color: #3b82f6; text-decoration: none; }
        .gh-link:hover { text-decoration: underline; }
        h1, h2, h3, h4, h5, h6 { color: #111827; }
        p, span, label { color: #374151; }
        .stButton>button {
            border-radius: 12px;
            height: 44px;
            font-weight: 600;
            border: none;
            background: linear-gradient(135deg, #3B82F6, #EC4899);
            color: white;
            transition: all 0.25s ease;
        }
        .stButton>button:hover {
            transform: translateY(-3px);
            box-shadow: 0px 10px 20px rgba(236,72,153,0.3);
        }
        .stMetric { background: white; border-radius: 12px; padding: 15px; box-shadow: 0px 1px 3px rgba(0,0,0,0.1); }
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 40px;
            background: white;
            border-radius: 20px;
            box-shadow: 0px 10px 30px rgba(0,0,0,0.1);
        }
        .search-box { margin-bottom: 20px; }
        </style>
        """

st.markdown(get_styles(st.session_state.dark_mode), unsafe_allow_html=True)

# ===== LOGIN PAGE =====
def login_page():
    st.markdown("""
    <h1 style="text-align:center; font-size:52px; font-weight:800; letter-spacing:-2px; 
               background: linear-gradient(135deg, #3B82F6, #EC4899, #A855F7);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom:20px;">
        🚀 SISTEMA DE AVALIAÇÃO
    </h1>
    <p style="text-align:center; font-size:18px; margin-bottom:40px;">
        Entre com seu email para acessar o sistema
    </p>
    """, unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            email = st.text_input("Email corporativo", placeholder="seuemail@artefact.com", key="login_email")
            
            st.markdown("---")
            st.caption("ℹ️ Use seu email corporativo.")
            
            if st.button("🔐 Entrar", type="primary", use_container_width=True):
                if email:
                    if is_email_allowed(email):
                        role = get_user_role(email)
                        name = extract_name_from_email(email)
                        
                        st.session_state.logged_in = True
                        st.session_state.user_email = email
                        st.session_state.user_name = name
                        st.session_state.user_role = role
                        add_notification(f"Bem-vindo, {name}!", "success")
                        st.rerun()
                    else:
                        st.error("❌ Email não autorizado. Contate o administrador.")
                else:
                    st.warning("⚠️ Digite seu email para acessar")
            
            st.markdown('</div>', unsafe_allow_html=True)

# ===== ADMIN FUNCTIONS =====
def admin_manage_emails():
    st.title("📧 Gerenciar Emails Autorizados")
    
    emails = get_all_allowed_emails()
    
    if emails:
        st.subheader("📋 Emails Autorizados")
        df = pd.DataFrame(emails, columns=["Email", "Role", "Adicionado por", "Data"])
        st.dataframe(df, use_container_width=True)
    
    st.divider()
    
    with st.expander("➕ Adicionar Novo Email"):
        col1, col2 = st.columns(2)
        with col1:
            new_email = st.text_input("Email")
        with col2:
            role = st.selectbox("Role", ["admin", "user", "viewer"])
        
        if st.button("Adicionar Email", type="primary"):
            if new_email:
                if add_allowed_email(new_email, role, st.session_state.user_email):
                    add_notification(f"✅ Email {new_email} adicionado com role {role}", "success")
                    st.rerun()
                else:
                    st.error("❌ Erro ao adicionar email")
            else:
                st.warning("⚠️ Digite um email")
    
    with st.expander("🗑️ Remover Email"):
        email_to_remove = st.selectbox(
            "Selecione o email para remover",
            [e[0] for e in emails if e[0] != "admin@artefact.com"]
        )
        
        if st.button("Remover Email", type="primary"):
            if email_to_remove:
                if remove_allowed_email(email_to_remove):
                    add_notification(f"✅ Email {email_to_remove} removido", "success")
                    st.rerun()
                else:
                    st.error("❌ Erro ao remover email")

def admin_dashboard():
    st.title("📊 Dashboard Administrativo")
    
    try:
        stats = get_estatisticas_gerais()
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("👥 Usuários", stats[5] if len(stats) > 5 else 0)
        with col2:
            st.metric("📋 Processos", stats[0] if len(stats) > 0 else 0)
        with col3:
            st.metric("👤 Candidatos", stats[1] if len(stats) > 1 else 0)
        with col4:
            st.metric("📝 Aplicações 2026", stats[2] if len(stats) > 2 else 0)
        with col5:
            st.metric("⭐ Avaliações", stats[3] if len(stats) > 3 else 0)
        with col6:
            st.metric("✅ GH Atualizado", stats[4] if len(stats) > 4 else 0)
        
        st.divider()
        
        # Seção de sincronização
        st.subheader("🔄 Sincronização com Google Sheets")
        
        # Verificar se precisa executar importação
        if st.session_state.get('executar_importacao', False):
            executar_importacao()
        else:
            sincronizar_dados_google_sheets()
        
        if st.session_state.ultima_sincronizacao:
            st.caption(f"📅 Última sincronização: {st.session_state.ultima_sincronizacao.strftime('%d/%m/%Y %H:%M:%S')}")
        
        st.divider()
        
        # Distribuição por role
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT role, COUNT(*) FROM allowed_emails GROUP BY role")
            roles = cursor.fetchall()
            cursor.close()
            
            if roles:
                st.subheader("👥 Distribuição por Role")
                cols = st.columns(len(roles))
                for i, (role, total) in enumerate(roles):
                    role_name = {"admin": "Administradores", "user": "Avaliadores", "viewer": "Visualizadores"}.get(role, role)
                    with cols[i]:
                        st.metric(role_name, total)
        finally:
            if conn:
                return_connection(conn)
        
        st.divider()
        
        st.subheader("📈 Atividade Recente")
        atividades = get_avaliacoes_recentes(10)
        
        if atividades:
            df = pd.DataFrame(atividades, columns=["Data", "Processo", "Candidato", "Nota", "Avaliador", "GH Atualizado"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhuma avaliação realizada ainda")
            
    except Exception as e:
        st.error(f"Erro ao carregar dashboard: {str(e)}")

def admin_relatorios():
    st.title("📈 Relatórios e Análises")
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        report_type = st.selectbox(
            "Tipo de Relatório",
            ["Resumo Geral", "Avaliações por Processo", "Status Greenhouse", "Candidatos Pendentes 2026"]
        )
        
        if report_type == "Resumo Geral":
            cursor.execute("""
                SELECT 
                    p.nome as processo,
                    COUNT(DISTINCT a.id) as aplicacoes_2026,
                    COUNT(av.id) as avaliacoes,
                    COALESCE(AVG(av.nota_final), 0) as media,
                    SUM(CASE WHEN av.nota_final >= 8 THEN 1 ELSE 0 END) as aprovados,
                    SUM(CASE WHEN av.gh_atualizada = true THEN 1 ELSE 0 END) as gh_atualizados
                FROM processos p
                LEFT JOIN aplicacoes a ON p.id = a.processo_id AND EXTRACT(YEAR FROM a.timestamp_aplicacao) = 2026
                LEFT JOIN avaliacoes av ON a.id = av.aplicacao_id
                GROUP BY p.id ORDER BY p.nome
            """)
            data = cursor.fetchall()
            if data:
                df = pd.DataFrame(data, columns=["Processo", "Aplicações 2026", "Avaliações", "Média", "Aprovados", "GH Atualizados"])
                st.dataframe(df, use_container_width=True)
        
        elif report_type == "Candidatos Pendentes 2026":
            cursor.execute("""
                SELECT 
                    p.nome as processo,
                    c.nome,
                    c.email,
                    a.timestamp_aplicacao,
                    a.greenhouse_id
                FROM aplicacoes a
                JOIN candidatos c ON a.candidato_id = c.id
                JOIN processos p ON a.processo_id = p.id
                LEFT JOIN avaliacoes av ON a.id = av.aplicacao_id
                WHERE EXTRACT(YEAR FROM a.timestamp_aplicacao) = 2026 AND av.id IS NULL
                ORDER BY p.nome, a.timestamp_aplicacao DESC
            """)
            data = cursor.fetchall()
            if data:
                df = pd.DataFrame(data, columns=["Processo", "Candidato", "Email", "Data Aplicação", "Greenhouse ID"])
                st.dataframe(df, use_container_width=True)
                st.info(f"Total de candidatos pendentes: {len(data)}")
            else:
                st.success("🎉 Não há candidatos pendentes para 2026!")
        
        cursor.close()
    except Exception as e:
        st.error(f"Erro ao gerar relatório: {str(e)}")
    finally:
        if conn:
            return_connection(conn)

# ===== SIDEBAR =====
def render_sidebar():
    with st.sidebar:
        if st.session_state.logged_in:
            role_display = {
                "admin": "👑 Administrador",
                "user": "⭐ Avaliador",
                "viewer": "👀 Visualizador"
            }.get(st.session_state.user_role, "👤 Usuário")
            
            st.markdown(f"""
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="background: linear-gradient(135deg, #3B82F6, #EC4899); 
                            border-radius: 50%; width: 60px; height: 60px; margin: 0 auto 10px;
                            display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 30px;">👤</span>
                </div>
                <h3 style="margin: 0;">{st.session_state.user_name}</h3>
                <p style="margin: 0; font-size: 12px; opacity: 0.8;">
                    {st.session_state.user_email}<br>
                    {role_display}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            if st.toggle("🌙 Modo Escuro", value=st.session_state.dark_mode):
                if not st.session_state.dark_mode:
                    st.session_state.dark_mode = True
                    st.rerun()
            else:
                if st.session_state.dark_mode:
                    st.session_state.dark_mode = False
                    st.rerun()
            
            st.markdown("---")
            
            if st.session_state.user_role == "admin":
                st.markdown("### 🛠️ Administração")
                admin_option = st.radio(
                    "Menu Admin",
                    ["📊 Dashboard", "📧 Emails", "📈 Relatórios"],
                    key="admin_menu",
                    index=0
                )
                
                if admin_option == "📊 Dashboard":
                    st.session_state.admin_view = "dashboard"
                elif admin_option == "📧 Emails":
                    st.session_state.admin_view = "emails"
                elif admin_option == "📈 Relatórios":
                    st.session_state.admin_view = "relatórios"
            
            st.markdown("---")
            
            if st.button("🚪 Sair", use_container_width=True):
                for key in ["logged_in", "user_email", "user_name", "user_role", "admin_view", "processo_id"]:
                    if key in st.session_state:
                        if key == "admin_view":
                            st.session_state[key] = "dashboard"
                        else:
                            st.session_state[key] = None
                st.session_state.logged_in = False
                st.rerun()

# ===== EVALUATION FORM =====
def evaluation_form(aplicacao_id, candidato_nome, email_candidato, linkedin, greenhouse_id, pbix_file, optional_file, processo_nome, area_processo):
    """Display evaluation form with all criteria"""
    
    estrutura = get_criterios_por_area(area_processo)
    
    # Mostrar informações do candidato
    st.subheader("👤 Informações do Candidato")
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown(f"**Nome:** {candidato_nome}")
        st.markdown(f"**Email:** {email_candidato}")
        st.markdown(f"**Vaga:** {processo_nome}")
    with col_info2:
        if linkedin:
            st.markdown(f"🔗 [LinkedIn]({linkedin})")
        if pbix_file:
            st.markdown(f"📊 [Arquivo PBIX]({pbix_file})")
        if optional_file:
            st.markdown(f"📁 [Arquivo Opcional]({optional_file})")
    
    st.divider()
    
    # Lembrete do Greenhouse
    st.info("🏢 **Lembrete:** Após finalizar a avaliação, não esqueça de mover o candidato no Greenhouse!")
    if greenhouse_id:
        st.markdown(f"🔗 Acesse o candidato no Greenhouse: [{greenhouse_id}]({greenhouse_id})")
    else:
        st.warning("⚠️ Nenhum link do Greenhouse encontrado para este candidato.")
    
    st.divider()
    
    # Critérios de avaliação
    st.subheader("📋 Critérios de Avaliação")
    
    soma_ponderada = 0
    soma_pesos = 0
    reprovado = False
    criterios_avaliados = 0
    total_criterios = sum(len(criterios) for criterios in estrutura.values())
    
    for bloco, criterios in estrutura.items():
        st.markdown(f"### {bloco}")
        
        for item in criterios:
            criterio = item["criterio"]
            peso = item["peso"]
            obrigatorio = item.get("obrigatorio", True)
            descricao = item.get("descricao", "")
            
            key_nota = f"{bloco}_{criterio}"
            key_just = f"just_{bloco}_{criterio}"
            
            if key_nota not in st.session_state:
                st.session_state[key_nota] = 5.0
            if key_just not in st.session_state:
                st.session_state[key_just] = ""
            
            with st.container():
                st.markdown(f"**{criterio}**")
                if descricao:
                    st.caption(f"ℹ️ {descricao}")
                
                col_nota, col_just = st.columns([1, 2])
                with col_nota:
                    nota = st.slider(
                        f"Nota (Peso: {peso}){' 🔴 Obrigatório' if obrigatorio else ''}",
                        0.0, 10.0,
                        st.session_state[key_nota],
                        step=0.5,
                        key=key_nota
                    )
                    
                    if nota > 0:
                        criterios_avaliados += 1
                    
                    if nota >= 8:
                        st.markdown("✅ Excelente")
                    elif nota >= 6:
                        st.markdown("⚠️ Bom")
                    else:
                        st.markdown("❌ Precisa melhorar")
                
                with col_just:
                    justificativa = st.text_area(
                        "Justificativa",
                        st.session_state[key_just],
                        key=key_just,
                        placeholder="Explique sua avaliação..."
                    )
                
                soma_ponderada += nota * peso
                soma_pesos += peso
                if obrigatorio and nota < 6:
                    reprovado = True
        
        st.divider()
    
    show_progress_bar(criterios_avaliados, total_criterios, "Critérios avaliados:")
    
    nota_final = round(soma_ponderada / soma_pesos, 2) if soma_pesos > 0 else 0
    
    # Resultado final
    st.subheader("🎯 Resultado Final")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Nota Final", nota_final)
    with col2:
        st.metric("Critérios Avaliados", f"{criterios_avaliados}/{total_criterios}")
    
    if reprovado:
        st.error("❌ Reprovado por critério obrigatório abaixo de 6")
    elif nota_final >= 8:
        st.success("✅ Recomendado para contratação")
    elif nota_final >= 6:
        st.warning("⚠️ Avaliar melhor - Pontos de melhoria identificados")
    else:
        st.error("❌ Não recomendado - Necessita desenvolvimento")
    
    st.divider()
    
    # Priorização
    st.subheader("⭐ Priorização")
    priorizacao = st.radio(
        "Selecione a prioridade do candidato:",
        ["Não priorizar", "Prioridade 1", "Prioridade 2", "Prioridade 3"],
        index=0,
        horizontal=True
    )
    
    # Comentário final
    comentario = st.text_area(
        "💬 Comentário Final Geral *",
        placeholder="Descreva sua avaliação de forma geral, destacando pontos fortes e áreas de melhoria...",
        height=100
    )
    
    # Greenhouse confirmation
    st.divider()
    st.subheader("🏢 Atualização no Greenhouse")
    
    col_gh1, col_gh2 = st.columns([3, 1])
    with col_gh1:
        st.markdown("**Já atualizou esse candidato no Greenhouse?**")
        if greenhouse_id:
            st.markdown(f"🔗 [Link para o candidato no Greenhouse]({greenhouse_id})")
    with col_gh2:
        gh_atualizado = st.checkbox("✅ Sim, já atualizei", key="gh_checkbox")
    
    # Confirmação
    st.divider()
    
    col_confirm1, col_confirm2, col_confirm3 = st.columns([1, 1, 1])
    with col_confirm2:
        if st.button("✅ Finalizar Avaliação", type="primary", use_container_width=True):
            if not comentario:
                st.error("❌ Comentário final é obrigatório")
            else:
                with st.popover("⚠️ Confirmar Avaliação"):
                    st.warning("Tem certeza que deseja finalizar esta avaliação?")
                    st.write(f"**Candidato:** {candidato_nome}")
                    st.write(f"**Nota Final:** {nota_final}")
                    st.write(f"**Priorização:** {priorizacao}")
                    st.write(f"**GH Atualizado:** {'Sim' if gh_atualizado else 'Não'}")
                    
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("✅ Sim, salvar avaliação", use_container_width=True):
                            # Salvar avaliação
                            avaliacao_id = salvar_avaliacao(
                                aplicacao_id, nota_final,
                                st.session_state.user_email, comentario, 
                                priorizacao, gh_atualizado
                            )
                            
                            if avaliacao_id:
                                # Salvar critérios
                                for bloco, criterios in estrutura.items():
                                    for item in criterios:
                                        criterio = item["criterio"]
                                        key_nota = f"{bloco}_{criterio}"
                                        key_just = f"just_{bloco}_{criterio}"
                                        
                                        nota = st.session_state.get(key_nota, 5.0)
                                        just = st.session_state.get(key_just, "")
                                        
                                        salvar_criterios_avaliacao(avaliacao_id, bloco, criterio, nota, just)
                                
                                add_notification(f"✅ Avaliação de {candidato_nome} salva com sucesso!", "success")
                                st.session_state.view = "processo"
                                st.rerun()
                            else:
                                st.error("❌ Erro ao salvar avaliação")
                    
                    with col_no:
                        if st.button("❌ Não, revisar", use_container_width=True):
                            st.rerun()

# ===== MAIN APP =====
if not st.session_state.logged_in:
    login_page()
else:
    render_sidebar()
    show_notifications()
    
    # Admin view
    if st.session_state.user_role == "admin":
        if st.session_state.admin_view == "emails":
            admin_manage_emails()
        elif st.session_state.admin_view == "relatórios":
            admin_relatorios()
        else:
            admin_dashboard()
        
        # Mostrar processos
        st.markdown("""
        <h1 style="text-align:center; font-size:48px; font-weight:700; 
                   background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6);
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            SISTEMA DE AVALIAÇÃO TÉCNICA
        </h1>
        """, unsafe_allow_html=True)
        
        st.divider()
        st.markdown("### 📋 Processos Disponíveis")
        
        processos = get_processos_ativos()
        if not processos:
            st.info("✨ Nenhum processo encontrado. Clique em 'Sincronizar' no dashboard para importar os dados.")
        else:
            for proc in processos:
                id_p, nome, job_title, admission_category = proc
                
                st.markdown(f"""
                <div class="card">
                    <h3>{nome}</h3>
                    <p><strong>Job Title:</strong> {job_title} • <strong>Categoria:</strong> {admission_category}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("📂 Entrar", key=f"entrar_{id_p}"):
                    st.session_state.processo_id = id_p
                    st.session_state.view = "processo"
                    st.rerun()
    
    else:
        # Usuários normais
        if st.session_state.view == "home":
            st.markdown("""
            <h1 style="text-align:center; font-size:48px; font-weight:700; 
                       background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                SISTEMA DE AVALIAÇÃO TÉCNICA
            </h1>
            """, unsafe_allow_html=True)
            
            st.divider()
            st.markdown("### 📋 Processos Disponíveis")
            
            processos = get_processos_ativos()
            if not processos:
                st.info("✨ Nenhum processo encontrado.")
            else:
                for proc in processos:
                    id_p, nome, job_title, admission_category = proc
                    
                    st.markdown(f"""
                    <div class="card">
                        <h3>{nome}</h3>
                        <p><strong>Job Title:</strong> {job_title} • <strong>Categoria:</strong> {admission_category}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("📂 Entrar", key=f"entrar_{id_p}"):
                        st.session_state.processo_id = id_p
                        st.session_state.view = "processo"
                        st.rerun()
        
        elif st.session_state.view == "processo":
            processo_id = st.session_state.processo_id
            processo_info = get_processo_info(processo_id)
            
            if processo_info:
                nome_processo, job_title, admission_category = processo_info
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.title(f"📂 {nome_processo}")
                    st.caption(f"Job Title: {job_title} | Categoria: {admission_category}")
                with col2:
                    if st.button("🏠 Home"):
                        st.session_state.view = "home"
                        st.session_state.processo_id = None
                        st.rerun()
                
                st.divider()
                
                # Estatísticas 2026
                stats = get_stats_2026(processo_id)
                if stats:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📝 Pendentes", stats[0])
                    with col2:
                        st.metric("✅ Avaliados", stats[1])
                    with col3:
                        st.metric("⭐ Média", f"{stats[2]:.1f}" if stats[2] else "—")
                    with col4:
                        st.metric("🏢 GH Atualizado", stats[6])
                
                st.divider()
                
                # Buscador
                st.markdown("### 🔍 Buscar Candidato")
                search_term = st.text_input(
                    "Buscar por nome ou email",
                    placeholder="Digite o nome ou email do candidato...",
                    key="search_input"
                )
                
                # Filtros
                st.markdown("### 📌 Filtrar por Status")
                col_filter1, col_filter2, col_filter3 = st.columns(3)
                
                with col_filter1:
                    if st.button("👥 Todos", key="filter_todos", use_container_width=True):
                        st.session_state.candidato_filter = "todos"
                        st.rerun()
                
                with col_filter2:
                    if st.button("✅ Avaliados", key="filter_avaliados", use_container_width=True):
                        st.session_state.candidato_filter = "avaliados"
                        st.rerun()
                
                with col_filter3:
                    if st.button("⏳ Pendentes", key="filter_pendentes", use_container_width=True):
                        st.session_state.candidato_filter = "pendentes"
                        st.rerun()
                
                st.markdown("---")
                st.markdown("### 👥 Candidatos 2026")
                
                # Buscar aplicações
                pendentes = get_aplicacoes_pendentes_2026(processo_id)
                avaliados = get_aplicacoes_avaliadas_2026(processo_id)
                
                # Aplicar busca
                if search_term:
                    search_lower = search_term.lower()
                    pendentes = [p for p in pendentes if search_lower in p[2].lower() or search_lower in p[3].lower()]
                    avaliados = [a for a in avaliados if search_lower in a[2].lower() or search_lower in a[3].lower()]
                
                # Aplicar filtro
                if st.session_state.candidato_filter == "avaliados":
                    candidatos_exibir = avaliados
                elif st.session_state.candidato_filter == "pendentes":
                    candidatos_exibir = pendentes
                else:
                    # Mesclar todos
                    candidatos_exibir = pendentes + avaliados
                
                # Mostrar contagem
                st.caption(f"Mostrando {len(candidatos_exibir)} candidatos")
                
                # Exibir pendentes primeiro
                for app in pendentes:
                    aplicacao_id, candidato_id, nome, email, linkedin, timestamp, greenhouse_id, pbix_file, optional_file = app
                    
                    st.markdown(f"""
                    <div class="card">
                        <h3>{nome} <span class="badge badge-info">⏳ Pendente</span></h3>
                        <p>📧 {email}</p>
                        <p>📅 Data de aplicação: {timestamp if timestamp else 'Data não informada'}</p>
                        <p><span class="badge badge-gh-pending">⚠️ Pendente GH</span></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if can_edit(st.session_state.user_email):
                        if st.button("📝 Avaliar", key=f"avaliar_{aplicacao_id}"):
                            st.session_state.aplicacao_id = aplicacao_id
                            st.session_state.view = "avaliar"
                            st.rerun()
                    
                    st.markdown("---")
                
                # Exibir avaliados
                for app in avaliados:
                    aplicacao_id, candidato_id, nome, email, timestamp, nota_final, priorizacao, gh_atualizada, data_avaliacao, avaliador = app
                    
                    # Badge de nota
                    if nota_final >= 8:
                        badge_class = "badge-success"
                        status_text = "Aprovado"
                    elif nota_final >= 6:
                        badge_class = "badge-warning"
                        status_text = "Em análise"
                    else:
                        badge_class = "badge-danger"
                        status_text = "Reprovado"
                    
                    # Badge de priorização
                    prior_badge = ""
                    if priorizacao == "Prioridade 1":
                        prior_badge = '<span class="badge badge-danger">🔴 Prioridade 1</span>'
                    elif priorizacao == "Prioridade 2":
                        prior_badge = '<span class="badge badge-warning">🟡 Prioridade 2</span>'
                    elif priorizacao == "Prioridade 3":
                        prior_badge = '<span class="badge badge-info">🔵 Prioridade 3</span>'
                    
                    # Badge de GH
                    gh_badge = "badge-gh-done" if gh_atualizada else "badge-gh-pending"
                    gh_text = "✅ GH Atualizado" if gh_atualizada else "⚠️ Pendente GH"
                    
                    st.markdown(f"""
                    <div class="card">
                        <h3>{nome} 
                            <span class="badge {badge_class}">{status_text} - {nota_final:.1f}</span>
                            {prior_badge}
                        </h3>
                        <p>📧 {email}</p>
                        <p>📅 Avaliado em: {data_avaliacao.strftime('%d/%m/%Y') if data_avaliacao else 'Data não registrada'}</p>
                        <p><span class="badge {gh_badge}">{gh_text}</span></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        # Buscar ID da avaliação para ver detalhes
                        avaliacao = get_ultima_avaliacao_por_aplicacao(aplicacao_id)
                        if avaliacao:
                            avaliacao_id_db = avaliacao[0]
                            if st.button("🔍 Ver Detalhes", key=f"det_{aplicacao_id}"):
                                st.session_state.avaliacao_id = avaliacao_id_db
                                st.session_state.view = "detalhe_avaliacao"
                                st.rerun()
                    
                    with col_btn2:
                        if can_edit(st.session_state.user_email):
                            gh_checkbox = st.checkbox(
                                "✅ Marcar como atualizado no Greenhouse",
                                value=gh_atualizada,
                                key=f"gh_{aplicacao_id}"
                            )
                            if gh_checkbox != gh_atualizada:
                                if atualizar_gh_status_aplicacao(aplicacao_id, gh_checkbox):
                                    add_notification(f"Status Greenhouse atualizado para {nome}", "success")
                                    st.rerun()
                    
                    st.markdown("---")
        
        elif st.session_state.view == "avaliar":
            if not can_edit(st.session_state.user_email):
                st.error("❌ Você não tem permissão para avaliar candidatos")
                if st.button("← Voltar"):
                    st.session_state.view = "processo"
                    st.rerun()
            else:
                aplicacao_id = st.session_state.aplicacao_id
                processo_id = st.session_state.processo_id
                
                if st.button("← Voltar para lista de candidatos"):
                    st.session_state.view = "processo"
                    st.rerun()
                
                # Buscar dados da aplicação
                app_info = get_aplicacao_info(aplicacao_id)
                if app_info:
                    aplicacao_id, candidato_id, nome, email, linkedin, greenhouse_id, pbix_file, optional_file, timestamp = app_info
                    
                    processo_info = get_processo_info(processo_id)
                    if processo_info:
                        nome_processo, job_title, admission_category = processo_info
                        
                        # Determinar área (simplificado)
                        area_processo = "Analytics Engineer"
                        
                        st.title(f"📝 Avaliar: {nome}")
                        
                        evaluation_form(
                            aplicacao_id, nome, email, linkedin, greenhouse_id, 
                            pbix_file, optional_file, nome_processo, area_processo
                        )
        
        elif st.session_state.view == "detalhe_avaliacao":
            avaliacao_id = st.session_state.avaliacao_id
            
            if st.button("← Voltar"):
                st.session_state.view = "processo"
                st.rerun()
            
            avaliacao = get_avaliacao_completa(avaliacao_id)
            if avaliacao:
                (nota_final, avaliador, comentario, data_avaliacao, priorizacao, gh_atualizada,
                 nome, email, linkedin, greenhouse_id, pbix_file, optional_file, timestamp, processo_nome) = avaliacao
                
                st.title(f"🔍 Detalhe da Avaliação")
                
                col1, col2 = st.columns(2)
                with col1:
                    if nota_final >= 8:
                        st.metric("Nota Final", f"{nota_final:.1f}", delta="Aprovado", delta_color="normal")
                    elif nota_final >= 6:
                        st.metric("Nota Final", f"{nota_final:.1f}", delta="Em análise", delta_color="off")
                    else:
                        st.metric("Nota Final", f"{nota_final:.1f}", delta="Reprovado", delta_color="inverse")
                with col2:
                    st.metric("Avaliador", extract_name_from_email(avaliador))
                
                st.write(f"**Candidato:** {nome} ({email})")
                st.write(f"**Processo:** {processo_nome}")
                st.write(f"**Data da Avaliação:** {data_avaliacao.strftime('%d/%m/%Y %H:%M') if data_avaliacao else 'Data não registrada'}")
                st.write(f"**Data da Aplicação:** {timestamp if timestamp else 'Data não informada'}")
                st.write(f"**Priorização:** {priorizacao if priorizacao else 'Não priorizar'}")
                st.write(f"**GH Atualizado:** {'✅ Sim' if gh_atualizada else '❌ Não'}")
                
                if linkedin:
                    st.markdown(f"🔗 [LinkedIn]({linkedin})")
                if greenhouse_id:
                    st.markdown(f"🏢 [Greenhouse]({greenhouse_id})")
                if pbix_file:
                    st.markdown(f"📊 [Arquivo PBIX]({pbix_file})")
                if optional_file:
                    st.markdown(f"📁 [Arquivo Opcional]({optional_file})")
                
                st.divider()
                st.subheader("💬 Comentário Geral")
                st.write(comentario)
                
                st.divider()
                st.subheader("📊 Avaliação por Critério")
                
                criterios = get_criterios_avaliacao(avaliacao_id)
                current_bloco = None
                for bloco, criterio, nota, just in criterios:
                    if bloco != current_bloco:
                        current_bloco = bloco
                        st.markdown(f"### {bloco}")
                    
                    with st.expander(f"{criterio} - Nota: {nota:.1f}"):
                        st.write(f"**Nota:** {nota:.1f}")
                        if nota >= 8:
                            st.success("✅ Critério atendido com excelência")
                        elif nota >= 6:
                            st.warning("⚠️ Critério atendido parcialmente")
                        else:
                            st.error("❌ Critério não atendido adequadamente")
                        if just:
                            st.write("**Justificativa:**")
                            st.write(just)