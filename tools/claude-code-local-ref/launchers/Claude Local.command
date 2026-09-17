#!/bin/bash
# Claude Code — Local AI (runs on your Mac, no cloud)
# Double-click to launch
# MLX Native Server — direct Anthropic API, no proxy needed
#
# Override the model with: MLX_MODEL=mlx-community/<model-id>

CLAUDE_BIN="${CLAUDE_BIN:-$HOME/.local/bin/claude}"
MLX_SERVER="$HOME/.local/mlx-native-server/server.py"
MLX_PYTHON="$HOME/.local/mlx-server/bin/python3"
MODEL_NAME="${MLX_MODEL_LABEL:-Gemma 4 31B}"

# Start MLX server if not running
if ! lsof -i :4000 >/dev/null 2>&1; then
  "$MLX_PYTHON" "$MLX_SERVER" >/tmp/mlx-server.log 2>&1 &
  echo "  Loading $MODEL_NAME on MLX..."
  while ! curl -s http://localhost:4000/health 2>/dev/null | grep -q "ok"; do
    sleep 2
  done
fi

clear
echo ""
echo "  → Claude Code with LOCAL AI ($MODEL_NAME)"
echo "  → MLX Native: zero proxy, zero cloud, zero API fees"
echo "  → Running 100% on your Apple Silicon GPU"
echo ""

# --bare forces API-key auth (blocks OAuth/Claude Max).
# CLAUDE.md and MCP config are added back explicitly so personal config still loads.
ANTHROPIC_BASE_URL=http://localhost:4000 \
ANTHROPIC_API_KEY=sk-local \
exec "$CLAUDE_BIN" --model claude-sonnet-4-6 \
  --permission-mode auto \
  --bare \
  --append-system-prompt-file "$HOME/.claude/CLAUDE.md" \
  --mcp-config "$HOME/.claude.json"
