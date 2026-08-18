# Whisper Transcriber Desktop

Aplicativo desktop local para transformar arquivos `.mp3` e `.m4a` em relatórios Markdown com
texto integral, metadados e marcadores temporais. A interface é construída com PySide6 e a
transcrição usa o modelo OpenAI Whisper `turbo`, fixado em Português do Brasil (`pt`).

## Recursos

- seleção por diálogo ou arrastar e soltar;
- processamento em `QThread`, sem bloquear a interface;
- CUDA quando disponível e fallback automático para CPU, inclusive por falta de VRAM;
- download automático e verificado do FFmpeg 8.1.2;
- progresso e trechos exibidos durante a transcrição;
- editor Markdown, prévia formatada, cópia e salvamento seguro;
- executável portátil Windows/Linux criado com PyInstaller;
- instalador Windows x64 com CUDA, FFmpeg, atalhos e desinstalador.

## Requisitos

- Windows 10/11 x64 ou Linux x86_64;
- `uv` instalado;
- conexão na primeira execução para baixar FFmpeg e o modelo `turbo`;
- aproximadamente 15 GB livres para dependências, cache e builds.

O projeto fixa Python 3.11. O ambiente de desenvolvimento usa PyTorch 2.12.1 com CUDA 13.0;
quando não existe GPU/driver compatível, o mesmo ambiente executa em CPU.

## Preparação e execução

```powershell
uv sync
uv run main.py
```

Na primeira transcrição, o aplicativo baixa o modelo `turbo` para o cache do usuário. O áudio e a
transcrição permanecem locais.

Autoverificação sem abrir a GUI nem baixar o modelo:

```powershell
uv run main.py --self-check
```

Em aplicativos empacotados sem console, use a saída JSON:

```powershell
WhisperTranscriber.exe --self-check-output self-check.json
```

## Testes e qualidade

```powershell
uv run ruff check .
uv run python -m pytest
```

Os testes simulam Whisper e Torch; o CI não baixa o modelo. Uma transcrição real deve usar um áudio
fornecido pelo usuário.

## Build local

Executável portátil da plataforma atual:

```powershell
uv run build.py
```

O script baixa e verifica o FFmpeg da plataforma e gera:

- Windows: `dist/WhisperTranscriber.exe`;
- Linux: `dist/WhisperTranscriber`.

O build local incorpora o PyTorch do ambiente atual. As releases por tag `v*` usam o perfil CPU
portátil definido em `requirements/cpu.txt`.

No Windows, o instalador completo com CUDA é gerado por:

```powershell
uv run build.py --installer
```

O resultado fica em `dist/installer/WhisperTranscriber-Setup-Windows-x64.exe`. A instalação é feita
somente para o usuário atual em `%LOCALAPPDATA%\Programs\Whisper Transcriber Desktop`, cria atalhos
e inclui desinstalador. O modelo `turbo` não é incorporado: ele é baixado e verificado na primeira
transcrição para o cache do usuário.

O instalador produzido localmente não possui assinatura Authenticode sem um certificado de
publicação. Em computadores com Smart App Control no modo estrito, o Windows pode impedir a
execução de binários locais sem reputação. Não desative essa proteção; assine o artefato com um
certificado público confiável antes de distribuí-lo amplamente.

## Estrutura

```text
whisper_desktop/
├── .github/workflows/       # CI e publicação por tag
├── app/
│   ├── core/                # FFmpeg, Whisper e exportação
│   └── ui/                  # Janela e tema QSS
├── assets/
│   └── ffmpeg/              # Destinos Windows/Linux dos binários gerados
├── docs/                    # Especificações e guias
├── installer/               # Script Inno Setup do instalador Windows
├── requirements/            # Perfil CPU para CI/releases
├── tests/                   # Suíte automatizada
├── build.py
├── main.py
├── pyproject.toml
└── uv.lock
```

Consulte também [VALIDACAO_QUALIDADE_SEGURANCA.md](VALIDACAO_QUALIDADE_SEGURANCA.md) e
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
