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
    _status_kw = ("status", "parque", "crítico", "critico",
                  "situação", "situacao", "manutencao aberta", "manutenção aberta",
                  "pontos criticos", "pontos críticos")
    _pend_kw = ("pendência", "pendencia", "pendente", "pendências",
                "pendencias", "em aberto", "abertas")
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

def responder_duvida(texto: str, origem: str = "api") -> dict:
    """Responde pergunta livre combinando banco + RAG conforme intenção detectada.

    Retorna:
      {resposta: str, contexto: dict, fonte: str}
    """
    from . import db
    from .rag import prescribe

    intencao = _detectar_intencao(texto)
    resposta: str
    contexto: dict
    fonte: str

    if intencao == "status_parque":
        resumo = db.resumo_semaforo()
        abertos = resumo.get("abertos", [])
        criticos = [e for e in abertos if e["semaforo"] == "🔴"]
        atencao = [e for e in abertos if e["semaforo"] == "🟡"]

        linhas = [
            f"📊 Status do parque de máquinas:",
            f"  🔴 Críticos: {resumo['vermelho']}",
            f"  🟡 Atenção:  {resumo['amarelo']}",
            f"  🟢 OK:       {resumo['verde']}",
        ]
        if criticos:
            nomes = ", ".join(e["defeito"] for e in criticos[:5])
            linhas.append(f"\n🚨 Pontos críticos: {nomes}")
        if atencao:
            nomes = ", ".join(e["defeito"] for e in atencao[:5])
            linhas.append(f"⚠️  Em atenção: {nomes}")
        if not criticos and not atencao:
            linhas.append("\n✅ Nenhuma manutenção aberta no momento.")

        resposta = "\n".join(linhas)
        contexto = resumo
        fonte = "banco"

    elif intencao == "pendencias":
        pendencias = db.listar_pendencias(limit=20)
        if pendencias:
            linhas = [f"📋 {len(pendencias)} pendência(s):"]
            for p in pendencias:
                sem = p.get("semaforo", "🔴")
                freq = p.get("frequency_per_week", 0)
                doc_flag = "" if p.get("documented") else " ⚠️sem manual"
                linhas.append(
                    f"  {sem} [{p['id']}] {p['defeito']}"
                    f" – {freq:.1f}/sem{doc_flag}"
                )
            resposta = "\n".join(linhas)
        else:
            resposta = "✅ Nenhuma pendência encontrada."
        contexto = {"pendencias": pendencias}
        fonte = "banco"

    elif intencao == "historico":
        defeito = _extrair_defeito_texto(texto)
        historico = db.historico_defeito(defeito)
        if historico:
            linhas = [f"📈 Histórico de '{defeito}': {len(historico)} ocorrência(s)"]
            for h in historico[:10]:
                sem = h.get("semaforo", "")
                linhas.append(f"  {sem} #{h['event_id']} – {h['status']} em {h['ts'][:10]}")
            resposta = "\n".join(linhas)
        else:
            resposta = f"Nenhum histórico encontrado para '{defeito}'."
        contexto = {"defeito": defeito, "historico": historico}
        fonte = "banco"

    else:  # pergunta tecnica sobre defeito
        defeito = _extrair_defeito_texto(texto)
        presc = prescribe(defeito, question=texto)
        resposta = presc.instructions
        if presc.sources:
            resposta += f"\n\n📄 Fonte: {', '.join(presc.sources)}"
        contexto = {
            "defeito": presc.canonical_fault,
            "documented": presc.documented,
            "sources": presc.sources,
        }
        fonte = "RAG" if presc.documented else "banco+RAG"

    db.salvar_consulta(pergunta=texto, resposta=resposta,
                       defeito=contexto.get("defeito"), origem=origem)

    return {"resposta": resposta, "contexto": contexto, "fonte": fonte}
