# Memory System

## Recall (Gecmis Ogrenimleri Cek)

```bash
cd ~/.claude && PYTHONPATH=scripts python3 scripts/core/recall_learnings.py --query "arama terimi"
```

### Ne Zaman
- Daha once yapilmis bir ise baslarken
- Hata veya zor durumda
- Mimari karar verirken

### Secenekler
- `--k 10` daha fazla sonuc
- `--vector-only` pure vector arama
- `--text-only` hizli text arama

### Skorlar
- Hybrid RRF: 0.01-0.03 normal (dusuk = iyi)
- Pure vector: 0.4-0.6 cosine similarity

## Store (Ogrenim Kaydet)

```bash
cd ~/.claude && PYTHONPATH=scripts python3 scripts/core/store_learning.py \
  --session-id "<id>" --content "<ne ogrendin>" \
  --context "<neyle ilgili>" --tags "tag1,tag2" --confidence high|medium|low
```

Tipler: ARCHITECTURAL_DECISION, WORKING_SOLUTION, CODEBASE_PATTERN, FAILED_APPROACH, ERROR_FIX, USER_PREFERENCE, OPEN_THREAD

## Ne Zaman Kaydet
- Zor sorun cozunce
- Mimari karar alinca
- Codebase pattern kesfedince
- Calismayan bir sey bulunca

## Agent'lar ve Memory

- Agent'lar ise baslamadan once memory'ye baksin
- MEMORY MATCH bulunursa kullaniciya kisa bahset
- Cok alakaliysa detay goster, az alakaliysa atla
- Her memory match'i soyleme, gereksiz gurultu yapma

## Backend

| Backend | Durum |
|---------|-------|
| PostgreSQL (Docker) | 12 ogrenim, mock embeddings |
| SQLite fallback | Bos olabilir |

Scripts: `~/.claude/scripts/core/` (recall_learnings.py, store_learning.py)
Docker: `~/.claude/docker/opc/docker-compose.yml`
Env: `~/.claude/.env` (CONTINUOUS_CLAUDE_DB_URL, EMBEDDING_PROVIDER)
