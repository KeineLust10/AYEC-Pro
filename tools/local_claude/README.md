# Local Claude on Windows

Bu klasor, `claude-code-local` reposunun Windows icin pratik uyarlamasidir.

Mimari:

- `Claude Code` yerelde calisir.
- `anthropic_proxy.py`, Claude Code'un Anthropic isteklerini Ollama'ya cevirir.
- `Ollama`, yerel modeli calistirir.

Hazir varsayilanlar:

- Claude Code: `C:\Users\yedek\AppData\Roaming\npm\claude.cmd`
- Ollama: `C:\Users\yedek\AppData\Local\Programs\Ollama\ollama.exe`
- Proxy portu: `4000`
- Ollama portu: `11434`
- Varsayilan model: `qwen3-coder:30b`

Kullanim:

Bu repo klasorunde acmak icin:

```bat
C:\Users\yedek\Desktop\yapay zeka\AYEC Pro\tools\local_claude\claude-local.cmd
```

Kisa yol:

```bat
C:\Users\yedek\Desktop\yapay zeka\AYEC Pro\Claude Local Windows.cmd
```

Baska bir klasoru dosya yoluyla acmak icin:

```bat
C:\Users\yedek\Desktop\yapay zeka\AYEC Pro\tools\local_claude\claude-local.cmd "C:\path\to\project"
```

Baska model secmek icin:

```bat
C:\Users\yedek\Desktop\yapay zeka\AYEC Pro\tools\local_claude\claude-local.cmd "C:\path\to\project" "deepseek-r1:8b"
```

Mevcut modeller:

- `qwen3-coder:30b`
- `qwen3-coder:480b-cloud`
- `deepseek-r1:8b`

Notlar:

- `qwen3-coder:30b` daha guclu ama daha agir.
- `deepseek-r1:8b` daha hafif ve daha kolay baslar.
- Ilk acilis biraz surebilir; Ollama ve proxy ayaga kalkar, sonra `claude` baslatilir.
