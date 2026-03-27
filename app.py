import streamlit as st
import pandas as pd
import time
from datetime import datetime
from database import (
    init_db, get_connection, return_connection,
    importar_candidatos_sheets, atualizar_gh_status,
    get_candidatos_com_gh_status, get_ultima_avaliacao_completa,
    get_ou_criar_processo, sincronizar_candidatos_processo
)
from criterios_areas import get_criterios_por_area, get_areas_disponiveis
from allowed_emails import (
    is_email_allowed, get_user_role, is_admin, is_viewer, can_edit,
    add_allowed_email, remove_allowed_email, get_all_allowed_emails
)
import gspread
from google.oauth2.service_account import Credentials
from functools import wraps
import hashlib

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
        "processo_nome": None,  # Mudança: agora usamos nome do processo em vez de ID
        "candidato_id": None,
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

def export_to_csv(data, filename):
    if data:
        df = pd.DataFrame(data)
        csv = df.to_csv(index=False)
        return st.download_button(
            label="📥 Exportar para CSV",
            data=csv,
            file_name=filename,
            mime="text/csv",
            key=f"export_{filename}_{time.time()}"
        )
    return None

# ===== GOOGLE SHEETS INTEGRATION =====
@st.cache_data(ttl=300)  # Cache por 5 minutos
def carregar_google_sheets(force_refresh=False):
    """Carrega dados do Google Sheets com cache"""
    try:
        # Configurar credenciais
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Usar secrets do Streamlit Cloud
        if 'google_credentials' in st.secrets:
            creds_dict = st.secrets["google_credentials"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        else:
            # Para desenvolvimento local
            try:
                creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
            except FileNotFoundError:
                st.warning("Arquivo credentials.json não encontrado. Usando dados de demonstração.")
                return carregar_google_sheets_demo()
        
        client = gspread.authorize(creds)
        
        # Abrir a planilha
        sheet_id = "1ZYJjoZDQAZEIthzNfB5gl4DJ3zkwvQdHhkaeBXDorcg"
        spreadsheet = client.open_by_key(sheet_id)
        
        # Pegar a primeira aba
        worksheet = spreadsheet.get_worksheet(0)
        
        # Pegar todos os dados
        data = worksheet.get_all_records()
        
        return data
        
    except Exception as e:
        st.error(f"Erro ao carregar Google Sheets: {str(e)}")
        return None

def carregar_google_sheets_demo():
    """Dados de demonstração para teste"""
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
            'Status': '✅',
            'Pais': 'Brasil',
            'Nível': 'Entry',
            'Treatment Part': 6.7,
            'Analytics Part': 6,
            'Visual Part': 3.5,
            'Overall Score': 5.4,
            'Comments': '',
            'Responsável Pela Correção': 'Tamires',
            'Data da Correção': '09/03/2026',
            'Priorização': 'Não priorize',
            'GH atualizada?': 'Sim'
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
            'Status': '✅',
            'Pais': 'Brasil',
            'Nível': 'Entry',
            'Treatment Part': 9.4,
            'Analytics Part': 8.75,
            'Visual Part': 9,
            'Overall Score': None,
            'Comments': 'Nao encontrei a etapa onde ele trata os valores com graficas diferentes, embora as grafias parecem ter sido ajustadas.',
            'Responsável Pela Correção': 'Tamires',
            'Data da Correção': '09/02',
            'Priorização': 'Prioridade 1',
            'GH atualizada?': 'Sim'
        }
    ]

