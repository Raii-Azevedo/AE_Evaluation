import streamlit as st
import pandas as pd
from database import init_db, get_connection

st.set_page_config(page_title="Sistema de Avaliação", layout="wide")

# ===== ESTILO =====
st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #0B1E3D 0%, #3A1C71 40%, #D4145A 100%); }
.card { background: linear-gradient(135deg, rgba(29,78,216,0.25), rgba(219,39,119,0.25)); backdrop-filter: blur(12px); padding: 28px; border-radius: 20px; margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.15); box-shadow: 0px 10px 30px rgba(0,0,0,0.35); }
.card:hover { transform: translateY(-6px); box-shadow: 0px 20px 40px rgba(0,0,0,0.5); }
.status-green { color: #22c55e; font-weight: bold; }
.status-yellow { color: #facc15; font-weight: bold; }
.status-red { color: #ef4444; font-weight: bold; }
.status-gray { color: #9ca3af; font-weight: bold; }
h1, h2, h3 { color: white; }
.stButton>button { border-radius: 12px; height: 44px; font-weight: 600; border: none; background: linear-gradient(135deg, #3B82F6, #EC4899); color: white; transition: 0.25s ease-in-out; }
.stButton>button:hover { transform: translateY(-3px); box-shadow: 0px 10px 20px rgba(236,72,153,0.5); }
.stTextInput>div>div>input, .stTextArea textarea { border-radius: 12px !important; background-color: rgba(255,255,255,0.08) !important; color: white !important; border: 1px solid rgba(255,255,255,0.15) !important; }
</style>
""", unsafe_allow_html=True)

# ===== DB =====
init_db()
conn = get_connection()
cursor = conn.cursor()

# ===== SESSION STATE =====
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
        for criterio in criterios:
            st.session_state[f"{bloco}_{criterio}"] = 5.0
            st.session_state[f"just_{bloco}_{criterio}"] = ""

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
        margin-bottom:30px;
    ">
        SISTEMA DE AVALIAÇÃO TÉCNICA
    </h1>
    """, unsafe_allow_html=True)

    with st.expander("➕ Criar Novo Processo"):
        nome = st.text_input("Nome do Processo", key="novo_nome_processo")
        area = st.selectbox("Área", ["Analytics Engineer"], key="novo_area_processo")
        tipo = st.selectbox("Tipo", ["Ampla Concorrência", "Afirnativa: Mulheres Cis e Trans", "Afirmativa: Pessoas Negras", "Afirmativa: LGBTQIAPN+"], key="novo_tipo_processo")
        senioridade = st.selectbox("Senioridade", ["Estágio", "Pleno"], key="novo_senioridade")
        status = st.selectbox("Status", ["Aberto", "Fechado"], key="novo_status")
        local = st.selectbox("Local", ["BRASIL", "LATAM"], key="novo_local_processo")

        if st.button("Criar Processo"):
            cursor.execute("""
                INSERT INTO processos (nome, area, tipo, senioridade, status, local)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (nome, area, tipo, senioridade, status, local))
            conn.commit()
            st.success("Processo criado!")
            st.rerun()

    st.divider()

    # Listar processos
    cursor.execute("SELECT id, nome, area, tipo, senioridade, local, status FROM processos ORDER BY id DESC")
    processos = cursor.fetchall()

    for id_p, nome, area, tipo, senioridade, local, status in processos:
        col1, col2 = st.columns([4,1])
        with col1:
            st.markdown("### {nome}".format(nome=nome))
            st.caption("{area} | {tipo} | {senioridade} | {local} | {status}".format(area=area, tipo=tipo, senioridade=senioridade, local=local, status=status))
        with col2:
            if st.button("Entrar", key=f"entrar_{id_p}"):
                st.session_state.processo_id = id_p
                st.session_state.view = "processo"
                st.rerun()

# =====================================================
# 📂 PROCESSO
# =====================================================
elif st.session_state.view == "processo":

    processo_id = st.session_state.processo_id
    cursor.execute("SELECT nome, status FROM processos WHERE id = %s", (processo_id,))
    nome_processo, status_processo = cursor.fetchone()

    st.title(f"📂 {nome_processo}")

    if st.button("← Voltar"):
        st.session_state.view = "home"
        st.session_state.processo_id = None
        st.rerun()

    # Botão fechar processo (apenas se aberto)
    if status_processo == "Aberto":
        if st.button("Fechar Processo"):
            cursor.execute("UPDATE processos SET status = %s WHERE id = %s", ("Fechado", processo_id))
            conn.commit()
            st.success("Processo fechado! 🔒")
            st.rerun()
    
    st.divider()

    # Adicionar candidato (só se aberto)
    if status_processo == "Aberto":
        with st.expander("➕ Adicionar Candidato"):
            nome_c = st.text_input("Nome do Candidato", key="novo_nome_c")
            email_c = st.text_input("Email", key="novo_email_c")
            if st.button("Adicionar"):
                cursor.execute("SELECT id FROM candidatos WHERE email = %s", (email_c,))
                existe = cursor.fetchone()
                if not existe:
                    cursor.execute("INSERT INTO candidatos (nome, email) VALUES (%s, %s)", (nome_c, email_c))
                    conn.commit()
                    candidato_id = cursor.lastrowid
                else:
                    candidato_id = existe[0]

                # Vínculo ao processo - PostgreSQL syntax
                cursor.execute("""
                    INSERT INTO processos_candidatos (processo_id, candidato_id) 
                    VALUES (%s, %s) 
                    ON CONFLICT (processo_id, candidato_id) DO NOTHING
                """, (processo_id, candidato_id))
                conn.commit()
                st.success("Candidato registrado!")

                # Reset seguro dos inputs
                st.session_state["novo_nome_c"] = ""
                st.session_state["novo_email_c"] = ""
                st.rerun()

    st.divider()

    # Listar candidatos Vinculados
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

    # =========================
    # 🔎 BUSCA
    # =========================
    busca = st.text_input("🔎 Buscar candidato por nome ou email")

    if busca:
        candidatos = [
            c for c in candidatos
            if busca.lower() in c[1].lower() or busca.lower() in c[2].lower()
        ]

    # =========================
    # 🎯 FILTRO POR STATUS
    # =========================
    filtro_status = st.radio(
        "Filtrar candidatos:",
        ["Todos", "Pendentes", "Avaliados"],
        horizontal=True
    )

    if filtro_status == "Pendentes":
        candidatos = [c for c in candidatos if c[3] == 0]

    elif filtro_status == "Avaliados":
        candidatos = [c for c in candidatos if c[3] > 0]

    # =========================
    # 📌 ORDENAR (Pendentes primeiro)
    # =========================
    candidatos.sort(key=lambda x: x[3])  # 0 (pendente) vem antes

    for id_c, nome, email, total_avaliacoes in candidatos:

        # Buscar a última avaliação do candidato neste processo
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
            elif nota_final >= 6:
                status_class = "status-yellow"
            else:
                status_class = "status-red"

            status_html = '<span class="{status_class}">Nota Final: {nota_final}</span>'.format(status_class=status_class, nota_final=nota_final)
        else:
            status_html = '<span class="status-gray">Pendente</span>'

        st.markdown("""
            <div class="card">
                <h3>{nome}</h3>
                <p style="color:#9CA3AF;">{email}</p>
                <p>{status_html}</p>
            </div>
        """.format(nome=nome, email=email, status_html=status_html), unsafe_allow_html=True)
        col1, col2 = st.columns([1,1])

        with col1:
            if avaliacao:
                if st.button("Ver Detalhes", key=f"det_{id_c}"):
                    st.session_state.avaliacao_id = avaliacao_id
                    st.session_state.view = "detalhe_avaliacao"
                    st.rerun()

        with col2:
            if not avaliacao and status_processo == "Aberto":
                if st.button("Avaliar", key=f"avaliar_{id_c}"):
                    st.session_state.candidato_id = id_c
                    st.session_state.view = "avaliar"
                    st.rerun()
                    
# =====================================================
# 📝 AVALIAR
# =====================================================
elif st.session_state.view == "avaliar":

    candidato_id = st.session_state.candidato_id
    processo_id = st.session_state.processo_id

    if st.button("← Voltar ao Processo"):
        st.session_state.view = "processo"
        st.rerun()

    cursor.execute("SELECT nome FROM candidatos WHERE id = %s", (candidato_id,))
    nome_candidato = cursor.fetchone()[0]
    st.title("📝 Avaliação - {}".format(nome_candidato))

    # ==============================
    # Estrutura com peso e obrigatório
    # ==============================

    estrutura = {
    "Tratamentos": [
        {
            "criterio": "Arquitetura em Camadas (Raw / Staging / Golden)",
            "descricao": "Raw (dados brutos), Staging (dados tratados e padronizados) e Golden (dados modelados e prontos para consumo analítico).",
            "peso": 1,
            "obrigatorio": False
        },
        {
            "criterio": "Criação de Dimensões",
            "descricao": "Construção de dimensões auxiliares como calendário (ano, mês, trimestre, semana etc.), dimensões descritivas (produto, cliente, canal, status) e tabelas de apoio.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Tratamento de Tipagem e Strings",
            "descricao": "Conversão adequada de tipos de dados, padronização de datas, TRIM, UPPER/LOWER, garantindo integridade nos joins.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Deduplicação",
            "descricao": "Tratamento de registros duplicados evitando explosão de métricas e aplicação de regras de priorização.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Padronização de Nomenclatura",
            "descricao": "Uso de padrão para nomes de tabelas e colunas (snake_case, prefixos fact_/dim_), garantindo consistência.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Normalização de Categorias",
            "descricao": "Consolidação e padronização de valores categóricos (ex: Google Ads, status etc.).",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Avaliação de Hard-Coding",
            "descricao": "Evitar regras fixas excessivas e preferir tabelas de-para para manutenção e governança.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Modelagem de Dados (Star / Snowflake)",
            "descricao": "Estruturação com fatos e dimensões bem definidas, relacionamento correto e granularidade clara.",
            "peso": 3,
            "obrigatorio": True
        },
        {
            "criterio": "Organização do Dashboard (Medidas e Relacionamentos)",
            "descricao": "Medidas organizadas, relacionamentos consistentes e uso adequado de cardinalidade e direção de filtro.",
            "peso": 2,
            "obrigatorio": True
        },
    ],

    "Análises": [
        {
            "criterio": "Escolha das Métricas Estratégicas",
            "descricao": "Definição de KPIs relevantes como Receita, Ticket Médio, CAC, LTV, Conversão e Churn.",
            "peso": 3,
            "obrigatorio": True
        },
        {
            "criterio": "Cálculo Correto das Métricas",
            "descricao": "Implementação correta das fórmulas respeitando granularidade, filtros e contexto.",
            "peso": 3,
            "obrigatorio": True
        },
        {
            "criterio": "Evolução dos Indicadores",
            "descricao": "Apresentação temporal dos KPIs permitindo análise de tendência e sazonalidade.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Segmentação das Métricas",
            "descricao": "Análise por canal, produto, região ou cliente com gráficos adequados.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Storytelling",
            "descricao": "Construção de narrativa lógica com destaque de insights e impactos.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Relatório Executivo vs Operacional",
            "descricao": "Separação clara entre visão estratégica (KPIs principais) e visão exploratória detalhada.",
            "peso": 2,
            "obrigatorio": True
        },
    ],

    "Visual": [
        {
            "criterio": "Organização dos Visuais",
            "descricao": "Layout limpo, alinhamento consistente, espaçamento adequado e hierarquia visual clara.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Filtros e Segmentadores",
            "descricao": "Criação estratégica de filtros (data, canal, produto etc.) facilitando navegação.",
            "peso": 2,
            "obrigatorio": True
        },
        {
            "criterio": "Paleta de Cores e Tipografia",
            "descricao": "Uso consistente de cores, contraste adequado e tipografia legível.",
            "peso": 1,
            "obrigatorio": True
        },
        {
            "criterio": "Títulos e Unidades de Medida",
            "descricao": "Títulos claros, unidades visíveis (R$ 10k) e rótulos legíveis.",
            "peso": 1,
            "obrigatorio": True
        },
    ]
}

    soma_ponderada = 0
    soma_pesos = 0
    reprovado_por_obrigatorio = False

    # ==============================
    # Sliders
    # ==============================

    for bloco, criterios in estrutura.items():
        st.divider()
        st.header(bloco)

        for item in criterios:
            criterio = item["criterio"]
            descricao = item.get("descricao", "")  # se tiver descrição
            peso = item["peso"]
            obrigatorio = item["obrigatorio"]

            key_nota = "{}_{}".format(bloco, criterio)
            key_just = "just_{}_{}".format(bloco, criterio)

            # Renderizar o critério com estilo
            st.markdown(f"""
                <p style="font-size:20px; font-weight:700; margin-bottom:4px;">{criterio}</p>
                <p style="font-size:15px; color:#D1D5DB; margin:0;">{descricao}</p>
                <p style="font-size:15px; color:#9CA3AF; margin-top:2px;">Peso: {peso}</p>
            """, unsafe_allow_html=True)

            nota = st.slider(
            "🔴 Obrigatório" if obrigatorio else "",
            0.0,
            10.0,
            st.session_state[key_nota],
            step=0.5,
            key=key_nota
            )

            justificativa = st.text_area(
                "Justificativa",
                st.session_state[key_just],
                key=key_just
            )

            soma_ponderada += nota * peso
            soma_pesos += peso

            if obrigatorio and nota < 6:
                reprovado_por_obrigatorio = True

    # ==============================
    # Resultado
    # ==============================

    nota_final = round(soma_ponderada / soma_pesos, 2)

    st.divider()
    st.subheader("🎯 Resultado Final")

    st.metric("Nota Final (Ponderada)", nota_final)

    if nota_final >= 8:
        st.success("Recomendado")
    elif nota_final >= 6:
        st.warning("Avaliar melhor")
    else:
        st.error("Não recomendado")

    # ==============================
    # Campos finais
    # ==============================

    avaliador = st.text_input("Nome do Avaliador")
    comentario_final = st.text_area("Comentário Final Geral")

    # ==============================
    # Salvar
    # ==============================

    if st.button("Salvar Avaliação"):

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

        st.success("Avaliação salva com sucesso!")
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

        st.title("📊 Detalhe da Avaliação")
        st.metric("Nota Final", nota_final)
        st.write("**Avaliador: {}**".format(avaliador))
        st.write("**Comentário Geral:**")
        st.write(comentario_final)

        st.divider()

        # Buscar critérios
        cursor.execute("""
            SELECT bloco, criterio, nota, justificativa
            FROM avaliacoes_criterios
            WHERE avaliacao_id = %s
            ORDER BY bloco
        """, (avaliacao_id,))

        criterios = cursor.fetchall()

        for bloco, criterio, nota, justificativa in criterios:
            st.subheader(bloco)
            st.write("**{}** — Nota: {}".format(criterio, nota))
            st.write("Justificativa: {}".format(justificativa))
            st.divider()
