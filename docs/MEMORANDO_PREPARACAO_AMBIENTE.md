# Memorando de Preparação do Ambiente

**Projeto:** Whisper Transcriber Desktop

**Target:** Windows 10/11 x64 e Linux x86_64

**Python:** 3.11
**Gerenciador:** uv

## 1. Pré-requisitos recomendados

- 16 GB de RAM e 15 GB livres;
- NVIDIA com pelo menos 6 GB de VRAM para o modelo `turbo`;
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
uv run pytest
uv run build.py
```

O build local incorpora o Torch/CUDA do ambiente. O GitHub Actions cria releases CPU portáteis em
tags `v*`.

## 5. Diagnóstico

| Sintoma | Ação |
| --- | --- |
| FFmpeg indisponível | Execute `uv run build.py --prepare-ffmpeg` e verifique rede/proxy. |
| CUDA não detectada | Atualize o driver e valide `uv run python -c "import torch; print(torch.cuda.is_available())"`. |
| Pouca VRAM | Aguarde o fallback automático para CPU. |
| Modelo não baixa | Verifique acesso HTTPS e espaço no cache do usuário. |
| DLL ausente no build | Recrie o ambiente com `uv sync --reinstall`. |
