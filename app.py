import streamlit as st
import pandas as pd
import time
from datetime import datetime
from database import (
    init_db, get_connection, return_connection,
    get_aplicacoes_pendentes, get_aplicacoes_avaliadas, get_stats,
    get_aplicacao_info, salvar_avaliacao, salvar_criterios_avaliacao,
    get_ultima_avaliacao_por_aplicacao, get_avaliacao_completa, get_criterios_avaliacao,
    atualizar_gh_status_aplicacao,
    get_processos_ativos, get_processo_info,
    get_estatisticas_gerais, get_avaliacoes_recentes,
    criar_processo, adicionar_candidato_processo
)
from criterios_areas import get_criterios_por_area, get_areas_disponiveis
from allowed_emails import (
    is_email_allowed, get_user_role, is_admin, is_viewer, can_edit,
    add_allowed_email, remove_allowed_email, get_all_allowed_emails
)

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
    defaults = {
        "view": "home",
        "processo_id": None,
        "aplicacao_id": None,
        "avaliacao_id": None,
        "notifications": [],
        "logged_in": False,
        "user_email": None,
        "user_name": None,
        "user_role": None,
        "admin_view": "dashboard",
        "candidato_filter": "todos",
        "search_term": ""
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
    if email:
        name_part = email.split('@')[0]
        name = name_part.replace('.', ' ').replace('_', ' ').title()
        return name
    return "Avaliador"

# ===== STYLES =====
def get_styles():
    return """
    <style>
    .stApp { background: linear-gradient(135deg, #0B1E3D 0%, #1E1E2F 40%, #2D1B3A 100%); }
    .card { background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03)); backdrop-filter: blur(12px); padding: 28px; border-radius: 20px; margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0px 10px 30px rgba(0,0,0,0.35); transition: all 0.3s ease; }
    .card:hover { transform: translateY(-6px); box-shadow: 0px 20px 40px rgba(0,0,0,0.5); border-color: rgba(255,255,255,0.2); }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-left: 10px; }
    .badge-success { background: rgba(34,197,94,0.2); color: #22c55e; }
    .badge-warning { background: rgba(250,204,21,0.2); color: #facc15; }
    .badge-danger { background: rgba(239,68,68,0.2); color: #ef4444; }
    .badge-info { background: rgba(59,130,246,0.2); color: #60a5fa; }
    .badge-gh-done { background: rgba(34,197,94,0.3); color: #22c55e; }
    .badge-gh-pending { background: rgba(239,68,68,0.3); color: #ef4444; }
    h1, h2, h3, h4, h5, h6, p, span, label { color: #f3f4f6; }
    .stButton>button { border-radius: 12px; height: 44px; font-weight: 600; border: none; background: linear-gradient(135deg, #3B82F6, #EC4899); color: white; transition: all 0.25s ease; }
    .stButton>button:hover { transform: translateY(-3px); box-shadow: 0px 10px 20px rgba(236,72,153,0.5); }
    .stMetric { background: rgba(255,255,255,0.05); border-radius: 12px; padding: 15px; }
    hr { border-color: rgba(255,255,255,0.1); }
    .login-container { max-width: 400px; margin: 0 auto; padding: 40px; background: rgba(255,255,255,0.05); border-radius: 20px; backdrop-filter: blur(10px); }
    </style>
    """

st.markdown(get_styles(), unsafe_allow_html=True)

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
                        st.error("❌ Email não autorizado.")
                else:
                    st.warning("⚠️ Digite seu email")
            st.markdown('</div>', unsafe_allow_html=True)

# ===== ADMIN FUNCTIONS =====
def admin_manage_emails():
    st.title("📧 Gerenciar Emails Autorizados")
    emails = get_all_allowed_emails()
    if emails:
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
                    add_notification(f"✅ Email {new_email} adicionado", "success")
                    st.rerun()
                else:
                    st.error("❌ Erro ao adicionar email")
    with st.expander("🗑️ Remover Email"):
        email_to_remove = st.selectbox("Selecione o email", [e[0] for e in emails if e[0] != "admin@artefact.com"])
        if st.button("Remover Email", type="primary"):
            if email_to_remove and remove_allowed_email(email_to_remove):
                add_notification(f"✅ Email removido", "success")
                st.rerun()

def admin_dashboard():
    st.title("📊 Dashboard Administrativo")
    
    # ===== CRIAR PROCESSO =====
    st.subheader("➕ Criar Novo Processo")
    with st.form("form_criar_processo"):
        col1, col2 = st.columns(2)
        with col1:
            nome_processo = st.text_input("Nome do Processo*")
            job_title = st.text_input("Job Title*")
            pais = st.text_input("País*", value="Brasil")
        with col2:
            admission_category = st.selectbox("Categoria*", ["Ampla Concorrência", "Pessoas Negras", "LGBTQIAPN+", "Mulheres (Cis | Trans)", "Pessoa com Deficiência"])
            area = st.selectbox("Área*", get_areas_disponiveis())
        submitted = st.form_submit_button("✅ Criar Processo")
        if submitted:
            if nome_processo and job_title and admission_category and area and pais:
                processo_id = criar_processo(nome_processo, area, "Pleno", job_title, admission_category, pais)
                if processo_id:
                    add_notification(f"✅ Processo '{nome_processo}' criado!", "success")
                    st.rerun()
                else:
                    st.error("❌ Erro ao criar processo")
            else:
                st.error("Preencha todos os campos obrigatórios!")

    st.divider()
    
    # ===== ESTATÍSTICAS =====
    try:
        stats = get_estatisticas_gerais()
        total_processos = stats[0] if len(stats) > 0 else 0
        total_candidatos = stats[1] if len(stats) > 1 else 0
        total_aplicacoes = stats[2] if len(stats) > 2 else 0
        total_avaliacoes = stats[3] if len(stats) > 3 else 0
        gh_atualizados = stats[4] if len(stats) > 4 else 0
        total_usuarios = stats[5] if len(stats) > 5 else 0
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1: st.metric("👥 Usuários", total_usuarios)
        with col2: st.metric("📋 Processos", total_processos)
        with col3: st.metric("👤 Candidatos", total_candidatos)
        with col4: st.metric("📝 Aplicações", total_aplicacoes)
        with col5: st.metric("⭐ Avaliações", total_avaliacoes)
        with col6: st.metric("✅ GH Atualizado", gh_atualizados)
    except Exception as e:
        st.error(f"Erro ao carregar estatísticas: {e}")

# ===== SIDEBAR =====
def render_sidebar():
    with st.sidebar:
        if st.session_state.logged_in:
            role_display = {"admin": "👑 Administrador", "user": "⭐ Avaliador", "viewer": "👀 Visualizador"}.get(st.session_state.user_role, "👤 Usuário")
            st.markdown(f"""
            <div style="text-align:center; margin-bottom:20px;">
                <div style="background:linear-gradient(135deg,#3B82F6,#EC4899); border-radius:50%; width:60px; height:60px; margin:0 auto 10px; display:flex; align-items:center; justify-content:center;">
                    <span style="font-size:30px;">👤</span>
                </div>
                <h3>{st.session_state.user_name}</h3>
                <p style="font-size:12px;">{st.session_state.user_email}<br>{role_display}</p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("---")
            
            if st.session_state.user_role == "admin":
                st.markdown("### 🛠️ Administração")
                current_option = "📧 Emails" if st.session_state.get("admin_view") == "emails" else "📊 Dashboard"
                admin_option = st.radio(
                    "Menu Admin",
                    ["📊 Dashboard", "📧 Emails"],
                    index=0 if current_option == "📊 Dashboard" else 1,
                    key="admin_menu"
                )

                selected_view = "dashboard" if admin_option == "📊 Dashboard" else "emails"
                if st.session_state.get("admin_view") != selected_view:
                    st.session_state.admin_view = selected_view
                    # Só reseta a view se não estiver dentro de um processo
                    if st.session_state.view not in ["processo", "avaliar", "detalhe_avaliacao"]:
                        st.session_state.view = "home"
                    st.rerun()

                if st.button("🏠 Voltar para Administração", use_container_width=True):
                    st.session_state.view = "home"
                    st.session_state.processo_id = None
                    st.session_state.aplicacao_id = None
                    st.session_state.avaliacao_id = None
                    st.rerun()
            
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

# ===== FORMULÁRIO PARA ADICIONAR CANDIDATO DENTRO DO PROCESSO =====
def add_candidate_form(processo_id):
    """Formulário para adicionar candidato dentro do processo"""
    with st.expander("➕ Adicionar Novo Candidato a este Processo", expanded=False):
        with st.form(f"form_add_candidato_{processo_id}"):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome do Candidato*")
                email = st.text_input("Email do Candidato*")
                linkedin = st.text_input("LinkedIn (URL)")
            with col2:
                greenhouse_id = st.text_input("Greenhouse ID (URL)")
                pbix_file = st.text_input("Link do arquivo PBIX")
                optional_file = st.text_input("Link do arquivo opcional")
            
            submitted = st.form_submit_button("➕ Adicionar Candidato", use_container_width=True)
            if submitted:
                if nome and email:
                    resultado = adicionar_candidato_processo(processo_id, nome, email, linkedin, greenhouse_id, pbix_file, optional_file)
                    if resultado and resultado.get("sucesso"):
                        acao = resultado.get("acao", "adicionado")
                        st.session_state.candidato_filter = "todos"
                        st.session_state.search_input = ""
                        add_notification(f"✅ Candidato {nome} {acao} no processo!", "success")
                        st.rerun()
                    else:
                        erro = resultado.get("erro", "Erro desconhecido") if isinstance(resultado, dict) else "Erro desconhecido"
                        st.error(f"❌ Erro ao adicionar candidato: {erro}")
                else:
                    st.error("Preencha nome e email do candidato!")

# ===== EVALUATION FORM =====
def evaluation_form(aplicacao_id, candidato_nome, email_candidato, linkedin, greenhouse_id, pbix_file, optional_file, processo_nome, area_processo):
    estrutura = get_criterios_por_area(area_processo)
    
    st.subheader("👤 Informações do Candidato")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Nome:** {candidato_nome}")
        st.write(f"**Email:** {email_candidato}")
        st.write(f"**Vaga:** {processo_nome}")
    with col2:
        if linkedin: st.markdown(f"🔗 [LinkedIn]({linkedin})")
        if greenhouse_id: st.markdown(f"🏢 [Greenhouse]({greenhouse_id})")
        if pbix_file: st.markdown(f"📊 [Arquivo PBIX]({pbix_file})")
        if optional_file: st.markdown(f"📁 [Arquivo Opcional]({optional_file})")
    
    st.divider()
    
    # NOTAS POR BLOCO
    soma_ponderada = 0
    soma_pesos = 0
    notas_blocos = {}
    
    for bloco, criterios in estrutura.items():
        st.subheader(f"📌 {bloco}")
        
        notas_itens = []
        for item in criterios:
            criterio = item["criterio"]
            peso = item["peso"]
            descricao = item.get("descricao", "")
            
            key_nota = f"{bloco}_{criterio}"
            
            if key_nota not in st.session_state:
                st.session_state[key_nota] = 5.0
            
            if descricao:
                st.caption(f"ℹ️ {descricao}")
            
            nota = st.slider(
                f"{criterio} (Peso: {peso})",
                0.0, 10.0, st.session_state[key_nota], 0.5, key=key_nota
            )
            notas_itens.append(nota * peso)
            soma_ponderada += nota * peso
            soma_pesos += peso
        
        peso_total_bloco = sum(item["peso"] for item in criterios)
        nota_bloco = sum(notas_itens) / peso_total_bloco if peso_total_bloco > 0 else 0
        notas_blocos[bloco] = nota_bloco
        
        key_just = f"just_{bloco}"
        if key_just not in st.session_state:
            st.session_state[key_just] = ""
        
        justificativa = st.text_area(
            f"Justificativa para {bloco}",
            st.session_state[key_just],
            key=key_just,
            placeholder=f"Explique sua avaliação para {bloco}...",
            height=80
        )
        st.divider()
    
    nota_final = sum(notas_blocos.values()) / len(notas_blocos) if notas_blocos else 0
    nota_final = round(nota_final, 2)
    
    st.subheader("🎯 Resultado Final")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Nota Final", nota_final)
    with col2:
        st.metric("Tratamentos", f"{notas_blocos.get('Tratamentos', 0):.1f}")
    with col3:
        st.metric("Análises", f"{notas_blocos.get('Análises', 0):.1f}")
    st.metric("Visual", f"{notas_blocos.get('Visual', 0):.1f}")
    
    if nota_final >= 8:
        st.success("✅ Recomendado para contratação")
    elif nota_final >= 6:
        st.warning("⚠️ Avaliar melhor - Pontos de melhoria identificados")
    else:
        st.error("❌ Não recomendado - Necessita desenvolvimento")
    
    st.divider()
    
    st.subheader("⭐ Priorização")
    priorizacao = st.radio(
        "Selecione a prioridade do candidato:",
        ["Não priorizar", "Prioridade 1", "Prioridade 2"],
        index=0, horizontal=True
    )
    
    comentario = st.text_area("💬 Comentário Final Geral *", height=100, placeholder="Descreva sua avaliação de forma geral...")
    
    st.divider()
    
    if "confirmar_avaliacao" not in st.session_state:
        st.session_state.confirmar_avaliacao = False
    
    if st.button("✅ Finalizar Avaliação", type="primary", use_container_width=True):
        if not comentario:
            st.error("❌ Comentário final é obrigatório")
        else:
            st.session_state.confirmar_avaliacao = True
            st.rerun()
    
    if st.session_state.confirmar_avaliacao:
        st.warning("⚠️ **CONFIRMAR AVALIAÇÃO**")
        st.write("**Lembrete importante:**")
        st.write("1. Após salvar, você precisará atualizar a planilha com a **data de correção**")
        st.write("2. Não esqueça de **mover o candidato no Greenhouse** para a etapa correta")
        
        st.divider()
        st.write(f"**Candidato:** {candidato_nome}")
        st.write(f"**Nota Final:** {nota_final}")
        st.write(f"**Priorização:** {priorizacao}")
        
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✅ Já avaliei, salvar", use_container_width=True, type="primary"):
                avaliacao_id = salvar_avaliacao(
                    aplicacao_id, nota_final, st.session_state.user_email, 
                    comentario, priorizacao
                )
                if avaliacao_id:
                    for bloco in estrutura.keys():
                        just = st.session_state.get(f"just_{bloco}", "")
                        salvar_criterios_avaliacao(avaliacao_id, bloco, "Justificativa", 0, just)
                    
                    for bloco, criterios in estrutura.items():
                        for item in criterios:
                            criterio = item["criterio"]
                            nota = st.session_state.get(f"{bloco}_{criterio}", 5.0)
                            salvar_criterios_avaliacao(avaliacao_id, bloco, criterio, nota, "")
                    
                    st.session_state.confirmar_avaliacao = False
                    add_notification(f"✅ Avaliação de {candidato_nome} salva!", "success")
                    st.session_state.view = "processo"
                    st.rerun()
                else:
                    st.error("❌ Erro ao salvar avaliação")
        with col_no:
            if st.button("❌ Revisar", use_container_width=True):
                st.session_state.confirmar_avaliacao = False
                st.rerun()

# ===== MAIN APP =====
if not st.session_state.logged_in:
    login_page()
else:
    render_sidebar()
    show_notifications()
    
    if st.session_state.user_role == "admin":
        if st.session_state.view == "processo" or st.session_state.view == "avaliar" or st.session_state.view == "detalhe_avaliacao":
            pass
        else:
            if st.session_state.admin_view == "emails":
                admin_manage_emails()
            else:
                admin_dashboard()
            
            st.markdown("""
            <h1 style="text-align:center; font-size:48px; font-weight:700; background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                SISTEMA DE AVALIAÇÃO TÉCNICA
            </h1>
            """, unsafe_allow_html=True)
            st.divider()
            st.markdown("### 📋 Processos Disponíveis")
            
            processos = get_processos_ativos()
            if not processos:
                st.info("✨ Nenhum processo encontrado. Crie um processo no dashboard.")
            else:
                for proc in processos:
                    id_p, nome, job_title, admission_category = proc
                    st.markdown(f"""
                    <div class="card">
                        <h3>{nome}</h3>
                        <p><strong>Job Title:</strong> {job_title} • <strong>Categoria:</strong> {admission_category}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("📂 Entrar", key=f"entrar_admin_{id_p}", use_container_width=True):
                        st.session_state.processo_id = id_p
                        st.session_state.view = "processo"
                        st.rerun()
    
    if st.session_state.view == "home" and st.session_state.user_role != "admin":
        st.markdown("""
        <h1 style="text-align:center; font-size:48px; font-weight:700; background: linear-gradient(90deg, #60A5FA, #A78BFA, #F472B6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
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
                if st.button("📂 Entrar", key=f"entrar_user_{id_p}", use_container_width=True):
                    st.session_state.processo_id = id_p
                    st.session_state.view = "processo"
                    st.rerun()
    
    elif st.session_state.view == "processo":
        processo_id = st.session_state.processo_id
        processo_info = get_processo_info(processo_id)
        
        if processo_info:
            if len(processo_info) == 4:
                nome_processo, job_title, admission_category, status = processo_info
            else:
                nome_processo, job_title, admission_category = processo_info[:3]
                status = "Aberto"
            
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
            
            # FORMULÁRIO PARA ADICIONAR CANDIDATO DENTRO DO PROCESSO
            if can_edit(st.session_state.user_email):
                add_candidate_form(processo_id)
            
            st.divider()
            
            stats = get_stats(processo_id)
            if stats:
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("📝 Pendentes", stats[0])
                with col2: st.metric("✅ Avaliados", stats[1])
                with col3: st.metric("⭐ Média", f"{stats[2]:.1f}" if stats[2] else "—")
                with col4: st.metric("🏢 GH Atualizado", stats[3] if len(stats) > 3 else 0)
            
            st.divider()
            
            st.markdown("### 🔍 Buscar Candidato")
            search_term = st.text_input("Buscar por nome ou email", placeholder="Digite o nome ou email...", key="search_input")
            
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
            st.markdown("### 👥 Candidatos")
            
            pendentes = get_aplicacoes_pendentes(processo_id)
            avaliados = get_aplicacoes_avaliadas(processo_id)
            
            # Diagnóstico visível para verificar dados
            with st.expander(f"🔍 Diagnóstico: {len(pendentes)} pendentes, {len(avaliados)} avaliados (processo_id={processo_id})", expanded=False):
                if pendentes:
                    st.write("Pendentes encontrados:")
                    for p in pendentes:
                        st.write(f"  - ID:{p[0]}, Nome:{p[2]}, Email:{p[3]}")
                else:
                    st.write("Nenhum candidato pendente retornado pela query.")
                if avaliados:
                    st.write("Avaliados encontrados:")
                    for a in avaliados:
                        st.write(f"  - ID:{a[0]}, Nome:{a[2]}, Email:{a[3]}")
                else:
                    st.write("Nenhum candidato avaliado retornado pela query.")
            
            if search_term:
                search_lower = search_term.lower()
                pendentes = [p for p in pendentes if search_lower in p[2].lower() or search_lower in p[3].lower()]
                avaliados = [a for a in avaliados if search_lower in a[2].lower() or search_lower in a[3].lower()]
            
            if st.session_state.candidato_filter == "avaliados":
                pendentes_exibir = []
                avaliados_exibir = avaliados
            elif st.session_state.candidato_filter == "pendentes":
                pendentes_exibir = pendentes
                avaliados_exibir = []
            else:
                pendentes_exibir = pendentes
                avaliados_exibir = avaliados

            candidatos_exibir = pendentes_exibir + avaliados_exibir
            st.caption(f"Mostrando {len(candidatos_exibir)} candidatos")
            
            if not candidatos_exibir:
                st.info("Nenhum candidato encontrado para este processo.")
            
            for app in pendentes_exibir:
                aplicacao_id, candidato_id, nome, email, linkedin, timestamp, greenhouse_id, pbix_file, optional_file = app[:9]
                ts_str = timestamp.strftime('%d/%m/%Y %H:%M') if timestamp else "Data não informada"
                
                st.markdown(f"""
                <div class="card">
                    <h3>{nome} <span class="badge badge-info">⏳ Pendente</span></h3>
                    <p>📧 {email}</p>
                    <p>📅 Data de aplicação: {ts_str}</p>
                    <p><span class="badge badge-gh-pending">⚠️ Pendente GH</span></p>
                </div>
                """, unsafe_allow_html=True)
                
                if can_edit(st.session_state.user_email):
                    if st.button("📝 Avaliar", key=f"avaliar_{aplicacao_id}"):
                        st.session_state.aplicacao_id = aplicacao_id
                        st.session_state.view = "avaliar"
                        st.rerun()
                st.markdown("---")
            
            for app in avaliados_exibir:
                aplicacao_id, candidato_id, nome, email, timestamp, nota_final, priorizacao, gh_atualizada, data_avaliacao, avaliador = app[:10]
                
                badge_class = "badge-success" if nota_final >= 8 else ("badge-warning" if nota_final >= 6 else "badge-danger")
                status_text = "Aprovado" if nota_final >= 8 else ("Em análise" if nota_final >= 6 else "Reprovado")
                
                prior_badge = ""
                if priorizacao == "Prioridade 1":
                    prior_badge = '<span class="badge badge-success">🟢 Prioridade 1</span>'
                elif priorizacao == "Prioridade 2":
                    prior_badge = '<span class="badge badge-warning">🟡 Prioridade 2</span>'
                elif priorizacao == "Não priorizar" or not priorizacao:
                    prior_badge = '<span class="badge badge-danger">🔴 Não priorizar</span>'
                
                data_str = data_avaliacao.strftime('%d/%m/%Y') if data_avaliacao else "Data não registrada"
                
                st.markdown(f"""
                <div class="card">
                    <h3>{nome} 
                        <span class="badge {badge_class}">{status_text} - {nota_final:.1f}</span>
                        {prior_badge}
                    </h3>
                    <p>📧 {email}</p>
                    <p>📅 Avaliado em: {data_str}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🔍 Ver Detalhes", key=f"det_{aplicacao_id}"):
                    st.session_state.avaliacao_id = aplicacao_id
                    st.session_state.view = "detalhe_avaliacao"
                    st.rerun()
                
                st.markdown("---")
        else:
            st.error("Processo não encontrado")
            if st.button("Voltar para Home"):
                st.session_state.view = "home"
                st.session_state.processo_id = None
                st.rerun()
    
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
            
            app_info = get_aplicacao_info(aplicacao_id)
            if app_info:
                _, _, nome, email, linkedin, gh_id, pbix, opt, ts = app_info
                processo_info = get_processo_info(processo_id)
                if processo_info:
                    nome_processo = processo_info[0] if processo_info else "Processo"
                    area_processo = "Analytics Engineer"
                    st.title(f"📝 Avaliar: {nome}")
                    evaluation_form(aplicacao_id, nome, email, linkedin, gh_id, pbix, opt, nome_processo, area_processo)
    
    elif st.session_state.view == "detalhe_avaliacao":
        aplicacao_id = st.session_state.avaliacao_id
        if st.button("← Voltar"):
            st.session_state.view = "processo"
            st.rerun()
        
        avaliacao = get_avaliacao_completa(aplicacao_id)
        if avaliacao:
            nota_final, avaliador, comentario, data_avaliacao, priorizacao, gh_atualizada, nome, email, linkedin, gh_id, pbix, opt, timestamp, processo_nome, avaliacao_id = avaliacao
            
            st.title(f"🔍 Detalhe da Avaliação")
            col1, col2 = st.columns(2)
            with col1:
                if nota_final >= 8:
                    st.metric("Nota Final", f"{nota_final:.1f}", delta="Aprovado")
                elif nota_final >= 6:
                    st.metric("Nota Final", f"{nota_final:.1f}", delta="Em análise")
                else:
                    st.metric("Nota Final", f"{nota_final:.1f}", delta="Reprovado")
            with col2:
                st.metric("Avaliador", extract_name_from_email(avaliador))
            
            data_av_str = data_avaliacao.strftime('%d/%m/%Y %H:%M') if data_avaliacao else "Data não registrada"
            ts_str = timestamp.strftime('%d/%m/%Y %H:%M') if timestamp else "Data não informada"
            
            st.write(f"**Candidato:** {nome} ({email})")
            st.write(f"**Processo:** {processo_nome}")
            st.write(f"**Data da Avaliação:** {data_av_str}")
            st.write(f"**Data da Aplicação:** {ts_str}")
            st.write(f"**Priorização:** {priorizacao if priorizacao else 'Não priorizar'}")
            
            if linkedin: st.markdown(f"🔗 [LinkedIn]({linkedin})")
            if gh_id: st.markdown(f"🏢 [Greenhouse]({gh_id})")
            if pbix: st.markdown(f"📊 [Arquivo PBIX]({pbix})")
            if opt: st.markdown(f"📁 [Arquivo Opcional]({opt})")
            
            st.divider()
            st.subheader("💬 Comentário Geral")
            st.write(comentario)
            
            st.divider()
            st.subheader("📊 Avaliação por Critério")
            
            criterios = get_criterios_avaliacao(avaliacao_id)
            
            # Agrupar critérios por bloco
            blocos = {}
            for bloco, criterio, nota, just in criterios:
                if bloco not in blocos:
                    blocos[bloco] = []
                blocos[bloco].append((criterio, nota, just))
            
            for bloco, itens in blocos.items():
                st.markdown(f"### {bloco}")
                
                # Separar justificativas e notas
                justificativas = [(c, n, j) for c, n, j in itens if n == 0 and j]
                notas = [(c, n, j) for c, n, j in itens if n > 0]
                
                if justificativas:
                    for criterio, _, just in justificativas:
                        st.markdown(f"""
                        <div style="background: rgba(255,255,255,0.05); border-left: 3px solid #60a5fa; 
                                    padding: 14px 18px; border-radius: 8px; margin-bottom: 10px;">
                            <span style="color: #94a3b8; font-size: 13px;">📝 Justificativa</span>
                            <p style="margin: 6px 0 0; color: #e2e8f0;">{just}</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                if notas:
                    cols = st.columns(min(len(notas), 3))
                    for i, (criterio, nota, _) in enumerate(notas):
                        cor = "#22c55e" if nota >= 8 else ("#facc15" if nota >= 6 else "#ef4444")
                        bg = f"rgba({34},{197},{94},0.1)" if nota >= 8 else (f"rgba({250},{204},{21},0.1)" if nota >= 6 else f"rgba({239},{68},{68},0.1)")
                        with cols[i % min(len(notas), 3)]:
                            st.markdown(f"""
                            <div style="background: {bg}; border: 1px solid {cor}30; 
                                        padding: 16px; border-radius: 12px; margin-bottom: 10px; text-align: center;">
                                <div style="font-size: 28px; font-weight: 700; color: {cor};">{nota:.1f}</div>
                                <div style="font-size: 13px; color: #94a3b8; margin-top: 4px;">{criterio}</div>
                            </div>
                            """, unsafe_allow_html=True)
                
                st.markdown("")