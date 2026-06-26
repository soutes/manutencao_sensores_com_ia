# ADR-003 — Banco Trocável: SQLite ↔ PostgreSQL/Supabase via SQLAlchemy

**Status:** Aceita
**Data:** 2026-06-26
**Autores:** Arquiteto

---

## Contexto

O sistema precisa persistir três entidades: eventos analisados, consultas Q&A e
pendências de documentação. Em produção on-prem, o banco deve funcionar sem servidor
adicional. Na demo cloud (HF Spaces), precisa de persistência entre sessões (HF Spaces
reinicia contêiner — SQLite seria perdido).

---

## Decisão

Usar **SQLAlchemy Core** com `DATABASE_URL` como única variável de configuração:

```
DATABASE_URL=sqlite:///./manutencao.db       → on-prem / desenvolvimento
DATABASE_URL=postgresql://user:pw@host/db   → Supabase / cloud
```

Modelos definidos com `sqlalchemy.orm` — mesmos modelos funcionam em ambos os bancos.
Migrations gerenciadas manualmente (projeto pequeno, Alembic seria overkill).

---

## Alternativas Consideradas

| Alternativa | Por que rejeitada |
|---|---|
| SQLite hardcoded | Não funciona para demo cloud (reinicialização de contêiner apaga dados) |
| MongoDB | Sem relações; driver adicional; overkill para 3 tabelas simples |
| Redis | Só cache/fila; sem persistência relacional estruturada |
| Alembic (migrations) | Complexidade desnecessária para 3 tabelas sem schema em evolução |
| Supabase SDK direto | Acoplamento ao provedor; perderia flexibilidade SQLite |

---

## Consequências

**Positivas:**
- Troca de banco = trocar string de conexão; zero código alterado
- SQLite = zero infraestrutura adicional para on-prem
- PostgreSQL (Supabase) = persistência entre sessões na demo cloud
- Padrão SQLAlchemy é conhecimento transferível e defensável

**Negativas / Trade-offs:**
- SQLite tem limitações de concorrência (writes serializados)
  — aceitável para este caso de uso (baixo volume de escrita)
- Schema deve ser criado manualmente na primeira execução (`db.init_db()`)
  — documentado no README
