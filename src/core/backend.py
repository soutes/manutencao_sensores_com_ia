"""Camada de orquestracao de alto nivel: backend de eventos e duvidas.

Contratos:
  responder_evento(event, origem) -> dict com report + semaforo + id_salvo
  responder_duvida(texto, origem) -> dict com resposta + contexto + fonte

Interruptor LGPD: llm_generate so e chamado via core.rag.prescribe, que por
sua vez so chama core.llm que respeita LLM_PROVIDER (ollama local vs openrouter).
Nenhum dado do payload bruto vai para o LLM — apenas o nome canonico do defeito.
"""
from __future__ import annotations

# RPM thresholds para detectar anomalia de velocidade
_RPM_MIN = 400
_RPM_MAX = 3800


# ─── classificacao de semaforo ─────────────────────────────────────────────

def _classificar_semaforo(report: dict, event: dict | None = None) -> str:
    """🟢 normal | 🟡 defeito com doc / baixa freq | 🔴 critico."""
    if not report.get("is_problem"):
        return "🟢"

    freq = float(report.get("frequency_per_week", 0.0))

    # rpm anormal (feature presente no payload de sensor)
    rpm_anormal = False
    if event:
        rpm = event.get("rpm")
        if rpm is not None:
            try:
                rpm_anormal = float(rpm) < _RPM_MIN or float(rpm) > _RPM_MAX
            except (TypeError, ValueError):
                pass

    if not report.get("documented") or freq > 5 or rpm_anormal:
        return "🔴"

    return "🟡"  # documentado + (1a ocorrencia ou baixa freq)


# ─── deteccao de intencao ─────────────────────────────────────────────────

def _detectar_intencao(texto: str) -> str:
    t = texto.lower()
    _status_kw = (
        "status", "parque", "crítico", "critico",
        "situação", "situacao", "manutencao aberta", "manutenção aberta",
        "pontos criticos", "pontos críticos",
        # perguntas naturais sobre estado geral do parque
        "atenção", "atencao", "alerta",
        "máquina", "maquina", "máquinas", "maquinas",
        "equipament", "motor precis", "motores precis",
        "precisa de", "precisam de",
    )
    _pend_kw = (
        "pendência", "pendencia", "pendente", "pendências",
        "pendencias", "em aberto", "abertas",
        "sem manual", "sem procedimento", "sem documento",
    )
    _hist_kw = ("histórico", "historico", "ocorrencias", "ocorrências",
                "vezes", "quantas vezes")

    if any(k in t for k in _status_kw):
        return "status_parque"
    if any(k in t for k in _pend_kw):
        return "pendencias"
    if any(k in t for k in _hist_kw):
        return "historico"
    return "tecnica"


def _extrair_defeito_texto(texto: str) -> str:
    """Extrai nome canonico de defeito mais provavel do texto livre."""
    from .faults import normalize_fault
    info = normalize_fault(texto)
    # se nao reconheceu, tenta pegar ultima 'palavra_composta' do texto
    if info.canonical == "desconhecido":
        import re
        candidatos = re.findall(r"[a-z_]{5,}", texto.lower())
        for c in reversed(candidatos):
            alt = normalize_fault(c)
            if alt.canonical != "desconhecido":
                return alt.canonical
    return info.canonical


# ─── responder_evento ─────────────────────────────────────────────────────

def responder_evento(event: dict, origem: str = "api") -> dict:
    """Processa evento de sensor: pipeline → semáforo → banco → report.

    Retorna:
      {**report, semaforo, id_salvo}
    """
    from .pipeline import process_event
    from . import db

    report = process_event(event)
    semaforo = _classificar_semaforo(report, event)

    id_salvo = db.salvar_evento(report, event, origem=origem, semaforo=semaforo)

    return {**report, "semaforo": semaforo, "id_salvo": id_salvo}


# ─── responder_duvida ─────────────────────────────────────────────────────

_SYSTEM_CHAT = (
    "Você é um assistente técnico de manutenção industrial. "
    "Responda em português, de forma natural e conversacional, como um especialista. "
    "Use APENAS as informações do CONTEXTO fornecido (banco de eventos + documentação). "
    "Não invente dados. Se a informação não estiver no contexto, diga claramente que não encontrou. "
    "Seja conciso e direto."
)


