# Memorando de Preparação do Ambiente

> Autor e desenvolvedor: **Lucas Dias — Estudante de Ciência da Computação**.

> **Versão Pro v0.3.0:** a implementação foi aceita localmente. Para instalar o bundle de
> homologação, extraia integralmente
> `WhisperTranscriber-Setup-Windows-x64-Offline.zip` (CUDA) ou
> `WhisperTranscriber-Setup-Windows-x64-CPU-Offline.zip` (CPU) e mantenha o `.exe` ao lado de todas
> as fatias `.bin`. Em Linux, use `WhisperTranscriber-Setup-Linux-x64.deb` ou extraia
> `WhisperTranscriber-Linux-x64.tar.gz`. Esses quatro pacotes já incluem FFmpeg, `medium` e `turbo`;
> não exigem internet para esses modelos. O `large-v3` é baixado somente após ação explícita e
> depois funciona offline. A versão pública é `0.3.0` e o MSIX de homologação
> usa somente o contador técnico `1.3.4.0`.

## 1. Identificação

- **Projeto:** Whisper Transcriber Desktop
- **Versão:** v0.3.0
- **Autor:** Lucas Dias — Estudante de Ciência da Computação
- **Alvos:** Windows 10/11 x64 e Debian/Ubuntu x86-64
- **Python de desenvolvimento:** 3.11
- **Gerenciador:** `uv`

## 2. Instalação por pacote pronto

### 2.1 Windows com GPU NVIDIA

