import streamlit as st
import pandas as pd
from database import init_db, get_connection
from allowed_emails import is_email_allowed, is_admin, is_viewer, can_edit, get_user_role, add_allowed_email, remove_allowed_email, get_all_allowed_emails
from criterios_areas import get_criterios_por_area, get_areas_disponiveis

st.set_page_config(page_title="Sistema de Avaliação Técnica", layout="wide", initial_sidebar_state="collapsed")

# ===== ESTILO APRIMORADO =====
st.markdown("""
<style>
/* Background e tema geral */
.stApp { 
    background: linear-gradient(135deg, #0B1E3D 0%, #1e3a5f 50%, #2d5a8a 100%); 
}

/* Cards com efeito glassmorphism */
.card { 
    background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05)); 
    backdrop-filter: blur(20px); 
    padding: 32px; 
    border-radius: 24px; 
    margin-bottom: 24px; 
    border: 1px solid rgba(255,255,255,0.18); 
    box-shadow: 0px 8px 32px rgba(0,0,0,0.3);
    transition: all 0.3s ease;
}

.card:hover { 
    transform: translateY(-4px); 
    box-shadow: 0px 16px 48px rgba(0,0,0,0.4);
    border: 1px solid rgba(255,255,255,0.25);
}

/* Login card especial */
.login-card {
    background: linear-gradient(135deg, rgba(59,130,246,0.15), rgba(147,51,234,0.15));
    backdrop-filter: blur(20px);
    padding: 48px;
    border-radius: 24px;
    border: 1px solid rgba(255,255,255,0.2);
    box-shadow: 0px 16px 48px rgba(0,0,0,0.4);
    max-width: 500px;
    margin: 80px auto;
}

/* Status badges */
.status-green { 
    color: #10b981; 
    font-weight: 700; 
    font-size: 16px;
    background: rgba(16,185,129,0.1);
    padding: 6px 16px;
    border-radius: 12px;
    display: inline-block;
}

.status-yellow { 
    color: #f59e0b; 
    font-weight: 700; 
    font-size: 16px;
    background: rgba(245,158,11,0.1);
    padding: 6px 16px;
    border-radius: 12px;
    display: inline-block;
}

.status-red { 
    color: #ef4444; 
    font-weight: 700; 
    font-size: 16px;
    background: rgba(239,68,68,0.1);
    padding: 6px 16px;
    border-radius: 12px;
    display: inline-block;
}

.status-gray { 
    color: #9ca3af; 
    font-weight: 700; 
    font-size: 16px;
    background: rgba(156,163,175,0.1);
    padding: 6px 16px;
    border-radius: 12px;
    display: inline-block;
}

/* Títulos e textos */
h1, h2, h3, h4 { 
    color: white !important; 
    font-weight: 700 !important;
}

h1 { 
    font-size: 42px !important; 
    margin-bottom: 24px !important;
}

h2 { 
    font-size: 32px !important; 
    margin-bottom: 20px !important;
}

h3 { 
    font-size: 24px !important; 
    margin-bottom: 16px !important;
}

p, label, .stMarkdown { 
    color: rgba(255,255,255,0.9) !important; 
}

/* Botões modernos */
.stButton>button { 
    border-radius: 16px !important; 
    height: 48px !important; 
    font-weight: 600 !important; 
    border: none !important; 
    background: linear-gradient(135deg, #3B82F6, #8B5CF6) !important; 
    color: white !important; 
    transition: all 0.3s ease !important;
    box-shadow: 0px 4px 12px rgba(59,130,246,0.3) !important;
    font-size: 15px !important;
}

.stButton>button:hover { 
    transform: translateY(-2px) !important; 
    box-shadow: 0px 8px 24px rgba(139,92,246,0.5) !important;
    background: linear-gradient(135deg, #2563EB, #7C3AED) !important;
}

/* Inputs modernos */
.stTextInput>div>div>input, 
.stTextArea textarea, 
.stSelectbox>div>div>select { 
    border-radius: 16px !important; 
    background-color: rgba(255,255,255,0.1) !important; 
    color: white !important; 
    border: 1px solid rgba(255,255,255,0.2) !important;
    padding: 12px 16px !important;
    font-size: 15px !important;
    transition: all 0.3s ease !important;
}

.stTextInput>div>div>input:focus, 
.stTextArea textarea:focus,
.stSelectbox>div>div>select:focus { 
    border: 1px solid rgba(139,92,246,0.6) !important;
    box-shadow: 0px 0px 0px 3px rgba(139,92,246,0.2) !important;
    background-color: rgba(255,255,255,0.15) !important;
}

/* Sliders */
.stSlider>div>div>div>div {
    background: linear-gradient(90deg, #3B82F6, #8B5CF6) !important;
}

/* Expanders */
.streamlit-expanderHeader {
    background-color: rgba(255,255,255,0.08) !important;
    border-radius: 16px !important;
    color: white !important;
    font-weight: 600 !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
}

/* Dividers */
hr {
    border-color: rgba(255,255,255,0.15) !important;
    margin: 32px 0 !important;
}

/* Métricas */
.stMetric {
    background: rgba(255,255,255,0.08);
    padding: 20px;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.15);
}

/* Radio buttons */
.stRadio>div {
    background: rgba(255,255,255,0.05);
    padding: 12px;
    border-radius: 16px;
}

/* Captions */
.caption {
    color: rgba(255,255,255,0.6) !important;
    font-size: 14px !important;
}

/* Success/Warning/Error messages */
.stSuccess, .stWarning, .stError, .stInfo {
    border-radius: 16px !important;
    padding: 16px !important;
    backdrop-filter: blur(10px) !important;
}
</style>
""", unsafe_allow_html=True)

