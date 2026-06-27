"""Dashboard Streamlit — Manutenção Prescritiva SENAI SC.

5 abas: Painel | Eventos | Pendências | Análise | Chat
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import streamlit as st

import app.ui as ui
from core import db
from core.backend import responder_duvida

st.set_page_config(
    page_title="Manutenção Prescritiva — SENAI SC",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui.inject_css()

# ── Sidebar ───────────────────────────────────────────────────────────────────
ui.sidebar_brand()
try:
    _resumo_g = db.resumo_geral()
except Exception:
    _resumo_g = {"eventos": 0, "pendencias": 0, "consultas": 0, "backend": "?"}
ui.sidebar_status(_resumo_g)

# ── Abas ──────────────────────────────────────────────────────────────────────
tab_painel, tab_eventos, tab_pend, tab_analise, tab_chat = st.tabs(
    ["📊 Painel", "📋 Eventos", "⚠️ Pendências", "🔍 Análise", "💬 Chat"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# Aba 1 — Painel
# ═══════════════════════════════════════════════════════════════════════════════
with tab_painel:
    ui.section("KPIs — Semáforo do parque")
    try:
        resumo_sem = db.resumo_semaforo()
        ui.kpi_semaforo(resumo_sem)
    except Exception as exc:
        st.error(f"Erro ao carregar semáforo: {exc}")
        resumo_sem = {"total": 0, "vermelho": 0, "amarelo": 0, "verde": 0, "abertos": []}

    ui.section("Série temporal — últimos 30 dias")
    try:
        serie = db.serie_temporal_resolvidos(dias=30)
        if serie:
            df_serie = pd.DataFrame(serie)
            fig_serie = px.line(
                df_serie,
                x="dia",
                y=["resolvidos", "abertos"],
                color_discrete_map={
                    "resolvidos": ui.ACCENT,
                    "abertos": ui.DANGER,
                },
                labels={"value": "Eventos", "dia": "Data", "variable": "Status"},
                title="Eventos resolvidos (🟢) vs abertos por dia",
            )
            fig_serie.update_layout(
                paper_bgcolor=ui.CARD_BG,
                plot_bgcolor=ui.BG,
                font=dict(color=ui.TEXT),
                legend=dict(bgcolor=ui.CARD_BG, bordercolor=ui.BORDER),
            )
            st.plotly_chart(fig_serie, use_container_width=True)
        else:
            st.info("Sem dados de série temporal no período.")
    except Exception as exc:
        st.error(f"Erro na série temporal: {exc}")

    ui.section("Eventos críticos / atenção abertos")
    try:
        abertos = resumo_sem.get("abertos", [])
        if abertos:
            for ev in abertos:
                sem_color = ui.DANGER if ev["semaforo"] == "🔴" else ui.WARN
                st.markdown(
                    f'<div class="mp-card" style="border-left:3px solid {sem_color};">'
                    f'<b style="color:{ui.TEXT};">#{ev["id"]} — {ev["defeito"]}</b>'
                    f'&nbsp;{ui.badge_semaforo(ev["semaforo"])}&nbsp;'
                    f'<span style="color:{ui.TEXT_MUTED};font-size:12px;">'
                    f'{ev["frequency_per_week"]:.1f}/sem'
                    f' · {"COM" if ev["documented"] else "SEM"} manual'
                    f'</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.success("Nenhum evento crítico aberto.")
    except Exception as exc:
        st.error(f"Erro ao listar abertos: {exc}")

# ═══════════════════════════════════════════════════════════════════════════════
# Aba 2 — Eventos
# ═══════════════════════════════════════════════════════════════════════════════
with tab_eventos:
    ui.section("Filtros")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filtro_status = st.selectbox(
            "Status",
            ["(todos)", "pendente", "em_andamento", "resolvido", "descartado"],
            label_visibility="visible",
        )
    with col_f2:
        filtro_sem = st.selectbox(
            "Semáforo", ["(todos)", "🔴", "🟡", "🟢"],
            label_visibility="visible",
        )
    with col_f3:
        filtro_defeito = st.text_input(
            "Defeito (texto livre)", placeholder="ex: cocked_rotor"
        )

    try:
        status_f = None if filtro_status == "(todos)" else filtro_status
        sem_f = None if filtro_sem == "(todos)" else filtro_sem
        eventos = db.listar_eventos(limit=200, status_filter=status_f,
                                    semaforo_filter=sem_f)
        def_f = filtro_defeito.strip().lower()
        if def_f:
            eventos = [e for e in eventos if def_f in e["defeito"].lower()]
    except Exception as exc:
        st.error(f"Erro ao listar eventos: {exc}")
        eventos = []

    ui.section(f"Eventos ({len(eventos)}) — ordenados 🔴 → 🟡 → 🟢")

    if not eventos:
        st.info("Nenhum evento encontrado com os filtros aplicados.")
    else:
        if "editar_id" not in st.session_state:
            st.session_state["editar_id"] = None

        _sem_color_map = {
            "🔴": ui.DANGER,
            "🟡": ui.WARN,
            "🟢": ui.ACCENT,
        }

        for ev in eventos:
            sem_c = _sem_color_map.get(ev["semaforo"], ui.TEXT_MUTED)
            ts_str = (ev.get("ts") or "")[:10]
            freq = ev.get("frequency_per_week", 0.0)
            doc_tag = "COM doc" if ev.get("documented") else "SEM doc"

            cols = st.columns([0.4, 2.2, 1.4, 1.2, 1.6, 0.8])
            with cols[0]:
                st.markdown(
                    f'<div style="padding-top:8px;font-size:20px;">{ev["semaforo"]}</div>',
                    unsafe_allow_html=True,
                )
            with cols[1]:
                st.markdown(
                    f'<div style="padding-top:8px;color:{ui.TEXT};font-weight:600;">'
                    f'#{ev["id"]} {ev["defeito"]}</div>',
                    unsafe_allow_html=True,
                )
            with cols[2]:
                st.markdown(
                    f'<div style="padding-top:8px;">{ui.badge_status(ev["status"])}</div>',
                    unsafe_allow_html=True,
                )
            with cols[3]:
                st.markdown(
                    f'<div style="padding-top:8px;color:{ui.TEXT_MUTED};font-size:12px;">'
                    f'{ts_str}</div>',
                    unsafe_allow_html=True,
                )
            with cols[4]:
                st.markdown(
                    f'<div style="padding-top:8px;color:{ui.TEXT_MUTED};font-size:12px;">'
                    f'{freq:.1f}/sem · {doc_tag}</div>',
                    unsafe_allow_html=True,
                )
            with cols[5]:
                btn_label = "Fechar" if st.session_state.get("editar_id") == ev["id"] else "Editar"
                if st.button(btn_label, key=f"btn_edit_{ev['id']}"):
                    st.session_state["editar_id"] = (
                        None if st.session_state.get("editar_id") == ev["id"]
                        else ev["id"]
                    )
                    st.rerun()

            if st.session_state.get("editar_id") == ev["id"]:
                resultado = ui.form_edicao_status(
                    ev["id"], ev["status"], key_prefix="ev_"
                )
                if resultado:
                    novo_status, comentario, responsavel = resultado
                    try:
                        ok = db.atualizar_status(
                            ev["id"], novo_status,
                            comentario=comentario,
                            responsavel=responsavel,
                        )
                        if ok:
                            st.success(f"Status #{ev['id']} → {novo_status}")
                            st.session_state["editar_id"] = None
                            st.rerun()
                        else:
                            st.error("Evento não encontrado no banco.")
                    except Exception as exc:
                        st.error(f"Erro ao atualizar: {exc}")

            st.markdown(
                f'<div style="border-bottom:1px solid {ui.BORDER};'
                f'margin:4px 0 6px 0;"></div>',
                unsafe_allow_html=True,
            )

# ═══════════════════════════════════════════════════════════════════════════════
# Aba 3 — Pendências
# ═══════════════════════════════════════════════════════════════════════════════
with tab_pend:
    ui.section("Pendências abertas")
    try:
        pendencias = db.listar_pendencias(limit=50)
    except Exception as exc:
        st.error(f"Erro ao listar pendências: {exc}")
        pendencias = []

    if not pendencias:
        st.success("Nenhuma pendência aberta.")
    else:
        if len(pendencias) > 5:
            st.markdown(
                f'<div style="background:rgba(255,107,122,0.10);'
                f'border:1px solid {ui.DANGER};border-radius:10px;'
                f'padding:14px 18px;margin-bottom:16px;">'
                f'<b style="color:{ui.DANGER};">⚠ {len(pendencias)} pendências abertas</b>'
                f' — acima do limite recomendado (5). Atenção imediata necessária.'
                f'</div>',
                unsafe_allow_html=True,
            )

        for p in pendencias:
            freq = p.get("frequency_per_week", 0.0)
            doc_color = ui.ACCENT if p.get("documented") else ui.DANGER
            doc_flag = "COM manual" if p.get("documented") else "SEM manual"
            ts_str = (p.get("ts") or "")[:10]

            st.markdown(
                f'<div class="mp-card" style="border-left:3px solid {ui.DANGER};">'
                f'<div style="display:flex;align-items:center;gap:10px;">'
                f'<span style="font-size:20px;">🔴</span>'
                f'<b style="color:{ui.TEXT};flex:1;">#{p["id"]} — {p["defeito"]}</b>'
                f'<span class="mp-badge" style="background:rgba(255,107,122,0.12);'
                f'color:{ui.DANGER};border:1px solid rgba(255,107,122,0.35);">PENDENTE</span>'
                f'</div>'
                f'<div style="margin-top:8px;font-size:12px;color:{ui.TEXT_MUTED};">'
                f'Frequência: <b style="color:{ui.TEXT};">{freq:.1f}/sem</b>'
                f' &nbsp;·&nbsp; <span style="color:{doc_color};">{doc_flag}</span>'
                f' &nbsp;·&nbsp; {ts_str}'
                f'</div></div>',
                unsafe_allow_html=True,
            )

# ═══════════════════════════════════════════════════════════════════════════════
# Aba 4 — Análise
# ═══════════════════════════════════════════════════════════════════════════════
with tab_analise:
    ui.section("Distribuição por semáforo")
    try:
        resumo_an = db.resumo_semaforo()
        df_sem = pd.DataFrame([
            {"Semáforo": "🔴 Crítico", "Qtd": resumo_an["vermelho"]},
            {"Semáforo": "🟡 Atenção",  "Qtd": resumo_an["amarelo"]},
            {"Semáforo": "🟢 OK",       "Qtd": resumo_an["verde"]},
        ])
        _color_disc = {
            "🔴 Crítico": ui.DANGER,
            "🟡 Atenção":  ui.WARN,
            "🟢 OK":       ui.ACCENT,
        }

        col_bar, col_pie = st.columns(2)
        with col_bar:
            fig_bar = px.bar(
                df_sem, x="Semáforo", y="Qtd", color="Semáforo",
                color_discrete_map=_color_disc,
                title="Eventos por semáforo",
            )
            fig_bar.update_layout(
                paper_bgcolor=ui.CARD_BG, plot_bgcolor=ui.BG,
                font=dict(color=ui.TEXT), showlegend=False,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_pie:
            fig_pie = px.pie(
                df_sem, names="Semáforo", values="Qtd",
                color="Semáforo",
                color_discrete_map=_color_disc,
                title="Proporção por semáforo",
            )
            fig_pie.update_layout(
                paper_bgcolor=ui.CARD_BG,
                font=dict(color=ui.TEXT),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    except Exception as exc:
        st.error(f"Erro nos gráficos de semáforo: {exc}")

    ui.section("Cobertura documental por defeito")
    try:
        todos = db.listar_eventos(limit=500)
        if todos:
            df_cov = pd.DataFrame(todos)
            df_cov_grp = (
                df_cov.groupby(["defeito", "documented"])
                .size()
                .reset_index(name="Ocorrências")
            )
            df_cov_grp["Cobertura"] = df_cov_grp["documented"].map(
                {True: "COM manual", False: "SEM manual"}
            )
            df_cov_grp = df_cov_grp.rename(columns={"defeito": "Defeito"})
            st.dataframe(
                df_cov_grp[["Defeito", "Cobertura", "Ocorrências"]]
                .sort_values("Ocorrências", ascending=False),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Sem dados para análise de cobertura.")
    except Exception as exc:
        st.error(f"Erro na tabela de cobertura: {exc}")

# ═══════════════════════════════════════════════════════════════════════════════
# Aba 5 — Chat
# ═══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    ui.section("Chat — Dúvidas sobre manutenção")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    pergunta = st.text_input(
        "Sua pergunta",
        placeholder="Ex: Quais os pontos críticos? Como corrigir cocked_rotor?",
        label_visibility="visible",
    )
    if st.button("Enviar", type="primary", use_container_width=False):
        if not pergunta.strip():
            st.warning("Digite uma pergunta.")
        else:
            try:
                with st.spinner("Consultando banco + RAG..."):
                    resultado = responder_duvida(pergunta.strip(), origem="streamlit")
                st.session_state["chat_history"].append({
                    "pergunta": pergunta,
                    "resposta": resultado["resposta"],
                    "fonte": resultado.get("fonte", "banco"),
                })
            except Exception as exc:
                st.error(f"Erro no chat: {exc}")

    if st.session_state["chat_history"]:
        st.markdown(
            f'<div style="margin-top:12px;font-size:10px;letter-spacing:0.7px;'
            f'text-transform:uppercase;color:{ui.TEXT_DIM};">'
            f'Histórico da sessão</div>',
            unsafe_allow_html=True,
        )
        for item in reversed(st.session_state["chat_history"]):
            fonte_color = ui.INFO if item["fonte"] in ("RAG", "banco+RAG") else ui.ACCENT
            st.markdown(
                f'<div class="mp-card" style="margin-bottom:12px;">'
                f'<div style="font-size:11px;color:{ui.TEXT_DIM};margin-bottom:8px;">'
                f'<b style="color:{ui.TEXT};">Você:</b> {item["pergunta"]}</div>'
                f'<div style="color:{ui.TEXT};font-size:14px;line-height:1.65;'
                f'white-space:pre-wrap;">{item["resposta"]}</div>'
                f'<div style="margin-top:10px;font-size:11px;">'
                f'<span style="color:{ui.TEXT_DIM};">Fonte:</span> '
                f'<span style="color:{fonte_color};font-weight:700;">{item["fonte"]}</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            f'<div style="color:{ui.TEXT_MUTED};font-size:13px;margin-top:20px;">'
            f'Faça uma pergunta sobre defeitos, pendências ou status do parque.'
            f'</div>',
            unsafe_allow_html=True,
        )
