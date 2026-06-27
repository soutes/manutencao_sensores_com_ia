"""Dashboard Streamlit — Manutenção Prescritiva SENAI SC.

6 abas: Evento | Painel | Eventos | Pendências | Análise | Chat
"""
from __future__ import annotations
import json
import os
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import streamlit as st

import app.ui as ui
from core import db
from core.backend import responder_duvida, responder_evento
from core.faults import FAULT_LABELS_PT, label_pt

st.set_page_config(
    page_title="Manutenção Prescritiva — SENAI SC",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui.inject_css()


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _fmt_defeito(canonical: str) -> str:
    """'Motor Excêntrico (eccentric_rotor)'."""
    pt = label_pt(canonical)
    if pt != canonical:
        return f"{pt} ({canonical})"
    return canonical


def _apply_llm_config(provider: str, host: str, model: str, api_key: str) -> None:
    """Patcha módulos LLM em runtime — válido para a sessão Streamlit atual."""
    import core.config as _cfg
    import core.llm as _llm

    os.environ["LLM_PROVIDER"] = provider
    os.environ["OLLAMA_HOST"] = host
    os.environ["OLLAMA_MODEL"] = model
    if api_key:
        os.environ["OPENROUTER_API_KEY"] = api_key

    _cfg.LLM_PROVIDER = provider
    _cfg.OLLAMA_HOST = host
    _cfg.OLLAMA_MODEL = model
    if api_key:
        _cfg.OPENROUTER_API_KEY = api_key
    _llm.LLM_PROVIDER = provider
    _llm.OLLAMA_HOST = host
    _llm.OLLAMA_MODEL = model
    if api_key:
        _llm.OPENROUTER_API_KEY = api_key


def _current_llm_provider() -> str:
    try:
        import core.llm as _llm
        return _llm.LLM_PROVIDER
    except Exception:
        return os.getenv("LLM_PROVIDER", "ollama")


# ── Dialog: Configuração IA ───────────────────────────────────────────────────
_SVG_GEAR = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="3"/>'
    '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83'
    'l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0'
    'v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1'
    '-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2'
    ' 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06'
    'a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0'
    ' 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0'
    ' 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82'
    'V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>'
    '</svg>'
)
_SVG_GEAR_ENC = urllib.parse.quote(_SVG_GEAR, safe="")