def sincronizar_dados_google_sheets():
    """Sincroniza dados do Google Sheets com o banco de dados"""
    with st.spinner("Sincronizando dados do Google Sheets..."):
        dados = carregar_google_sheets()
        
        if not dados:
            st.error("❌ Não foi possível carregar dados do Google Sheets")
            return False
        
        # Agrupar dados por processo (Job Title + Admission Category)
        processos_data = {}
        for linha in dados:
            job_title = linha.get('Job title', '').strip()
            admission_category = linha.get('Admission Category', '').strip()
            
            if job_title and admission_category:
                chave_processo = f"{job_title}||{admission_category}"
                
                if chave_processo not in processos_data:
                    processos_data[chave_processo] = {
                        'nome': f"{job_title} - {admission_category}",
                        'job_title': job_title,
                        'admission_category': admission_category,
                        'candidatos': []
                    }
                
                # Extrair dados do candidato
                candidato = {
                    'timestamp': linha.get('Timestamp'),
                    'email': linha.get('Email address', '').strip(),
                    'nome': linha.get('Full name', '').strip(),
                    'email_application': linha.get('Email used on application', '').strip(),
                    'linkedin': linha.get('LinkedIn', '').strip(),
                    'greenhouse_id': linha.get('Greenhouse ID', '').strip(),
                    'pbix_file': linha.get('Pbix file', '').strip(),
                    'optional_file': linha.get('Optional file', '').strip(),
                    'status_sheets': linha.get('Status', '').strip(),
                    'pais': linha.get('Pais', '').strip(),
                    'nivel': linha.get('Nível', '').strip(),
                    'priorizacao': linha.get('Priorização', '').strip(),
                    'gh_atualizada': linha.get('GH atualizada?', '').strip().lower() == 'sim',
                    'treatment_part': linha.get('Treatment Part'),
                    'analytics_part': linha.get('Analytics Part'),
                    'visual_part': linha.get('Visual Part'),
                    'overall_score': linha.get('Overall Score'),
                    'comments': linha.get('Comments', ''),
                    'responsavel': linha.get('Responsável Pela Correção', ''),
                    'data_correcao': linha.get('Data da Correção', '')
                }
                
                processos_data[chave_processo]['candidatos'].append(candidato)
        
        # Importar cada processo e seus candidatos
        total_importados = 0
        for chave, processo in processos_data.items():
            # Criar ou obter processo
            processo_id = get_ou_criar_processo(
                processo['nome'],
                processo['job_title'],
                processo['admission_category']
            )
            
            if processo_id:
                # Importar candidatos do processo
                resultado = importar_candidatos_sheets(
                    processo['candidatos'],
                    processo_id,
                    st.session_state.user_email
                )
                
                if resultado['sucesso']:
                    total_importados += resultado['novos'] + resultado['atualizados']
        
        if total_importados > 0:
            add_notification(f"✅ Sincronização concluída! {total_importados} candidatos processados.", "success")
            st.session_state.ultima_sincronizacao = datetime.now()
            return True
        else:
            add_notification("ℹ️ Nenhum dado novo para sincronizar.", "info")
            return True

# ===== DATABASE FUNCTIONS =====
def get_processos_ativos():
    """Busca processos ativos (todos, já que não temos mais status de abertura)"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Buscar todos os processos, ordenados por nome
        cursor.execute("""
            SELECT id, nome, job_title, admission_category, area 
            FROM processos 
            ORDER BY nome
        """)
        
        processos = cursor.fetchall()
        cursor.close()
        return processos
    except Exception as e:
        st.error(f"Erro ao buscar processos: {str(e)}")
        return []
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
                c.priorizacao,
                c.timestamp as data_entrada,
                COUNT(a.id) as total_avaliacoes,
                MAX(a.id) as ultima_avaliacao_id
            FROM processos_candidatos pc
            JOIN candidatos c ON pc.candidato_id = c.id
            LEFT JOIN avaliacoes a ON c.id = a.candidato_id AND a.processo_id = %s
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

def get_processo_info(processo_id):
    """Get processo info by id"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nome, job_title, admission_category, area 
            FROM processos WHERE id = %s
        """, (processo_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        st.error(f"Erro ao buscar processo: {str(e)}")
        return None
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
                   c.nome, c.email, p.nome, a.treatment_part, a.analytics_part, a.visual_part
            FROM avaliacoes a
            JOIN candidatos c ON a.candidato_id = c.id
            JOIN processos p ON a.processo_id = p.id
            WHERE a.id = %s
        """, (avaliacao_id,))
        result = cursor.fetchone()
        cursor.close()
        return result
    except Exception as e:
        st.error(f"Erro ao buscar avaliação: {str(e)}")
        return None
    finally:
        if conn:
            return_connection(conn)

def get_avaliacao_criterios(avaliacao_id):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT bloco, criterio, nota, justificativa FROM avaliacoes_criterios WHERE avaliacao_id = %s", (avaliacao_id,))
        result = cursor.fetchall()
        cursor.close()
        return result
    except Exception as e:
        st.error(f"Erro ao buscar critérios: {str(e)}")
        return []
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
        return None
    finally:
        if conn:
            return_connection(conn)

def get_ultima_avaliacao_completa(processo_id, candidato_id):
    """Busca a última avaliação completa"""
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

def save_draft(estrutura, processo_id, candidato_id):
    draft = {
        "processo_id": processo_id,
        "candidato_id": candidato_id,
        "data": datetime.now().isoformat(),
        "avaliacoes": {}
    }
    
    for bloco, criterios in estrutura.items():
        for item in criterios:
            criterio = item["criterio"]
            key_nota = f"{bloco}_{criterio}"
            key_just = f"just_{bloco}_{criterio}"
            
            if key_nota in st.session_state:
                draft["avaliacoes"][key_nota] = st.session_state[key_nota]
            if key_just in st.session_state:
                draft["avaliacoes"][key_just] = st.session_state[key_just]
    
    st.session_state.draft_data = draft
    return True

def load_draft():
    if st.session_state.draft_data:
        for key, value in st.session_state.draft_data.get("avaliacoes", {}).items():
            st.session_state[key] = value
        return True
    return False