# ===== DB =====
init_db()
conn = get_connection()
cursor = conn.cursor()

# ===== SESSION STATE =====
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "view" not in st.session_state:
    st.session_state.view = "home"
if "processo_id" not in st.session_state:
    st.session_state.processo_id = None
if "candidato_id" not in st.session_state:
    st.session_state.candidato_id = None
if "avaliacao_id" not in st.session_state:
    st.session_state.avaliacao_id = None

# Função para resetar avaliação
def reset_avaliacao(estrutura):
    for bloco, criterios in estrutura.items():
        for item in criterios:
            criterio = item["criterio"]
            st.session_state[f"{bloco}_{criterio}"] = 5.0
            st.session_state[f"just_{bloco}_{criterio}"] = ""

# =====================================================
# 🔐 LOGIN PAGE
# =====================================================
if not st.session_state.authenticated:
    
    # Logo e título animado
    st.markdown("""
    <div style="text-align:center; margin-top: 80px; margin-bottom: 60px;">
        <div style="
            display: inline-block;
            background: linear-gradient(135deg, rgba(59,130,246,0.2), rgba(147,51,234,0.2));
            padding: 30px;
            border-radius: 50%;
            margin-bottom: 30px;
            box-shadow: 0px 20px 60px rgba(59,130,246,0.4);
            animation: pulse 2s ease-in-out infinite;
        ">
            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="url(#gradient1)" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 17L12 22L22 17" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                <defs>
                    <linearGradient id="gradient1" x1="2" y1="2" x2="22" y2="12">
                        <stop offset="0%" style="stop-color:#60A5FA;stop-opacity:1" />
                        <stop offset="100%" style="stop-color:#A78BFA;stop-opacity:1" />
                    </linearGradient>
                </defs>
            </svg>
        </div>
        <h1 style="
            font-size:64px;
            font-weight:900;
            letter-spacing:-3px;
            background: linear-gradient(135deg, #60A5FA 0%, #A78BFA 50%, #F472B6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom:20px;
            text-shadow: 0px 4px 20px rgba(96,165,250,0.3);
        ">
            Artefact Evaluation
        </h1>
        <p style="font-size:20px; color:rgba(255,255,255,0.8); margin-bottom:10px; font-weight:500;">
            Sistema de Avaliação Técnica
        </p>
        <p style="font-size:16px; color:rgba(255,255,255,0.5);">
            🔐 Acesso restrito a colaboradores autorizados
        </p>
    </div>
    
    <style>
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .login-container {
            animation: slideUp 0.6s ease-out;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Container centralizado para o login
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        # Input de email com estilo
        st.markdown("""
        <div style="margin-bottom:20px; margin-top:20px;">
            <label style="
                display:block;
                font-size:14px;
                font-weight:600;
                color:rgba(255,255,255,0.9);
                margin-bottom:8px;
            ">
                📧 Email Corporativo
            </label>
        </div>
        """, unsafe_allow_html=True)
        
        email_input = st.text_input(
            "Email",
            placeholder="seu.nome@artefact.com",
            key="login_email",
            label_visibility="collapsed"
        )
        
        st.markdown("<div style='margin-bottom:25px;'></div>", unsafe_allow_html=True)
        
        # Botão de login estilizado
        if st.button("🚀 Entrar no Sistema", use_container_width=True, key="login_btn"):
            if is_email_allowed(email_input):
                st.session_state.authenticated = True
                st.session_state.user_email = email_input
                st.success(f"✅ Bem-vindo(a), {email_input.split('@')[0]}!")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Acesso negado. Apenas emails @artefact.com são permitidos.")
        
        # Informações adicionais
        st.markdown("""
        <div style="
            margin-top:30px;
            padding:20px;
            background:rgba(59,130,246,0.1);
            border-radius:16px;
            border-left:4px solid #3B82F6;
        ">
            <p style="font-size:13px; color:rgba(255,255,255,0.8); margin:0;">
                <strong>ℹ️ Informação:</strong><br>
                Apenas emails <strong>previamente cadastrados</strong> têm acesso autorizado ao sistema. Entre em contato com um administrador para solicitar acesso.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("""
    <div style="
        text-align:center;
        margin-top:80px;
        padding-top:30px;
        border-top:1px solid rgba(255,255,255,0.1);
    ">
        <p style="color:rgba(255,255,255,0.4); font-size:13px; margin-bottom:8px;">
            🔒 Conexão segura e criptografada
        </p>
        <p style="color:rgba(255,255,255,0.3); font-size:12px;">
            © 2026 Artefact - Todos os direitos reservados
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.stop()

# =====================================================
# HEADER COM LOGOUT E NAVEGAÇÃO
# =====================================================
user_role = get_user_role(st.session_state.user_email)
role_badge = {
    'admin': '👑 Admin',
    'user': '👤 User',
    'viewer': '👁️ Viewer'
}.get(user_role, '👤 User')

role_color = {
    'admin': '#F472B6',
    'user': '#60A5FA',
    'viewer': '#9ca3af'
}.get(user_role, '#60A5FA')

col_h1, col_h2, col_h3, col_h4, col_h5 = st.columns([2, 1, 1, 1, 1])

with col_h1:
    st.markdown(f"""
    <p style="color:rgba(255,255,255,0.7); font-size:14px; margin-top:16px;">
        <strong>{st.session_state.user_email}</strong>
        <span style="background:{role_color}20; color:{role_color}; padding:4px 12px; border-radius:8px; font-size:12px; margin-left:8px;">{role_badge}</span>
    </p>
    """, unsafe_allow_html=True)

with col_h2:
    if st.button("🏠 Início", key="nav_home"):
        st.session_state.view = "home"
        st.rerun()

with col_h3:
    if st.button("📊 Estatísticas", key="nav_stats"):
        st.session_state.view = "statistics"
        st.rerun()

with col_h4:
    if is_admin(st.session_state.user_email):
        if st.button("⚙️ Admin", key="nav_admin"):
            st.session_state.view = "admin"
            st.rerun()

with col_h5:
    if st.button("🚪 Sair", key="logout_btn"):
        st.session_state.authenticated = False
        st.session_state.user_email = None
        st.session_state.view = "home"
        st.rerun()

# Mostrar aviso para viewers
if is_viewer(st.session_state.user_email):
    st.info("👁️ Você está no modo visualização. Você pode ver todas as informações mas não pode criar ou editar.")

st.markdown("<hr>", unsafe_allow_html=True)

# =====================================================
# 🏠 HOME
# =====================================================
if st.session_state.view == "home":

    st.markdown("""
    <h1 style="
        text-align:center;
        font-size:48px;
        font-weight:700;
        letter-spacing:-1.5px;
        background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom:40px;
    ">
        PROCESSOS SELETIVOS
    </h1>
    """, unsafe_allow_html=True)

    # Apenas administradores podem criar processos
    if is_admin(st.session_state.user_email):
        with st.expander("➕ Criar Novo Processo", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome do Processo", key="novo_nome_processo")
                area = st.selectbox("Área", get_areas_disponiveis(), key="novo_area_processo")
                tipo = st.selectbox("Tipo", [
                    "Ampla Concorrência",
                    "Afirmativa: Mulheres Cis e Trans",
                    "Afirmativa: Pessoas Negras",
                    "Afirmativa: LGBTQIAPN+"
                ], key="novo_tipo_processo")
            
            with col2:
                senioridade = st.selectbox("Senioridade", ["Estágio", "Júnior", "Pleno", "Sênior"], key="novo_senioridade")
                status = st.selectbox("Status", ["Aberto", "Fechado"], key="novo_status")
                local = st.selectbox("Local", ["BRASIL", "LATAM", "EUROPA", "GLOBAL"], key="novo_local_processo")

            if st.button("✨ Criar Processo", use_container_width=True):
                cursor.execute("""
                    INSERT INTO processos (nome, area, tipo, senioridade, status, local)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (nome, area, tipo, senioridade, status, local))
                conn.commit()
                st.success("✅ Processo criado com sucesso!")
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Listar processos
    cursor.execute("SELECT id, nome, area, tipo, senioridade, local, status FROM processos ORDER BY id DESC")
    processos = cursor.fetchall()

    if not processos:
        st.info("📋 Nenhum processo cadastrado ainda. Crie o primeiro!")
    else:
        for id_p, nome, area, tipo, senioridade, local, status in processos:
            status_badge = "🟢" if status == "Aberto" else "🔴"
            
            st.markdown(f"""
            <div class="card">
                <h3>{status_badge} {nome}</h3>
                <p style="color:#9CA3AF; font-size:15px; margin-top:8px;">
                    <strong>Área:</strong> {area} | 
                    <strong>Tipo:</strong> {tipo} | 
                    <strong>Senioridade:</strong> {senioridade} | 
                    <strong>Local:</strong> {local}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([5, 1])
            with col2:
                if st.button("Abrir →", key=f"entrar_{id_p}", use_container_width=True):
                    st.session_state.processo_id = id_p
                    st.session_state.view = "processo"
                    st.rerun()

# =====================================================
# 📂 PROCESSO
# =====================================================
elif st.session_state.view == "processo":

    processo_id = st.session_state.processo_id
    cursor.execute("SELECT nome, status, area FROM processos WHERE id = %s", (processo_id,))
    result = cursor.fetchone()
    nome_processo, status_processo, area_processo = result

    col_back, col_title, col_close = st.columns([1, 6, 2])
    
    with col_back:
        if st.button("← Voltar"):
            st.session_state.view = "home"
            st.session_state.processo_id = None
            st.rerun()
    
    with col_title:
        st.markdown(f"<h1>📂 {nome_processo}</h1>", unsafe_allow_html=True)
        st.caption(f"Área: {area_processo}")
    
    with col_close:
        if status_processo == "Aberto" and is_admin(st.session_state.user_email):
            if st.button("🔒 Fechar Processo"):
                cursor.execute("UPDATE processos SET status = %s WHERE id = %s", ("Fechado", processo_id))
                conn.commit()
                st.success("Processo fechado!")
                st.rerun()
    
    st.divider()

    # Adicionar candidato (só se aberto e usuário pode editar)
    if status_processo == "Aberto" and can_edit(st.session_state.user_email):
        with st.expander("➕ Adicionar Candidato", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                nome_c = st.text_input("Nome do Candidato", key="novo_nome_c")
            with col2:
                email_c = st.text_input("Email", key="novo_email_c")
            
            if st.button("✨ Adicionar Candidato", use_container_width=True):
                cursor.execute("SELECT id FROM candidatos WHERE email = %s", (email_c,))
                existe = cursor.fetchone()
                if not existe:
                    cursor.execute("INSERT INTO candidatos (nome, email) VALUES (%s, %s)", (nome_c, email_c))
                    conn.commit()
                    candidato_id = cursor.lastrowid
                else:
                    candidato_id = existe[0]

                cursor.execute("""
                    INSERT INTO processos_candidatos (processo_id, candidato_id)
                    VALUES (%s, %s)
                    ON CONFLICT (processo_id, candidato_id) DO NOTHING
                """, (processo_id, candidato_id))
                conn.commit()
                st.success("✅ Candidato registrado!")

                st.session_state["novo_nome_c"] = ""
                st.session_state["novo_email_c"] = ""
                st.rerun()

    st.divider()

    # Listar candidatos vinculados
    cursor.execute("""
        SELECT 
            c.id, 
            c.nome, 
            c.email,
            COUNT(a.id) as total_avaliacoes
        FROM processos_candidatos pc
        JOIN candidatos c ON pc.candidato_id = c.id
        LEFT JOIN avaliacoes a
            ON c.id = a.candidato_id AND a.processo_id = %s
        WHERE pc.processo_id = %s
        GROUP BY c.id
        ORDER BY c.nome
    """, (processo_id, processo_id))

    candidatos = cursor.fetchall()

    # Busca e filtros
    col_search, col_filter = st.columns([2, 1])
    
    with col_search:
        busca = st.text_input("🔎 Buscar candidato", placeholder="Nome ou email...")
    
    with col_filter:
        filtro_status = st.selectbox(
            "Filtrar por status:",
            ["Todos", "Pendentes", "Avaliados"]
        )

    if busca:
        candidatos = [
            c for c in candidatos
            if busca.lower() in c[1].lower() or busca.lower() in c[2].lower()
        ]

    if filtro_status == "Pendentes":
        candidatos = [c for c in candidatos if c[3] == 0]
    elif filtro_status == "Avaliados":
        candidatos = [c for c in candidatos if c[3] > 0]

    candidatos.sort(key=lambda x: x[3])

    st.markdown(f"<h3>👥 Candidatos ({len(candidatos)})</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    for id_c, nome, email, total_avaliacoes in candidatos:

        cursor.execute("""
            SELECT nota_final, id 
            FROM avaliacoes 
            WHERE processo_id = %s AND candidato_id = %s 
            ORDER BY data DESC 
            LIMIT 1
        """, (processo_id, id_c))
        avaliacao = cursor.fetchone()

        if avaliacao:
            nota_final = avaliacao[0]
            avaliacao_id = avaliacao[1]

            if nota_final >= 8:
                status_class = "status-green"
                status_text = f"✅ Nota Final: {nota_final}"
            elif nota_final >= 6:
                status_class = "status-yellow"
                status_text = f"⚠️ Nota Final: {nota_final}"
            else:
                status_class = "status-red"
                status_text = f"❌ Nota Final: {nota_final}"

            status_html = f'<span class="{status_class}">{status_text}</span>'
        else:
            status_html = '<span class="status-gray">⏳ Pendente</span>'

        st.markdown(f"""
            <div class="card">
                <h3>{nome}</h3>
                <p style="color:#9CA3AF; margin:8px 0;">{email}</p>
                <p style="margin-top:12px;">{status_html}</p>
            </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1])

        with col1:
            if avaliacao:
                if st.button("📊 Ver Detalhes", key=f"det_{id_c}", use_container_width=True):
                    st.session_state.avaliacao_id = avaliacao_id
                    st.session_state.view = "detalhe_avaliacao"
                    st.rerun()

        with col2:
            if not avaliacao and status_processo == "Aberto" and can_edit(st.session_state.user_email):
                if st.button("📝 Avaliar", key=f"avaliar_{id_c}", use_container_width=True):
                    st.session_state.candidato_id = id_c
                    st.session_state.view = "avaliar"
                    st.rerun()
                    
