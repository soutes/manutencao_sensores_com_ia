# Anomalias na coluna `fault` — docs/banner.csv

Revisão: 2026-06-27. Total de classes únicas: ~140. Anomalias identificadas abaixo.

---

## Categoria 1 — Estado de máquina, NÃO é falha

| valor | contagem | motivo |
|---|---|---|
| `motor_desligado` | 397 | Motor desligado (RPM=0). Estado operacional, não falha. Vibração inativa → contamina treino como classe espúria. |
| `motor_desligado_novo` | 50 | Idem, variante "novo". Mesmo problema. |
| `mortor_desligado_novo` | 50 | **Typo** de `motor_desligado_novo` ("mortor"). Dado duplicado com label errado. |
| `acelerando` | 7 | Estado transiente de rampa de velocidade. Não é falha estável. 7 amostras — lote incompleto. |

---

## Categoria 2 — Labels de teste / placeholder

| valor | contagem | motivo |
|---|---|---|
| `teste` | 97 | Label genérico sem semântica de falha. Provavelmente coleta experimental não rotulada. |
| `new_teste` | 2 | Idem — 2 amostras, resíduo de coleta. |
| `new_tes` | 2 | Label truncado/incompleto ("new_tes…"). Escrita interrompida, dado corrompido. |
| `new_baseline` | 69 | "baseline" = linha de referência, não classe de falha. Deveria ser `normal` ou separado do dataset de treino. |

---

## Categoria 3 — Typos que criam labels inválidos

Classes que referenciam falhas reais mas com grafia errada → o modelo aprende classes fantasma separadas da classe correta.

| valor | contagem | motivo |
|---|---|---|
| `desabalanceado_3` | 50 | Typo: `desabalanceado` → deveria ser `desbalanceado`. |
| `desbanlanceado_carga_3_2` | 50 | Typo: `desbanlanceado` → `desbalanceado`. |
| `normla_carga_3_3` | 50 | Typo: `normla` → `normal`. |
| `ddesbalanceado_adxl_0` | 50 | Typo: `d` duplicado no prefixo (`ddesbalanceado`). |
| `cockecocked_adxl_0` | 50 | Typo: `cockecocked` → `cocked`. Prefixo repetido. |
| `new_desabanceado_1` | 50 | Typo: `desabanceado` → `desbalanceado` (troca de `l` por nada). |
| `dedesbalanceado_adxl_1` | 21 | Typo: prefixo `de` duplicado → `dedesbalanceado`. |

---

## Categoria 4 — Sufixo "teste" em labels técnicos (borderline)

Classe tecnicamente válida mas marcada como dado de teste — risco de contaminação se incluída em treino/val.

| valor | contagem | motivo |
|---|---|---|
| `rolamento_outer_novo_teste` | 50 | Base `rolamento_outer_novo` é válida; sufixo `_teste` indica coleta experimental separada. |
| `normal_novo_teste` | 100 | Base `normal_novo` válida; sufixo `_teste` idem. |

---

## Resumo

| Categoria | Qtd de classes | Total de amostras afetadas |
|---|---|---|
| Estado de máquina (não falha) | 4 | 504 |
| Placeholder / teste | 4 | 170 |
| Typos (label fantasma) | 7 | 321 |
| Borderline (sufixo teste) | 2 | 150 |
| **TOTAL anomalias** | **17** | **1.145** |

Amostras limpas estimadas: ~168.855 de ~170.000 (~99,3% válidas).

**Ação recomendada:**
- Categoria 1: Remover `motor_desligado*` e `acelerando` do dataset de classificação de falhas.
- Categoria 2: Remover todos.
- Categoria 3: Corrigir typos → mapear para a classe correta antes do treino.
- Categoria 4: Decidir se dados `_teste` entram em validação somente (não treino).