# ===== STYLES =====
def get_styles(dark_mode=False):
    if dark_mode:
        return """
        <style>
        .stApp { 
            background: linear-gradient(135deg, #0B1E3D 0%, #1E1E2F 40%, #2D1B3A 100%);
        }
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
        .status-green { color: #22c55e; font-weight: bold; }
        .status-yellow { color: #facc15; font-weight: bold; }
        .status-red { color: #ef4444; font-weight: bold; }
        .status-gray { color: #9ca3af; font-weight: bold; }
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
        .stMetric {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 15px;
        }
        hr { border-color: rgba(255,255,255,0.1); }
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 40px;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        .filter-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .gh-link {
            color: #60a5fa;
            text-decoration: none;
        }
        .gh-link:hover {
            text-decoration: underline;
        }
        .sync-button {
            background: linear-gradient(135deg, #10B981, #059669);
        }
        </style>
        """
    else:
        return """
        <style>
        .stApp { 
            background: linear-gradient(135deg, #f5f7fa 0%, #e8edf5 100%);
        }
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
        .status-green { color: #059669; font-weight: bold; }
        .status-yellow { color: #d97706; font-weight: bold; }
        .status-red { color: #dc2626; font-weight: bold; }
        .status-gray { color: #6b7280; font-weight: bold; }
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
        .stMetric {
            background: white;
            border-radius: 12px;
            padding: 15px;
            box-shadow: 0px 1px 3px rgba(0,0,0,0.1);
        }
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 40px;
            background: white;
            border-radius: 20px;
            box-shadow: 0px 10px 30px rgba(0,0,0,0.1);
        }
        .filter-buttons {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .gh-link {
            color: #3b82f6;
            text-decoration: none;
        }
        .gh-link:hover {
            text-decoration: underline;
        }
        .sync-button {
            background: linear-gradient(135deg, #10B981, #059669);
        }
        </style>
        """

st.markdown(get_styles(st.session_state.dark_mode), unsafe_allow_html=True)