# =====================================================
# 📝 AVALIAR
# =====================================================
elif st.session_state.view == "avaliar":
    
    # Verificar se usuário pode editar
    if not can_edit(st.session_state.user_email):
        st.error("❌ Você não tem permissão para avaliar candidatos. Apenas usuários com role 'user' ou 'admin' podem avaliar.")
        if st.button("← Voltar ao Processo"):
            st.session_state.view = "processo"
            st.rerun()
        st.stop()

    candidato_id = st.session_state.candidato_id
    processo_id = st.session_state.processo_id

    if st.button("← Voltar ao Processo"):
        st.session_state.view = "processo"
        st.rerun()

    cursor.execute("SELECT nome FROM candidatos WHERE id = %s", (candidato_id,))
    nome_candidato = cursor.fetchone()[0]
    
    cursor.execute("SELECT area FROM processos WHERE id = %s", (processo_id,))
    area_processo = cursor.fetchone()[0]
    
    st.markdown(f"<h1>📝 Avaliação - {nome_candidato}</h1>", unsafe_allow_html=True)
    st.caption(f"Área: {area_processo}")

    # Obter critérios baseados na área
    estrutura = get_criterios_por_area(area_processo)

    soma_ponderada = 0
    soma_pesos = 0
    reprovado_por_obrigatorio = False

    # Sliders
    for bloco, criterios in estrutura.items():
        st.divider()
        st.markdown(f"<h2>{bloco}</h2>", unsafe_allow_html=True)

        for item in criterios:
            criterio = item["criterio"]
            descricao = item.get("descricao", "")
            peso = item["peso"]
            obrigatorio = item["obrigatorio"]

            key_nota = f"{bloco}_{criterio}"
            key_just = f"just_{bloco}_{criterio}"

            if key_nota not in st.session_state:
                st.session_state[key_nota] = 5.0
            if key_just not in st.session_state:
                st.session_state[key_just] = ""

            obrigatorio_badge = "🔴 OBRIGATÓRIO" if obrigatorio else "⚪ Opcional"
            
            st.markdown(f"""
                <div style="background:rgba(255,255,255,0.05); padding:20px; border-radius:16px; margin-bottom:20px; border-left:4px solid {'#ef4444' if obrigatorio else '#6b7280'};">
                    <p style="font-size:18px; font-weight:700; margin-bottom:8px;">{criterio}</p>
                    <p style="font-size:14px; color:#D1D5DB; margin-bottom:8px;">{descricao}</p>
                    <p style="font-size:13px; color:#9CA3AF;">
                        <strong>Peso:</strong> {peso} | {obrigatorio_badge}
                    </p>
                </div>
            """, unsafe_allow_html=True)

            nota = st.slider(
                "Nota (0-10)",
                0.0,
                10.0,
                st.session_state[key_nota],
                step=0.5,
                key=key_nota
            )

            justificativa = st.text_area(
                "Justificativa",
                st.session_state[key_just],
                key=key_just,
                height=100
            )

            soma_ponderada += nota * peso
            soma_pesos += peso

            if obrigatorio and nota < 6:
                reprovado_por_obrigatorio = True

    # Resultado
    nota_final = round(soma_ponderada / soma_pesos, 2)

    st.divider()
    st.markdown("<h2>🎯 Resultado Final</h2>", unsafe_allow_html=True)

    col_metric1, col_metric2, col_metric3 = st.columns(3)
    
    with col_metric1:
        st.metric("Nota Final (Ponderada)", nota_final)
    
    with col_metric2:
        if nota_final >= 8:
            st.success("✅ Recomendado")
        elif nota_final >= 6:
            st.warning("⚠️ Avaliar melhor")
        else:
            st.error("❌ Não recomendado")
    
    with col_metric3:
        if reprovado_por_obrigatorio:
            st.error("🔴 Reprovado em critério obrigatório")

    st.divider()

    # Campos finais
    col1, col2 = st.columns(2)
    
    with col1:
        avaliador = st.text_input("Nome do Avaliador", value=st.session_state.user_email)
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
    
    comentario_final = st.text_area("Comentário Final Geral", height=150)

    # Salvar
    if st.button("💾 Salvar Avaliação", use_container_width=True):

        cursor.execute("""
        INSERT INTO avaliacoes
        (processo_id, candidato_id, nota_final, avaliador, comentario_final)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """, (processo_id, candidato_id, nota_final, avaliador, comentario_final))

        avaliacao_id = cursor.fetchone()[0]

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

        st.success("✅ Avaliação salva com sucesso!")
        st.balloons()
        st.session_state.view = "processo"
        st.rerun()