@st.dialog("Configuração — IA", width="medium")
def _dlg_cfg_ia() -> None:
    _prov_atual = _current_llm_provider()
    selected_provider = st.selectbox(
        "Provedor",
        ["ollama", "openrouter"],
        index=0 if _prov_atual == "ollama" else 1,
        key="dlg_provider",
        help="ollama = local on-prem (LGPD) | openrouter = API externa (só DEMO)",
    )

    if selected_provider == "ollama":
        dlg_host = st.text_input(
            "Host Ollama",
            value=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            key="dlg_host",
        )
        dlg_model = st.text_input(
            "Modelo",
            value=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
            key="dlg_model",
        )
        dlg_api_key = ""
        st.markdown(
            '<div style="padding:10px 14px;border-radius:8px;border:1px solid #1A2030;'
            'background:#10141C;font-size:12px;color:#10F5A3;margin-top:12px;">'
            'Dados processados localmente — nenhum conteúdo de manual sai da empresa. '
            'Conforme LGPD.</div>',
            unsafe_allow_html=True,
        )
    else:
        dlg_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        dlg_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        dlg_api_key = st.text_input(
            "API Key OpenRouter",
            type="password",
            value=os.getenv("OPENROUTER_API_KEY", ""),
            key="dlg_api_key",
        )
        st.text_input("Modelo", value=dlg_model, key="dlg_or_model", disabled=True)
        st.markdown(
            '<div style="padding:10px 14px;border-radius:8px;'
            'border:1px solid rgba(255,107,122,0.3);'
            'background:rgba(255,107,122,0.06);'
            'font-size:12px;color:#FF6B7A;margin-top:12px;">'
            'API externa — use apenas com dados sintéticos (DEMO). '
            'Nunca envie dados reais de producao.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
    col_save, col_cancel = st.columns([3, 1])
    with col_save:
        if st.button("Aplicar", type="primary", use_container_width=True, key="dlg_save"):
            _apply_llm_config(selected_provider, dlg_host, dlg_model, dlg_api_key)
            st.success(f"LLM alterado para {selected_provider}")
    with col_cancel:
        if st.button("Fechar", use_container_width=True, key="dlg_cancel"):
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ═══════════════════════════════════════════════════════════════════════════════
ui.sidebar_brand()

# Botão "Configuração › IA" com ícone gear SVG inline (sem emoji)
st.sidebar.markdown(
    f"""<style>
.element-container:has(.cfg-ia-mk) + .element-container button {{
    background: transparent !important;
    border: none !important;
    color: #C8CDD6 !important;
    text-align: left !important;
    font-size: 13px !important;
    padding: 8px 14px !important;
    border-radius: 8px !important;
    width: 100% !important;
    font-weight: 500 !important;
    box-shadow: none !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    letter-spacing: 0.1px !important;
}}
.element-container:has(.cfg-ia-mk) + .element-container button::before {{
    content: ""; display: inline-block;
    width: 15px; height: 15px;
    margin-right: 10px; vertical-align: -3px; flex-shrink: 0;
    background-color: #8B92A0;
    -webkit-mask: url("data:image/svg+xml;utf8,{_SVG_GEAR_ENC}") no-repeat center / contain;
    mask: url("data:image/svg+xml;utf8,{_SVG_GEAR_ENC}") no-repeat center / contain;
}}
.element-container:has(.cfg-ia-mk) + .element-container button:hover {{
    background: #131B28 !important;
    color: #E8ECF2 !important;
}}
.element-container:has(.cfg-ia-mk) + .element-container button:hover::before {{
    background-color: #E8ECF2 !important;
}}
</style>
<span class="cfg-ia-mk" style="display:none;"></span>""",
    unsafe_allow_html=True,
)
if st.sidebar.button("Configuração  ›  IA", key="btn_cfg_ia", use_container_width=True):
    _dlg_cfg_ia()

try:
    _resumo_g = db.resumo_geral()
except Exception:
    _resumo_g = {"eventos": 0, "pendencias": 0, "consultas": 0, "backend": "?"}
ui.sidebar_status(_resumo_g)

with st.sidebar.expander("📖 Legenda de defeitos", expanded=False):
    for canon, pt_name in FAULT_LABELS_PT.items():
        if canon in ("normal", "baseline", "teste", "acelerando",
                     "motor_desligado", "desconhecido"):
            continue
        st.markdown(
            f'<div style="font-size:11px;color:{ui.TEXT_MUTED};line-height:1.8;">'
            f'<b style="color:{ui.TEXT};">{pt_name}</b>'
            f'<span style="font-family:monospace;color:{ui.TEXT_DIM};">'
            f' · {canon}</span></div>',
            unsafe_allow_html=True,
        )

# ═══════════════════════════════════════════════════════════════════════════════
# Abas
# ═══════════════════════════════════════════════════════════════════════════════
(tab_evento, tab_painel, tab_eventos,
 tab_pend, tab_analise, tab_chat) = st.tabs(
    ["📡 Evento", "📊 Painel", "📋 Eventos",
     "⚠️ Pendências", "🔍 Análise", "💬 Chat"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# Aba 0 — Evento
# ═══════════════════════════════════════════════════════════════════════════════
with tab_evento:
    ui.section("Analisar evento de sensor")

    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        st.markdown(
            f'<div style="font-size:12px;color:{ui.TEXT_MUTED};margin-bottom:10px;">'
            f'Cole o JSON do sensor ou faça upload do arquivo. '
            f'O sistema classifica via KNN, calcula o semáforo e consulta o RAG.'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Upload de arquivo JSON
        _uploaded = st.file_uploader(
            "Upload JSON do sensor",
            type=["json", "txt"],
            key="ev_upload",
            help="Arquivo .json ou .txt com o payload do sensor",
        )
        if _uploaded is not None:
            try:
                _file_content = _uploaded.read().decode("utf-8")
                json.loads(_file_content)  # valida antes de aceitar
                st.session_state["evento_json_override"] = _file_content
                st.rerun()
            except Exception as exc:
                st.error(f"Arquivo inválido: {exc}")

        _exemplo = ""

        _textarea_val = st.session_state.pop("evento_json_override", _exemplo)
        json_input = st.text_area(
            "JSON do evento",
            value=_textarea_val,
            height=220,
            key="evento_json",
            help="Qualquer subconjunto das 24 features de vibração.",
        )

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            analisar = st.button(
                "Analisar", type="primary",
                use_container_width=True, key="btn_analisar",
            )
        with col_btn2:
            if st.button("Limpar", use_container_width=True, key="btn_clear"):
                for k in ("evento_resultado", "evento_erro"):
                    st.session_state.pop(k, None)
                st.rerun()

    with col_right:
        st.markdown(
            f'<div style="font-size:12px;color:{ui.TEXT_MUTED};margin-bottom:8px;">'
            f'Ou monte o payload por campos:</div>',
            unsafe_allow_html=True,
        )
        _rpm = st.number_input("RPM", min_value=0, max_value=6000, value=0,
                               step=50, key="ev_rpm")
        _temp = st.number_input("Temperatura (°C)", min_value=0.0, max_value=200.0,
                                value=0.0, step=0.5, key="ev_temp")
        _zrms = st.number_input("Z RMS velocity (mm/s)", min_value=0.0, max_value=50.0,
                                value=0.0, step=0.1, key="ev_zrms")
        _xrms = st.number_input("X RMS velocity (mm/s)", min_value=0.0, max_value=50.0,
                                value=0.0, step=0.1, key="ev_xrms")
        _zkurt = st.number_input("Z Kurtosis", min_value=0.0, max_value=30.0,
                                 value=0.0, step=0.1, key="ev_zkurt")
        if st.button("Usar estes campos →", use_container_width=True, key="btn_campos"):
            st.session_state["evento_json_override"] = json.dumps({
                "rpm": _rpm,
                "temperature_c": _temp,
                "z_rms_velocity_mm_s": _zrms,
                "x_rms_velocity_mm_s": _xrms,
                "z_kurtosis": _zkurt,
            }, indent=2)
            st.rerun()

    if analisar:
        st.session_state.pop("evento_resultado", None)
        st.session_state.pop("evento_erro", None)
        try:
            payload = json.loads(json_input)
        except json.JSONDecodeError as exc:
            st.error(f"JSON inválido: {exc}")
            payload = None
        if payload is not None:
            with st.spinner("Executando análise — classificando defeito + consultando RAG..."):
                try:
                    resultado = responder_evento(payload, origem="streamlit")
                    st.session_state["evento_resultado"] = resultado
                    st.toast("Análise concluída", icon="✅")
                except Exception as exc:
                    st.session_state["evento_erro"] = str(exc)

    if "evento_resultado" in st.session_state:
        res = st.session_state["evento_resultado"]
        sem = res.get("semaforo", "🟢")
        defeito = res.get("canonical_fault", res.get("defeito", "—"))
        _sem_color_map = {"🔴": ui.DANGER, "🟡": ui.WARN, "🟢": ui.ACCENT}
        sem_c = _sem_color_map.get(sem, ui.TEXT_MUTED)
        _is_prob = res.get("is_problem", False)
        _doc = res.get("documented", False)
        _freq = res.get("frequency_per_week", 0.0)
        _id = res.get("id_salvo")
        _fmt_def = _fmt_defeito(defeito)

        st.markdown("---")
        col_s, col_d = st.columns([0.28, 1.72])
        with col_s:
            st.markdown(
                f'<div style="font-size:64px;text-align:center;line-height:1.1;">{sem}</div>',
                unsafe_allow_html=True,
            )
        with col_d:
            st.markdown(
                f'<div style="font-size:22px;font-weight:700;color:{sem_c};'
                f'padding-top:8px;">{_fmt_def}</div>',
                unsafe_allow_html=True,
            )
            tags = []
            tags.append("DEFEITO" if _is_prob else "ESTADO NORMAL")
            tags.append("COM manual" if _doc else "SEM manual")
            tags.append(f"{_freq:.1f}/sem")
            if _id:
                tags.append(f"ID #{_id} salvo")
            st.markdown(
                f'<div style="font-size:12px;color:{ui.TEXT_MUTED};margin-top:4px;">'
                + " · ".join(tags) + "</div>",
                unsafe_allow_html=True,
            )

        instrucoes = res.get("instructions", "")
        if instrucoes:
            st.markdown(
                f'<div class="mp-card" style="margin-top:14px;">'
                f'<div style="font-size:10px;letter-spacing:0.8px;'
                f'text-transform:uppercase;color:{ui.TEXT_DIM};margin-bottom:8px;">'
                f'Prescrição</div>'
                f'<div style="color:{ui.TEXT};font-size:14px;line-height:1.7;'
                f'white-space:pre-wrap;">{instrucoes}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if not _doc and _is_prob:
            st.warning(
                f"**{_fmt_def}** sem procedimento documentado. "
                f"Pendência registrada — solicitar elaboração de manual técnico."
            )

        fontes = res.get("sources", [])
        if fontes:
            st.markdown(
                f'<div style="font-size:11px;color:{ui.TEXT_DIM};margin-top:6px;">'
                f'📄 Fonte RAG: {", ".join(fontes)}</div>',
                unsafe_allow_html=True,
            )

    if "evento_erro" in st.session_state:
        st.error(st.session_state["evento_erro"])

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
                df_serie, x="dia", y=["resolvidos", "abertos"],
                color_discrete_map={"resolvidos": ui.ACCENT, "abertos": ui.DANGER},
                labels={"value": "Eventos", "dia": "Data", "variable": "Status"},
                title="Eventos resolvidos (🟢) vs abertos por dia",
            )
            fig_serie.update_layout(
                paper_bgcolor=ui.CARD_BG, plot_bgcolor=ui.BG,
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
                _def_fmt = _fmt_defeito(ev["defeito"])
                st.markdown(
                    f'<div class="mp-card" style="border-left:3px solid {sem_color};">'
                    f'<b style="color:{ui.TEXT};">#{ev["id"]} — {_def_fmt}</b>'
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
        )
    with col_f2:
        filtro_sem = st.selectbox("Semáforo", ["(todos)", "🔴", "🟡", "🟢"])
    with col_f3:
        filtro_defeito = st.text_input(
            "Defeito (técnico ou português)",
            placeholder="ex: eccentric_rotor ou Rotor",
        )

    try:
        status_f = None if filtro_status == "(todos)" else filtro_status
        sem_f = None if filtro_sem == "(todos)" else filtro_sem
        eventos = db.listar_eventos(limit=200, status_filter=status_f,
                                    semaforo_filter=sem_f)
        def_f = filtro_defeito.strip().lower()
        if def_f:
            eventos = [
                e for e in eventos
                if def_f in e["defeito"].lower()
                or def_f in label_pt(e["defeito"]).lower()
            ]
    except Exception as exc:
        st.error(f"Erro ao listar eventos: {exc}")
        eventos = []

    ui.section(f"Eventos ({len(eventos)}) — ordenados 🔴 → 🟡 → 🟢")

    if not eventos:
        st.info("Nenhum evento encontrado com os filtros aplicados.")
    else:
        if "editar_id" not in st.session_state:
            st.session_state["editar_id"] = None

        _sem_color_map = {"🔴": ui.DANGER, "🟡": ui.WARN, "🟢": ui.ACCENT}

        for ev in eventos:
            sem_c = _sem_color_map.get(ev["semaforo"], ui.TEXT_MUTED)
            ts_str = (ev.get("ts") or "")[:10]
            freq = ev.get("frequency_per_week", 0.0)
            doc_tag = "COM doc" if ev.get("documented") else "SEM doc"
            _def_fmt = _fmt_defeito(ev["defeito"])

            cols = st.columns([0.4, 2.6, 1.4, 1.2, 1.6, 0.8])
            with cols[0]:
                st.markdown(
                    f'<div style="padding-top:8px;font-size:20px;">{ev["semaforo"]}</div>',
                    unsafe_allow_html=True,
                )
            with cols[1]:
                st.markdown(
                    f'<div style="padding-top:8px;color:{ui.TEXT};font-weight:600;">'
                    f'#{ev["id"]} {_def_fmt}</div>',
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
                resultado = ui.form_edicao_status(ev["id"], ev["status"], key_prefix="ev_")
                if resultado:
                    novo_status, comentario, responsavel = resultado
                    try:
                        ok = db.atualizar_status(
                            ev["id"], novo_status,
                            comentario=comentario, responsavel=responsavel,
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
            _def_fmt = _fmt_defeito(p["defeito"])

            st.markdown(
                f'<div class="mp-card" style="border-left:3px solid {ui.DANGER};">'
                f'<div style="display:flex;align-items:center;gap:10px;">'
                f'<span style="font-size:20px;">🔴</span>'
                f'<b style="color:{ui.TEXT};flex:1;">#{p["id"]} — {_def_fmt}</b>'
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
                color_discrete_map=_color_disc, title="Eventos por semáforo",
            )
            fig_bar.update_layout(
                paper_bgcolor=ui.CARD_BG, plot_bgcolor=ui.BG,
                font=dict(color=ui.TEXT), showlegend=False,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_pie:
            fig_pie = px.pie(
                df_sem, names="Semáforo", values="Qtd",
                color="Semáforo", color_discrete_map=_color_disc,
                title="Proporção por semáforo",
            )
            fig_pie.update_layout(
                paper_bgcolor=ui.CARD_BG, font=dict(color=ui.TEXT)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    except Exception as exc:
        st.error(f"Erro nos gráficos de semáforo: {exc}")

    ui.section("Cobertura documental por defeito")
    try:
        todos = db.listar_eventos(limit=500)
        if todos:
            df_cov = pd.DataFrame(todos)
            df_cov["Defeito PT"] = df_cov["defeito"].apply(label_pt)
            df_cov_grp = (
                df_cov.groupby(["Defeito PT", "defeito", "documented"])
                .size()
                .reset_index(name="Ocorrências")
            )
            df_cov_grp["Cobertura"] = df_cov_grp["documented"].map(
                {True: "COM manual", False: "SEM manual"}
            )
            df_cov_grp = df_cov_grp.rename(columns={"defeito": "Técnico"})
            st.dataframe(
                df_cov_grp[["Defeito PT", "Técnico", "Cobertura", "Ocorrências"]]
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

    _chat_col, _ = st.columns([2, 1])
    with _chat_col:
        pergunta = st.text_input(
            "Sua pergunta",
            placeholder="Ex: Quais motores precisam de atenção? Como corrigir desbalanceamento?",
            label_visibility="collapsed",
            key="chat_input",
        )
    if st.button("Enviar", type="primary", key="btn_chat"):
        if not pergunta.strip():
            st.warning("Digite uma pergunta.")
        else:
            with st.spinner("Consultando banco de eventos + documentação técnica..."):
                try:
                    resultado = responder_duvida(pergunta.strip(), origem="streamlit")
                    st.session_state["chat_history"].append({
                        "pergunta": pergunta,
                        "resposta": resultado["resposta"],
                        "fonte": resultado.get("fonte", "banco"),
                        "sources": resultado.get("sources", []),
                    })
                except Exception as exc:
                    st.error(f"Erro no chat: {exc}")

    if st.session_state["chat_history"]:
        st.markdown(
            f'<div style="margin-top:12px;font-size:10px;letter-spacing:0.7px;'
            f'text-transform:uppercase;color:{ui.TEXT_DIM};">Histórico da sessão</div>',
            unsafe_allow_html=True,
        )
        for item in reversed(st.session_state["chat_history"]):
            _fontes_str = item.get("fonte", "banco")
            _docs = item.get("sources", [])
            _fonte_color = ui.ACCENT if "LLM" in _fontes_str else ui.INFO
            _docs_html = (
                f' · <span style="color:{ui.TEXT_DIM};">📄 {", ".join(_docs)}</span>'
                if _docs else ""
            )
            st.markdown(
                f'<div class="mp-card" style="margin-bottom:12px;">'
                f'<div style="font-size:11px;color:{ui.TEXT_DIM};margin-bottom:8px;">'
                f'<b style="color:{ui.TEXT};">Você:</b> {item["pergunta"]}</div>'
                f'<div style="color:{ui.TEXT};font-size:14px;line-height:1.7;'
                f'white-space:pre-wrap;">{item["resposta"]}</div>'
                f'<div style="margin-top:10px;font-size:11px;">'
                f'<span style="color:{ui.TEXT_DIM};">Fonte:</span> '
                f'<span style="color:{_fonte_color};font-weight:700;">{_fontes_str}</span>'
                f'{_docs_html}'
                f'</div></div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            f'<div style="color:{ui.TEXT_MUTED};font-size:13px;margin-top:20px;">'
            f'Faça uma pergunta sobre defeitos, pendências ou status do parque.</div>',
            unsafe_allow_html=True,
        )