def _ctx_banco(texto: str) -> tuple[str, dict]:
    """Monta bloco de contexto a partir do banco de dados."""
    from . import db
    geral = db.resumo_geral()
    resumo = db.resumo_semaforo()
    abertos = resumo.get("abertos", [])
    pendencias = db.listar_pendencias(limit=10)
    todos = db.listar_eventos(limit=500)

    criticos = [e for e in abertos if e["semaforo"] == "🔴"]
    atencao = [e for e in abertos if e["semaforo"] == "🟡"]

    linhas = [
        f"TOTAIS: {geral.get('eventos', 0)} eventos analisados | "
        f"{geral.get('pendencias', 0)} pendências | "
        f"{geral.get('consultas', 0)} consultas realizadas",
        f"SEMÁFORO ATUAL: {resumo['vermelho']} críticos | "
        f"{resumo['amarelo']} em atenção | {resumo['verde']} OK",
    ]

    # lista todos os eventos com defeito e status
    if todos:
        ev_lines = ", ".join(
            f"{e['defeito']} (#{e['id']} {e['semaforo']} {e['status']})"
            for e in todos[:20]
        )
        linhas.append(f"EVENTOS REGISTRADOS: {ev_lines}")

    if criticos:
        items = ", ".join(
            f"{e['defeito']} (id={e['id']}, {e['frequency_per_week']:.1f}/sem, "
            f"{'COM' if e['documented'] else 'SEM'} manual)"
            for e in criticos[:6]
        )
        linhas.append(f"DEFEITOS CRÍTICOS: {items}")
    if atencao:
        items = ", ".join(
            f"{e['defeito']} (id={e['id']})" for e in atencao[:6]
        )
        linhas.append(f"DEFEITOS EM ATENÇÃO: {items}")
    if not criticos and not atencao:
        linhas.append("Nenhum defeito crítico ou em atenção no momento.")
    if pendencias:
        items = ", ".join(
            f"{p['defeito']} (id={p['id']}, sem manual)" for p in pendencias[:5]
        )
        linhas.append(f"PENDÊNCIAS SEM MANUAL: {items}")

    # histórico do defeito mencionado no texto, se houver
    defeito_mencionado = _extrair_defeito_texto(texto)
    if defeito_mencionado != "desconhecido":
        hist = db.historico_defeito(defeito_mencionado)
        if hist:
            linhas.append(
                f"HISTÓRICO DE '{defeito_mencionado}': "
                f"{len(hist)} ocorrência(s), "
                f"última em {hist[-1]['ts'][:10]}"
            )

    return "\n".join(linhas), {
        "resumo": resumo,
        "pendencias": pendencias,
        "defeito": defeito_mencionado if defeito_mencionado != "desconhecido" else None,
    }


def _ctx_rag(texto: str) -> tuple[str, list[str]]:
    """Busca livre no índice RAG e retorna contexto + fontes."""
    from .rag import search_all
    hits = search_all(texto, top_k=4, min_score=0.05)
    if not hits:
        return "", []
    blocos = [f"[{doc}] {chunk[:450]}" for chunk, doc, _ in hits]
    fontes = list(dict.fromkeys(doc for _, doc, _ in hits))  # unique, ordered
    return "\nDOCUMENTAÇÃO TÉCNICA:\n" + "\n\n".join(blocos[:2]), fontes


def _fallback_estruturado(ctx: dict, rag_ctx: str) -> str:
    """Resposta estruturada quando LLM está offline."""
    resumo = ctx.get("resumo", {})
    pendencias = ctx.get("pendencias", [])
    abertos = resumo.get("abertos", [])
    criticos = [e for e in abertos if e["semaforo"] == "🔴"]
    atencao = [e for e in abertos if e["semaforo"] == "🟡"]

    linhas = [
        f"📊 {resumo.get('vermelho', 0)} críticos · "
        f"{resumo.get('amarelo', 0)} atenção · "
        f"{resumo.get('verde', 0)} OK"
    ]
    if criticos:
        linhas.append("\n🔴 Críticos:")
        for e in criticos[:5]:
            linhas.append(
                f"  • {e['defeito']} (#{e['id']}) — "
                f"{e['frequency_per_week']:.1f}/sem · "
                f"{'COM' if e['documented'] else 'SEM'} manual"
            )
    if atencao:
        linhas.append("\n🟡 Em atenção:")
        for e in atencao[:5]:
            linhas.append(f"  • {e['defeito']} (#{e['id']})")
    if pendencias:
        linhas.append(f"\n📋 {len(pendencias)} pendência(s) sem procedimento:")
        for p in pendencias[:5]:
            linhas.append(f"  • {p['defeito']} (#{p['id']})")
    if not criticos and not atencao and not pendencias:
        linhas.append("\n✅ Nenhuma manutenção pendente no momento.")
    if rag_ctx:
        linhas.append("\n" + rag_ctx[:400])
    return "\n".join(linhas)


def responder_duvida(texto: str, origem: str = "api") -> dict:
    """Responde pergunta livre em linguagem natural.

    Sempre busca banco + RAG. Se LLM disponível: gera resposta natural.
    Fallback: resposta estruturada do banco sem LLM.

    Retorna {resposta, contexto, fonte, sources}.
    """
    from .llm import llm_generate, LLMError
    from . import db

    banco_ctx, ctx_dict = _ctx_banco(texto)
    rag_ctx, fontes = _ctx_rag(texto)

    contexto_completo = banco_ctx + rag_ctx
    prompt = f"Contexto:\n{contexto_completo}\n\nPergunta: {texto}"

    try:
        resposta = llm_generate(prompt, system=_SYSTEM_CHAT)
        fonte = "LLM+banco+RAG" if fontes else "LLM+banco"
    except LLMError:
        resposta = _fallback_estruturado(ctx_dict, rag_ctx)
        fonte = "banco+RAG" if fontes else "banco"

    db.salvar_consulta(
        pergunta=texto,
        resposta=resposta,
        defeito=ctx_dict.get("defeito"),
        origem=origem,
    )

    return {
        "resposta": resposta,
        "contexto": ctx_dict,
        "fonte": fonte,
        "sources": fontes,
    }
