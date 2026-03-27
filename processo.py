import streamlit as st
import pandas as pd
from database import get_connection, return_connection
from datetime import datetime

st.set_page_config(layout="wide")

# -----------------------------
# SESSION STATE
# -----------------------------
if "processo_id" not in st.session_state:
    st.session_state.processo_id = None

if "candidato_id" not in st.session_state:
    st.session_state.candidato_id = None

if "aplicacao_id" not in st.session_state:
    st.session_state.aplicacao_id = None


# =============================
# 1️⃣ LISTA DE PROCESSOS
# =============================

if st.session_state.processo_id is None:

    st.title("Processos Seletivos")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, job_title, admission_category, status, data_inicio
        FROM processos
        ORDER BY data_inicio DESC
    """)
    processos = cursor.fetchall()

    cursor.close()
    return_connection(conn)

    if not processos:
        st.info("Nenhum processo encontrado.")
    else:
        for id_p, nome, job_title, admission_category, status, data_inicio in processos:

            col1, col2 = st.columns([4, 1])

            with col1:
                st.subheader(nome)
                if job_title and admission_category:
                    st.caption(f"{job_title} | {admission_category}")
                st.caption(f"Status: {status} | Início: {data_inicio.strftime('%d/%m/%Y') if data_inicio else 'N/A'}")

            with col2:
                if st.button("Abrir", key="abrir_" + str(id_p)):
                    st.session_state.processo_id = id_p
                    st.session_state.candidato_id = None
                    st.session_state.aplicacao_id = None
                    st.rerun()


# =============================
# 2️⃣ DETALHE DO PROCESSO
# =============================

elif st.session_state.processo_id and st.session_state.candidato_id is None:

    processo_id = st.session_state.processo_id

    if st.button("← Voltar para Processos"):
        st.session_state.processo_id = None
        st.rerun()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT nome, job_title, admission_category, status
        FROM processos
        WHERE id = %s
    """, (processo_id,))
    
    resultado = cursor.fetchone()

    if not resultado:
        st.error("Processo não encontrado.")
        cursor.close()
        return_connection(conn)
        st.stop()

    nome_processo, job_title, admission_category, status_processo = resultado

    st.title(f"Processo: {nome_processo}")
    if job_title and admission_category:
        st.caption(f"{job_title} | {admission_category}")

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
    # QUERY - Usando a nova estrutura com aplicacoes
    # -----------------------------

    cursor.execute("""
        SELECT 
            a.id as aplicacao_id,
            c.id as candidato_id,
            c.nome,
            c.email,
            c.linkedin,
            a.timestamp_aplicacao,
            a.greenhouse_id,
            av.nota_final,
            av.priorizacao,
            av.gh_atualizada,
            av.data_avaliacao
        FROM aplicacoes a
        JOIN candidatos c ON a.candidato_id = c.id
        LEFT JOIN avaliacoes av ON a.id = av.aplicacao_id
        WHERE a.processo_id = %s
        ORDER BY 
            (av.nota_final IS NULL) DESC,
            av.nota_final DESC,
            c.nome ASC
    """, (processo_id,))

    aplicacoes = cursor.fetchall()

    cursor.close()
    return_connection(conn)

    if not aplicacoes:
        st.info("Nenhum candidato vinculado a este processo.")
    else:
        for app_id, cand_id, nome, email, linkedin, timestamp, greenhouse_id, nota_final, priorizacao, gh_atualizada, data_avaliacao in aplicacoes:

            if filtro_status == "Pendentes" and nota_final is not None:
                continue

            if filtro_status == "Avaliados" and nota_final is None:
                continue

            col1, col2 = st.columns([4, 1])

            with col1:
                st.write("**" + nome + "**")
                st.caption(email)
                if linkedin:
                    st.caption(f"🔗 [LinkedIn]({linkedin})")
                if greenhouse_id:
                    st.caption(f"🏢 [Greenhouse]({greenhouse_id})")
                if timestamp:
                    # Formatar timestamp se for string
                    if isinstance(timestamp, str):
                        st.caption(f"📅 Aplicação: {timestamp}")
                    else:
                        st.caption(f"📅 Aplicação: {timestamp.strftime('%d/%m/%Y %H:%M') if timestamp else 'Data não informada'}")

            with col2:
                if nota_final is None:
                    st.warning("⏳ Pendente")
                else:
                    st.success(f"⭐ Nota: {round(float(nota_final), 2)}")
                    if priorizacao and priorizacao != "Não priorizar":
                        st.caption(f"🎯 {priorizacao}")
                    if gh_atualizada:
                        st.caption("✅ GH Atualizado")

                if st.button("Ver Detalhes", key="cand_" + str(cand_id)):
                    st.session_state.candidato_id = cand_id
                    st.session_state.aplicacao_id = app_id
                    st.rerun()

            st.divider()


