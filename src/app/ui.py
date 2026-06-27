"""Design system Streamlit — Manutencao Prescritiva SENAI SC.

Componentes puros: recebem dados, renderizam via st.markdown/st.columns.
Paleta e CSS portados do Gestor_Financeiro (neon escuro).
"""
from __future__ import annotations
import streamlit as st

# ── Paleta ──────────────────────────────────────────────────────────────────
ACCENT      = "#10F5A3"   # verde neon (semaforo ok / documentado)
ACCENT_SOFT = "#0FCC88"
WARN        = "#F5C518"   # amarelo (semaforo atencao)
DANGER      = "#FF6B7A"   # vermelho (semaforo critico / sem doc)
INFO        = "#4FC3F7"   # azul (estado / informativo)
TEXT        = "#E8ECF2"
TEXT_MUTED  = "#8B92A0"
TEXT_DIM    = "#6E7A8C"
BG          = "#0B0E13"
CARD_BG     = "#10141C"
BORDER      = "#1F2530"

# ── Mapa semaforo → cor ─────────────────────────────────────────────────────
_SEM_COLOR = {"🔴": DANGER, "🟡": WARN, "🟢": ACCENT}
_SEM_LABEL = {"🔴": "CRÍTICO", "🟡": "ATENÇÃO", "🟢": "OK"}

# ── Status → cor ────────────────────────────────────────────────────────────
_STATUS_COLOR = {
    "pendente":      DANGER,
    "em_andamento":  WARN,
    "ok":            ACCENT,
    "resolvido":     ACCENT,
    "descartado":    TEXT_MUTED,
}
_STATUS_LABEL = {
    "pendente":      "PENDENTE",
    "em_andamento":  "EM ANDAMENTO",
    "ok":            "OK",
    "resolvido":     "RESOLVIDO",
    "descartado":    "DESCARTADO",
}
STATUS_OPTIONS = ["pendente", "em_andamento", "resolvido", "descartado"]

