# Implementação completa do Whisper Transcriber Desktop

## Status da entrega

A implementação prevista foi concluída e publicada na
[release v0.2.1](https://github.com/lucasitdias/whisper_desktop/releases/tag/v0.2.1). O código da
release corresponde ao commit `7fe798c622e8a47c029edf529866268be9934ab8` na `main`.

## Funcionalidades entregues

- Python 3.11, PySide6 e tema escuro High-DPI;
- OpenAI Whisper `turbo`, idioma `pt` e tarefa `transcribe`;
- worker `QThread` com status, progresso, segmentos, conclusão, falha e cancelamento;
- MP3/M4A por seletor ou drag-and-drop;
- cancelamento cooperativo sem `terminate()` e sem resultado parcial;
- detecção de NVIDIA CUDA, AMD ROCm, Intel XPU e CPU conforme o runtime PyTorch instalado;
- exibição do dispositivo real e fallback por indisponibilidade ou falta de memória;
- FFmpeg 8.1.2 estático, URL imutável, SHA-256 e extração restrita;
- `beam_size=5`, `best_of=5`, contexto anterior e timestamps por palavra;
- métricas de cobertura, última fala e confiança estimada;
- Markdown editável com prévia sincronizada, cópia e salvamento atômico;
- autodiagnóstico por console ou JSON;
- instaladores Windows NVIDIA/CPU, portáteis Windows/Linux e DEB Linux;
- MSIX com identidade reservada para submissão à Microsoft Store;
- CI Windows/Linux e publicação automática por tag.

## Dependências e versões

| Componente | Versão/perfil |
| --- | --- |
| Python | `>=3.11,<3.12` |
| OpenAI Whisper | `20250625` |
| PyTorch | `2.12.1` |
| Ambiente padrão | CUDA 13.0 |
| PySide6 | `>=6.8,<7` |
| PyInstaller | `>=6.16,<7` |
| FFmpeg | `8.1.2-34-g9b6c8969e0` |
| Gerenciador | `uv` + `uv.lock` |

CUDA, ROCm, XPU e CPU são distribuições separadas do PyTorch. A release v0.2.1 publica NVIDIA
CUDA 13 e CPU; ROCm/XPU permanecem suportados pelo código quando o ambiente é construído com a
wheel correspondente.

## Artefatos publicados

| Arquivo | Bytes | SHA-256 |
| --- | ---: | --- |
| `WhisperTranscriber-Setup-Windows-x64.exe` | 1.798.357.601 | `88d2739535156d679f36afdae5a2187b671ddc76416080c9b62d20dd9124fbbd` |
| `WhisperTranscriber-Setup-Windows-x64-CPU.exe` | 220.426.772 | `6b00c4d26a8d0686511f51090fb43e36074a327ebd039ca10f982935ae83df96` |
| `WhisperTranscriber-Windows-x64.exe` | 317.271.727 | `4824f87090e76b9f6e1800f005224ab44b80db91cd78f5c18807e4a5b8b7a0f5` |
| `WhisperTranscriber-Setup-Linux-x64.deb` | 612.959.506 | `9161ae8e30a9da0fffe62876d2a7560697ed8891f9de8c902c8cf6f85061e2db` |
| `WhisperTranscriber-Linux-x64` | 630.137.840 | `5b49c278a2663d46826afb7a8ad21ff2fb135fc251c4e1a4c4fc32705534f0ed` |

Também foram publicados três manifestos SHA-256, atalho da Microsoft Store e arquivos-fonte
ZIP/TAR.GZ.

## Validação concluída

- Ruff aprovado;
- 55 testes aprovados;
- autodiagnóstico de fonte e empacotados aprovado;
- instaladores NVIDIA CUDA e CPU instalados, executados e removidos em runners Windows limpos;
- DEB instalado, executado e removido em runner Linux limpo;
- portáteis Windows/Linux autoverificados;
- nove anexos baixados depois da publicação;
- cinco hashes grandes recalculados e comparados com os manifestos da release;
- workflow final: <https://github.com/lucasitdias/whisper_desktop/actions/runs/32487388099>.

## Decisões de distribuição

- Aplicação, runtime PyTorch, Whisper e FFmpeg ficam nos pacotes offline.
- O modelo `turbo` é baixado no primeiro uso e armazenado no cache da aplicação.
- A variante NVIDIA é o download principal no Windows; a variante CPU é a alternativa universal.
- Linux v0.2.1 usa CPU para maximizar compatibilidade entre máquinas Debian/Ubuntu x86-64.
- O MSIX não é oferecido diretamente: ele é enviado ao Partner Center e só deve ser adquirido
  depois que a Microsoft validar e assinar o pacote.
- Instaladores GitHub sem Authenticode podem ser bloqueados pelo Smart App Control. A proteção do
  Windows não deve ser desativada.

## Limites assumidos

- sem diarização, tradução, microfone ou lote;
- somente MP3/M4A e um arquivo por vez;
- Windows/Linux x86-64; sem macOS/ARM;
- nenhum ASR garante fidelidade literal para todo áudio;
- publicação/aquisição na Store depende do processo externo da Microsoft.

## Referências

- [OpenAI Whisper](https://github.com/openai/whisper)
- [PyTorch](https://pytorch.org/get-started/previous-versions/)
- [uv](https://docs.astral.sh/uv/guides/projects/)
- [FFmpeg](https://ffmpeg.org/download.html)
- [BtbN FFmpeg Builds](https://github.com/BtbN/FFmpeg-Builds)
- [PyInstaller](https://pyinstaller.org/en/stable/usage.html)
- [Inno Setup](https://jrsoftware.org/isinfo.php)
