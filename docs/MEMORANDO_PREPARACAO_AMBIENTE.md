# Memorando de Preparação do Ambiente

**Projeto:** Whisper Transcriber Desktop

**Target:** Windows 10/11 x64 e Linux x86_64

**Python:** 3.11
**Gerenciador:** uv

## 1. Pré-requisitos recomendados

- 16 GB de RAM e 15 GB livres;
- GPU compatível com o runtime PyTorch escolhido; para CUDA, NVIDIA com pelo menos 6 GB de VRAM;
- Git 2.30+;
- driver NVIDIA atual. O CUDA Toolkit do sistema não é obrigatório porque a wheel do PyTorch inclui
  o runtime necessário.

## 2. Instalação do uv

Windows:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Reabra o terminal e valide com `uv --version`.

## 3. Projeto

```powershell
uv python install 3.11
uv sync
uv run main.py --self-check
uv run main.py
```

O FFmpeg 8.1.2 é resolvido automaticamente. Seu binário é verificado por SHA-256 e armazenado no
cache local. O modelo `turbo` é baixado na primeira transcrição.

## 4. Qualidade e build

```powershell
uv run ruff check .
uv run python -m pytest
uv run build.py
uv run build.py --msix
uv run build.py --installer
```

O build local incorpora o Torch/CUDA do ambiente. No Windows, `--msix` requer o Windows SDK e
gera o pacote destinado ao Partner Center; a instalação pública ocorre pela
[Microsoft Store](https://apps.microsoft.com/detail/9PHWS6MM59BG). O GitHub Actions publica o
executável Linux CPU, o instalador Windows offline CPU, checksums separados, atalho da Store e
arquivos-fonte em tags `v*`.

O comando `--installer` requer Inno Setup 6 ou 7 e gera um pacote NVIDIA CUDA por usuário em
`dist/installer/WhisperTranscriber-Setup-Windows-x64.exe`; `--installer-cpu` gera a variante CPU
usada na release. Sem Authenticode, ele pode ser bloqueado pelo Smart App Control e não substitui
o MSIX assinado da Store em computadores com essa política.

## 5. Diagnóstico

| Sintoma | Ação |
| --- | --- |
| FFmpeg indisponível | Execute `uv run build.py --prepare-ffmpeg` e verifique rede/proxy. |
| CUDA não detectada | Atualize o driver e valide `uv run python -c "import torch; print(torch.cuda.is_available())"`. |
| GPU AMD/Intel não detectada | Confirme que o artefato contém, respectivamente, o runtime ROCm (Linux) ou XPU; uma wheel CUDA não usa essas GPUs. |
| Pouca VRAM | Aguarde o fallback automático para CPU. |
| Modelo não baixa | Verifique acesso HTTPS e espaço no cache do usuário. |
| DLL ausente no build | Recrie o ambiente com `uv sync --reinstall`. |
| `NoneType` sem atributo `write` | Atualize para a versão 0.1.1 ou posterior; o bootstrap cria fluxos seguros em builds sem console. |
| `WinError 4551` | O Smart App Control bloqueou um binário sem assinatura/reputação. Use um certificado Authenticode confiável; não desative a proteção. |
| Inno Setup ausente | Instale uma versão oficial 6/7 e repita `uv run build.py --installer`. |
| MakeAppx ausente | Instale o Windows SDK ou defina `MAKEAPPX_PATH` e repita `uv run build.py --msix`. |
