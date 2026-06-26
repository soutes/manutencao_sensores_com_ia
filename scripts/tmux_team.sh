#!/usr/bin/env bash
# Cria a sessao tmux do time de agentes: 6 panes, um por papel.
# Uso:  bash scripts/tmux_team.sh        (rode da raiz do projeto)
#       tmux attach -t fiesc             (para reconectar)
set -e

SESSION="fiesc"
DIR="${1:-$PWD}"

# papeis na ordem dos panes (0..5)
ROLES=("LEAD" "BACKEND" "UIUX" "FRONTEND" "QA" "REVIEWER")

tmux kill-session -t "$SESSION" 2>/dev/null || true
tmux new-session -d -s "$SESSION" -c "$DIR"

# cria 6 panes em grid
for _ in 1 2 3 4 5; do
  tmux split-window -t "$SESSION" -c "$DIR"
  tmux select-layout -t "$SESSION" tiled >/dev/null
done

# borda com titulo do papel + label inicial em cada pane
tmux set -t "$SESSION" pane-border-status top
tmux set -t "$SESSION" pane-border-format " #{pane_index} #{@role} "
for i in 0 1 2 3 4 5; do
  tmux set -p -t "$SESSION.$i" @role "${ROLES[$i]}"
  tmux send-keys -t "$SESSION.$i" \
    "clear; echo '=== PANE $i : ${ROLES[$i]} ==='; echo 'rode: claude  -> cole o prompt do papel (prompt_execucao.md)'" C-m
done

tmux select-pane -t "$SESSION.0"
echo "Sessao '$SESSION' criada com 6 panes: ${ROLES[*]}"
echo "Conecte com:  tmux attach -t $SESSION"
