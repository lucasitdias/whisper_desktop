# Implementação completa do Whisper Transcriber Desktop

## Resumo

- Aplicação desktop em Python 3.11 com PySide6, OpenAI Whisper `turbo`, idioma `pt` e processamento assíncrono por `QThread`.
- Dependências gerenciadas por `pyproject.toml`, `.python-version` e `uv.lock`.
- Ambiente local com `openai-whisper==20250625` e PyTorch 2.12.1/CUDA 13.0, compatível com a RTX 5070 e com fallback para CPU.
- Repositório privado `lucasitdias/whisper_desktop`, com `README.md` na raiz e especificações em
  `docs/`.

Referências: [Whisper](https://github.com/openai/whisper), [PyTorch](https://pytorch.org/get-started/previous-versions/) e [uv](https://docs.astral.sh/uv/guides/projects/).

## Arquitetura e interfaces

- Estrutura modular em `app/core`, `app/ui`, `assets`, `tests` e `.github/workflows`.
- `main.py` inicializa o Qt, tema, ícone e expõe `--self-check` e `--self-check-output`.
- `FFmpegFinder` resolve recursos PyInstaller, checkout, `PATH` e cache verificado, nessa ordem.
- Windows e Linux x86_64 usam FFmpeg estático da BtbN, com URL imutável e SHA-256 fixado.
- `TranscriberWorker(QThread)` detecta CUDA/CPU, usa FP16/FP32, emite sinais de status, progresso, segmentos, conclusão e falha, e faz fallback por falta de VRAM.
- `MarkdownExporter` oferece renderização pura e escrita UTF-8 atômica, sem expor caminhos absolutos.

## Interface e experiência

- Seleção única de `.mp3` ou `.m4a` por diálogo ou drag-and-drop, sem distinção entre maiúsculas e minúsculas.
- Tema escuro, estados, botões, barra de progresso e scrollbars de acordo com o design system.
- Dispositivo, arquivo, progresso e log exibidos em pt-BR.
- Processamento não bloqueante e proteção contra fechamento enquanto a thread estiver ativa.
- Abas “Markdown” editável e “Visualização” sincronizada.
- Ações “Copiar Markdown” e “Salvar como”, sem salvamento automático.

## Build, instalador e entrega

- `uv run build.py` gera o executável portátil `--onefile` da plataforma atual.
- `uv run build.py --msix` gera, no Windows, o pacote CUDA destinado à Microsoft Store.
- `uv run build.py --installer` gera o instalador Inno Setup CUDA; `--installer-cpu` gera a variante
  CPU publicada como download offline.
- Todos os builds usam `--windowed`, ícone próprio, FFmpeg incorporado, `--collect-all whisper` e `--collect-all torch`.
- Builds por tag `v*` usam PyTorch CPU e publicam o Linux x86-64, o instalador Windows offline,
  checksums separados, um atalho para a Microsoft Store e os arquivos-fonte do GitHub.
- A versão Windows pública é validada, assinada e distribuída pela
  [Microsoft Store](https://apps.microsoft.com/detail/9PHWS6MM59BG).
- O modelo `turbo` não é incorporado e é baixado na primeira transcrição.
- `.venv`, modelos, áudios, FFmpeg baixado, `build/`, `dist/` e caches permanecem ignorados; `uv.lock` é versionado.
- Commits e mensagens de entrega usam português do Brasil; não há implantação Vercel para esta aplicação desktop.

Referências: [FFmpeg](https://ffmpeg.org/download.html), [BtbN FFmpeg Builds](https://github.com/BtbN/FFmpeg-Builds), [PyInstaller](https://pyinstaller.org/en/stable/usage.html) e [Inno Setup](https://jrsoftware.org/isinfo.php).

## Testes e critérios de aceite

- Testes do FFmpeg cobrem precedência, checksum, extração segura, cache, `PATH` e plataforma.
- Testes do exportador cobrem Unicode, metadados, duração, timestamps, vazio e escrita atômica.
- Testes do worker cobrem CUDA, CPU, falta de VRAM, progresso, segmentos, download e sinais Qt.
- Testes de GUI cobrem seleção, drag-and-drop, estados, thread, abas, edição, cópia, salvamento e mensagens.
- O CI não baixa o modelo; a inferência real é uma aceitação local opt-in com áudio do usuário.
- O aceite inclui GUI responsiva, transcrição MP3/M4A, CUDA na RTX 5070, fallback CPU e exportação Markdown.

Premissas: Windows/Linux x86_64; `README.md` na raiz; especificações e avisos de terceiros em
`docs/`; tags de release acionadas manualmente; repositório privado sem licença própria até decisão
posterior.