# =============================
# 3️⃣ DETALHE DO CANDIDATO
# =============================

elif st.session_state.candidato_id:

    candidato_id = st.session_state.candidato_id
    aplicacao_id = st.session_state.aplicacao_id
    processo_id = st.session_state.processo_id

    if st.button("← Voltar para Ranking"):
        st.session_state.candidato_id = None
        st.session_state.aplicacao_id = None
        st.rerun()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT nome, email, linkedin
        FROM candidatos 
        WHERE id = %s
    """, (candidato_id,))

    resultado = cursor.fetchone()

    if not resultado:
        st.error("Candidato não encontrado.")
        cursor.close()
        return_connection(conn)
        st.stop()

    nome_candidato, email_candidato, linkedin = resultado

    st.title(f"Candidato: {nome_candidato}")
    st.caption(email_candidato)
    if linkedin:
        st.markdown(f"🔗 [LinkedIn]({linkedin})")

    st.divider()

    # Buscar dados da aplicação
    cursor.execute("""
        SELECT greenhouse_id, pbix_file, optional_file, timestamp_aplicacao
        FROM aplicacoes
        WHERE id = %s
    """, (aplicacao_id,))

    app_dados = cursor.fetchone()

    if app_dados:
        greenhouse_id, pbix_file, optional_file, timestamp_aplicacao = app_dados
        with st.expander("📎 Links da Aplicação"):
            if greenhouse_id:
                st.markdown(f"🏢 [Greenhouse]({greenhouse_id})")
            if pbix_file:
                st.markdown(f"📊 [Arquivo PBIX]({pbix_file})")
            if optional_file:
                st.markdown(f"📁 [Arquivo Opcional]({optional_file})")
            if timestamp_aplicacao:
                if isinstance(timestamp_aplicacao, str):
                    st.write(f"📅 Data da Aplicação: {timestamp_aplicacao}")
                else:
                    st.write(f"📅 Data da Aplicação: {timestamp_aplicacao.strftime('%d/%m/%Y %H:%M')}")

    # Buscar avaliações
    cursor.execute("""
        SELECT id, nota_final, avaliador, comentario_final, priorizacao, gh_atualizada, data_avaliacao
        FROM avaliacoes
        WHERE aplicacao_id = %s
        ORDER BY data_avaliacao DESC
    """, (aplicacao_id,))

    avaliacoes = cursor.fetchall()

    if not avaliacoes:
        st.info("Nenhuma avaliação encontrada para esta aplicação.")
    else:
        for avaliacao_id, nota_final, avaliador, comentario, priorizacao, gh_atualizada, data_avaliacao in avaliacoes:

            # Formatar data da avaliação com segurança
            data_formatada = "Data não registrada"
            if data_avaliacao:
                if isinstance(data_avaliacao, str):
                    data_formatada = data_avaliacao
                else:
                    data_formatada = data_avaliacao.strftime('%d/%m/%Y %H:%M')

            st.subheader(f"Avaliação - {avaliador} ({data_formatada})")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Nota Final", round(float(nota_final), 2))
            with col2:
                st.metric("Priorização", priorizacao if priorizacao else "Não priorizar")
            with col3:
                st.metric("GH Atualizado", "✅ Sim" if gh_atualizada else "❌ Não")

            if comentario:
                st.markdown("**Comentário Geral:**")
                st.write(comentario)

            cursor.execute("""
                SELECT bloco, criterio, nota, justificativa
                FROM avaliacoes_criterios
                WHERE avaliacao_id = %s
                ORDER BY bloco, criterio
            """, (avaliacao_id,))

            notas = cursor.fetchall()

            if notas:
                st.markdown("### 📊 Avaliação por Critério")
                
                current_bloco = None
                for bloco, criterio, nota, just in notas:
                    if bloco != current_bloco:
                        current_bloco = bloco
                        st.markdown(f"#### {bloco}")
                    
                    with st.expander(f"{criterio} - Nota: {nota:.1f}"):
                        if nota >= 8:
                            st.success("✅ Excelente")
                        elif nota >= 6:
                            st.warning("⚠️ Bom")
                        else:
                            st.error("❌ Precisa melhorar")
                        if just:
                            st.write("**Justificativa:**")
                            st.write(just)

            st.divider()

    cursor.close()
    return_connection(conn)