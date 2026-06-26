"""Dashboard + chat Streamlit - Manutencao Prescritiva (Figura 01 - Saida).

Entrada: JSON de novo evento. Saida: tipo de defeito, qtd ocorrencias, frequencia,
distribuicao temporal e instrucoes de correcao (RAG) ou aviso 'registre documento'.
Robusto: se os indices/LLM nao existirem, cai para MODO DEMO usando so o parquet.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import streamlit as st

from core.faults import normalize_fault, FAULT_DOC_MAP, STATES
from core.config import DATA_DIR

st.set_page_config(page_title="Manutencao Prescritiva", layout="wide")
PARQUET = DATA_DIR / "banner_clean.parquet"


@st.cache_data
def load_df() -> pd.DataFrame:
    df = pd.read_parquet(PARQUET)
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    return df


@st.cache_data
def sample_event() -> dict:
    p = Path(__file__).resolve().parents[2] / "tests" / "sample_events.json"
    return json.loads(p.read_text(encoding="utf-8"))[0]


def demo_report(event: dict, df: pd.DataFrame) -> dict:
    """Fallback sem indices: classifica pelo campo 'fault' do JSON e estatistica no parquet."""
    info = normalize_fault(str(event.get("fault", "")))
    canon = info.canonical
    same = df[df["fault_canonical"] == canon]
    months = same["created_at"].dt.strftime("%Y-%m").value_counts().sort_index()
    return {
        "event_id": event.get("id"), "created_at": event.get("created_at"),
        "defeito_canonico": canon, "is_problem": info.is_problem,
        "n_similar": int(len(same)),
        "frequency_per_week": round(len(same) / 6.7, 2),
        "last_occurrence": str(same["created_at"].max()) if len(same) else None,
        "time_distribution": {k: int(v) for k, v in months.items()},
        "documented": info.documented,
        "instructions": "(modo demo - construa os indices com `python scripts/build_all.py` "
                        "para prescricao via RAG)" if info.is_problem else
                        f"Estado operacional '{canon}'. Nenhuma acao.",
        "sources": [], "_demo": True,
    }


def analyze(event: dict, df: pd.DataFrame) -> dict:
    try:
        from core.pipeline import process_event
        r = process_event(event)
        r["_demo"] = False
        return r
    except Exception as e:  # noqa: BLE001
        st.warning(f"Indices/LLM indisponiveis ({type(e).__name__}). Usando MODO DEMO.")
        return demo_report(event, df)


# ===================== UI =====================
st.title("Manutencao Prescritiva - SENAI SC")
st.caption("Novo evento de sensor -> defeito similar no historico + acao de correcao (RAG).")

df = load_df()

with st.sidebar:
    st.header("Novo evento")
    txt = st.text_area("JSON do evento", value=json.dumps(sample_event(), indent=2), height=320)
    run = st.button("Analisar", type="primary", use_container_width=True)

tab_an, tab_dash, tab_chat = st.tabs(["Analise do evento", "Dashboard geral", "Chat"])

with tab_an:
    if run:
        try:
            event = json.loads(txt)
        except json.JSONDecodeError as e:
            st.error(f"JSON invalido: {e}")
            st.stop()
        rep = analyze(event, df)

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Defeito", rep["defeito_canonico"])
        c2.metric("E problema?", "Sim" if rep["is_problem"] else "Nao (estado)")
        c3.metric("Ocorrencias", f"{rep['n_similar']:,}")
        c4.metric("Freq/semana", rep["frequency_per_week"])
        c5.metric("Ultima", (rep["last_occurrence"] or "-")[:10])

        if rep["time_distribution"]:
            td = pd.DataFrame({"mes": list(rep["time_distribution"].keys()),
                               "ocorrencias": list(rep["time_distribution"].values())})
            st.plotly_chart(px.bar(td, x="mes", y="ocorrencias",
                                   title=f"Distribuicao temporal - {rep['defeito_canonico']}"),
                            use_container_width=True)

        st.subheader("Instrucoes de solucao")
        if not rep["is_problem"]:
            st.info(rep["instructions"])
        elif rep["documented"]:
            st.success(rep["instructions"])
            if rep["sources"]:
                st.caption("Fonte: " + ", ".join(rep["sources"]))
        else:
            st.warning("**Defeito sem procedimento documentado.**\n\n" + rep["instructions"])
    else:
        st.info("Cole um evento na barra lateral e clique em Analisar.")

with tab_dash:
    prob = df[df["is_problem"]]
    hist = prob["fault_canonical"].value_counts().reset_index()
    hist.columns = ["defeito", "ocorrencias"]
    st.plotly_chart(px.bar(hist, x="defeito", y="ocorrencias",
                           title="Defeitos no historico"), use_container_width=True)

    daily = df.set_index("created_at").resample("D").size().reset_index(name="eventos")
    st.plotly_chart(px.line(daily, x="created_at", y="eventos",
                            title="Eventos por dia"), use_container_width=True)

    st.subheader("Cobertura de documentos")
    cov = (df[df["is_problem"]].groupby("fault_canonical")
           .size().reset_index(name="ocorrencias"))
    cov["documentado"] = cov["fault_canonical"].map(
        lambda c: "Sim" if FAULT_DOC_MAP.get(c) else "Nao (registrar)")
    cov["doc"] = cov["fault_canonical"].map(lambda c: FAULT_DOC_MAP.get(c) or "-")
    st.dataframe(cov.sort_values("ocorrencias", ascending=False), use_container_width=True)

with tab_chat:
    st.caption("Pergunte sobre a correcao de um defeito (usa RAG).")
    q = st.text_input("Pergunta", value="Como corrigir cocked_rotor?")
    if st.button("Perguntar"):
        try:
            from core.rag import prescribe
            fault = normalize_fault(q).canonical
            res = prescribe(fault, question=q)
            if res.documented:
                st.success(res.instructions)
                st.caption("Fonte: " + ", ".join(res.sources))
            else:
                st.warning(res.instructions)
        except Exception as e:  # noqa: BLE001
            st.error(f"RAG indisponivel: {e}")