# ===== LOGIN PAGE =====
def login_page():
    st.markdown("""
    <h1 style="
        text-align:center;
        font-size:52px;
        font-weight:800;
        letter-spacing:-2px;
        background: linear-gradient(135deg, #3B82F6, #EC4899, #A855F7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom:20px;
    ">
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
                        name = email.split('@')[0]
                        
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
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                (SELECT COUNT(*) FROM allowed_emails) as total_usuarios,
                (SELECT COUNT(*) FROM processos) as total_processos,
                (SELECT COUNT(*) FROM candidatos) as total_candidatos,
                (SELECT COUNT(*) FROM avaliacoes) as total_avaliacoes,
                (SELECT COUNT(*) FROM candidatos WHERE gh_atualizada = true) as gh_atualizados,
                (SELECT COUNT(*) FROM avaliacoes WHERE treatment_part IS NOT NULL) as avaliacoes_completas
        """)
        stats = cursor.fetchone()
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("👥 Usuários", stats[0])
        with col2:
            st.metric("📋 Processos", stats[1])
        with col3:
            st.metric("👤 Candidatos", stats[2])
        with col4:
            st.metric("📝 Avaliações", stats[3])
        with col5:
            st.metric("✅ GH Atualizado", stats[4])
        with col6:
            st.metric("⭐ Avaliações Completas", stats[5])
        
        st.divider()
        
        # Botão de sincronização manual
        col_sync1, col_sync2, col_sync3 = st.columns([1, 2, 1])
        with col_sync2:
            if st.button("🔄 Sincronizar com Google Sheets", type="primary", use_container_width=True):
                sincronizar_dados_google_sheets()
                st.rerun()
        
        if st.session_state.ultima_sincronizacao:
            st.caption(f"Última sincronização: {st.session_state.ultima_sincronizacao.strftime('%d/%m/%Y %H:%M:%S')}")
        
        st.divider()
        
        cursor.execute("""
            SELECT role, COUNT(*) as total
            FROM allowed_emails
            GROUP BY role
        """)
        roles = cursor.fetchall()
        
        if roles:
            st.subheader("👥 Distribuição por Role")
            cols = st.columns(len(roles))
            for i, (role, total) in enumerate(roles):
                role_name = {"admin": "Administradores", "user": "Avaliadores", "viewer": "Visualizadores"}.get(role, role)
                with cols[i]:
                    st.metric(role_name, total)
        
        st.divider()
        
        st.subheader("📈 Atividade Recente")
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
            LIMIT 10
        """)
        
        atividades = cursor.fetchall()
        
        if atividades:
            df = pd.DataFrame(atividades, columns=["Data", "Processo", "Candidato", "Nota", "Avaliador", "GH Atualizado"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhuma avaliação realizada ainda")
            
        cursor.close()
    except Exception as e:
        st.error(f"Erro ao carregar dashboard: {str(e)}")
    finally:
        if conn:
            return_connection(conn)

def admin_relatorios():
    st.title("📈 Relatórios e Análises")
    
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        report_type = st.selectbox(
            "Tipo de Relatório",
            ["Resumo Geral", "Avaliações por Processo", "Status Greenhouse", "Candidatos Pendentes"]
        )
        
        if report_type == "Resumo Geral":
            cursor.execute("""
                SELECT 
                    p.nome as processo,
                    COUNT(DISTINCT c.id) as candidatos,
                    COUNT(a.id) as avaliacoes,
                    AVG(a.nota_final) as media,
                    SUM(CASE WHEN a.nota_final >= 8 THEN 1 ELSE 0 END) as aprovados,
                    SUM(CASE WHEN c.gh_atualizada THEN 1 ELSE 0 END) as gh_atualizados
                FROM processos p
                LEFT JOIN processos_candidatos pc ON p.id = pc.processo_id
                LEFT JOIN candidatos c ON pc.candidato_id = c.id
                LEFT JOIN avaliacoes a ON p.id = a.processo_id AND c.id = a.candidato_id
                GROUP BY p.id
                ORDER BY p.nome
            """)
            
            data = cursor.fetchall()
            if data:
                df = pd.DataFrame(data, columns=["Processo", "Candidatos", "Avaliações", "Média", "Aprovados", "GH Atualizados"])
                st.dataframe(df, use_container_width=True)
                export_to_csv(data, "relatorio_resumo_geral.csv")
        
        elif report_type == "Avaliações por Processo":
            cursor.execute("SELECT id, nome FROM processos ORDER BY nome")
            processos = cursor.fetchall()
            
            if processos:
                processo_options = {p[1]: p[0] for p in processos}
                selected_processo = st.selectbox("Selecione o Processo", list(processo_options.keys()))
                processo_id = processo_options[selected_processo]
                
                cursor.execute("""
                    SELECT 
                        c.nome as candidato,
                        a.nota_final,
                        a.treatment_part,
                        a.analytics_part,
                        a.visual_part,
                        a.avaliador,
                        a.data,
                        a.comentario_final
                    FROM avaliacoes a
                    JOIN candidatos c ON a.candidato_id = c.id
                    WHERE a.processo_id = %s
                    ORDER BY a.data DESC
                """, (processo_id,))
                
                data = cursor.fetchall()
                if data:
                    df = pd.DataFrame(data, columns=["Candidato", "Nota Final", "Treatment", "Analytics", "Visual", "Avaliador", "Data", "Comentário"])
                    st.dataframe(df, use_container_width=True)
                    export_to_csv(data, f"relatorio_{selected_processo}.csv")
                else:
                    st.info("Nenhuma avaliação encontrada para este processo")
        
        elif report_type == "Status Greenhouse":
            cursor.execute("""
                SELECT 
                    p.nome as processo,
                    c.nome as candidato,
                    c.email,
                    c.greenhouse_id,
                    c.gh_atualizada,
                    CASE 
                        WHEN a.nota_final >= 8 THEN 'Aprovado'
                        WHEN a.nota_final >= 6 THEN 'Em análise'
                        ELSE 'Reprovado'
                    END as status_avaliacao
                FROM candidatos c
                LEFT JOIN processos_candidatos pc ON c.id = pc.candidato_id
                LEFT JOIN processos p ON pc.processo_id = p.id
                LEFT JOIN avaliacoes a ON c.id = a.candidato_id
                WHERE a.id IS NOT NULL
                ORDER BY c.gh_atualizada DESC, p.nome, c.nome
            """)
            
            data = cursor.fetchall()
            if data:
                df = pd.DataFrame(data, columns=["Processo", "Candidato", "Email", "Greenhouse ID", "GH Atualizado", "Status Avaliação"])
                st.dataframe(df, use_container_width=True)
                export_to_csv(data, "relatorio_gh_status.csv")
            else:
                st.info("Nenhum dado encontrado")
        
        elif report_type == "Candidatos Pendentes":
            cursor.execute("""
                SELECT 
                    p.nome as processo,
                    c.nome as candidato,
                    c.email,
                    c.priorizacao,
                    c.timestamp as data_entrada
                FROM candidatos c
                JOIN processos_candidatos pc ON c.id = pc.candidato_id
                JOIN processos p ON pc.processo_id = p.id
                LEFT JOIN avaliacoes a ON c.id = a.candidato_id
                WHERE a.id IS NULL
                ORDER BY 
                    CASE 
                        WHEN c.priorizacao = 'Prioridade 1' THEN 1
                        WHEN c.priorizacao = 'Prioridade 2' THEN 2
                        WHEN c.priorizacao = 'Prioridade 3' THEN 3
                        ELSE 4
                    END,
                    p.nome,
                    c.nome
            """)
            
            data = cursor.fetchall()
            if data:
                df = pd.DataFrame(data, columns=["Processo", "Candidato", "Email", "Priorização", "Data Entrada"])
                st.dataframe(df, use_container_width=True)
                export_to_csv(data, "relatorio_candidatos_pendentes.csv")
                st.info(f"Total de candidatos pendentes: {len(data)}")
            else:
                st.success("🎉 Todos os candidatos já foram avaliados!")
        
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
                            border-radius: 50%; 
                            width: 60px; 
                            height: 60px; 
                            margin: 0 auto 10px;
                            display: flex;
                            align-items: center;
                            justify-content: center;">
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
            
            if st.session_state.view == "processo" and st.session_state.processo_nome:
                # Buscar stats do processo atual
                conn = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM processos WHERE nome = %s", (st.session_state.processo_nome,))
                    result = cursor.fetchone()
                    if result:
                        processo_id = result[0]
                        stats = get_stats_processo(processo_id)
                        if stats and stats[0] > 0:
                            st.markdown("### 📊 Estatísticas")
                            st.metric("Total Candidatos", stats[0])
                            st.metric("Avaliações Realizadas", stats[1] or 0)
                            st.metric("Média Geral", f"{stats[2]:.1f}" if stats[2] else "—")
                            st.metric("Aprovados", stats[3] or 0)
                            st.metric("GH Atualizados", stats[4] or 0)
                    cursor.close()
                except:
                    pass
                finally:
                    if conn:
                        return_connection(conn)
            
            st.markdown("---")
            
            if st.button("🚪 Sair", use_container_width=True):
                for key in ["logged_in", "user_email", "user_name", "user_role", "admin_view", "processo_nome"]:
                    if key in st.session_state:
                        if key == "admin_view":
                            st.session_state[key] = "dashboard"
                        else:
                            st.session_state[key] = None
                st.session_state.logged_in = False
                st.rerun()

# ===== EVALUATION FORM =====
def evaluation_form(candidato_id, processo_id, nome_candidato, email_candidato, nome_processo, area_processo):
    estrutura = get_criterios_por_area(area_processo)
    
    soma_ponderada = 0
    soma_pesos = 0
    reprovado = False
    criterios_avaliados = 0
    total_criterios = sum(len(criterios) for criterios in estrutura.values())
    
    if st.button("📂 Carregar Rascunho"):
        if load_draft():
            add_notification("✅ Rascunho carregado!", "success")
            st.rerun()
    
    for bloco, criterios in estrutura.items():
        st.divider()
        st.header(bloco)
        
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
                        0.0,
                        10.0,
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
    
    show_progress_bar(criterios_avaliados, total_criterios, "Critérios avaliados:")
    
    nota_final = round(soma_ponderada / soma_pesos, 2) if soma_pesos > 0 else 0
    
    if st.session_state.auto_save_enabled:
        current_time = time.time()
        if current_time - st.session_state.last_save_time > 30:
            save_draft(estrutura, processo_id, candidato_id)
            st.session_state.last_save_time = current_time
            st.toast("💾 Rascunho salvo automaticamente", icon="💾")
    
    st.divider()
    st.subheader("🎯 Resultado Final")
    
    # Novos campos específicos para avaliação
    st.subheader("📊 Avaliação Técnica Específica")
    col_t1, col_t2, col_t3 = st.columns(3)
    
    with col_t1:
        treatment_part = st.slider("Treatment Part", 0.0, 10.0, 5.0, step=0.5, key="treatment_part")
    with col_t2:
        analytics_part = st.slider("Analytics Part", 0.0, 10.0, 5.0, step=0.5, key="analytics_part")
    with col_t3:
        visual_part = st.slider("Visual Part", 0.0, 10.0, 5.0, step=0.5, key="visual_part")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Nota Final", nota_final)
    with col2:
        st.metric("Total de Peso", soma_pesos)
    with col3:
        st.metric("Critérios Avaliados", f"{criterios_avaliados}/{total_criterios}")
    
    if reprovado:
        st.error("❌ Reprovado por critério obrigatório abaixo de 6")
    elif nota_final >= 8:
        st.success("✅ Recomendado para contratação")
        st.balloons()
    elif nota_final >= 6:
        st.warning("⚠️ Avaliar melhor - Pontos de melhoria identificados")
    else:
        st.error("❌ Não recomendado - Necessita desenvolvimento")
    
    comentario = st.text_area("Comentário Final Geral*", placeholder="Resumo da avaliação...")
    
    col_actions = st.columns([1, 1])
    with col_actions[0]:
        if st.button("💾 Salvar Rascunho", use_container_width=True):
            save_draft(estrutura, processo_id, candidato_id)
            add_notification("✅ Rascunho salvo!", "success")
    
    with col_actions[1]:
        if st.button("✅ Salvar Avaliação Final", type="primary", use_container_width=True):
            if not comentario:
                st.error("❌ Comentário final é obrigatório")
            else:
                conn = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO avaliacoes 
                        (processo_id, candidato_id, nota_final, avaliador, comentario_final, 
                         treatment_part, analytics_part, visual_part, data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (processo_id, candidato_id, nota_final, st.session_state.user_email, 
                          comentario, treatment_part, analytics_part, visual_part, datetime.now()))
                    conn.commit()
                    avaliacao_id = cursor.lastrowid
                    
                    for bloco, criterios in estrutura.items():
                        for item in criterios:
                            criterio = item["criterio"]
                            nota = st.session_state[f"{bloco}_{criterio}"]
                            just = st.session_state[f"just_{bloco}_{criterio}"]
                            cursor.execute("""
                                INSERT INTO avaliacoes_criterios (avaliacao_id, bloco, criterio, nota, justificativa)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (avaliacao_id, bloco, criterio, nota, just))
                    conn.commit()
                    cursor.close()
                    add_notification(f"✅ Avaliação salva! Nota: {nota_final}", "success")
                    
                    # Limpar rascunho após salvar
                    st.session_state.draft_data = {}
                    
                    st.session_state.view = "processo"
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar avaliação: {str(e)}")
                finally:
                    if conn:
                        return_connection(conn)

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
        
        # Mostrar processos também para admin
        st.markdown("""
        <h1 style="text-align:center; font-size:48px; font-weight:700; background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom:30px;">
            SISTEMA DE AVALIAÇÃO TÉCNICA
        </h1>
        """, unsafe_allow_html=True)
        
        # Botão de sincronização
        col_sync1, col_sync2, col_sync3 = st.columns([1, 2, 1])
        with col_sync2:
            if st.button("🔄 Sincronizar com Google Sheets", use_container_width=True):
                sincronizar_dados_google_sheets()
                st.rerun()
        
        if st.session_state.ultima_sincronizacao:
            st.caption(f"📅 Última sincronização: {st.session_state.ultima_sincronizacao.strftime('%d/%m/%Y %H:%M:%S')}")
        
        st.divider()
        st.markdown("### 📋 Processos Disponíveis")
        
        processos = get_processos_ativos()
        if not processos:
            st.info("✨ Nenhum processo encontrado. Clique em 'Sincronizar' para importar os dados do Google Sheets.")
        else:
            for proc in processos:
                id_p, nome, job_title, admission_category, area = proc
                
                st.markdown(f"""
                <div class="card">
                    <h3>{nome}</h3>
                    <p><strong>Job Title:</strong> {job_title} • <strong>Categoria:</strong> {admission_category}</p>
                    <p><strong>Área:</strong> {area if area else 'Não definida'}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("📂 Entrar", key=f"entrar_{id_p}"):
                    st.session_state.processo_nome = nome
                    st.session_state.processo_id = id_p
                    st.session_state.view = "processo"
                    st.rerun()
    
    else:
        # Usuários normais
        if st.session_state.view == "home":
            st.markdown("""
            <h1 style="text-align:center; font-size:48px; font-weight:700; background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom:30px;">
                SISTEMA DE AVALIAÇÃO TÉCNICA
            </h1>
            """, unsafe_allow_html=True)
            
            # Botão de sincronização (apenas admin vê o botão, mas todos podem ver o status)
            if st.session_state.user_role == "admin":
                col_sync1, col_sync2, col_sync3 = st.columns([1, 2, 1])
                with col_sync2:
                    if st.button("🔄 Sincronizar com Google Sheets", use_container_width=True):
                        sincronizar_dados_google_sheets()
                        st.rerun()
            
            if st.session_state.ultima_sincronizacao:
                st.caption(f"📅 Dados sincronizados em: {st.session_state.ultima_sincronizacao.strftime('%d/%m/%Y %H:%M:%S')}")
            
            st.divider()
            st.markdown("### 📋 Processos Disponíveis")
            
            processos = get_processos_ativos()
            if not processos:
                st.info("✨ Nenhum processo encontrado. Aguarde a sincronização com o Google Sheets.")
            else:
                for proc in processos:
                    id_p, nome, job_title, admission_category, area = proc
                    
                    st.markdown(f"""
                    <div class="card">
                        <h3>{nome}</h3>
                        <p><strong>Job Title:</strong> {job_title} • <strong>Categoria:</strong> {admission_category}</p>
                        <p><strong>Área:</strong> {area if area else 'Não definida'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("📂 Entrar", key=f"entrar_{id_p}"):
                        st.session_state.processo_nome = nome
                        st.session_state.processo_id = id_p
                        st.session_state.view = "processo"
                        st.rerun()
        
        elif st.session_state.view == "processo":
            processo_id = st.session_state.processo_id
            processo_nome = st.session_state.processo_nome
            processo_info = get_processo_info(processo_id)
            
            if processo_info:
                nome_processo, job_title, admission_category, area_processo = processo_info
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.title(f"📂 {nome_processo}")
                    st.caption(f"Job Title: {job_title} | Categoria: {admission_category}")
                with col2:
                    if st.button("🏠 Home"):
                        st.session_state.view = "home"
                        st.session_state.processo_id = None
                        st.session_state.processo_nome = None
                        st.rerun()
                
                st.divider()
                
                st.markdown("### 👥 Candidatos")
                
                # Filtros de candidatos
                col_filter1, col_filter2, col_filter3 = st.columns(3)
                
                with col_filter1:
                    if st.button("👥 Todos os Candidatos", key="filter_todos", use_container_width=True):
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
                
                if st.session_state.candidato_filter == "avaliados":
                    st.info("📌 Exibindo apenas candidatos **avaliados**")
                elif st.session_state.candidato_filter == "pendentes":
                    st.info("📌 Exibindo apenas candidatos **pendentes**")
                else:
                    st.info("📌 Exibindo **todos** os candidatos")
                
                st.markdown("---")
                
                # Buscar candidatos
                candidatos_data = get_candidatos_processo_completo(processo_id)
                
                candidatos_avaliados = 0
                candidatos_pendentes = 0
                candidatos_filtrados = []
                
                for cand in candidatos_data:
                    id_c, nome, email, linkedin, greenhouse_id, gh_atualizada, pbix_file, optional_file, priorizacao, data_entrada, total_avaliacoes, ultima_avaliacao_id = cand
                    
                    # Verificar se tem avaliação
                    if ultima_avaliacao_id:
                        candidatos_avaliados += 1
                    else:
                        candidatos_pendentes += 1
                    
                    # Aplicar filtro
                    if st.session_state.candidato_filter == "avaliados" and not ultima_avaliacao_id:
                        continue
                    elif st.session_state.candidato_filter == "pendentes" and ultima_avaliacao_id:
                        continue
                    
                    candidatos_filtrados.append(cand)
                
                # Mostrar contagem
                if st.session_state.candidato_filter == "avaliados":
                    st.caption(f"Mostrando {len(candidatos_filtrados)} de {candidatos_avaliados} candidatos avaliados")
                elif st.session_state.candidato_filter == "pendentes":
                    st.caption(f"Mostrando {len(candidatos_filtrados)} de {candidatos_pendentes} candidatos pendentes")
                else:
                    st.caption(f"Mostrando todos os {len(candidatos_filtrados)} candidatos")
                
                # Exibir candidatos
                for cand in candidatos_filtrados:
                    id_c, nome, email, linkedin, greenhouse_id, gh_atualizada, pbix_file, optional_file, priorizacao, data_entrada, total_avaliacoes, ultima_avaliacao_id = cand
                    
                    # Buscar avaliação se existir
                    if ultima_avaliacao_id:
                        avaliacao = get_ultima_avaliacao_completa(processo_id, id_c)
                        if avaliacao:
                            nota_final, avaliacao_id, avaliador, treatment_part, analytics_part, visual_part, comentario, data = avaliacao
                            
                            if nota_final >= 8:
                                status_text = "✅ Aprovado"
                                badge = "badge-success"
                            elif nota_final >= 6:
                                status_text = "⚠️ Em análise"
                                badge = "badge-warning"
                            else:
                                status_text = "❌ Reprovado"
                                badge = "badge-danger"
                            
                            status_html = f'<span class="badge {badge}">{status_text}</span>'
                            nota_html = f'⭐ {nota_final:.1f}'
                            
                            # Badge do Greenhouse
                            if gh_atualizada:
                                gh_badge = '<span class="badge badge-gh-done">✅ GH Atualizado</span>'
                            else:
                                gh_badge = '<span class="badge badge-gh-pending">⚠️ Pendente GH</span>'
                            
                            # Badge de priorização
                            priorizacao_badge = ""
                            if priorizacao == "Prioridade 1":
                                priorizacao_badge = '<span class="badge badge-danger">🔴 Prioridade 1</span>'
                            elif priorizacao == "Prioridade 2":
                                priorizacao_badge = '<span class="badge badge-warning">🟡 Prioridade 2</span>'
                            elif priorizacao == "Prioridade 3":
                                priorizacao_badge = '<span class="badge badge-info">🔵 Prioridade 3</span>'
                        else:
                            status_html = '<span class="badge badge-info">⏳ Pendente</span>'
                            nota_html = '—'
                            avaliacao_id = None
                            gh_badge = '<span class="badge badge-gh-pending">⚠️ Pendente GH</span>' if not gh_atualizada else '<span class="badge badge-gh-done">✅ GH Atualizado</span>'
                            priorizacao_badge = ""
                    else:
                        status_html = '<span class="badge badge-info">⏳ Pendente</span>'
                        nota_html = '—'
                        avaliacao_id = None
                        gh_badge = '<span class="badge badge-gh-pending">⚠️ Pendente GH</span>' if not gh_atualizada else '<span class="badge badge-gh-done">✅ GH Atualizado</span>'
                        priorizacao_badge = ""
                    
                    st.markdown(f"""
                    <div class="card">
                        <h3>{nome} {status_html} {priorizacao_badge}</h3>
                        <p>📧 {email}</p>
                        <p>{nota_html} {gh_badge}</p>
                        <p><small>📅 Entrada: {data_entrada if data_entrada else 'Data não informada'}</small></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Exibir links e informações adicionais
                    with st.expander("📎 Detalhes e Links"):
                        if linkedin:
                            st.markdown(f"🔗 [LinkedIn]({linkedin})")
                        if greenhouse_id:
                            st.markdown(f"🏢 [Greenhouse]({greenhouse_id})")
                        if pbix_file:
                            st.markdown(f"📊 [Arquivo PBIX]({pbix_file})")
                        if optional_file:
                            st.markdown(f"📁 [Arquivo Opcional]({optional_file})")
                        
                        # Se já avaliado, mostrar notas específicas
                        if avaliacao_id and 'avaliacao' in locals() and avaliacao:
                            st.markdown("**Notas da Avaliação Técnica:**")
                            col_t1, col_t2, col_t3 = st.columns(3)
                            with col_t1:
                                st.metric("Treatment", f"{treatment_part:.1f}" if treatment_part else "—")
                            with col_t2:
                                st.metric("Analytics", f"{analytics_part:.1f}" if analytics_part else "—")
                            with col_t3:
                                st.metric("Visual", f"{visual_part:.1f}" if visual_part else "—")
                    
                    # Botões de ação
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if avaliacao_id:
                            if st.button("🔍 Ver Detalhes", key=f"det_{id_c}"):
                                st.session_state.avaliacao_id = avaliacao_id
                                st.session_state.view = "detalhe_avaliacao"
                                st.rerun()
                    
                    with col2:
                        if not avaliacao_id and can_edit(st.session_state.user_email):
                            if st.button("📝 Avaliar", key=f"avaliar_{id_c}"):
                                st.session_state.candidato_id = id_c
                                st.session_state.view = "avaliar"
                                st.rerun()
                    
                    with col3:
                        if can_edit(st.session_state.user_email) and greenhouse_id:
                            # Checkbox para atualizar status do Greenhouse
                            gh_checkbox = st.checkbox(
                                "✅ Marcar como atualizado no Greenhouse",
                                value=gh_atualizada,
                                key=f"gh_{id_c}"
                            )
                            if gh_checkbox != gh_atualizada:
                                if atualizar_gh_status(id_c, gh_checkbox):
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
                candidato_id = st.session_state.candidato_id
                processo_id = st.session_state.processo_id
                
                if st.button("← Voltar"):
                    st.session_state.view = "processo"
                    st.rerun()
                
                conn = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT nome, email, linkedin, greenhouse_id, pbix_file, optional_file 
                        FROM candidatos WHERE id = %s
                    """, (candidato_id,))
                    result = cursor.fetchone()
                    if result:
                        nome_candidato, email_candidato, linkedin, greenhouse_id, pbix_file, optional_file = result
                    cursor.close()
                    
                    cursor = conn.cursor()
                    cursor.execute("SELECT nome, area FROM processos WHERE id = %s", (processo_id,))
                    nome_processo, area_processo = cursor.fetchone()
                    cursor.close()
                    
                    st.title(f"📝 Avaliar: {nome_candidato}")
                    st.caption(f"📧 {email_candidato} | 📂 {nome_processo} | Área: {area_processo}")
                    
                    # Mostrar links do candidato
                    with st.expander("📎 Links do Candidato"):
                        if linkedin:
                            st.markdown(f"🔗 [LinkedIn]({linkedin})")
                        if greenhouse_id:
                            st.markdown(f"🏢 [Greenhouse]({greenhouse_id})")
                        if pbix_file:
                            st.markdown(f"📊 [Arquivo PBIX]({pbix_file})")
                        if optional_file:
                            st.markdown(f"📁 [Arquivo Opcional]({optional_file})")
                    
                    st.divider()
                    
                    evaluation_form(candidato_id, processo_id, nome_candidato, email_candidato, nome_processo, area_processo)
                    
                except Exception as e:
                    st.error(f"Erro ao carregar avaliação: {str(e)}")
                finally:
                    if conn:
                        return_connection(conn)
        
        elif st.session_state.view == "detalhe_avaliacao":
            avaliacao_id = st.session_state.avaliacao_id
            
            if st.button("← Voltar"):
                st.session_state.view = "processo"
                st.rerun()
            
            avaliacao = get_avaliacao_info_completa(avaliacao_id)
            if avaliacao:
                nota_final, avaliador, comentario, data, candidato_nome, candidato_email, processo_nome, treatment_part, analytics_part, visual_part = avaliacao
                
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
                    st.metric("Avaliador", avaliador)
                
                st.write(f"**Candidato:** {candidato_nome} ({candidato_email})")
                st.write(f"**Processo:** {processo_nome}")
                st.write(f"**Data:** {data}")
                
                # Mostrar notas específicas
                st.divider()
                st.subheader("📊 Notas da Avaliação Técnica")
                col_t1, col_t2, col_t3 = st.columns(3)
                with col_t1:
                    st.metric("Treatment Part", f"{treatment_part:.1f}" if treatment_part else "—")
                with col_t2:
                    st.metric("Analytics Part", f"{analytics_part:.1f}" if analytics_part else "—")
                with col_t3:
                    st.metric("Visual Part", f"{visual_part:.1f}" if visual_part else "—")
                
                st.divider()
                st.subheader("💬 Comentário Geral")
                st.write(comentario)
                
                st.divider()
                st.subheader("📊 Avaliação por Critério")
                
                criterios = get_avaliacao_criterios(avaliacao_id)
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