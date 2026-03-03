import streamlit as st
import pandas as pd
from database import get_connection

st.set_page_config(layout="wide")

conn = get_connection()
cursor = conn.cursor()

# -----------------------------
# SESSION STATE
# -----------------------------

if "processo_id" not in st.session_state:
    st.session_state.processo_id = None

if "candidato_id" not in st.session_state:
    st.session_state.candidato_id = None


# =============================
# 1️⃣ LISTA DE PROCESSOS
# =============================

if st.session_state.processo_id is None:

    st.title("Processos Seletivos")

    cursor.execute("""
        SELECT id, nome, area, senioridade, status, data_inicio
        FROM processos
        ORDER BY data_inicio DESC
    """)
    processos = cursor.fetchall()

    if not processos:
        st.info("Nenhum processo encontrado.")
    else:
        for id_p, nome, area, senioridade, status, data_inicio in processos:

            col1, col2 = st.columns([4, 1])

            with col1:
                st.subheader(nome)
                st.caption(
                    area + " | " + senioridade + " | " + status + " | Início: " + str(data_inicio)
                )

            with col2:
                if st.button("Abrir", key="abrir_" + str(id_p)):
                    st.session_state.processo_id = id_p
                    st.session_state.candidato_id = None
                    st.rerun()


# =============================
# 2️⃣ DETALHE DO PROCESSO
# =============================

elif st.session_state.processo_id and st.session_state.candidato_id is None:

    processo_id = st.session_state.processo_id

    if st.button("← Voltar para Processos"):
        st.session_state.processo_id = None
        st.rerun()

    cursor.execute("""
        SELECT nome, status
        FROM processos
        WHERE id = %s
    """, (processo_id,))
    
    resultado = cursor.fetchone()

    if not resultado:
        st.error("Processo não encontrado.")
        st.stop()

    nome_processo, status_processo = resultado

    st.title("Processo: " + nome_processo)

    # -----------------------------
    # FECHAR / REABRIR
    # -----------------------------
    col1, col2 = st.columns([3,1])

    with col2:
        if status_processo == "Aberto":
            if st.button("🔒 Fechar Processo"):
                cursor.execute(
                    "UPDATE processos SET status = %s WHERE id = %s",
                    ("Fechado", processo_id)
                )
                conn.commit()
                st.rerun()
        else:
            if st.button("🔓 Reabrir Processo"):
                cursor.execute(
                    "UPDATE processos SET status = %s WHERE id = %s",
                    ("Aberto", processo_id)
                )
                conn.commit()
                st.rerun()

    if status_processo == "Fechado":
        st.warning("Processo encerrado - somente leitura")

    st.divider()

    # -----------------------------
    # FILTRO
    # -----------------------------
    st.subheader("Ranking de Candidatos")

    filtro_status = st.radio(
        "Filtrar por:",
        ["Todos", "Pendentes", "Avaliados"],
        horizontal=True
    )

    # -----------------------------
    # QUERY
    # -----------------------------

    cursor.execute("""
        SELECT 
            c.id,
            c.nome,
            c.email,
            MAX(a.nota_final) as nota_final
        FROM processos_candidatos pc
        JOIN candidatos c ON pc.candidato_id = c.id
        LEFT JOIN avaliacoes a
            ON a.candidato_id = c.id
            AND a.processo_id = %s
        WHERE pc.processo_id = %s
        GROUP BY c.id, c.nome, c.email
        ORDER BY 
            (MAX(a.nota_final) IS NULL) ASC,
            MAX(a.nota_final) DESC,
            c.nome ASC
    """, (processo_id, processo_id))

    candidatos = cursor.fetchall()

    if not candidatos:
        st.info("Nenhum candidato vinculado a este processo.")
    else:
        for id_c, nome, email, nota_final in candidatos:

            if filtro_status == "Pendentes" and nota_final is not None:
                continue

            if filtro_status == "Avaliados" and nota_final is None:
                continue

            col1, col2 = st.columns([4,1])

            with col1:
                st.write("**" + nome + "**")
                st.caption(email)

            with col2:
                if nota_final is None:
                    st.warning("Pendente")
                else:
                    st.success("Nota: " + str(round(float(nota_final), 2)))

                if st.button("Ver Detalhes", key="cand_" + str(id_c)):
                    st.session_state.candidato_id = id_c
                    st.rerun()

            st.divider()


# =============================
# 3️⃣ DETALHE DO CANDIDATO
# =============================

elif st.session_state.candidato_id:

    processo_id = st.session_state.processo_id
    candidato_id = st.session_state.candidato_id

    if st.button("← Voltar para Ranking"):
        st.session_state.candidato_id = None
        st.rerun()

    cursor.execute("""
        SELECT nome, email 
        FROM candidatos 
        WHERE id = %s
    """, (candidato_id,))

    resultado = cursor.fetchone()

    if not resultado:
        st.error("Candidato não encontrado.")
        st.stop()

    nome_candidato, email_candidato = resultado

    st.title("Candidato: " + nome_candidato)
    st.caption(email_candidato)

    st.divider()

    cursor.execute("""
        SELECT id, nota_final, avaliador, data
        FROM avaliacoes
        WHERE processo_id = %s AND candidato_id = %s
        ORDER BY data DESC
    """, (processo_id, candidato_id))

    avaliacoes = cursor.fetchall()

    if not avaliacoes:
        st.info("Nenhuma avaliação encontrada.")
    else:
        for avaliacao_id, nota_final, avaliador, data in avaliacoes:

            st.subheader("Avaliação - " + str(avaliador) + " (" + str(data) + ")")
            st.metric("Nota Final", round(float(nota_final), 2))

            cursor.execute("""
                SELECT bloco, criterio, nota, justificativa
                FROM avaliacoes_criterios
                WHERE avaliacao_id = %s
                ORDER BY bloco
            """, (avaliacao_id,))

            notas = cursor.fetchall()

            if notas:

                df_notas = pd.DataFrame(
                    notas,
                    columns=["Bloco", "Critério", "Nota", "Justificativa"]
                )

                for bloco in df_notas["Bloco"].unique():

                    st.markdown("### " + bloco)
                    df_bloco = df_notas[df_notas["Bloco"] == bloco]

                    for _, row in df_bloco.iterrows():
                        st.markdown(
                            "**" + row["Critério"] + "** — Nota: " + str(row["Nota"])
                        )
                        st.write(row["Justificativa"])
                        st.markdown("---")

            st.divider()