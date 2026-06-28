"""Dashboard Streamlit — Manutenção Prescritiva SENAI SC.

7 abas: Overview | Nova Análise | Pendências | Resolvidos | Análise | Chat | Relatório IA
"""
from __future__ import annotations
import json
import os
import sys
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import streamlit as st

import app.ui as ui
from core import db
from core.backend import gerar_relatorio_ia, responder_duvida, responder_evento
from core.faults import FAULT_DOC_MAP, FAULT_LABELS_PT, label_pt

st.set_page_config(
    page_title="Manutenção Prescritiva — SENAI SC",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Dataset de treino (cached) ────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _dataset_stats() -> dict:
    try:
        _p = Path(__file__).resolve().parents[2] / "data" / "banner_clean.parquet"
        df = pd.read_parquet(_p)
        return {"registros": len(df), "features": len(df.columns)}
    except Exception:
        return {"registros": 166_000, "features": 18}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_defeito(canonical: str) -> str:
    pt = label_pt(canonical)
    if pt != canonical:
        return f"{pt} ({canonical})"
    return canonical


def _apply_llm_config(provider: str, host: str, model: str, api_key: str) -> None:
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


def _period_slicer(key: str) -> tuple[str, str]:
    """Seletor de período estilo Power BI. Retorna (inicio, fim) YYYY-MM-DD."""
    _opts = ["Últimos 7 dias", "Últimos 30 dias", "Últimos 60 dias",
             "Últimos 90 dias", "Personalizado"]
    _map  = {"Últimos 7 dias": 7, "Últimos 30 dias": 30,
             "Últimos 60 dias": 60, "Últimos 90 dias": 90}
    _col_sel, _col_d1, _col_d2 = st.columns([2, 1.2, 1.2])
    with _col_sel:
        sel = st.selectbox("Período", _opts, key=f"{key}_sel", label_visibility="collapsed")
    hoje = date.today()
    if sel == "Personalizado":
        with _col_d1:
            dt_ini = st.date_input("De", value=hoje - timedelta(days=30),
                                   key=f"{key}_d1", label_visibility="collapsed")
        with _col_d2:
            dt_fim = st.date_input("Até", value=hoje,
                                   key=f"{key}_d2", label_visibility="collapsed")
    else:
        dias = _map[sel]
        dt_ini = hoje - timedelta(days=dias)
        dt_fim = hoje
    return str(dt_ini), str(dt_fim)


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


def _dlg_cfg_ia() -> None:
    st.markdown(
        f'<div style="padding:18px 0 12px 0;">'
        f'<div style="font-size:20px;font-weight:700;color:{ui.TEXT};">'
        f'Configuração IA</div>'
        f'<div style="font-size:12px;color:{ui.TEXT_MUTED};margin-top:4px;">'
        f'Configurar o modelo de linguagem (LLM) para prescrições</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    _prov_atual = _current_llm_provider()
    selected_provider = st.selectbox(
        "Provedor", ["ollama", "openrouter"],
        index=0 if _prov_atual == "ollama" else 1,
        key="cfg_provider",
        help="ollama = local on-prem (LGPD) | openrouter = API externa (só DEMO)",
    )
    if selected_provider == "ollama":
        dlg_host = st.text_input("Host Ollama",
                                 value=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                                 key="cfg_host")
        dlg_model = st.text_input("Modelo",
                                  value=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
                                  key="cfg_model")
        dlg_api_key = ""
        st.markdown(
            '<div style="padding:10px 14px;border-radius:8px;border:1px solid #1A2030;'
            'background:#10141C;font-size:12px;color:#10F5A3;margin-top:12px;">'
            'Dados processados localmente — nenhum conteúdo de manual sai da empresa. '
            'Conforme LGPD.</div>',
            unsafe_allow_html=True,
        )
    else:
        dlg_host    = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        dlg_model   = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        dlg_api_key = st.text_input("API Key OpenRouter", type="password",
                                    value=os.getenv("OPENROUTER_API_KEY", ""),
                                    key="cfg_api_key")
        st.text_input("Modelo", value=dlg_model, key="cfg_or_model", disabled=True)
        st.markdown(
            '<div style="padding:10px 14px;border-radius:8px;'
            'border:1px solid rgba(255,107,122,0.3);'
            'background:rgba(255,107,122,0.06);'
            'font-size:12px;color:#FF6B7A;margin-top:12px;">'
            'API externa — use apenas com dados sintéticos (DEMO).</div>',
            unsafe_allow_html=True,
        )
    if st.button("Aplicar configuração", type="primary", key="cfg_save"):
        _apply_llm_config(selected_provider, dlg_host, dlg_model, dlg_api_key)
        st.success(f"LLM alterado para {selected_provider}")




# ═══════════════════════════════════════════════════════════════════════════════
# Header: Logo + Título + ONLINE + data
# ═══════════════════════════════════════════════════════════════════════════════
ui.inject_css()
ui.render_header()

# ═══════════════════════════════════════════════════════════════════════════════
# Abas
# ═══════════════════════════════════════════════════════════════════════════════
(tab_overview, tab_nova, tab_pend, tab_resolvidos,
 tab_analise, tab_chat, tab_relatorio, tab_config) = st.tabs([
    "Overview", "Nova Análise", "Pendências", "Resolvidos",
    "Análise", "Chat", "Relatório IA", "Configuração IA",
])

# ═══════════════════════════════════════════════════════════════════════════════
# Aba 0 — Overview
# ═══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    try:
        _ov_sem   = db.resumo_semaforo()
        _ov_geral = db.resumo_geral()
        _ov_top   = db.top_defeitos(limit=5)
        _ov_rec   = db.listar_recentes(limit=4)
    except Exception:
        _ov_sem   = {"total": 0, "vermelho": 0, "amarelo": 0, "verde": 0, "abertos": []}
        _ov_geral = {"eventos": 0, "pendencias": 0, "consultas": 0, "backend": "?"}
        _ov_top   = []
        _ov_rec   = []

    _ov_total  = _ov_sem.get("total", 0)
    _ov_verm   = _ov_sem.get("vermelho", 0)
    _ov_amar   = _ov_sem.get("amarelo", 0)
    _ov_verd   = _ov_sem.get("verde", 0)
    _ov_pend   = _ov_geral.get("pendencias", 0)
    _ov_consul = _ov_geral.get("consultas", 0)
    _ov_db     = _ov_geral.get("backend", "SQLite")
    _ov_health = round((_ov_verd / _ov_total * 100) if _ov_total > 0 else 100)
    _ov_hc     = ui.ACCENT if _ov_health >= 70 else (ui.WARN if _ov_health >= 40 else ui.DANGER)
    _ov_pct_v  = round(_ov_verm / _ov_total * 100) if _ov_total else 0
    _ov_pct_a  = round(_ov_amar / _ov_total * 100) if _ov_total else 0
    _ov_pend_c = ui.DANGER if _ov_pend > 0 else ui.ACCENT
    _ov_now    = pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
    _ov_llm    = _current_llm_provider()
    _ov_model  = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
    _ov_lgpd     = _ov_llm == "ollama"
    _ov_lgpd_c   = ui.ACCENT if _ov_lgpd else ui.DANGER
    _ov_lgpd_bg  = "rgba(16,245,163,0.06)" if _ov_lgpd else "rgba(255,107,122,0.06)"
    _ov_lgpd_brd = "rgba(16,245,163,0.2)"  if _ov_lgpd else "rgba(255,107,122,0.2)"
    _ov_lgpd_txt = "✓ Processamento local — LGPD" if _ov_lgpd else "⚠ API externa — DEMO"
    _ov_cov_doc  = sum(1 for v in FAULT_DOC_MAP.values() if v)
    _ov_cov_tot  = len(FAULT_DOC_MAP)
    _ov_cov_pct  = round(_ov_cov_doc / _ov_cov_tot * 100)
    _ds          = _dataset_stats()

    # ── KPIs (só no Overview) ────────────────────────────────────────────────
    ui.render_kpis(_ov_geral, _ov_sem)

    # ── Atividade + Top Defeitos ──────────────────────────────────────────────
    _col_act, _col_top_def = st.columns([3, 2])

    with _col_act:
        st.markdown(
            f'<div style="font-size:10px;letter-spacing:0.8px;text-transform:uppercase;'
            f'color:{ui.TEXT_DIM};font-weight:600;margin-bottom:10px;">'
            f'Atividade — Últimos 7 dias</div>',
            unsafe_allow_html=True,
        )
        try:
            _serie7 = db.serie_temporal_resolvidos(dias=7)
            if _serie7:
                _df7 = pd.DataFrame(_serie7)
                _fig7 = px.bar(
                    _df7, x="dia", y=["abertos", "resolvidos"],
                    barmode="group",
                    color_discrete_map={"abertos": ui.DANGER, "resolvidos": ui.ACCENT},
                    labels={"value": "", "dia": "", "variable": ""},
                )
                _fig7.update_layout(
                    height=260,
                    paper_bgcolor=ui.CARD_BG,
                    plot_bgcolor=ui.CARD_BG,
                    font=dict(color=ui.TEXT_MUTED, size=11),
                    margin=dict(l=40, r=16, t=20, b=50),
                    legend=dict(
                        bgcolor="rgba(0,0,0,0)", orientation="h",
                        x=0.5, y=-0.18, xanchor="center", yanchor="top",
                        font=dict(size=11),
                    ),
                    xaxis=dict(showgrid=False, tickfont=dict(size=10, color=ui.TEXT_DIM)),
                    yaxis=dict(gridcolor=ui.BORDER, showgrid=True,
                               tickfont=dict(size=10, color=ui.TEXT_DIM), zeroline=False),
                    bargap=0.3, bargroupgap=0.08,
                )
                _fig7.update_traces(marker_line_width=0)
                st.plotly_chart(_fig7, width="stretch")
            else:
                st.markdown(
                    f'<div style="height:80px;display:flex;align-items:center;'
                    f'color:{ui.TEXT_DIM};font-size:13px;">'
                    f'Nenhum evento nos últimos 7 dias</div>',
                    unsafe_allow_html=True,
                )
        except Exception as _e7:
            st.error(str(_e7))

    with _col_top_def:
        st.markdown(
            f'<div style="font-size:10px;letter-spacing:0.8px;text-transform:uppercase;'
            f'color:{ui.TEXT_DIM};font-weight:600;margin-bottom:10px;">'
            f'Top Defeitos</div>',
            unsafe_allow_html=True,
        )
        if _ov_top:
            _max_cnt = _ov_top[0]["count"]
            _bars_h = ""
            for _td in _ov_top:
                _bpct = round(_td["count"] / _max_cnt * 100) if _max_cnt else 0
                _bc   = ui.ACCENT if _td["documented"] else ui.DANGER
                _dlbl = label_pt(_td["defeito"])
                _bars_h += (
                    f'<div style="margin-bottom:14px;">'
                    f'<div style="display:flex;justify-content:space-between;'
                    f'align-items:center;margin-bottom:5px;">'
                    f'<span style="font-size:12px;color:{ui.TEXT};font-weight:500;'
                    f'max-width:170px;white-space:nowrap;overflow:hidden;'
                    f'text-overflow:ellipsis;" title="{_td["defeito"]}">{_dlbl}</span>'
                    f'<span style="font-size:12px;color:{ui.TEXT_MUTED};'
                    f'font-variant-numeric:tabular-nums;flex-shrink:0;'
                    f'margin-left:8px;">{_td["count"]}</span></div>'
                    f'<div style="height:4px;background:{ui.BORDER};'
                    f'border-radius:2px;overflow:hidden;">'
                    f'<div style="height:100%;width:{_bpct}%;background:{_bc};'
                    f'border-radius:2px;box-shadow:0 0 6px {_bc}66;"></div>'
                    f'</div></div>'
                )
            st.markdown(
                f'<div style="background:{ui.CARD_BG};border:1px solid {ui.BORDER};'
                f'border-radius:14px;padding:18px 20px;">' + _bars_h + '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("Nenhum defeito registrado ainda.")

    # ── Bottom cards: Saúde · Ocorrências · Infraestrutura ───────────────────
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    _col_saude, _col_evs, _col_infra = st.columns(3)

    with _col_saude:
        st.markdown(
            f'<div style="background:{ui.CARD_BG};border:1px solid {ui.BORDER};'
            f'border-radius:14px;padding:20px 22px;">'
            f'<div style="font-size:10px;letter-spacing:0.8px;text-transform:uppercase;'
            f'color:{ui.TEXT_DIM};font-weight:600;margin-bottom:16px;">Saúde do Parque</div>'
            f'<div style="text-align:center;margin-bottom:14px;">'
            f'<div style="font-size:52px;font-weight:800;color:{_ov_hc};'
            f'line-height:1;font-variant-numeric:tabular-nums;">{_ov_health}%</div>'
            f'<div style="font-size:11px;color:{ui.TEXT_DIM};margin-top:6px;">'
            f'motores em estado OK</div></div>'
            f'<div style="height:6px;background:{ui.BORDER};border-radius:3px;'
            f'margin-bottom:16px;">'
            f'<div style="height:100%;width:{_ov_health}%;background:{_ov_hc};'
            f'border-radius:3px;box-shadow:0 0 10px {_ov_hc}66;"></div></div>'
            f'<div style="display:flex;flex-direction:column;gap:8px;">'
            f'<div style="display:flex;justify-content:space-between;">'
            f'<span style="font-size:12px;color:{ui.TEXT_MUTED};">Crítico</span>'
            f'<span style="font-size:13px;font-weight:700;color:{ui.DANGER};'
            f'font-variant-numeric:tabular-nums;">{_ov_verm}</span></div>'
            f'<div style="display:flex;justify-content:space-between;">'
            f'<span style="font-size:12px;color:{ui.TEXT_MUTED};">Atenção</span>'
            f'<span style="font-size:13px;font-weight:700;color:{ui.WARN};'
            f'font-variant-numeric:tabular-nums;">{_ov_amar}</span></div>'
            f'<div style="display:flex;justify-content:space-between;">'
            f'<span style="font-size:12px;color:{ui.TEXT_MUTED};">OK</span>'
            f'<span style="font-size:13px;font-weight:700;color:{ui.ACCENT};'
            f'font-variant-numeric:tabular-nums;">{_ov_verd}</span></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    with _col_evs:
        _ev_rows_h = ""
        for _er in _ov_rec:
            _er_sc  = {"🔴": ui.DANGER, "🟡": ui.WARN, "🟢": ui.ACCENT}.get(
                _er["semaforo"], ui.TEXT_MUTED)
            _er_ts  = (_er.get("ts") or "")[:10]
            _er_def = label_pt(_er["defeito"])
            _er_st  = _er.get("status", "").upper()
            _ev_rows_h += (
                f'<div style="display:flex;align-items:center;gap:10px;'
                f'padding:9px 0;border-bottom:1px solid {ui.BORDER};">'
                f'<span style="font-size:16px;flex-shrink:0;">{_er["semaforo"]}</span>'
                f'<div style="flex:1;min-width:0;">'
                f'<div style="font-size:12px;color:{ui.TEXT};font-weight:600;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
                f'#{_er["id"]} {_er_def}</div>'
                f'<div style="font-size:10px;color:{ui.TEXT_DIM};">{_er_ts}</div>'
                f'</div>'
                f'<span style="font-size:9px;font-weight:700;color:{_er_sc};'
                f'flex-shrink:0;letter-spacing:0.3px;">{_er_st}</span>'
                f'</div>'
            )
        st.markdown(
            f'<div style="background:{ui.CARD_BG};border:1px solid {ui.BORDER};'
            f'border-radius:14px;padding:18px 20px;">'
            f'<div style="font-size:10px;letter-spacing:0.8px;text-transform:uppercase;'
            f'color:{ui.TEXT_DIM};font-weight:600;margin-bottom:4px;">'
            f'Últimas Ocorrências</div>'
            + (_ev_rows_h or f'<div style="color:{ui.TEXT_DIM};font-size:12px;'
               f'padding-top:10px;">Sem eventos registrados</div>')
            + '</div>',
            unsafe_allow_html=True,
        )

    with _col_infra:
        st.markdown(
            f'<div style="background:{ui.CARD_BG};border:1px solid {ui.BORDER};'
            f'border-radius:14px;padding:20px 22px;">'
            f'<div style="font-size:10px;letter-spacing:0.8px;text-transform:uppercase;'
            f'color:{ui.TEXT_DIM};font-weight:600;margin-bottom:14px;">Infraestrutura</div>'
            f'<div style="margin-bottom:12px;">'
            f'<div style="font-size:10px;color:{ui.TEXT_DIM};margin-bottom:3px;">Modelo IA</div>'
            f'<div style="font-size:13px;color:{ui.TEXT};font-weight:600;">{_ov_llm}</div>'
            f'<div style="font-size:11px;color:{ui.TEXT_MUTED};">{_ov_model}</div>'
            f'</div>'
            f'<div style="margin-bottom:12px;">'
            f'<div style="font-size:10px;color:{ui.TEXT_DIM};margin-bottom:3px;">'
            f'Banco de Dados</div>'
            f'<div style="font-size:13px;color:{ui.TEXT};font-weight:600;">{_ov_db}</div>'
            f'</div>'
            f'<div style="margin-bottom:14px;">'
            f'<div style="font-size:10px;color:{ui.TEXT_DIM};margin-bottom:3px;">'
            f'Features · Classes</div>'
            f'<div style="font-size:13px;color:{ui.TEXT};font-weight:600;">'
            f'{_ds["features"]} features · 17 classes</div>'
            f'<div style="font-size:11px;color:{ui.TEXT_MUTED};">'
            f'acc RF 87,9%</div>'
            f'</div>'
            f'<div style="padding:8px 12px;border-radius:8px;'
            f'background:{_ov_lgpd_bg};border:1px solid {_ov_lgpd_brd};'
            f'font-size:11px;color:{_ov_lgpd_c};font-weight:600;">'
            f'{_ov_lgpd_txt}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
# Aba — Nova Análise  (helper em módulo — fora do with tab_nova)
# ═══════════════════════════════════════════════════════════════════════════════
import re as _re


def _limpar_prescricao(texto: str) -> str:
    """Normaliza o texto do LLM para diagramação limpa e uniforme.

    Remove: **bold**, *italico*, listas markdown inconsistentes.
    Colapsa: linhas em branco excessivas.
    Padroniza: numeração e indentação.
    """
    t = texto
    # Remove bold/italico markdown
    t = _re.sub(r'\*\*(.+?)\*\*', r'\1', t)     # **bold** → bold
    t = _re.sub(r'\*(.+?)\*', r'\1', t)           # *italic* → italic
    t = _re.sub(r'__([^_]+)__', r'\1', t)          # __bold__ → bold
    t = _re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'\1', t)  # _italic_ → italic
    # Remove marcadores de lista markdown
    t = _re.sub(r'^[\s]*[-•]\s+', '  • ', t, flags=_re.MULTILINE)
    t = _re.sub(r'^[\s]*o\s+', '  • ', t, flags=_re.MULTILINE)
    # Remove numeração markdown solta (ex: "1.\n\n**bold:**" → "1. bold:")
    t = _re.sub(r'^(\d+)\.\s*\n+\s*', r'\1. ', t, flags=_re.MULTILINE)
    # Colapsa 3+ linhas brancas em 2
    t = _re.sub(r'\n{3,}', '\n\n', t)
    # Remove espaços trailing por linha
    t = '\n'.join(line.rstrip() for line in t.split('\n'))
    return t.strip()


def _na_show_operador(res: dict) -> None:
    """Relatório focado no operador — o que aconteceu e o que fazer."""
    _sem  = res.get("semaforo", "🟢")
    _def  = res.get("defeito_canonico", res.get("defeito", "—"))
    _prob = res.get("is_problem", False)
    _doc  = res.get("documented", False)
    _freq = res.get("frequency_per_week", 0.0)
    _sc   = {"🔴": ui.DANGER, "🟡": ui.WARN, "🟢": ui.ACCENT}.get(_sem, ui.TEXT_MUTED)
    _sem_label = {"🔴": "CRÍTICO", "🟡": "ATENÇÃO", "🟢": "OK"}.get(_sem, "—")
    _def_pt = _fmt_defeito(_def)

    # ── Header: semáforo grande + defeito ──────────────────────────────────────
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:24px;'
        f'padding:24px 0 16px 0;">'
        f'<div style="font-size:72px;line-height:1;">{_sem}</div>'
        f'<div>'
        f'<div style="font-size:28px;font-weight:700;color:{_sc};">{_def_pt}</div>'
        f'<div style="font-size:13px;color:{ui.TEXT_MUTED};margin-top:4px;">'
        f'{_sem_label} · '
        f'{"Defeito detectado" if _prob else "Estado operacional normal"}'
        f' · {_freq:.1f} ocorrências/semana'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )

    # ── KPIs compactos ─────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            f'<div class="mp-glow" style="text-align:center;padding:14px 8px;">'
            f'<div style="font-size:10px;color:{ui.TEXT_DIM};text-transform:uppercase;'
            f'letter-spacing:0.6px;">Frequência</div>'
            f'<div style="font-size:22px;font-weight:700;color:{ui.TEXT};'
            f'margin-top:4px;">{_freq:.1f}<span style="font-size:12px;'
            f'color:{ui.TEXT_MUTED};"> /sem</span></div></div>',
            unsafe_allow_html=True,
        )
    with k2:
        _doc_label = "SIM" if _doc else "NÃO"
        _doc_color = ui.ACCENT if _doc else ui.DANGER
        st.markdown(
            f'<div class="mp-glow" style="text-align:center;padding:14px 8px;">'
            f'<div style="font-size:10px;color:{ui.TEXT_DIM};text-transform:uppercase;'
            f'letter-spacing:0.6px;">Manual Técnico</div>'
            f'<div style="font-size:22px;font-weight:700;color:{_doc_color};'
            f'margin-top:4px;">{_doc_label}</div></div>',
            unsafe_allow_html=True,
        )
    with k3:
        _n_sim = res.get("n_similar", 0)
        st.markdown(
            f'<div class="mp-glow" style="text-align:center;padding:14px 8px;">'
            f'<div style="font-size:10px;color:{ui.TEXT_DIM};text-transform:uppercase;'
            f'letter-spacing:0.6px;">Eventos Similares</div>'
            f'<div style="font-size:22px;font-weight:700;color:{ui.TEXT};'
            f'margin-top:4px;">{_n_sim:,}</div></div>',
            unsafe_allow_html=True,
        )
    with k4:
        _id_salvo = res.get("id_salvo")
        _id_label = f"#{_id_salvo}" if _id_salvo else "—"
        st.markdown(
            f'<div class="mp-glow" style="text-align:center;padding:14px 8px;">'
            f'<div style="font-size:10px;color:{ui.TEXT_DIM};text-transform:uppercase;'
            f'letter-spacing:0.6px;">Evento Salvo</div>'
            f'<div style="font-size:22px;font-weight:700;color:{ui.TEXT};'
            f'margin-top:4px;">{_id_label}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # ── Prescrição (card grande) ───────────────────────────────────────────────
    _instr = res.get("instructions", "")
    if _instr:
        _instr = _limpar_prescricao(_instr)
    if _instr:
        _border = ui.ACCENT if _prob else ui.INFO
        st.markdown(
            f'<div style="background:{ui.CARD_BG};border:1px solid {ui.BORDER};'
            f'border-left:4px solid {_border};border-radius:12px;padding:20px 24px;">'
            f'<div style="font-size:11px;letter-spacing:0.8px;text-transform:uppercase;'
            f'color:{ui.TEXT_DIM};margin-bottom:12px;">📋 Procedimento de Correção</div>'
            f'<div style="color:{ui.TEXT};font-size:15px;line-height:1.9;'
            f'white-space:pre-wrap;">{_instr}</div></div>',
            unsafe_allow_html=True,
        )
    elif _prob and not _doc:
        st.markdown(
            f'<div style="background:rgba(255,107,122,0.08);border:1px solid '
            f'rgba(255,107,122,0.3);border-left:4px solid {ui.DANGER};'
            f'border-radius:12px;padding:20px 24px;">'
            f'<div style="font-size:11px;letter-spacing:0.8px;text-transform:uppercase;'
            f'color:{ui.DANGER};margin-bottom:12px;">⚠ Sem Procedimento Documentado</div>'
            f'<div style="color:{ui.TEXT};font-size:14px;line-height:1.8;">'
            f'Não existe manual técnico para <b>{_def_pt}</b>. '
            f'Uma pendência foi registrada automaticamente para que o '
            f'documento seja cadastrado.</div></div>',
            unsafe_allow_html=True,
        )

    # ── Fontes RAG ─────────────────────────────────────────────────────────────
    _fontes = res.get("sources", [])
    if _fontes:
        st.markdown(
            f'<div style="font-size:11px;color:{ui.TEXT_DIM};margin-top:12px;">'
            f'📎 Fontes: {", ".join(_fontes)}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)

    # ── Botão voltar ───────────────────────────────────────────────────────────
    if st.button("← Nova análise", key="na_btn_voltar", width="stretch"):
        st.session_state.pop("na_resultado", None)
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
with tab_nova:
    # ── Estado: resultado pronto → mostra relatório do operador ────────────────
    if "na_resultado" in st.session_state:
        _na_show_operador(st.session_state["na_resultado"])

    # ── Estado: processando → mostra spinner (tudo o que veio antes some) ──────
    elif "na_payload_analisar" in st.session_state:
        _na_slot = st.empty()
        with _na_slot.container():
            st.markdown(
                f'<div style="text-align:center;padding:60px 0;">'
                f'<div style="font-size:48px;margin-bottom:16px;">⚙️</div>'
                f'<div style="font-size:18px;font-weight:600;color:{ui.TEXT};">'
                f'Analisando evento...</div>'
                f'<div style="font-size:12px;color:{ui.TEXT_MUTED};margin-top:8px;">'
                f'Classificação KNN + prescrição RAG</div></div>',
                unsafe_allow_html=True,
            )
        _na_json_str = st.session_state.pop("na_payload_analisar")
        try:
            _na_payload = json.loads(_na_json_str)
        except json.JSONDecodeError as exc:
            _na_slot.empty()
            st.error(f"JSON inválido: {exc}")
            _na_payload = None
        if _na_payload is not None:
            try:
                _na_res = responder_evento(_na_payload, origem="streamlit")
                st.session_state["na_resultado"] = _na_res
                st.rerun()
            except Exception as exc:
                _na_slot.empty()
                st.error(f"Erro na análise: {exc}")

    # ── Estado: formulário → upload + textarea + campos ────────────────────────
    else:
        st.markdown(
            f'<div style="padding:18px 0 16px 0;">'
            f'<div style="font-size:20px;font-weight:700;color:{ui.TEXT};">'
            f'Nova Análise</div>'
            f'<div style="font-size:12px;color:{ui.TEXT_MUTED};margin-top:4px;">'
            f'Envie o JSON do sensor — o sistema classifica e prescreve a correção</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Upload: detecta arquivo, salva em session_state, dispara análise ───
        _na_upload = st.file_uploader(
            "Upload JSON", type=["json", "txt"], key="na_upload",
            label_visibility="collapsed",
        )
        if _na_upload is not None:
            try:
                _uc = _na_upload.read().decode("utf-8")
                json.loads(_uc)  # valida JSON
                st.session_state["na_payload_analisar"] = _uc
                st.rerun()
            except Exception as _ue:
                st.error(f"Arquivo inválido: {_ue}")

        # ── Textarea + campos manuais (só aparece se não fez upload) ───────────
        if "na_payload_analisar" not in st.session_state:
            _na_left, _na_right = st.columns([1.3, 1])
            with _na_left:
                _prefill_val = st.session_state.pop("na_json_prefill_manual", "")
                _na_json = st.text_area(
                    "JSON do evento",
                    value=_prefill_val,
                    height=240,
                    key="na_textarea",
                    placeholder='{"rpm": 1750, "z_rms_velocity_mm_s": 4.2, '
                                '"z_kurtosis": 3.1, "temperature_c": 65.0}',
                    label_visibility="collapsed",
                )
            with _na_right:
                st.markdown(
                    f'<div style="font-size:12px;color:{ui.TEXT_MUTED};'
                    f'margin-bottom:10px;margin-top:2px;">Ou preencha os campos:</div>',
                    unsafe_allow_html=True,
                )
                _na_rpm   = st.number_input("RPM", 0, 6000, 0, 50, key="na_rpm")
                _na_temp  = st.number_input("Temperatura (°C)", 0.0, 200.0, 0.0, 0.5, key="na_temp")
                _na_zrms  = st.number_input("Z RMS velocity (mm/s)", 0.0, 50.0, 0.0, 0.1, key="na_zrms")
                _na_xrms  = st.number_input("X RMS velocity (mm/s)", 0.0, 50.0, 0.0, 0.1, key="na_xrms")
                _na_zkurt = st.number_input("Z Kurtosis", 0.0, 30.0, 0.0, 0.1, key="na_zkurt")
                if st.button("Usar campos →", width="stretch", key="na_btn_campos"):
                    st.session_state["na_json_prefill_manual"] = json.dumps({
                        "rpm": _na_rpm, "temperature_c": _na_temp,
                        "z_rms_velocity_mm_s": _na_zrms,
                        "x_rms_velocity_mm_s": _na_xrms,
                        "z_kurtosis": _na_zkurt,
                    }, indent=2)
                    st.rerun()

            st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
            _na_b1, _na_b2 = st.columns([4, 1])
            with _na_b1:
                _na_analisar = st.button(
                    "Analisar", type="primary",
                    width="stretch", key="na_btn_analisar",
                )
            with _na_b2:
                if st.button("Limpar", width="stretch", key="na_btn_limpar"):
                    for k in ["na_json_prefill_manual", "na_resultado"]:
                        st.session_state.pop(k, None)
                    st.rerun()

            # Análise manual via botão
            if _na_analisar and _na_json.strip():
                st.session_state["na_payload_analisar"] = _na_json
                st.rerun()
            elif _na_analisar:
                st.warning("Cole ou envie um JSON de sensor para analisar.")


# ═══════════════════════════════════════════════════════════════════════════════
with tab_pend:
    ui.section("Pendências")
    try:
        pendencias = db.listar_pendencias(limit=50)
    except Exception as exc:
        st.error(f"Erro ao listar pendências: {exc}")
        pendencias = []

    if not pendencias:
        st.success("Nenhuma pendência registrada.")
    else:
        # Conta pendentes vs resolvidos
        _pendentes = [p for p in pendencias if p.get("status") == "pendente"]
        _resolvidos = [p for p in pendencias if p.get("status") == "resolvido"]

        if len(_pendentes) > 5:
            st.markdown(
                f'<div style="background:rgba(255,107,122,0.10);'
                f'border:1px solid {ui.DANGER};border-radius:10px;'
                f'padding:14px 18px;margin-bottom:16px;">'
                f'<b style="color:{ui.DANGER};">⚠ {len(_pendentes)} pendências abertas</b>'
                f' — acima do limite recomendado (5). Atenção imediata necessária.'
                f'</div>',
                unsafe_allow_html=True,
            )

        for p in pendencias:
            _pid = p["id"]
            _is_resolved = p.get("status") == "resolvido"
            freq      = p.get("frequency_per_week", 0.0)
            doc_color = ui.ACCENT if p.get("documented") else ui.DANGER
            doc_flag  = "COM manual" if p.get("documented") else "SEM manual"
            ts_str    = (p.get("ts") or "")[:10]
            _def_fmt  = _fmt_defeito(p["defeito"])

            # ── Card da pendência (vermelho = pendente, verde = resolvido) ──
            _card_border = ui.ACCENT if _is_resolved else ui.DANGER
            _card_bg = f'rgba(16,245,163,0.04)' if _is_resolved else 'rgba(255,107,122,0.04)'
            _badge_bg = 'rgba(16,245,163,0.12)' if _is_resolved else 'rgba(255,107,122,0.12)'
            _badge_brd = 'rgba(16,245,163,0.35)' if _is_resolved else 'rgba(255,107,122,0.35)'
            _badge_color = ui.ACCENT if _is_resolved else ui.DANGER
            _badge_text = "✅ RESOLVIDO" if _is_resolved else "PENDENTE"

            st.markdown(
                f'<div class="mp-card" style="border-left:3px solid {_card_border};'
                f'background:{_card_bg};">'
                f'<div style="display:flex;align-items:center;gap:10px;">'
                f'<div style="width:14px;height:14px;border-radius:50%;'
                f'background:{_card_border};flex-shrink:0;"></div>'
                f'<b style="color:{ui.TEXT};flex:1;">#{_pid} — {_def_fmt}</b>'
                f'<span class="mp-badge" style="background:{_badge_bg};'
                f'color:{_badge_color};border:1px solid {_badge_brd};">{_badge_text}</span>'
                f'</div>'
                f'<div style="margin-top:8px;font-size:12px;color:{ui.TEXT_MUTED};">'
                f'Frequência: <b style="color:{ui.TEXT};">{freq:.1f}/sem</b>'
                f' &nbsp;·&nbsp; <span style="color:{doc_color};">{doc_flag}</span>'
                f' &nbsp;·&nbsp; {ts_str}'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            # ── Botões de ação (só para pendentes) ──────────────────────────
            if not _is_resolved:
                _col_rec, _col_res, _spacer = st.columns([2, 2, 6])

                with _col_rec:
                    if st.button("Ver recomendação", key=f"pend_rec_{_pid}",
                                 width="stretch"):
                        st.session_state[f"pend_show_rec_{_pid}"] = not st.session_state.get(
                            f"pend_show_rec_{_pid}", False)

                with _col_res:
                    if st.button("✅ Resolvido", key=f"pend_res_{_pid}",
                                 width="stretch"):
                        st.session_state[f"pend_confirm_{_pid}"] = True
                        st.rerun()

                # --- Expansão: prescrição ---
                if st.session_state.get(f"pend_show_rec_{_pid}", False):
                    _ev = db.buscar_evento(_pid)
                    if _ev and _ev.get("report"):
                        _rep = _ev["report"]
                        _instr = _rep.get("instructions", "")
                        if _instr:
                            _instr = _limpar_prescricao(_instr)
                        _fontes = _rep.get("sources", [])
                        _border = ui.ACCENT if _ev.get("documented") else ui.INFO
                        st.markdown(
                            f'<div style="background:{ui.CARD_BG};border:1px solid {ui.BORDER};'
                            f'border-left:4px solid {_border};border-radius:12px;padding:16px 20px;'
                            f'margin:4px 0 8px 0;">'
                            f'<div style="font-size:11px;letter-spacing:0.8px;text-transform:uppercase;'
                            f'color:{ui.TEXT_DIM};margin-bottom:8px;">📋 Procedimento de Correção</div>'
                            f'<div style="color:{ui.TEXT};font-size:14px;line-height:1.8;'
                            f'white-space:pre-wrap;">{_instr or "Sem prescrição disponível."}</div>'
                            + (f'<div style="font-size:11px;color:{ui.TEXT_DIM};margin-top:8px;">'
                               f'Fontes: {", ".join(_fontes)}</div>' if _fontes else '')
                            + f'</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.info("Prescrição não encontrada.")

                # --- Fluxo: confirmar resolução ---
                if st.session_state.get(f"pend_confirm_{_pid}", False):
                    st.markdown(
                        f'<div style="font-size:12px;color:{ui.TEXT_DIM};'
                        f'margin-bottom:4px;">Comentário (opcional):</div>',
                        unsafe_allow_html=True,
                    )
                    _comentario = st.text_input(
                        "Comentário", key=f"pend_comentario_{_pid}",
                        label_visibility="collapsed",
                        placeholder="Ex: rolamento substituído, correia tensionada...",
                    )
                    _col_ok, _col_cancel, _ = st.columns([2, 2, 6])
                    with _col_ok:
                        if st.button("Confirmar", type="primary",
                                     key=f"pend_confirmar_{_pid}",
                                     width="stretch"):
                            db.atualizar_status(
                                _pid, "resolvido",
                                comentario=_comentario or None,
                                responsavel="operador",
                            )
                            st.session_state.pop(f"pend_confirm_{_pid}", None)
                            st.session_state.pop(f"pend_show_rec_{_pid}", None)
                            st.rerun()
                    with _col_cancel:
                        if st.button("Cancelar", key=f"pend_cancelar_{_pid}",
                                     width="stretch"):
                            st.session_state.pop(f"pend_confirm_{_pid}", None)
                            st.rerun()

            st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Aba 3 — Resolvidos (timeline + slicer)
# ═══════════════════════════════════════════════════════════════════════════════
with tab_resolvidos:
    # ── Slicer ───────────────────────────────────────────────────────────────
    _res_ini, _res_fim = _period_slicer("res")

    # ── Timeline chart ────────────────────────────────────────────────────────
    try:
        from datetime import datetime as _dt
        _dias_res = max(1, (_dt.fromisoformat(_res_fim) - _dt.fromisoformat(_res_ini)).days)
        serie_res = db.serie_temporal_resolvidos(dias=_dias_res + 1)

        if serie_res:
            # filtrar pelo período selecionado
            serie_res = [r for r in serie_res if _res_ini <= r["dia"] <= _res_fim]

        if serie_res:
            # ── KPIs do período (primeiro) ─────────────────────────────────────
            _tot_ab = sum(r["abertos"] for r in serie_res)
            _tot_res = sum(r["resolvidos"] for r in serie_res)
            _res_pct = round(_tot_res / (_tot_ab + _tot_res) * 100) if (_tot_ab + _tot_res) else 0
            _ks = [
                ("Abertos no período",   str(_tot_ab),  ui.DANGER),
                ("Resolvidos",            str(_tot_res), ui.ACCENT),
                ("Taxa de resolução",    f"{_res_pct}%", ui.ACCENT if _res_pct >= 60 else ui.WARN),
                ("Dias analisados",       str(len(serie_res)), ui.TEXT_MUTED),
            ]
            _kst_html = ""
            for _ki2, (_kl2, _kv2, _kc2) in enumerate(_ks):
                _kbl2 = f"border-left:1px solid {ui.BORDER};" if _ki2 > 0 else ""
                _kst_html += (
                    f'<div style="flex:1;padding:0 20px;{_kbl2};text-align:center;">'
                    f'<div style="font-size:9px;letter-spacing:0.7px;text-transform:uppercase;'
                    f'color:{ui.TEXT_DIM};font-weight:600;margin-bottom:6px;">{_kl2}</div>'
                    f'<div style="font-size:26px;font-weight:800;color:{_kc2};'
                    f'font-variant-numeric:tabular-nums;">{_kv2}</div>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="background:{ui.CARD_BG};border:1px solid {ui.BORDER};'
                f'border-radius:12px;padding:16px 4px;margin-bottom:16px;'
                f'display:flex;align-items:center;">' + _kst_html + '</div>',
                unsafe_allow_html=True,
            )

            # ── Linha do Tempo (depois dos KPIs) ──────────────────────────────
            st.markdown(
                f'<div style="font-size:10px;letter-spacing:0.7px;text-transform:uppercase;'
                f'color:{ui.TEXT_DIM};font-weight:600;margin-bottom:8px;">'
                f'Linha do Tempo</div>',
                unsafe_allow_html=True,
            )
            df_res = pd.DataFrame(serie_res)
            fig_res = px.line(
                df_res, x="dia", y=["resolvidos", "abertos"],
                color_discrete_map={"resolvidos": ui.ACCENT, "abertos": ui.DANGER},
                labels={"value": "", "dia": "", "variable": ""},
            )
            fig_res.update_layout(
                paper_bgcolor=ui.CARD_BG, plot_bgcolor=ui.BG,
                font=dict(color=ui.TEXT_MUTED, size=11),
                height=420,
                margin=dict(l=40, r=16, t=20, b=50),
                legend=dict(
                    bgcolor=ui.CARD_BG, bordercolor=ui.BORDER, borderwidth=1,
                    orientation="h", x=0.5, y=-0.12,
                    xanchor="center", yanchor="top", font=dict(size=11),
                    title=None,
                ),
                xaxis=dict(showgrid=False, tickfont=dict(size=10), title=None),
                yaxis=dict(gridcolor=ui.BORDER, showgrid=True, title=None, tickfont=dict(size=10)),
            )
            fig_res.update_traces(line=dict(width=2))
            st.plotly_chart(fig_res, width="stretch")
        else:
            st.info(f"Sem dados de série temporal para o período {_res_ini} → {_res_fim}.")
    except Exception as exc:
        st.error(f"Erro na série temporal: {exc}")


# ═══════════════════════════════════════════════════════════════════════════════
# Aba 4 — Análise
# ═══════════════════════════════════════════════════════════════════════════════
with tab_analise:
    ui.section("Distribuição por Criticidade")
    try:
        resumo_an = db.resumo_semaforo()
        df_crit = pd.DataFrame([
            {"Criticidade": "Crítico",  "Qtd": resumo_an["vermelho"]},
            {"Criticidade": "Atenção",  "Qtd": resumo_an["amarelo"]},
            {"Criticidade": "Normal",   "Qtd": resumo_an["verde"]},
        ])
        _color_disc = {
            "Crítico": ui.DANGER,
            "Atenção": ui.WARN,
            "Normal":  ui.ACCENT,
        }

        col_bar, col_pie = st.columns(2)
        with col_bar:
            fig_bar = px.bar(
                df_crit, x="Criticidade", y="Qtd", color="Criticidade",
                color_discrete_map=_color_disc,
                title="Eventos por nível de criticidade",
            )
            fig_bar.update_layout(
                paper_bgcolor=ui.CARD_BG, plot_bgcolor=ui.CARD_BG,
                font=dict(color=ui.TEXT_MUTED, size=11),
                margin=dict(l=40, r=16, t=40, b=50),
                showlegend=False,
                xaxis=dict(title=None, tickfont=dict(size=11)),
                yaxis=dict(title=None, gridcolor=ui.BORDER, tickfont=dict(size=10)),
                bargap=0.3,
            )
            st.plotly_chart(fig_bar, width="stretch")

        with col_pie:
            fig_pie = px.pie(
                df_crit, names="Criticidade", values="Qtd",
                color="Criticidade", color_discrete_map=_color_disc,
                title="Proporção por criticidade",
            )
            fig_pie.update_layout(
                paper_bgcolor=ui.CARD_BG, plot_bgcolor=ui.CARD_BG,
                font=dict(color=ui.TEXT_MUTED, size=11),
                margin=dict(l=16, r=16, t=40, b=16),
                legend=dict(
                    orientation="h", x=0.5, y=-0.1, xanchor="center",
                    font=dict(size=11),
                ),
            )
            fig_pie.update_traces(textinfo="label+percent", textposition="outside",
                                  textfont=dict(size=10))
            st.plotly_chart(fig_pie, width="stretch")


    except Exception as exc:
        st.error(f"Erro nos gráficos: {exc}")

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
                width="stretch", hide_index=True,
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
            _docs       = item.get("sources", [])
            _fonte_color = ui.ACCENT if "LLM" in _fontes_str else ui.INFO
            _docs_html  = (
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


# ═══════════════════════════════════════════════════════════════════════════════
# Aba 6 — Relatório IA
# ═══════════════════════════════════════════════════════════════════════════════
with tab_relatorio:
    # ── Header + Botão na mesma linha ────────────────────────────────────────
    _rh_col, _rg_col = st.columns([4, 1])
    with _rh_col:
        st.markdown(
            f'<div style="padding:18px 0 4px 0;">'
            f'<div style="font-size:20px;font-weight:700;color:{ui.TEXT};">'
            f'Relatório IA</div>'
            f'<div style="font-size:12px;color:{ui.TEXT_MUTED};margin-top:4px;">'
            f'A IA analisa todos os eventos do período selecionado e gera um '
            f'relatório executivo de manutenção</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with _rg_col:
        st.markdown('<div style="padding-top:20px;"></div>', unsafe_allow_html=True)
        gerar_btn = st.button(
            "Gerar Relatório →", type="primary", width="stretch", key="btn_gerar_rel",
        )

    # ── Slicer ───────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:10px;letter-spacing:0.7px;text-transform:uppercase;'
        f'color:{ui.TEXT_DIM};font-weight:600;margin-bottom:8px;">Período de análise</div>',
        unsafe_allow_html=True,
    )
    _rep_ini, _rep_fim = _period_slicer("rep")

    st.markdown(
        f'<div style="border-bottom:1px solid {ui.BORDER};margin:12px 0 16px 0;"></div>',
        unsafe_allow_html=True,
    )

    # ── Geração ──────────────────────────────────────────────────────────────
    if gerar_btn:
        st.session_state.pop("relatorio_resultado", None)
        with st.spinner(f"Analisando eventos de {_rep_ini} a {_rep_fim} · consultando IA..."):
            try:
                _rel = gerar_relatorio_ia(_rep_ini, _rep_fim)
                st.session_state["relatorio_resultado"] = _rel
            except Exception as exc:
                st.session_state["relatorio_resultado"] = {
                    "ok": False, "erro": str(exc), "stats": {}
                }

    # ── Resultado ─────────────────────────────────────────────────────────────
    if "relatorio_resultado" in st.session_state:
        _rel = st.session_state["relatorio_resultado"]
        _stats = _rel.get("stats", {})

        # KPIs do período
        if _stats.get("total", 0) > 0:
            _skpis = [
                ("Eventos",       str(_stats.get("total", 0)),     ui.TEXT),
                ("Críticos",      str(_stats.get("criticos", 0)),  ui.DANGER),
                ("Atenção",       str(_stats.get("atencao", 0)),   ui.WARN),
                ("Pendentes",     str(_stats.get("pendentes", 0)), ui.DANGER if _stats.get("pendentes", 0) > 0 else ui.ACCENT),
                ("Resolvidos",    str(_stats.get("resolvidos", 0)), ui.ACCENT),
                ("Sem doc",       str(_stats.get("sem_doc", 0)),   ui.DANGER if _stats.get("sem_doc", 0) > 0 else ui.ACCENT),
            ]
            _sk_html = ""
            for _si, (_sl, _sv, _sc) in enumerate(_skpis):
                _sbl = f"border-left:1px solid {ui.BORDER};" if _si > 0 else ""
                _sk_html += (
                    f'<div style="flex:1;padding:0 16px;{_sbl};text-align:center;">'
                    f'<div style="font-size:9px;letter-spacing:0.7px;text-transform:uppercase;'
                    f'color:{ui.TEXT_DIM};font-weight:600;margin-bottom:5px;">{_sl}</div>'
                    f'<div style="font-size:22px;font-weight:800;color:{_sc};'
                    f'font-variant-numeric:tabular-nums;">{_sv}</div>'
                    f'</div>'
                )
            st.markdown(
                f'<div style="background:{ui.CARD_BG};border:1px solid {ui.BORDER};'
                f'border-top:2px solid {ui.ACCENT};border-radius:12px;'
                f'padding:14px 4px;margin-bottom:20px;'
                f'display:flex;align-items:center;">' + _sk_html + '</div>',
                unsafe_allow_html=True,
            )

        if _rel.get("ok"):
            st.markdown(
                f'<div style="background:{ui.CARD_BG};border:1px solid {ui.BORDER};'
                f'border-radius:14px;padding:24px 28px;">'
                f'<div style="font-size:10px;letter-spacing:0.7px;text-transform:uppercase;'
                f'color:{ui.TEXT_DIM};font-weight:600;margin-bottom:16px;">'
                f'Relatório gerado pela IA — {_rep_ini} a {_rep_fim}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(_rel["relatorio"])
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.error(f"Erro ao gerar relatório: {_rel.get('erro', '?')}")
    else:
        st.markdown(
            f'<div style="background:{ui.CARD_BG};border:1px solid {ui.BORDER};'
            f'border-radius:14px;padding:48px 24px;text-align:center;">'
            f'<div style="font-size:32px;margin-bottom:12px;">📋</div>'
            f'<div style="font-size:15px;font-weight:600;color:{ui.TEXT};margin-bottom:6px;">'
            f'Nenhum relatório gerado</div>'
            f'<div style="font-size:13px;color:{ui.TEXT_MUTED};">'
            f'Selecione o período e clique em <b>Gerar Relatório →</b></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ═══════════════════════════════════════════════════════════════════════════════
# Aba 7 — Configuração IA
# ═══════════════════════════════════════════════════════════════════════════════
with tab_config:
    _dlg_cfg_ia()