# =====================================================
# 🔎 DETALHE DA AVALIAÇÃO
# =====================================================
elif st.session_state.view == "detalhe_avaliacao":

    avaliacao_id = st.session_state.avaliacao_id

    if st.button("← Voltar ao Processo"):
        st.session_state.view = "processo"
        st.rerun()

    cursor.execute("""
        SELECT nota_final, avaliador, comentario_final
        FROM avaliacoes
        WHERE id = %s
    """, (avaliacao_id,))
    avaliacao = cursor.fetchone()

    if avaliacao:
        nota_final, avaliador, comentario_final = avaliacao

        st.markdown("<h1>📊 Detalhe da Avaliação</h1>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Nota Final", nota_final)
        
        with col2:
            if nota_final >= 8:
                st.success("✅ Recomendado")
            elif nota_final >= 6:
                st.warning("⚠️ Avaliar melhor")
            else:
                st.error("❌ Não recomendado")
        
        st.markdown(f"**👤 Avaliador:** {avaliador}")
        
        st.divider()
        
        st.markdown("### 💬 Comentário Geral")
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.05); padding:20px; border-radius:16px; border-left:4px solid #3B82F6;">
            {comentario_final if comentario_final else "Sem comentário"}
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # Buscar critérios
        cursor.execute("""
            SELECT bloco, criterio, nota, justificativa
            FROM avaliacoes_criterios
            WHERE avaliacao_id = %s
            ORDER BY bloco
        """, (avaliacao_id,))

        criterios = cursor.fetchall()

        bloco_atual = None
        for bloco, criterio, nota, justificativa in criterios:
            if bloco != bloco_atual:
                st.markdown(f"<h3>{bloco}</h3>", unsafe_allow_html=True)
                bloco_atual = bloco
            
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.05); padding:16px; border-radius:12px; margin-bottom:16px;">
                <p style="font-size:16px; font-weight:600; margin-bottom:8px;">{criterio}</p>
                <p style="color:#10b981; font-size:18px; font-weight:700; margin-bottom:8px;">Nota: {nota}</p>
                <p style="color:#D1D5DB; font-size:14px;"><strong>Justificativa:</strong> {justificativa if justificativa else "Sem justificativa"}</p>
            </div>
            """, unsafe_allow_html=True)

# =====================================================
# 📊 ESTATÍSTICAS
# =====================================================
elif st.session_state.view == "statistics":
    
    st.markdown("""
    <h1 style="
        text-align:center;
        font-size:48px;
        font-weight:700;
        letter-spacing:-1.5px;
        background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom:40px;
    ">
        📊 ESTATÍSTICAS DO SISTEMA
    </h1>
    """, unsafe_allow_html=True)
    
    # Estatísticas gerais
    cursor.execute("SELECT COUNT(*) FROM processos")
    total_processos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM processos WHERE status = 'Aberto'")
    processos_abertos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM candidatos")
    total_candidatos = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM avaliacoes")
    total_avaliacoes = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT c.id)
        FROM candidatos c
        LEFT JOIN avaliacoes a ON c.id = a.candidato_id
        WHERE a.id IS NULL
    """)
    candidatos_pendentes = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(nota_final) FROM avaliacoes")
    media_geral = cursor.fetchone()[0]
    media_geral = round(float(media_geral), 2) if media_geral else 0
    
    # Cards de estatísticas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class="card">
            <h2 style="color:#60A5FA; margin-bottom:16px;">📋 Processos</h2>
            <p style="font-size:48px; font-weight:800; margin:20px 0;">{total_processos}</p>
            <p style="color:#9CA3AF;">Total de processos</p>
            <p style="color:#10b981; font-weight:600; margin-top:12px;">🟢 {processos_abertos} abertos</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="card">
            <h2 style="color:#A78BFA; margin-bottom:16px;">👥 Candidatos</h2>
            <p style="font-size:48px; font-weight:800; margin:20px 0;">{total_candidatos}</p>
            <p style="color:#9CA3AF;">Total de candidatos</p>
            <p style="color:#f59e0b; font-weight:600; margin-top:12px;">⏳ {candidatos_pendentes} pendentes</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="card">
            <h2 style="color:#F472B6; margin-bottom:16px;">✅ Avaliações</h2>
            <p style="font-size:48px; font-weight:800; margin:20px 0;">{total_avaliacoes}</p>
            <p style="color:#9CA3AF;">Total de avaliações</p>
            <p style="color:#10b981; font-weight:600; margin-top:12px;">📈 Média: {media_geral}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Estatísticas por processo
    st.markdown("<h2>📊 Estatísticas por Processo</h2>", unsafe_allow_html=True)
    
    cursor.execute("""
        SELECT
            p.nome,
            p.area,
            p.status,
            COUNT(DISTINCT pc.candidato_id) as total_candidatos,
            COUNT(DISTINCT a.id) as total_avaliacoes,
            AVG(a.nota_final) as media_notas
        FROM processos p
        LEFT JOIN processos_candidatos pc ON p.id = pc.processo_id
        LEFT JOIN avaliacoes a ON p.id = a.processo_id
        GROUP BY p.id, p.nome, p.area, p.status
        ORDER BY p.id DESC
    """)
    
    processos_stats = cursor.fetchall()
    
    if processos_stats:
        for nome, area, status, total_cand, total_aval, media in processos_stats:
            media_formatted = round(float(media), 2) if media else 0
            pendentes = total_cand - total_aval
            
            status_badge = "🟢" if status == "Aberto" else "🔴"
            
            st.markdown(f"""
            <div class="card">
                <h3>{status_badge} {nome}</h3>
                <p style="color:#9CA3AF; margin:8px 0;">Área: {area}</p>
                <div style="display:flex; gap:24px; margin-top:16px;">
                    <div>
                        <p style="font-size:24px; font-weight:700; color:#60A5FA;">{total_cand}</p>
                        <p style="color:#9CA3AF; font-size:13px;">Candidatos</p>
                    </div>
                    <div>
                        <p style="font-size:24px; font-weight:700; color:#10b981;">{total_aval}</p>
                        <p style="color:#9CA3AF; font-size:13px;">Avaliados</p>
                    </div>
                    <div>
                        <p style="font-size:24px; font-weight:700; color:#f59e0b;">{pendentes}</p>
                        <p style="color:#9CA3AF; font-size:13px;">Pendentes</p>
                    </div>
                    <div>
                        <p style="font-size:24px; font-weight:700; color:#F472B6;">{media_formatted}</p>
                        <p style="color:#9CA3AF; font-size:13px;">Média</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📋 Nenhum processo cadastrado ainda.")
    
    st.divider()
    
    # Top candidatos
    st.markdown("<h2>🏆 Top 10 Candidatos</h2>", unsafe_allow_html=True)
    
    cursor.execute("""
        SELECT
            c.nome,
            c.email,
            MAX(a.nota_final) as melhor_nota,
            COUNT(a.id) as num_avaliacoes
        FROM candidatos c
        JOIN avaliacoes a ON c.id = a.candidato_id
        GROUP BY c.id, c.nome, c.email
        ORDER BY MAX(a.nota_final) DESC
        LIMIT 10
    """)
    
    top_candidatos = cursor.fetchall()
    
    if top_candidatos:
        for idx, (nome, email, nota, num_aval) in enumerate(top_candidatos, 1):
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}º"
            
            if nota >= 8:
                nota_color = "#10b981"
            elif nota >= 6:
                nota_color = "#f59e0b"
            else:
                nota_color = "#ef4444"
            
            st.markdown(f"""
            <div style="
                background:rgba(255,255,255,0.05);
                padding:16px 24px;
                border-radius:12px;
                margin-bottom:12px;
                display:flex;
                justify-content:space-between;
                align-items:center;
            ">
                <div>
                    <p style="font-size:20px; font-weight:700; margin:0;">{medal} {nome}</p>
                    <p style="color:#9CA3AF; font-size:14px; margin:4px 0 0 0;">{email}</p>
                    <p style="color:#9CA3AF; font-size:14px; margin:4px 0 0 0;">{area}</p>
                </div>
                <div style="text-align:right;">
                    <p style="font-size:32px; font-weight:800; color:{nota_color}; margin:0;">{nota}</p>
                    <p style="color:#9CA3AF; font-size:12px; margin:4px 0 0 0;">{num_aval} avaliações</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📋 Nenhuma avaliação realizada ainda.")

# =====================================================
# ⚙️ ADMIN - GERENCIAR EMAILS
# =====================================================
elif st.session_state.view == "admin":
    
    if not is_admin(st.session_state.user_email):
        st.error("❌ Acesso negado. Apenas administradores podem acessar esta página.")
        st.stop()
    
    st.markdown("""
    <h1 style="
        text-align:center;
        font-size:48px;
        font-weight:700;
        letter-spacing:-1.5px;
        background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom:40px;
    ">
        ⚙️ PAINEL DE ADMINISTRAÇÃO
    </h1>
    """, unsafe_allow_html=True)
    
    st.markdown("<h2>📧 Gerenciar Emails Autorizados</h2>", unsafe_allow_html=True)
    
    # Adicionar novo email
    with st.expander("➕ Adicionar Novo Email", expanded=False):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            new_email = st.text_input("Email", placeholder="usuario@exemplo.com", key="new_email_input")
        
        with col2:
            new_role = st.selectbox("Role", ["user", "admin", "viewer"], key="new_email_role")
        
        st.markdown("""
        <div style="background:rgba(59,130,246,0.1); padding:12px; border-radius:12px; margin-bottom:12px;">
            <p style="font-size:13px; color:rgba(255,255,255,0.8); margin:0;">
                <strong>👑 Admin:</strong> Criar/fechar processos + gerenciar usuários + avaliar<br>
                <strong>👤 User:</strong> Adicionar candidatos e avaliar (não cria processos)<br>
                <strong>👁️ Viewer:</strong> Apenas visualização (read-only)
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("✨ Adicionar Email", use_container_width=True):
            if new_email:
                if add_allowed_email(new_email, new_role, st.session_state.user_email):
                    st.success(f"✅ Email {new_email} adicionado como {new_role}!")
                    st.rerun()
                else:
                    st.error("❌ Erro ao adicionar email.")
            else:
                st.warning("⚠️ Por favor, insira um email válido.")
    
    st.divider()
    
    # Listar emails autorizados
    st.markdown("<h3>📋 Emails Autorizados</h3>", unsafe_allow_html=True)
    
    allowed_emails = get_all_allowed_emails()
    
    if allowed_emails:
        for email, role, added_by, added_at in allowed_emails:
            role_info = {
                'admin': {'badge': '👑 ADMIN', 'color': '#F472B6'},
                'user': {'badge': '👤 USER', 'color': '#60A5FA'},
                'viewer': {'badge': '👁️ VIEWER', 'color': '#9ca3af'}
            }
            
            info = role_info.get(role, role_info['user'])
            role_badge = info['badge']
            role_color = info['color']
            
            st.markdown(f"""
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h3 style="margin:0;">{email}</h3>
                        <p style="color:#9CA3AF; font-size:14px; margin:8px 0 0 0;">
                            Adicionado por: {added_by if added_by else "Sistema"} | {added_at.strftime('%d/%m/%Y %H:%M') if added_at else "N/A"}
                        </p>
                    </div>
                    <div style="text-align:right;">
                        <span style="
                            background:{role_color}20;
                            color:{role_color};
                            padding:8px 16px;
                            border-radius:12px;
                            font-weight:700;
                            font-size:14px;
                        ">{role_badge}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([5, 1])
            
            with col2:
                if email != "admin@artefact.com":  # Proteger admin principal
                    if st.button("🗑️ Remover", key=f"remove_{email}", use_container_width=True):
                        if remove_allowed_email(email):
                            st.success(f"✅ Email {email} removido!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao remover email.")
    else:
        st.info("📋 Nenhum email cadastrado no sistema.")
    
    st.divider()
    
    # Informações do sistema
    st.markdown("<h3>ℹ️ Informações do Sistema</h3>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style="
        background:rgba(59,130,246,0.1);
        padding:20px;
        border-radius:16px;
        border-left:4px solid #3B82F6;
    ">
        <p style="font-size:14px; color:rgba(255,255,255,0.9); margin:0;">
            <strong>🔐 Política de Acesso:</strong><br><br>
            • <strong>APENAS</strong> emails cadastrados nesta lista têm acesso ao sistema<br>
            • Não há acesso automático por domínio - todos devem ser adicionados manualmente<br>
            • Apenas administradores podem gerenciar a lista de emails autorizados<br>
            • O email <strong>admin@artefact.com</strong> é protegido e não pode ser removido<br><br>
            <strong>👥 Roles do Sistema:</strong><br><br>
            • <strong>👑 Admin:</strong> Criar/fechar processos + gerenciar usuários + adicionar candidatos + avaliar<br>
            • <strong>👤 User:</strong> Adicionar candidatos e avaliar em processos existentes (não cria processos)<br>
            • <strong>👁️ Viewer:</strong> Apenas visualização (read-only), não pode editar nada
        </p>
    </div>
    """, unsafe_allow_html=True)