# ── CSS ─────────────────────────────────────────────────────────────────────
CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,500;14..32,600;14..32,700;14..32,800&display=swap');

    html, body, .stApp, [class*="css"] {{
        font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif !important;
        font-optical-sizing: auto;
    }}
    .stApp {{ background: {BG}; }}
    section[data-testid="stSidebar"] {{
        background: {BG};
        border-right: 1px solid {BORDER};
    }}
    section[data-testid="stSidebar"] > div {{ padding-top: 1.5rem; }}
    .block-container {{ padding-top: 4rem; padding-bottom: 3rem; max-width: 1500px; }}

    /* ===== Cards genéricos ===== */
    .mp-card {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 14px;
    }}

    /* ===== GLOW KPI box ===== */
    .mp-glow {{
        position: relative;
        background:
            radial-gradient(ellipse 80% 100% at 0% 0%, rgba(16,245,163,0.10) 0%, rgba(16,245,163,0.02) 35%, transparent 70%),
            {CARD_BG};
        border: 1px solid rgba(16,245,163,0.22);
        border-radius: 18px;
        padding: 22px 24px;
        margin-bottom: 20px;
        box-shadow:
            0 0 1px rgba(16,245,163,0.35),
            0 0 22px rgba(16,245,163,0.10),
            inset 0 1px 0 rgba(255,255,255,0.03);
    }}
    .mp-glow::before {{
        content: "";
        position: absolute;
        top: -1px; left: -1px; right: -1px; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(16,245,163,0.55), transparent);
        border-radius: 18px 18px 0 0;
    }}
    .mp-glow-title {{
        font-size: 11px; letter-spacing: 0.8px; text-transform: uppercase;
        color: {ACCENT}; font-weight: 700; margin-bottom: 12px;
        display: flex; align-items: center; gap: 8px;
    }}
    .mp-glow-title::before {{
        content: ""; width: 6px; height: 6px; border-radius: 50%;
        background: {ACCENT};
        box-shadow: 0 0 8px {ACCENT}, 0 0 16px {ACCENT};
    }}

    /* ===== KPI grid (dentro do glow) ===== */
    .mp-kpi-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 0;
    }}
    .mp-kpi-cell {{
        padding: 4px 18px;
        border-right: 1px solid rgba(255,255,255,0.05);
    }}
    .mp-kpi-cell:first-child {{ padding-left: 4px; }}
    .mp-kpi-cell:last-child  {{ border-right: none; }}
    .mp-kpi-label {{
        font-size: 10px; letter-spacing: 0.7px; text-transform: uppercase;
        color: {TEXT_DIM}; font-weight: 600; margin-bottom: 4px;
    }}
    .mp-kpi-value {{
        font-size: 26px; font-weight: 800; color: {TEXT}; line-height: 1.1;
        font-variant-numeric: tabular-nums; letter-spacing: -0.3px;
    }}
    .mp-kpi-sub {{ font-size: 11px; color: {TEXT_MUTED}; margin-top: 4px; }}

    /* ===== Semaforo KPI (barra superior colorida) ===== */
    .mp-sem-card {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 18px 22px;
        text-align: center;
    }}
    .mp-sem-count {{
        font-size: 38px; font-weight: 800; line-height: 1;
        font-variant-numeric: tabular-nums;
    }}
    .mp-sem-label {{
        font-size: 10px; letter-spacing: 0.8px; text-transform: uppercase;
        color: {TEXT_DIM}; font-weight: 700; margin-top: 6px;
    }}
    .mp-sem-icon {{ font-size: 20px; margin-bottom: 6px; }}

    /* ===== Badge inline (status / semaforo) ===== */
    .mp-badge {{
        display: inline-block;
        padding: 2px 9px;
        border-radius: 999px;
        font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
    }}

    /* ===== Section heading ===== */
    .mp-h {{
        font-size: 13px; letter-spacing: 0.7px; text-transform: uppercase;
        color: #C8CDD6; font-weight: 700;
        margin: 18px 0 12px 2px;
        display: flex; align-items: center; gap: 10px;
    }}
    .mp-h-default::before {{
        content: ""; width: 4px; height: 16px;
        background: linear-gradient(180deg, {ACCENT}, {ACCENT_SOFT});
        border-radius: 2px;
        box-shadow: 0 0 8px rgba(16,245,163,0.5);
        flex-shrink: 0;
    }}
    .mp-h-bar {{
        display: inline-block; width: 4px; height: 16px;
        border-radius: 2px; flex-shrink: 0;
    }}

    /* ===== Prescricao box ===== */
    .mp-presc-ok {{
        background:
            linear-gradient(135deg, rgba(16,245,163,0.05) 0%, transparent 60%),
            {CARD_BG};
        border: 1px solid {BORDER};
        border-left: 3px solid {ACCENT};
        border-radius: 12px;
        padding: 16px 20px;
        color: #D4D8E0; font-size: 14px; line-height: 1.65;
    }}
    .mp-presc-ok b {{ color: {ACCENT}; }}
    .mp-presc-warn {{
        background:
            linear-gradient(135deg, rgba(245,197,24,0.05) 0%, transparent 60%),
            {CARD_BG};
        border: 1px solid {BORDER};
        border-left: 3px solid {WARN};
        border-radius: 12px;
        padding: 16px 20px;
        color: #D4D8E0; font-size: 14px; line-height: 1.65;
    }}
    .mp-presc-warn b {{ color: {WARN}; }}
    .mp-presc-danger {{
        background:
            linear-gradient(135deg, rgba(255,107,122,0.05) 0%, transparent 60%),
            {CARD_BG};
        border: 1px solid {BORDER};
        border-left: 3px solid {DANGER};
        border-radius: 12px;
        padding: 16px 20px;
        color: #D4D8E0; font-size: 14px; line-height: 1.65;
    }}
    .mp-presc-danger b {{ color: {DANGER}; }}

    /* ===== Sidebar ===== */
    .mp-sb-brand {{
        font-size: 16px; font-weight: 800; color: {TEXT}; letter-spacing: -0.3px;
        margin-bottom: 2px;
    }}
    .mp-sb-tag {{ font-size: 11px; color: {TEXT_MUTED}; margin-bottom: 18px; }}
    .mp-sb-section {{
        font-size: 10px; letter-spacing: 0.8px; text-transform: uppercase;
        color: {TEXT_DIM}; font-weight: 700; margin: 18px 0 10px 0;
    }}
    .mp-sb-row {{
        display: flex; justify-content: space-between; align-items: center;
        padding: 9px 0; border-bottom: 1px solid {BORDER};
    }}
    .mp-sb-row:last-child {{ border-bottom: none; }}
    .mp-sb-label {{ color: {TEXT_MUTED}; font-size: 12px; }}
    .mp-sb-val   {{ color: {TEXT}; font-size: 13px; font-weight: 600;
                    font-variant-numeric: tabular-nums; }}
    .mp-sb-badge {{
        display: inline-block; padding: 2px 8px; border-radius: 999px;
        font-size: 9px; font-weight: 700; letter-spacing: 0.5px;
        background: rgba(16,245,163,0.10); color: {ACCENT};
        border: 1px solid rgba(16,245,163,0.3);
        box-shadow: 0 0 8px rgba(16,245,163,0.15);
    }}

    /* ===== Tabs ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px; border-bottom: 1px solid {BORDER};
    }}
    .stTabs [data-baseweb="tab"] {{
        padding: 10px 18px; border-radius: 8px 8px 0 0;
        background: transparent; color: {TEXT_MUTED};
    }}
    .stTabs [aria-selected="true"] {{
        background: {CARD_BG} !important; color: {TEXT} !important;
        border-top: 1px solid {BORDER};
        border-left: 1px solid {BORDER};
        border-right: 1px solid {BORDER};
    }}

    /* ===== Botão primary ===== */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(180deg, {ACCENT} 0%, {ACCENT_SOFT} 100%);
        color: #08120D; border: none; font-weight: 700;
        box-shadow: 0 0 18px rgba(16,245,163,0.22);
    }}
    .stButton > button[kind="primary"]:hover {{
        background: linear-gradient(180deg, #1FFFB0 0%, {ACCENT} 100%);
        box-shadow: 0 0 28px rgba(16,245,163,0.38);
    }}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


# ── Section heading ──────────────────────────────────────────────────────────

def section(title: str, color: str | None = None) -> None:
    if color:
        bar = (
            f'<span class="mp-h-bar" style="'
            f'background:linear-gradient(180deg,{color},{color}cc);'
            f'box-shadow:0 0 8px {color}99;"></span>'
        )
        st.markdown(f'<div class="mp-h">{bar}<span>{title}</span></div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="mp-h mp-h-default">{title}</div>',
                    unsafe_allow_html=True)


# ── Generic glow KPI box ─────────────────────────────────────────────────────

def glow_kpi_box(title: str, items: list[tuple[str, str, str | None]]) -> None:
    """Box luminoso com KPIs em grid. Item: (label, value, sub_html|None)."""
    cells = []
    for label, value, sub in items:
        sub_html = f'<div class="mp-kpi-sub">{sub}</div>' if sub else ""
        cells.append(
            f'<div class="mp-kpi-cell">'
            f'<div class="mp-kpi-label">{label}</div>'
            f'<div class="mp-kpi-value">{value}</div>{sub_html}'
            f'</div>'
        )
    st.markdown(
        f'<div class="mp-glow">'
        f'<div class="mp-glow-title">{title}</div>'
        f'<div class="mp-kpi-grid">{"".join(cells)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Semaphore KPI panel ──────────────────────────────────────────────────────

def kpi_semaforo(resumo: dict) -> None:
    """Painel de 4 KPIs: total + 🔴🟡🟢.

    resumo = resumo_semaforo() do db.py:
      {"total": int, "vermelho": int, "amarelo": int, "verde": int, ...}
    """
    total    = resumo.get("total", 0)
    vermelho = resumo.get("vermelho", 0)
    amarelo  = resumo.get("amarelo", 0)
    verde    = resumo.get("verde", 0)

    c0, c1, c2, c3 = st.columns([1.4, 1, 1, 1])

    with c0:
        st.markdown(
            f'<div class="mp-sem-card" style="border-top:3px solid {TEXT_MUTED};">'
            f'<div class="mp-sem-icon">📊</div>'
            f'<div class="mp-sem-count" style="color:{TEXT};">{total}</div>'
            f'<div class="mp-sem-label">Total eventos</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with c1:
        st.markdown(
            f'<div class="mp-sem-card" style="border-top:3px solid {DANGER};">'
            f'<div class="mp-sem-icon">🔴</div>'
            f'<div class="mp-sem-count" style="color:{DANGER};">{vermelho}</div>'
            f'<div class="mp-sem-label">Crítico</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f'<div class="mp-sem-card" style="border-top:3px solid {WARN};">'
            f'<div class="mp-sem-icon">🟡</div>'
            f'<div class="mp-sem-count" style="color:{WARN};">{amarelo}</div>'
            f'<div class="mp-sem-label">Atenção</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f'<div class="mp-sem-card" style="border-top:3px solid {ACCENT};">'
            f'<div class="mp-sem-icon">🟢</div>'
            f'<div class="mp-sem-count" style="color:{ACCENT};">{verde}</div>'
            f'<div class="mp-sem-label">OK</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Badge inline ─────────────────────────────────────────────────────────────

def badge_status(status: str) -> str:
    """Retorna HTML de badge colorido para um status. Use com unsafe_allow_html=True."""
    color = _STATUS_COLOR.get(status, TEXT_MUTED)
    label = _STATUS_LABEL.get(status, status.upper())
    return (
        f'<span class="mp-badge" style="'
        f'background:rgba({_hex_to_rgb(color)},0.12);'
        f'color:{color};'
        f'border:1px solid rgba({_hex_to_rgb(color)},0.35);'
        f'">{label}</span>'
    )


def badge_semaforo(semaforo: str) -> str:
    """Badge HTML para símbolo de semáforo (🔴/🟡/🟢)."""
    color = _SEM_COLOR.get(semaforo, TEXT_MUTED)
    label = _SEM_LABEL.get(semaforo, semaforo)
    return (
        f'<span class="mp-badge" style="'
        f'background:rgba({_hex_to_rgb(color)},0.12);'
        f'color:{color};'
        f'border:1px solid rgba({_hex_to_rgb(color)},0.35);'
        f'">{semaforo} {label}</span>'
    )


def badge_defeito(defeito: str, documented: bool) -> str:
    """Badge HTML para tipo de defeito com indicador de cobertura documental."""
    color = ACCENT if documented else DANGER
    icon = "📄" if documented else "⚠"
    return (
        f'<span class="mp-badge" style="'
        f'background:rgba({_hex_to_rgb(color)},0.10);'
        f'color:{color};'
        f'border:1px solid rgba({_hex_to_rgb(color)},0.30);'
        f'">{icon} {defeito}</span>'
    )


# ── Prescricao card ───────────────────────────────────────────────────────────

def prescricao_card(
    instructions: str,
    documented: bool,
    is_problem: bool,
    sources: list[str] | None = None,
) -> None:
    """Bloco de instrucao de prescricao com estilo condicional."""
    if not is_problem:
        cls = "mp-presc-ok"
    elif documented:
        cls = "mp-presc-ok"
    else:
        cls = "mp-presc-danger"

    src_html = ""
    if sources:
        src_html = (
            f'<div style="margin-top:10px;font-size:11px;color:{TEXT_DIM};">'
            f'Fonte: {", ".join(sources)}</div>'
        )

    st.markdown(
        f'<div class="{cls}">{instructions}{src_html}</div>',
        unsafe_allow_html=True,
    )


# ── Form edicao de status ────────────────────────────────────────────────────

def form_edicao_status(
    evento_id: int,
    status_atual: str,
    key_prefix: str = "",
) -> tuple[str, str, str] | None:
    """Formulario inline para alterar status de um evento.

    Retorna (novo_status, comentario, responsavel) quando submetido,
    ou None se nao houve submit.
    """
    key = f"{key_prefix}form_status_{evento_id}"
    with st.form(key=key, clear_on_submit=True):
        st.markdown(
            f'<div style="font-size:11px;letter-spacing:0.7px;'
            f'text-transform:uppercase;color:{TEXT_DIM};font-weight:700;'
            f'margin-bottom:10px;">Atualizar status — evento #{evento_id}</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns([2, 2, 1])
        with cols[0]:
            novo_status = st.selectbox(
                "Novo status",
                options=STATUS_OPTIONS,
                index=STATUS_OPTIONS.index(status_atual)
                      if status_atual in STATUS_OPTIONS else 0,
                format_func=lambda s: _STATUS_LABEL.get(s, s),
                label_visibility="collapsed",
            )
        with cols[1]:
            responsavel = st.text_input(
                "Responsável",
                placeholder="Nome / matrícula",
                label_visibility="collapsed",
            )
        with cols[2]:
            submitted = st.form_submit_button("Salvar", use_container_width=True)

        comentario = st.text_area(
            "Comentário",
            placeholder="Observação sobre a intervenção (opcional)",
            height=68,
            label_visibility="collapsed",
        )

    if submitted:
        return (novo_status, comentario, responsavel)
    return None


# ── Sidebar brand ─────────────────────────────────────────────────────────────

def sidebar_brand() -> None:
    with st.sidebar:
        st.markdown(
            f'<div class="mp-sb-brand">⚙ Manutenção Prescritiva</div>'
            f'<div class="mp-sb-tag">SENAI SC — Diagnóstico por similaridade + RAG</div>',
            unsafe_allow_html=True,
        )


def sidebar_status(resumo: dict, llm_label: str = "", db_label: str = "") -> None:
    """Bloco de status na sidebar.

    resumo = resumo_geral() do db.py:
      {"eventos": int, "pendencias": int, "consultas": int, "backend": str}
    """
    with st.sidebar:
        if llm_label:
            st.markdown(
                f'<div class="mp-sb-section">Modelo ativo'
                f'<span style="float:right;">'
                f'<span class="mp-sb-badge">ATIVO</span></span></div>'
                f'<div style="color:{TEXT};font-size:12px;line-height:1.5;'
                f'padding:6px 0 10px 0;border-bottom:1px solid {BORDER};">'
                f'{llm_label}</div>',
                unsafe_allow_html=True,
            )
        _db = resumo.get("backend", db_label or "SQLite")
        st.markdown(
            f'<div class="mp-sb-section">Parque de máquinas</div>'
            f'<div class="mp-sb-row">'
            f'<span class="mp-sb-label">Eventos analisados</span>'
            f'<span class="mp-sb-val">{resumo.get("eventos", 0)}</span></div>'
            f'<div class="mp-sb-row">'
            f'<span class="mp-sb-label">Pendências abertas</span>'
            f'<span class="mp-sb-val" style="color:{DANGER};">'
            f'{resumo.get("pendencias", 0)}</span></div>'
            f'<div class="mp-sb-row">'
            f'<span class="mp-sb-label">Consultas (Q&A)</span>'
            f'<span class="mp-sb-val">{resumo.get("consultas", 0)}</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="mp-sb-section">Sistema</div>'
            f'<div class="mp-sb-row">'
            f'<span class="mp-sb-label">Banco</span>'
            f'<span class="mp-sb-val">{_db}</span></div>'
            f'<div class="mp-sb-row">'
            f'<span class="mp-sb-label">Status</span>'
            f'<span class="mp-sb-badge">ONLINE</span></div>',
            unsafe_allow_html=True,
        )


# ── Helpers internos ─────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"