1. Na [release v0.3.0](https://github.com/lucasitdias/whisper_desktop/releases/tag/v0.3.0), baixe
   `WhisperTranscriber-Setup-Windows-x64.exe` e todas as partes CUDA `.bin`.
2. Confira `SHA256SUMS-Windows-NVIDIA-CUDA.txt`.
3. Execute o instalador por usuário.
4. Abra pelo menu **Whisper Transcriber Desktop**.
5. Confirme no cabeçalho se a GPU real foi identificada.

Esse pacote inclui PyTorch CUDA 13. Se CUDA não estiver disponível, o programa continua em CPU.
O CUDA Toolkit do sistema não é necessário; o driver NVIDIA compatível continua obrigatório.

### 2.2 Windows CPU

Use `WhisperTranscriber-Setup-Windows-x64-CPU.exe` com todas as partes CPU `.bin` para instalação
tradicional ou reconstrua `WhisperTranscriber-Windows-x64.zip` a partir das partes numeradas. Confira
`SHA256SUMS-Windows-CPU.txt`.

Os executáveis diretos ainda não possuem Authenticode. O Smart App Control pode bloquear um hash
sem assinatura/reputação. Não desative a proteção do Windows; use a Microsoft Store quando a
aquisição estiver liberada para essa máquina.

### 2.3 Debian/Ubuntu x86-64

Instalação recomendada, incluindo dependências declaradas pelo pacote:

```bash
sudo apt install ./WhisperTranscriber-Setup-Linux-x64.deb
whisper-transcriber --self-check
whisper-transcriber
```

Remoção:

```bash
sudo apt remove whisper-transcriber-desktop
```

Portátil reconstruído:

```bash
tar -xzf WhisperTranscriber-Linux-x64.tar.gz
chmod +x WhisperTranscriber/WhisperTranscriber
./WhisperTranscriber/WhisperTranscriber --self-check
./WhisperTranscriber/WhisperTranscriber
```

Confira `SHA256SUMS-Linux.txt` antes de executar.

## 3. Pré-requisitos para desenvolvimento

- 16 GB de RAM recomendados;
- aproximadamente 15 GB livres para ambiente, caches e builds;
- Git 2.30+;
- Python 3.11 gerenciado pelo `uv`;
- em Windows CUDA, driver NVIDIA atualizado e GPU com VRAM suficiente;
- Inno Setup 6/7 para instaladores Windows;
- Windows SDK/MakeAppx para MSIX;
- ferramentas Debian (`dpkg-deb`) para gerar DEB.

## 4. Instalar o `uv`

Windows:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Reabra o terminal e execute `uv --version`.

## 5. Ambiente padrão CUDA

O `pyproject.toml` associa `torch==2.12.1` ao índice CUDA 13:

```powershell
git clone https://github.com/lucasitdias/whisper_desktop.git
cd whisper_desktop
uv python install 3.11
uv sync --frozen
uv run main.py --self-check
uv run main.py
```

Validação CUDA:

```powershell
uv run python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

## 6. Ambiente CPU reproduzível

O CI evita dependências CUDA ao construir os pacotes CPU:

```powershell
uv venv --python 3.11 .venv-cpu
uv pip install --python .venv-cpu torch==2.12.1 --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .venv-cpu -r requirements/cpu.txt
.venv-cpu\Scripts\python.exe main.py --self-check
```

No Linux, substitua o último comando por `.venv-cpu/bin/python main.py --self-check`.

## 7. FFmpeg e modelo

FFmpeg fixado:

- versão `8.1.2-34-g9b6c8969e0`;
- release `autobuild-2026-07-31-14-10`;
- variante estática LGPL da BtbN;
- SHA-256 verificado antes da extração.

Preparação manual:

```powershell
uv run build.py --prepare-ffmpeg
```

Os modelos `medium` e `turbo` são incorporados e não usam rede. `tiny`, `base`, `small` e
`large-v3` são baixados somente após ação explícita:

- Windows: `%LOCALAPPDATA%\WhisperTranscriber\models`;
- Linux: `${XDG_CACHE_HOME:-~/.cache}/WhisperTranscriber/models`.

O autodiagnóstico não baixa o modelo.

## 8. Qualidade

```powershell
uv run ruff check .
uv run python -m pytest
uv run main.py --self-check
git diff --check
```

Resultado de referência da v0.3.0 final: 131 testes aprovados.

## 9. Builds

```powershell
# Portátil da plataforma atual
uv run build.py

# Windows NVIDIA CUDA 13
uv run build.py --installer

# Windows CPU (execute em ambiente Torch CPU)
uv run build.py --installer-cpu

# MSIX para Partner Center
uv run build.py --msix

# Reempacotar diretório existente
uv run build.py --installer-only
uv run build.py --msix-only
```

Saídas principais:

- `dist/installer/WhisperTranscriber-Setup-Windows-x64.exe`;
- `dist/installer/WhisperTranscriber-Setup-Windows-x64-CPU.exe`;
- `dist/WhisperTranscriber-Windows-x64.zip` ou `dist/WhisperTranscriber-Linux-x64.tar.gz`;
- `dist/store/WhisperTranscriber-Desktop-<versao>-Windows-x64.msix`.

Cada build incorpora exatamente o runtime PyTorch existente no ambiente. Uma wheel CUDA não usa
GPU AMD/Intel; ROCm e XPU requerem ambientes próprios.

## 10. Verificação de checksum

PowerShell:

```powershell
Get-FileHash .\WhisperTranscriber-Setup-Windows-x64.exe -Algorithm SHA256
Get-Content .\SHA256SUMS-Windows-NVIDIA-CUDA.txt
```

Linux:

```bash
sha256sum -c SHA256SUMS-Linux.txt
```

## 11. Diagnóstico de problemas

| Sintoma | Verificação e ação |
| --- | --- |
| FFmpeg indisponível | Execute `uv run build.py --prepare-ffmpeg`; confira rede, proxy e permissão do cache. |
| CUDA não detectada | Atualize o driver e confirme `torch.version.cuda`/`torch.cuda.is_available()`. |
| GPU AMD/Intel não detectada | Confirme que o ambiente contém a wheel ROCm/XPU; os anexos v0.3.0 não incluem esses runtimes. |
| Pouca VRAM | Aguarde a mensagem de fallback automático para CPU. |
| Modelo não baixa | Verifique HTTPS, proxy e espaço no cache da aplicação. |
| Download repete | Confira permissão de escrita no cache e se o arquivo foi concluído. |
| `NoneType` sem `write` | Use a v0.3.0 final; o bootstrap fornece streams graváveis em builds `--windowed`. |
| Smart App Control / código 4551 | O binário não possui assinatura/reputação aceita. Não desative a proteção; use a Store quando disponível. |
| Inno Setup ausente | Instale Inno Setup 6/7 oficial e repita o build. |
| MakeAppx ausente | Instale Windows SDK ou defina `MAKEAPPX_PATH`. |
| Cancelamento demora | O worker aguarda o próximo ponto cooperativo/trecho incremental; não encerre o processo à força. |
| Resultado com baixa confiança | Revise as palavras marcadas e ouça os timestamps correspondentes. |

## 12. Dados que não devem ser versionados

`.venv`, `.venv-cpu`, modelos, áudios, downloads FFmpeg, `build/`, `dist/`, caches, logs e arquivos
de autodiagnóstico são gerados localmente. `uv.lock` deve permanecer versionado.
