# AYEC Orchestrator Operations

## Hızlı Başlangıç

1. `.env.example` dosyasını kopyalayıp `.env` oluşturun.
2. Gerekli env değişkenlerini doldurun.
3. Dashboard başlatın:

```powershell
.\.venv_active\Scripts\python.exe -m agent_orchestrator.run_dashboard
```

4. Smoke run çalıştırın:

```powershell
.\.venv_active\Scripts\python.exe -m agent_orchestrator.smoke_run
```

5. Webhook server başlatın:

```powershell
.\.venv_active\Scripts\python.exe -m uvicorn webhook_server:app --port 8000
```

6. Tüm servisleri birlikte başlatın:

```powershell
.\.venv_active\Scripts\python.exe -m agent_orchestrator.supervisor
```

7. Remediation worker planını çalıştırın:

```powershell
.\.venv_active\Scripts\python.exe -m agent_orchestrator.remediation_worker
```

8. Remediation supervisor akışını çalıştırın:

```powershell
.\.venv_active\Scripts\python.exe -m agent_orchestrator.remediation_supervisor --run-plan remediation_v1
```

9. Entegrasyon önkontrolünü çalıştırın:

```powershell
.\.venv_active\Scripts\python.exe -m agent_orchestrator.preflight_check
```

## Dashboard

- URL: `http://127.0.0.1:8010/`
- JSON uçları:
  - `/summary`
  - `/metrics`
  - `/memory`
  - `/graph`
  - `/runs/recent`

## Gerçek Entegrasyon İçin Gerekli

- GitHub PR ve merge için:
  - `GITHUB_TOKEN`
  - `GITHUB_REPO`
- Semantic memory için:
  - `OPENAI_API_KEY`
- Neo4j graph sync için:
  - `NEO4J_URI`
  - `NEO4J_USERNAME`
  - `NEO4J_PASSWORD`
- Dış ajan köprüsü için:
  - `AGENT_EXECUTOR_COMMAND`
  - `CODEX_EXECUTOR_INVOKE`

## Notlar

- `executor.py` varsayılan olarak mock veya dış ajan köprüsü olarak çalışır.
- `AGENT_EXECUTOR_COMMAND` tanımlanırsa prompt bu komuta stdin ile gönderilir.
- Varsayılan önerilen köprü:

```powershell
$env:AGENT_EXECUTOR_COMMAND='powershell -ExecutionPolicy Bypass -File agent_orchestrator\run_real_executor.ps1'
```

- Gerçek Codex/CLI çağrısı wrapper içinde şu env ile verilir:

```powershell
$env:CODEX_EXECUTOR_INVOKE='codex <gercek-komut> {prompt_file}'
```

- `{prompt_file}` placeholder'ı wrapper tarafından gerçek geçici prompt dosyasıyla değiştirilir.
- `ENABLE_AUTO_MERGE=1` yapmadan auto merge denemesi başlamaz.
- `GITHUB_PR_DRAFT=0` olmadan PR hazır yerine draft açılabilir.
- Dashboard koruması istenirse `DASHBOARD_TOKEN` ayarlayın.
- Remediation akışı durum dosyaları:
  - `agent_orchestrator/state/remediation_plan.json`
  - `agent_orchestrator/state/remediation_heartbeat.json`
  - `agent_orchestrator/state/remediation_run.log`
- Remediation bitiş raporu:
  - `tasks/REMEDIATION_EXECUTION_REPORT.md`
- Gerçek onarım yürütmesi için `AGENT_EXECUTOR_COMMAND` tanımlı olmalıdır; aksi halde remediation adımı `blocked` olur.
