import streamlit as st
import pandas as pd
import io
import time
from datetime import datetime
from database import init_db, get_connection
from functools import wraps

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="Sistema de Avaliação Técnica",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== DATABASE CONNECTION =====
init_db()
conn = get_connection()
cursor = conn.cursor()

# ===== SESSION STATE INITIALIZATION =====
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "view": "home",
        "processo_id": None,
        "candidato_id": None,
        "avaliacao_id": None,
        "dark_mode": False,
        "auto_save_enabled": True,
        "last_save_time": 0,
        "draft_data": {},
        "notifications": [],
        "logged_in": False,
        "user_email": None,
        "user_name": None,
        "user_role": None,
        "admin_view": "dashboard"
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ===== HELPER FUNCTIONS =====
def safe_db_operation(func):
    """Decorator for safe database operations"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"❌ Erro no banco de dados: {str(e)}")
            return None
    return wrapper

def add_notification(message, type="info"):
    """Add notification to session state"""
    st.session_state.notifications.append({
        "message": message,
        "type": type,
        "timestamp": datetime.now()
    })

def show_notifications():
    """Display all notifications"""
    for notif in st.session_state.notifications[-5:]:  # Show last 5
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
    """Show progress bar for evaluation completion"""
    if total > 0:
        progress = current / total
        st.progress(progress)
        st.caption(f"{label} {current}/{total} itens avaliados")

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_processos_cached():
    """Get cached processos data based on user role"""
    if st.session_state.user_role == "admin":
        cursor.execute("SELECT id, nome, area, senioridade, status, local FROM processos ORDER BY id DESC")
    else:
        cursor.execute("""
            SELECT p.id, p.nome, p.area, p.senioridade, p.status, p.local 
            FROM processos p
            JOIN usuarios_processos up ON p.id = up.processo_id
            WHERE up.usuario_email = %s
            ORDER BY p.id DESC
        """, (st.session_state.user_email,))
    return cursor.fetchall()

@st.cache_data(ttl=300)
def get_candidatos_processo_cached(processo_id):
    """Get cached candidatos data for a processo"""
    cursor.execute("""
        SELECT 
            c.id, 
            c.nome, 
            c.email,
            COUNT(a.id) as total_avaliacoes,
            MAX(a.nota_final) as ultima_nota
        FROM processos_candidatos pc
        JOIN candidatos c ON pc.candidato_id = c.id
        LEFT JOIN avaliacoes a
            ON c.id = a.candidato_id AND a.processo_id = ?
        WHERE pc.processo_id = ?
        GROUP BY c.id
        ORDER BY c.nome
    """, (processo_id, processo_id))
    return cursor.fetchall()

def export_to_csv(data, filename):
    """Export data to CSV"""
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

def confirm_action(action_name, key_prefix=""):
    """Add confirmation dialog for destructive actions"""
    confirm_key = f"confirm_{key_prefix}_{action_name}"
    
    if st.button(action_name, key=f"btn_{confirm_key}"):
        with st.popover("⚠️ Confirmar ação"):
            st.warning("Tem certeza que deseja realizar esta ação?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Sim", key=f"yes_{confirm_key}"):
                    return True
            with col2:
                if st.button("❌ Não", key=f"no_{confirm_key}"):
                    return False
    return False

def save_draft(estrutura, processo_id, candidato_id):
    """Save evaluation draft"""
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
    """Load evaluation draft"""
    if st.session_state.draft_data:
        for key, value in st.session_state.draft_data.get("avaliacoes", {}).items():
            st.session_state[key] = value
        return True
    return False

def check_permission(required_role=None, required_processo=None):
    """Check if user has permission to access resource"""
    if not st.session_state.logged_in:
        return False
    
    if required_role and st.session_state.user_role != required_role:
        return False
    
    if required_processo and st.session_state.user_role != "admin":
        cursor.execute("""
            SELECT 1 FROM usuarios_processos 
            WHERE usuario_email = %s AND processo_id = %s
        """, (st.session_state.user_email, required_processo))
        if not cursor.fetchone():
            return False
    
    return True

# ===== STYLES =====
def get_styles(dark_mode=False):
    """Get CSS styles based on mode"""
    if dark_mode:
        return """
        <style>
        /* Dark Mode Styles */
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
        hr {
            border-color: rgba(255,255,255,0.1);
        }
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 40px;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        </style>
        """
    else:
        return """
        <style>
        /* Light Mode Styles */
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
        </style>
        """

# Apply styles
st.markdown(get_styles(st.session_state.dark_mode), unsafe_allow_html=True)

# ===== LOGIN PAGE =====
def login_page():
    """Display login page - email only, no password"""
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
            st.caption("ℹ️ Use seu email corporativo. O admin@artefact.com tem acesso administrativo total.")
            
            if st.button("🔐 Entrar", type="primary", use_container_width=True):
                if email:
                    # Check if user exists in database
                    cursor.execute(
                        "SELECT nome, role FROM usuarios WHERE email = %s",
                        (email,)
                    )
                    user = cursor.fetchone()
                    
                    if user:
                        # User exists
                        st.session_state.logged_in = True
                        st.session_state.user_email = email
                        st.session_state.user_name = user[0]
                        st.session_state.user_role = user[1]
                        add_notification(f"Bem-vindo, {user[0]}!", "success")
                        st.rerun()
                    else:
                        # New user - auto-register as viewer
                        nome = email.split('@')[0]  # Use part before @ as name
                        role = "admin" if email == "admin@artefact.com" else "viewer"
                        
                        cursor.execute("""
                            INSERT INTO usuarios (nome, email, role)
                            VALUES (%s, %s, %s)
                        """, (nome, email, role))
                        conn.commit()
                        
                        st.session_state.logged_in = True
                        st.session_state.user_email = email
                        st.session_state.user_name = nome
                        st.session_state.user_role = role
                        add_notification(f"Bem-vindo, {nome}! Seu acesso foi registrado.", "success")
                        st.rerun()
                else:
                    st.warning("⚠️ Digite seu email para acessar")
            
            st.markdown('</div>', unsafe_allow_html=True)

# ===== SIDEBAR =====
def render_sidebar():
    """Render sidebar with user info and controls"""
    with st.sidebar:
        if st.session_state.logged_in:
            # User info
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
            
            # Dark mode toggle
            if st.toggle("🌙 Modo Escuro", value=st.session_state.dark_mode):
                if not st.session_state.dark_mode:
                    st.session_state.dark_mode = True
                    st.rerun()
            else:
                if st.session_state.dark_mode:
                    st.session_state.dark_mode = False
                    st.rerun()
            
            # Auto-save toggle (only for user role)
            if st.session_state.user_role == "user":
                st.session_state.auto_save_enabled = st.toggle(
                    "💾 Auto-save",
                    value=st.session_state.auto_save_enabled,
                    help="Salvar rascunho automaticamente a cada 30 segundos"
                )
            
            st.markdown("---")
            
            # Admin menu (only for admin)
            if st.session_state.user_role == "admin":
                st.markdown("### 🛠️ Administração")
                admin_option = st.radio(
                    "Menu Admin",
                    ["📊 Dashboard", "👥 Usuários", "🔐 Permissões", "📈 Relatórios"],
                    key="admin_menu"
                )
                st.session_state.admin_view = admin_option.lower().replace(" ", "_")
            
            # Statistics (if in processo view)
            if st.session_state.view == "processo" and st.session_state.processo_id:
                cursor.execute("""
                    SELECT 
                        COUNT(DISTINCT c.id) as total_candidatos,
                        COUNT(a.id) as total_avaliacoes,
                        AVG(a.nota_final) as media_geral,
                        SUM(CASE WHEN a.nota_final >= 8 THEN 1 ELSE 0 END) as aprovados
                    FROM processos_candidatos pc
                    JOIN candidatos c ON pc.candidato_id = c.id
                    LEFT JOIN avaliacoes a ON c.id = a.candidato_id AND a.processo_id = ?
                    WHERE pc.processo_id = ?
                """, (st.session_state.processo_id, st.session_state.processo_id))
                
                stats = cursor.fetchone()
                if stats and stats[0] > 0:
                    st.markdown("### 📊 Estatísticas")
                    st.metric("Total Candidatos", stats[0])
                    st.metric("Avaliações Realizadas", stats[1] or 0)
                    st.metric("Média Geral", f"{stats[2]:.1f}" if stats[2] else "—")
                    st.metric("Aprovados", stats[3] or 0)
            
            st.markdown("---")
            
            # Logout button
            if st.button("🚪 Sair", use_container_width=True):
                for key in ["logged_in", "user_email", "user_name", "user_role", "admin_view"]:
                    if key in st.session_state:
                        st.session_state[key] = None if key != "admin_view" else "dashboard"
                st.session_state.logged_in = False
                st.rerun()
            
            st.markdown("---")
            if st.session_state.user_role == "user" and st.session_state.auto_save_enabled:
                st.caption("💡 Dica: Use Ctrl+S para salvar rapidamente")
                st.caption(f"🕒 Último auto-save: {datetime.fromtimestamp(st.session_state.last_save_time).strftime('%H:%M:%S') if st.session_state.last_save_time else 'Nunca'}")

# ===== ADMIN FUNCTIONS =====
def admin_dashboard():
    """Admin dashboard with system overview"""
    st.title("📊 Dashboard Administrativo")
    
    # System stats
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM usuarios) as total_usuarios,
            (SELECT COUNT(*) FROM processos) as total_processos,
            (SELECT COUNT(*) FROM candidatos) as total_candidatos,
            (SELECT COUNT(*) FROM avaliacoes) as total_avaliacoes
    """)
    stats = cursor.fetchone()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Usuários", stats[0])
    with col2:
        st.metric("📋 Processos", stats[1])
    with col3:
        st.metric("👤 Candidatos", stats[2])
    with col4:
        st.metric("📝 Avaliações", stats[3])
    
    st.divider()
    
    # User distribution
    st.subheader("👥 Distribuição de Usuários")
    cursor.execute("""
        SELECT role, COUNT(*) as total
        FROM usuarios
        GROUP BY role
    """)
    roles = cursor.fetchall()
    
    if roles:
        col1, col2, col3 = st.columns(3)
        role_colors = {"admin": "#EF4444", "user": "#3B82F6", "viewer": "#10B981"}
        for i, (role, total) in enumerate(roles):
            role_name = {"admin": "Administradores", "user": "Avaliadores", "viewer": "Visualizadores"}.get(role, role)
            with [col1, col2, col3][i % 3]:
                st.metric(role_name, total)
    
    st.divider()
    
    # Recent activity
    st.subheader("📈 Atividade Recente")
    cursor.execute("""
        SELECT 
            a.data,
            p.nome as processo,
            c.nome as candidato,
            a.nota_final,
            u.nome as avaliador
        FROM avaliacoes a
        JOIN processos p ON a.processo_id = p.id
        JOIN candidatos c ON a.candidato_id = c.id
        JOIN usuarios u ON a.avaliador_email = u.email
        ORDER BY a.data DESC
        LIMIT 10
    """)
    
    atividades = cursor.fetchall()
    if atividades:
        df = pd.DataFrame(atividades, columns=["Data", "Processo", "Candidato", "Nota", "Avaliador"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhuma avaliação realizada ainda")

def admin_usuarios():
    """User management interface"""
    st.title("👥 Gerenciamento de Usuários")
    
    # List users
    cursor.execute("SELECT email, nome, role, created_at FROM usuarios ORDER BY created_at DESC")
    usuarios = cursor.fetchall()
    
    if usuarios:
        df = pd.DataFrame(usuarios, columns=["Email", "Nome", "Role", "Data Cadastro"])
        st.dataframe(df, use_container_width=True)
    
    st.divider()
    
    # Change user role
    with st.expander("✏️ Alterar Role de Usuário"):
        cursor.execute("SELECT email, nome, role FROM usuarios")
        users = cursor.fetchall()
        
        if users:
            user_options = {f"{u[1]} ({u[0]})": u[0] for u in users}
            selected_user = st.selectbox("Selecione o usuário", list(user_options.keys()))
            user_email = user_options[selected_user]
            
            current_role = [u[2] for u in users if u[0] == user_email][0]
            
            new_role = st.selectbox(
                "Nova Role",
                ["admin", "user", "viewer"],
                index=["admin", "user", "viewer"].index(current_role)
            )
            
            if st.button("Atualizar Role", type="primary"):
                if new_role != current_role:
                    cursor.execute("""
                        UPDATE usuarios SET role = %s WHERE email = %s
                    """, (new_role, user_email))
                    conn.commit()
                    add_notification(f"✅ Role de {user_email} alterada para {new_role}", "success")
                    st.rerun()
                else:
                    st.info("Role já é a mesma")
        else:
            st.info("Nenhum usuário cadastrado")

def admin_permissoes():
    """Manage user permissions for processes"""
    st.title("🔐 Gerenciamento de Permissões")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👤 Usuários")
        cursor.execute("SELECT email, nome, role FROM usuarios WHERE role IN ('user', 'viewer')")
        usuarios = cursor.fetchall()
        
        if usuarios:
            user_options = {f"{u[1]} ({u[0]})": u[0] for u in usuarios}
            selected_user = st.selectbox("Selecione um usuário", list(user_options.keys()))
            user_email = user_options[selected_user]
            user_role = [u[2] for u in usuarios if u[0] == user_email][0]
            
            if user_role == "viewer":
                st.info("👀 Visualizadores têm acesso apenas de leitura a todos os processos")
        else:
            st.info("Nenhum avaliador ou visualizador cadastrado")
            return
    
    with col2:
        st.subheader("📋 Processos")
        cursor.execute("SELECT id, nome, status FROM processos ORDER BY nome")
        processos = cursor.fetchall()
        
        if processos and user_role == "user":
            # Get user's current permissions
            cursor.execute("""
                SELECT processo_id FROM usuarios_processos 
                WHERE usuario_email = %s
            """, (user_email,))
            user_processos = [p[0] for p in cursor.fetchall()]
            
            for processo in processos:
                id_p, nome_p, status_p = processo
                is_checked = id_p in user_processos
                
                if st.checkbox(f"{nome_p} ({status_p})", value=is_checked, key=f"perm_{user_email}_{id_p}"):
                    if not is_checked:
                        cursor.execute("""
                            INSERT INTO usuarios_processos (usuario_email, processo_id)
                            VALUES (%s, %s)
                        """, (user_email, id_p))
                        conn.commit()
                        add_notification(f"✅ Permissão adicionada para {nome_p}", "success")
                else:
                    if is_checked:
                        cursor.execute("""
                            DELETE FROM usuarios_processos 
                            WHERE usuario_email = %s AND processo_id = %s
                        """, (user_email, id_p))
                        conn.commit()
                        add_notification(f"❌ Permissão removida para {nome_p}", "warning")
            
            if st.button("💾 Salvar Permissões", use_container_width=True):
                st.rerun()
        elif user_role == "viewer":
            st.info("👀 Visualizadores têm acesso a todos os processos automaticamente")

def admin_relatorios():
    """Generate reports"""
    st.title("📈 Relatórios e Análises")
    
    # Report type selection
    report_type = st.selectbox(
        "Tipo de Relatório",
        ["Resumo Geral", "Avaliações por Processo", "Desempenho por Avaliador", "Análise de Critérios"]
    )
    
    if report_type == "Resumo Geral":
        cursor.execute("""
            SELECT 
                p.nome as processo,
                COUNT(DISTINCT c.id) as candidatos,
                COUNT(a.id) as avaliacoes,
                AVG(a.nota_final) as media,
                SUM(CASE WHEN a.nota_final >= 8 THEN 1 ELSE 0 END) as aprovados
            FROM processos p
            LEFT JOIN processos_candidatos pc ON p.id = pc.processo_id
            LEFT JOIN candidatos c ON pc.candidato_id = c.id
            LEFT JOIN avaliacoes a ON p.id = a.processo_id AND c.id = a.candidato_id
            GROUP BY p.id
            ORDER BY p.nome
        """)
        
        data = cursor.fetchall()
        if data:
            df = pd.DataFrame(data, columns=["Processo", "Candidatos", "Avaliações", "Média", "Aprovados"])
            st.dataframe(df, use_container_width=True)
            
            # Export button
            export_to_csv(data, "relatorio_resumo_geral.csv")
    
    elif report_type == "Avaliações por Processo":
        processos = get_processos_cached()
        processo_names = [p[1] for p in processos]
        selected_processo = st.selectbox("Selecione o Processo", processo_names)
        
        if selected_processo:
            cursor.execute("""
                SELECT 
                    c.nome as candidato,
                    a.nota_final,
                    u.nome as avaliador,
                    a.data,
                    a.comentario_final
                FROM avaliacoes a
                JOIN candidatos c ON a.candidato_id = c.id
                JOIN usuarios u ON a.avaliador_email = u.email
                JOIN processos p ON a.processo_id = p.id
                WHERE p.nome = %s
                ORDER BY a.data DESC
            """, (selected_processo,))
            
            data = cursor.fetchall()
            if data:
                df = pd.DataFrame(data, columns=["Candidato", "Nota", "Avaliador", "Data", "Comentário"])
                st.dataframe(df, use_container_width=True)
                export_to_csv(data, f"relatorio_{selected_processo}.csv")
            else:
                st.info("Nenhuma avaliação encontrada para este processo")

# =====================================================
# 🏠 HOME (After Login)
# =====================================================
def home_page():
    """Main home page after login"""
    st.markdown("""
    <h1 style="
        text-align:center;
        font-size:48px;
        font-weight:700;
        letter-spacing:-1.5px;
        background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom:30px;
    ">
        SISTEMA DE AVALIAÇÃO TÉCNICA
    </h1>
    """, unsafe_allow_html=True)
    
    # Create Process Section (only for admin)
    if st.session_state.user_role == "admin":
        with st.expander("➕ Criar Novo Processo"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome do Processo*", key="novo_nome_processo")
                area = st.selectbox(
                    "Área*",
                    ["Analytics Engineer", "Data Engineer", "Data Scientist", "Business Intelligence"],
                    key="novo_area_processo"
                )
                senioridade = st.selectbox(
                    "Senioridade*",
                    ["Estágio", "Júnior", "Pleno", "Sênior", "Especialista"],
                    key="novo_senioridade"
                )
            
            with col2:
                status = st.selectbox(
                    "Status*",
                    ["Aberto", "Fechado"],
                    key="novo_status"
                )
                local = st.selectbox(
                    "Local*",
                    ["BRASIL", "LATAM", "EUA", "Europa"],
                    key="novo_local_processo"
                )
                descricao = st.text_area("Descrição do Processo (opcional)", key="novo_descricao")
            
            if st.button("✅ Criar Processo", type="primary", use_container_width=True):
                if not nome:
                    st.error("❌ Nome do processo é obrigatório")
                else:
                    try:
                        cursor.execute("""
                            INSERT INTO processos (nome, area, senioridade, status, local, descricao)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (nome, area, senioridade, status, local, descricao))
                        conn.commit()
                        add_notification(f"✅ Processo '{nome}' criado com sucesso!", "success")
                        
                        # Reset inputs
                        for key in ["novo_nome_processo", "novo_area_processo", "novo_senioridade", 
                                    "novo_status", "novo_local_processo", "novo_descricao"]:
                            if key in st.session_state:
                                del st.session_state[key]
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao criar processo: {str(e)}")
    
    st.divider()
    
    # List Processes
    st.markdown("### 📋 Meus Processos")
    
    processos = get_processos_cached()
    
    if not processos:
        st.info("✨ Nenhum processo encontrado.")
        if st.session_state.user_role == "admin":
            st.info("Crie um novo processo usando o botão acima!")
    else:
        # Search and filter
        col_search, col_filter = st.columns([3, 1])
        with col_search:
            search_term = st.text_input("🔍 Buscar processo", placeholder="Digite o nome do processo...")
        with col_filter:
            status_filter = st.selectbox("Filtrar por status", ["Todos", "Aberto", "Fechado"])
        
        # Filter processes
        filtered_processos = []
        for proc in processos:
            id_p, nome, area, senioridade, status_proc, local = proc
            
            if search_term and search_term.lower() not in nome.lower():
                continue
            if status_filter != "Todos" and status_proc != status_filter:
                continue
            
            filtered_processos.append(proc)
        
        # Display processes in cards
        for proc in filtered_processos:
            id_p, nome, area, senioridade, status_proc, local = proc
            
            # Determine status badge
            if status_proc == "Aberto":
                status_badge = '<span class="badge badge-success">🟢 Aberto</span>'
            else:
                status_badge = '<span class="badge badge-danger">🔴 Fechado</span>'
            
            with st.container():
                st.markdown(f"""
                <div class="card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3 style="margin: 0;">{nome}</h3>
                            <p style="margin: 5px 0 0 0; color: #9CA3AF;">
                                {area} • {senioridade} • {local} {status_badge}
                            </p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("📂 Entrar", key=f"entrar_{id_p}", use_container_width=True):
                        st.session_state.processo_id = id_p
                        st.session_state.view = "processo"
                        st.rerun()

# =====================================================
# MAIN APP FLOW
# =====================================================

# Check if user is logged in
if not st.session_state.logged_in:
    # Show login page
    login_page()
else:
    # User is logged in, show sidebar and main content
    render_sidebar()
    
    # Show notifications
    show_notifications()
    
    # Admin views
    if st.session_state.user_role == "admin" and st.session_state.admin_view != "dashboard":
        if st.session_state.admin_view == "usuários":
            admin_usuarios()
        elif st.session_state.admin_view == "permissões":
            admin_permissoes()
        elif st.session_state.admin_view == "relatórios":
            admin_relatorios()
        else:
            admin_dashboard()
    else:
        # Regular app flow
        if st.session_state.view == "home":
            home_page()
        elif st.session_state.view == "processo":
            # Processo view (simplified - same as before but with permission checks)
            processo_id = st.session_state.processo_id
            
            # Check permission
            if not check_permission(required_processo=processo_id):
                st.error("❌ Você não tem permissão para acessar este processo")
                if st.button("← Voltar para Home"):
                    st.session_state.view = "home"
                    st.rerun()
            else:
                cursor.execute("SELECT nome, status FROM processos WHERE id = %s", (processo_id,))
                result = cursor.fetchone()
                
                if not result:
                    st.error("Processo não encontrado")
                    if st.button("← Voltar para Home"):
                        st.session_state.view = "home"
                        st.rerun()
                else:
                    nome_processo, status_processo = result
                    
                    # Header with actions
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.title(f"📂 {nome_processo}")
                    with col2:
                        if st.button("🏠 Home", use_container_width=True):
                            st.session_state.view = "home"
                            st.session_state.processo_id = None
                            st.rerun()
                    with col3:
                        if status_processo == "Aberto" and st.session_state.user_role == "admin":
                            if confirm_action("🔒 Fechar Processo", key_prefix=f"fechar_{processo_id}"):
                                cursor.execute("UPDATE processos SET status = %s WHERE id = %s", ("Fechado", processo_id))
                                conn.commit()
                                add_notification("✅ Processo fechado com sucesso!", "success")
                                st.rerun()
                    
                    st.markdown("---")
                    
                    # Add Candidate (only for admin and user roles, not viewers)
                    if status_processo == "Aberto" and st.session_state.user_role in ["admin", "user"]:
                        with st.expander("➕ Adicionar Candidato", expanded=False):
                            col1, col2 = st.columns(2)
                            with col1:
                                nome_c = st.text_input("Nome do Candidato*", key="novo_nome_c")
                                email_c = st.text_input("Email*", key="novo_email_c")
                            with col2:
                                telefone_c = st.text_input("Telefone", key="novo_telefone_c")
                                linkedin_c = st.text_input("LinkedIn", key="novo_linkedin_c")
                            
                            if st.button("✅ Adicionar Candidato", type="primary", use_container_width=True):
                                if not nome_c or not email_c:
                                    st.error("❌ Nome e email são obrigatórios")
                                else:
                                    try:
                                        # Check if candidate exists
                                        cursor.execute("SELECT id FROM candidatos WHERE email = %s", (email_c,))
                                        existe = cursor.fetchone()
                                        
                                        if not existe:
                                            cursor.execute("""
                                                INSERT INTO candidatos (nome, email, telefone, linkedin)
                                                VALUES (%s, %s, %s, %s)
                                            """, (nome_c, email_c, telefone_c, linkedin_c))
                                            conn.commit()
                                            candidato_id = cursor.lastrowid
                                            add_notification(f"✅ Candidato {nome_c} cadastrado!", "success")
                                        else:
                                            candidato_id = existe[0]
                                            add_notification(f"ℹ️ Candidato {nome_c} já existente", "info")
                                        
                                        # Link to process
                                        cursor.execute("""
                                            INSERT OR IGNORE INTO processos_candidatos (processo_id, candidato_id)
                                            VALUES (%s, %s)
                                        """, (processo_id, candidato_id))
                                        conn.commit()
                                        
                                        # Reset inputs
                                        for key in ["novo_nome_c", "novo_email_c", "novo_telefone_c", "novo_linkedin_c"]:
                                            if key in st.session_state:
                                                del st.session_state[key]
                                        
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Erro ao adicionar candidato: {str(e)}")
                    
                    st.divider()
                    
                    # List Candidates
                    st.markdown("### 👥 Candidatos")
                    
                    # Filters
                    col_filters = st.columns([2, 1, 1, 1])
                    with col_filters[0]:
                        busca = st.text_input("🔎 Buscar candidato", placeholder="Nome ou email...")
                    with col_filters[1]:
                        filtro_status = st.selectbox(
                            "Status",
                            ["Todos", "Pendentes", "Avaliados", "Aprovados", "Reprovados"]
                        )
                    with col_filters[2]:
                        nota_min = st.slider("Nota mínima", 0.0, 10.0, 0.0, step=0.5)
                    with col_filters[3]:
                        ordenar = st.selectbox("Ordenar por", ["Nome", "Nota (maior)", "Nota (menor)", "Data"])
                    
                    # Get candidates
                    candidatos = get_candidatos_processo_cached(processo_id)
                    
                    # Apply filters
                    filtered_candidatos = []
                    for cand in candidatos:
                        id_c, nome, email, total_avaliacoes, ultima_nota = cand
                        
                        # Search filter
                        if busca and busca.lower() not in nome.lower() and busca.lower() not in email.lower():
                            continue
                        
                        # Status filter
                        if filtro_status == "Pendentes" and total_avaliacoes > 0:
                            continue
                        elif filtro_status == "Avaliados" and total_avaliacoes == 0:
                            continue
                        elif filtro_status == "Aprovados" and (not ultima_nota or ultima_nota < 8):
                            continue
                        elif filtro_status == "Reprovados" and (not ultima_nota or ultima_nota >= 8):
                            continue
                        
                        # Score filter
                        if ultima_nota and ultima_nota < nota_min:
                            continue
                        
                        filtered_candidatos.append(cand)
                    
                    # Apply sorting
                    if ordenar == "Nome":
                        filtered_candidatos.sort(key=lambda x: x[1])
                    elif ordenar == "Nota (maior)":
                        filtered_candidatos.sort(key=lambda x: x[4] or -1, reverse=True)
                    elif ordenar == "Nota (menor)":
                        filtered_candidatos.sort(key=lambda x: x[4] or 999)
                    
                    # Display candidates
                    if not filtered_candidatos:
                        st.info("👀 Nenhum candidato encontrado com os filtros selecionados")
                    
                    for cand in filtered_candidatos:
                        id_c, nome, email, total_avaliacoes, ultima_nota = cand
                        
                        # Get evaluation details
                        cursor.execute("""
                            SELECT nota_final, id, avaliador_email, data
                            FROM avaliacoes 
                            WHERE processo_id = %s AND candidato_id = %s 
                            ORDER BY data DESC 
                            LIMIT 1
                        """, (processo_id, id_c))
                        avaliacao = cursor.fetchone()
                        
                        if avaliacao:
                            nota_final = avaliacao[0]
                            avaliacao_id = avaliacao[1]
                            avaliador = avaliacao[2]
                            data_avaliacao = avaliacao[3]
                            
                            if nota_final >= 8:
                                status_text = "✅ Aprovado"
                                badge_class = "badge-success"
                            elif nota_final >= 6:
                                status_text = "⚠️ Em análise"
                                badge_class = "badge-warning"
                            else:
                                status_text = "❌ Reprovado"
                                badge_class = "badge-danger"
                            
                            status_html = f'<span class="badge {badge_class}">{status_text}</span>'
                            nota_html = f'⭐ {nota_final:.1f}'
                        else:
                            status_html = '<span class="badge badge-info">⏳ Pendente</span>'
                            nota_html = '—'
                            avaliacao_id = None
                        
                        # Display candidate card
                        with st.container():
                            st.markdown(f"""
                            <div class="card">
                                <div style="display: flex; justify-content: space-between; align-items: start;">
                                    <div>
                                        <h3 style="margin: 0;">{nome} {status_html}</h3>
                                        <p style="margin: 5px 0; color: #9CA3AF;">📧 {email}</p>
                                        <p style="margin: 5px 0; font-size: 14px;">
                                            {nota_html}
                                        </p>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            col_actions = st.columns([1, 1, 2])
                            with col_actions[0]:
                                if avaliacao_id:
                                    if st.button("🔍 Ver Detalhes", key=f"det_{id_c}", use_container_width=True):
                                        st.session_state.avaliacao_id = avaliacao_id
                                        st.session_state.view = "detalhe_avaliacao"
                                        st.rerun()
                            
                            with col_actions[1]:
                                if not avaliacao_id and status_processo == "Aberto" and st.session_state.user_role in ["admin", "user"]:
                                    if st.button("📝 Avaliar", key=f"avaliar_{id_c}", type="primary", use_container_width=True):
                                        st.session_state.candidato_id = id_c
                                        st.session_state.view = "avaliar"
                                        st.rerun()
                            
                            with col_actions[2]:
                                if avaliacao_id and status_processo == "Aberto" and st.session_state.user_role in ["admin", "user"]:
                                    if st.button("🔄 Reavaliar", key=f"reavaliar_{id_c}", use_container_width=True):
                                        st.session_state.candidato_id = id_c
                                        st.session_state.view = "avaliar"
                                        st.rerun()
        
        elif st.session_state.view == "avaliar":
            # Only allow evaluation for users with proper role
            if st.session_state.user_role not in ["admin", "user"]:
                st.error("❌ Você não tem permissão para avaliar candidatos")
                if st.button("← Voltar"):
                    st.session_state.view = "processo"
                    st.rerun()
            else:
                candidato_id = st.session_state.candidato_id
                processo_id = st.session_state.processo_id
                
                # Navigation
                if st.button("← Voltar", use_container_width=True):
                    st.session_state.view = "processo"
                    st.session_state.candidato_id = None
                    st.rerun()
                
                # Get candidate info
                cursor.execute("SELECT nome, email FROM candidatos WHERE id = %s", (candidato_id,))
                nome_candidato, email_candidato = cursor.fetchone()
                
                cursor.execute("SELECT nome FROM processos WHERE id = %s", (processo_id,))
                nome_processo = cursor.fetchone()[0]
                
                st.title(f"📝 Avaliar: {nome_candidato}")
                st.caption(f"📧 {email_candidato} | 📂 {nome_processo}")
                
                # Evaluation structure
                estrutura = {
                    "Tratamentos": [
                        {"criterio": "Arquitetura em Camadas (Raw / Staging / Golden)", "peso": 1, "obrigatorio": False, "descricao": "Avalie a organização em camadas de dados"},
                        {"criterio": "Criação de Dimensões", "peso": 2, "obrigatorio": True, "descricao": "Verifique a criação e gerenciamento de dimensões"},
                        {"criterio": "Tratamento de Tipagem e Strings", "peso": 2, "obrigatorio": True, "descricao": "Avalie o tratamento de tipos de dados e strings"},
                        {"criterio": "Deduplicação", "peso": 2, "obrigatorio": True, "descricao": "Verifique estratégias de deduplicação"},
                        {"criterio": "Modelagem de Dados (Star / Snowflake)", "peso": 3, "obrigatorio": True, "descricao": "Avalie a modelagem dimensional"},
                    ],
                    "Análises": [
                        {"criterio": "Escolha das Métricas Estratégicas", "peso": 3, "obrigatorio": True, "descricao": "Avalie a relevância das métricas escolhidas"},
                        {"criterio": "Cálculo Correto das Métricas", "peso": 3, "obrigatorio": True, "descricao": "Verifique a precisão dos cálculos"},
                        {"criterio": "Storytelling", "peso": 2, "obrigatorio": True, "descricao": "Avalie a capacidade de contar história com dados"},
                    ],
                    "Visual": [
                        {"criterio": "Organização dos Visuais", "peso": 2, "obrigatorio": True, "descricao": "Avalie a disposição e clareza dos visuais"},
                        {"criterio": "Paleta de Cores e Tipografia", "peso": 1, "obrigatorio": True, "descricao": "Verifique a escolha de cores e fontes"},
                    ]
                }
                
                soma_ponderada = 0
                soma_pesos = 0
                reprovado_por_obrigatorio = False
                criterios_avaliados = 0
                total_criterios = sum(len(criterios) for criterios in estrutura.values())
                
                # Evaluation criteria
                for bloco, criterios in estrutura.items():
                    st.divider()
                    st.header(bloco)
                    
                    for item in criterios:
                        criterio = item["criterio"]
                        peso = item["peso"]
                        obrigatorio = item["obrigatorio"]
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
                                reprovado_por_obrigatorio = True
                
                show_progress_bar(criterios_avaliados, total_criterios, "Critérios avaliados:")
                
                if soma_pesos > 0:
                    nota_final = round(soma_ponderada / soma_pesos, 2)
                else:
                    nota_final = 0
                
                st.divider()
                st.subheader("🎯 Resultado Final")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Nota Final (Ponderada)", f"{nota_final:.1f}")
                with col2:
                    st.metric("Total de Peso", soma_pesos)
                with col3:
                    st.metric("Critérios Avaliados", f"{criterios_avaliados}/{total_criterios}")
                
                if reprovado_por_obrigatorio:
                    st.error("❌ Reprovado por critério obrigatório abaixo de 6")
                elif nota_final >= 8:
                    st.success("✅ Recomendado para contratação")
                    st.balloons()
                elif nota_final >= 6:
                    st.warning("⚠️ Avaliar melhor - Pontos de melhoria identificados")
                else:
                    st.error("❌ Não recomendado - Necessita desenvolvimento")
                
                st.divider()
                st.subheader("📝 Considerações Finais")
                
                comentario_final = st.text_area(
                    "Comentário Final Geral*",
                    placeholder="Resumo da avaliação, pontos fortes, áreas de melhoria..."
                )
                
                if st.button("✅ Salvar Avaliação Final", type="primary", use_container_width=True):
                    if not comentario_final:
                        st.error("❌ Comentário final é obrigatório")
                    else:
                        try:
                            cursor.execute("""
                                INSERT INTO avaliacoes
                                (processo_id, candidato_id, nota_final, avaliador_email, comentario_final, data)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """, (processo_id, candidato_id, nota_final, st.session_state.user_email, comentario_final, datetime.now()))
                            
                            conn.commit()
                            avaliacao_id = cursor.lastrowid
                            
                            for bloco, criterios in estrutura.items():
                                for item in criterios:
                                    criterio = item["criterio"]
                                    nota = st.session_state[f"{bloco}_{criterio}"]
                                    justificativa = st.session_state[f"just_{bloco}_{criterio}"]
                                    
                                    cursor.execute("""
                                        INSERT INTO avaliacoes_criterios
                                        (avaliacao_id, bloco, criterio, nota, justificativa)
                                        VALUES (%s, %s, %s, %s, %s)
                                    """, (avaliacao_id, bloco, criterio, nota, justificativa))
                            
                            conn.commit()
                            
                            add_notification(f"✅ Avaliação salva com sucesso! Nota final: {nota_final:.1f}", "success")
                            
                            st.session_state.view = "processo"
                            st.session_state.candidato_id = None
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Erro ao salvar avaliação: {str(e)}")
        
        elif st.session_state.view == "detalhe_avaliacao":
            # Detalhe view - accessible by all logged-in users
            avaliacao_id = st.session_state.avaliacao_id
            
            if st.button("← Voltar ao Processo", use_container_width=True):
                st.session_state.view = "processo"
                st.rerun()
            
            cursor.execute("""
                SELECT 
                    a.nota_final, 
                    u.nome as avaliador, 
                    a.comentario_final,
                    a.data,
                    c.nome as candidato_nome,
                    c.email,
                    p.nome as processo_nome
                FROM avaliacoes a
                JOIN candidatos c ON a.candidato_id = c.id
                JOIN processos p ON a.processo_id = p.id
                JOIN usuarios u ON a.avaliador_email = u.email
                WHERE a.id = %s
            """, (avaliacao_id,))
            
            avaliacao = cursor.fetchone()
            
            if not avaliacao:
                st.error("Avaliação não encontrada")
            else:
                nota_final, avaliador, comentario_final, data_avaliacao, candidato_nome, candidato_email, processo_nome = avaliacao
                
                st.title(f"🔍 Detalhe da Avaliação")
                
                with st.container():
                    st.markdown(f"""
                    <div class="card">
                        <h3>📋 Informações do Candidato</h3>
                        <p><strong>Nome:</strong> {candidato_nome}</p>
                        <p><strong>Email:</strong> {candidato_email}</p>
                        <p><strong>Processo:</strong> {processo_nome}</p>
                        <p><strong>Data:</strong> {data_avaliacao.strftime('%d/%m/%Y %H:%M') if data_avaliacao else '—'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
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
                
                st.divider()
                st.subheader("💬 Comentário Geral")
                st.write(comentario_final)
                
                st.divider()
                st.subheader("📊 Avaliação por Critério")
                
                cursor.execute("""
                    SELECT bloco, criterio, nota, justificativa
                    FROM avaliacoes_criterios
                    WHERE avaliacao_id = %s
                    ORDER BY bloco, criterio
                """, (avaliacao_id,))
                
                criterios = cursor.fetchall()
                
                current_bloco = None
                for bloco, criterio, nota, justificativa in criterios:
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
                        
                        if justificativa:
                            st.write("**Justificativa:**")
                            st.write(justificativa)
                        else:
                            st.caption("*Sem justificativa registrada*")