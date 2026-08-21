# Whisper Transcriber Desktop

Aplicativo desktop local para transcrever um arquivo `.mp3` ou `.m4a` em Português do Brasil com
OpenAI Whisper `turbo`. A interface PySide6 permanece responsiva durante o processamento, mostra o
dispositivo realmente utilizado e gera um documento Markdown editável com metadados, texto
integral, indicadores de cobertura e timestamps.

Versão estável atual: **v0.2.1**.

## Sumário

- [Downloads](#downloads)
- [Qual versão instalar](#qual-versão-instalar)
- [Funcionalidades](#funcionalidades)
- [Como usar](#como-usar)
- [Cancelamento seguro](#cancelamento-seguro)
- [Integridade e qualidade da transcrição](#integridade-e-qualidade-da-transcrição)
- [GPU e CPU](#gpu-e-cpu)
- [Privacidade, rede e cache](#privacidade-rede-e-cache)
- [Executar pelo código-fonte](#executar-pelo-código-fonte)
- [Autodiagnóstico](#autodiagnóstico)
- [Testes e builds](#testes-e-builds)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Documentação](#documentação)

## Downloads

Todos os anexos oficiais estão na
[release v0.2.1](https://github.com/lucasitdias/whisper_desktop/releases/tag/v0.2.1).

| Plataforma | Pacote | Finalidade |
| --- | --- | --- |
| Windows 10/11 x64 + NVIDIA | [`WhisperTranscriber-Setup-Windows-x64.exe`](https://github.com/lucasitdias/whisper_desktop/releases/download/v0.2.1/WhisperTranscriber-Setup-Windows-x64.exe) | Instalador offline recomendado; inclui PyTorch CUDA 13 e fallback para CPU. |
| Windows 10/11 x64 | [`WhisperTranscriber-Setup-Windows-x64-CPU.exe`](https://github.com/lucasitdias/whisper_desktop/releases/download/v0.2.1/WhisperTranscriber-Setup-Windows-x64-CPU.exe) | Instalador offline para máquinas sem NVIDIA CUDA. |
| Windows 10/11 x64 | [`WhisperTranscriber-Windows-x64.exe`](https://github.com/lucasitdias/whisper_desktop/releases/download/v0.2.1/WhisperTranscriber-Windows-x64.exe) | Executável portátil CPU, sem assistente de instalação. |
| Debian/Ubuntu x86-64 | [`WhisperTranscriber-Setup-Linux-x64.deb`](https://github.com/lucasitdias/whisper_desktop/releases/download/v0.2.1/WhisperTranscriber-Setup-Linux-x64.deb) | Pacote offline com atalho no menu e comando `whisper-transcriber`. |
| Linux x86-64 | [`WhisperTranscriber-Linux-x64`](https://github.com/lucasitdias/whisper_desktop/releases/download/v0.2.1/WhisperTranscriber-Linux-x64) | Executável portátil CPU. |
| Windows Store | [Microsoft Store](https://apps.microsoft.com/detail/9PHWS6MM59BG) | Canal assinado pela Microsoft quando a aquisição estiver liberada. |
| Código-fonte | [ZIP](https://github.com/lucasitdias/whisper_desktop/archive/refs/tags/v0.2.1.zip) / [TAR.GZ](https://github.com/lucasitdias/whisper_desktop/archive/refs/tags/v0.2.1.tar.gz) | Fontes correspondentes à tag `v0.2.1`. |

Checksums publicados:

- [Windows NVIDIA CUDA](https://github.com/lucasitdias/whisper_desktop/releases/download/v0.2.1/SHA256SUMS-Windows-NVIDIA-CUDA.txt)
- [Windows CPU](https://github.com/lucasitdias/whisper_desktop/releases/download/v0.2.1/SHA256SUMS-Windows-CPU.txt)
- [Linux CPU](https://github.com/lucasitdias/whisper_desktop/releases/download/v0.2.1/SHA256SUMS-Linux.txt)

## Qual versão instalar

- Use o instalador **Windows NVIDIA CUDA** quando a máquina tiver uma GPU NVIDIA e driver
  compatível. Se CUDA não estiver disponível, esse mesmo pacote recua automaticamente para CPU.
- Use o instalador **Windows CPU** quando não houver GPU NVIDIA compatível ou quando a política da
  empresa exigir uma variante menor e independente de CUDA.
- Use a versão **portátil** quando não quiser criar atalhos ou entrada de desinstalação.
- Em Debian ou Ubuntu x86-64, prefira o pacote **DEB**. Ele instala o programa em
  `/opt/whisper-transcriber`, o comando `/usr/bin/whisper-transcriber`, ícone e arquivo desktop.
- A Microsoft Store é o canal recomendado em computadores que aceitam somente aplicativos
  assinados. A disponibilidade de aquisição depende da certificação e publicação pela Microsoft.

Os instaladores offline incluem a aplicação, PySide6, PyTorch, Whisper e FFmpeg. Os pesos do
modelo `turbo` não são incorporados: são baixados uma vez na primeira transcrição.

## Funcionalidades

- seleção única de MP3 ou M4A por diálogo ou arrastar e soltar;
- processamento local em `QThread`, sem congelar a interface;
- modelo Whisper `turbo`, tarefa `transcribe` e idioma fixado em `pt`;
- estratégia de qualidade com `beam_size=5`, `best_of=5`, contexto entre janelas e timestamps por
  palavra;
- prioridade automática para o backend de GPU disponível no runtime PyTorch instalado;
- identificação visível do fabricante, backend e nome real da GPU usada;
- fallback automático para CPU/FP32 quando não há acelerador ou quando falta memória de GPU;
- FFmpeg 8.1.2 estático incorporado nos pacotes e validado por SHA-256;
- progresso por etapa e por timestamps, com trechos decodificados exibidos durante a transcrição;
- cancelamento cooperativo, sem encerrar a thread à força e sem salvar resultado parcial;
- Markdown com metadados, texto integral, timestamps, cobertura, última fala e confiança estimada;
- editor Markdown e visualização sincronizada;
- cópia para a área de transferência e salvamento UTF-8 atômico;
- confirmação antes de sobrescrever um arquivo;
- tema escuro, interface em pt-BR, suporte High-DPI e ícone próprio;
- autodiagnóstico por linha de comando sem abrir a janela nem baixar o modelo.

## Como usar

1. Abra o aplicativo.
2. Confira no canto superior direito o dispositivo inicialmente detectado.
3. Arraste um `.mp3`/`.m4a` para a área indicada ou clique nela para selecionar o arquivo.
4. Clique em **Iniciar Transcrição**.
5. Acompanhe a etapa atual, o percentual e os trechos reconhecidos no log.
6. Ao concluir, revise a aba **Markdown** e a aba **Visualização**.
7. Use **Copiar Markdown** ou **Salvar como**. O aplicativo sugere
   `<nome-do-audio>_transcricao.md`, mas nunca salva automaticamente.

A aba Markdown permanece editável. Qualquer alteração feita nela é refletida na visualização.

## Cancelamento seguro

O botão **Cancelar Transcrição** fica habilitado somente enquanto o worker está ativo. Ao clicar:

1. a solicitação é marcada em um evento thread-safe;
2. a interface informa que a etapa atual está sendo finalizada com segurança;
3. o worker interrompe no próximo ponto cooperativo disponível;
4. modelo e caches do acelerador são liberados;
5. nenhum Markdown parcial é publicado ou salvo.

O aplicativo não usa `QThread.terminate()`. Durante a inferência, a resposta ao cancelamento ocorre
quando o Whisper devolve a próxima saída incremental; por isso, ela pode não ser instantânea em uma
etapa longa.

## Integridade e qualidade da transcrição

O resultado mostra:

- duração total decodificada;
- duração processada e percentual de cobertura;
- timestamp da última fala detectada;
- quantidade de palavras analisadas;
- confiança média estimada pelo Whisper;
- quantidade e lista de palavras abaixo de 50% de confiança.

Cobertura de 100% confirma que o pipeline processou toda a duração decodificada. Isso não garante
fidelidade literal. Nenhum sistema de reconhecimento de fala garante transcrição perfeita palavra
por palavra: ruído, sobreposição de vozes, sotaques, nomes próprios e baixa qualidade de gravação
podem produzir erros. Para conteúdo crítico, revise o áudio usando os timestamps e os marcadores de
baixa confiança.

## GPU e CPU

PyTorch distribui CUDA, ROCm, XPU e CPU como runtimes separados. O programa só pode usar um backend
que esteja realmente incluído no ambiente ou instalador.

| Backend | Detecção no código | Disponível nos anexos v0.2.1 |
| --- | --- | --- |
| NVIDIA CUDA | Sim; prioridade quando `torch.cuda.is_available()` | Sim, no instalador NVIDIA CUDA 13. |
| AMD ROCm | Sim; exposto pela API `torch.cuda` quando `torch.version.hip` existe | Não; requer build Linux com wheel ROCm. |
| Intel XPU | Sim; usado quando `torch.xpu.is_available()` | Não; requer build com wheel XPU. |
| CPU | Sim; fallback universal FP32 | Sim, nos pacotes CPU e como fallback do pacote NVIDIA. |

A interface mostra **Dispositivo usado** após a conclusão, evitando indicar uma GPU quando a
inferência ocorreu na CPU. GPU usa FP16; CPU usa FP32. A estratégia de decodificação e o idioma são
os mesmos nos dois caminhos, embora pequenas diferenças numéricas possam ocorrer.

## Privacidade, rede e cache

- Áudio e transcrição não são enviados a uma API de transcrição.
- O FFmpeg dos instaladores é local; no código-fonte, pode ser obtido do cache ou baixado com
  checksum fixado.
- A primeira transcrição baixa o modelo `turbo` para um cache próprio da aplicação.
- Windows: `%LOCALAPPDATA%\WhisperTranscriber\models`.
- Linux: `${XDG_CACHE_HOME:-~/.cache}/WhisperTranscriber/models`.
- Transcrições só são gravadas quando o usuário escolhe **Salvar como**.

## Executar pelo código-fonte

Requisitos:

- Windows 10/11 x64 ou Linux x86-64;
- Python 3.11;
- [`uv`](https://docs.astral.sh/uv/);
- conexão no primeiro uso para baixar FFmpeg/modelo quando ainda não estiverem em cache;
- aproximadamente 15 GB livres para ambiente, caches e builds.

```powershell
git clone https://github.com/lucasitdias/whisper_desktop.git
cd whisper_desktop
uv python install 3.11
uv sync --frozen
uv run main.py --self-check
uv run main.py
```

O `pyproject.toml` padrão aponta o Torch para CUDA 13. Para um ambiente CPU reproduzível, siga os
mesmos comandos utilizados pelo CI:

```powershell
uv venv --python 3.11 .venv-cpu
uv pip install --python .venv-cpu torch==2.12.1 --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .venv-cpu -r requirements/cpu.txt
```

## Autodiagnóstico

Sem abrir a interface:

```powershell
uv run main.py --self-check
```

Em um executável empacotado sem console, grave o resultado em JSON:

```powershell
WhisperTranscriber.exe --self-check-output self-check.json
```

O JSON informa versão do aplicativo, Python incorporado, caminho do FFmpeg, dispositivo detectado,
runtime PyTorch incorporado e estado final. O comando não baixa o modelo `turbo`.

## Testes e builds

Portões locais:

```powershell
uv run ruff check .
uv run python -m pytest
git diff --check
```

A suíte atual possui **55 testes**. O CI executa lint, testes, preparação do FFmpeg e
`--self-check` em Windows e Linux. A inferência com áudio real é opt-in e usa somente arquivos
autorizados pelo usuário.

Comandos de build:

```powershell
# Portátil da plataforma atual
uv run build.py

# Preparar somente o FFmpeg
uv run build.py --prepare-ffmpeg

# Windows NVIDIA CUDA + instalador Inno Setup
uv run build.py --installer

# Windows CPU + instalador Inno Setup
uv run build.py --installer-cpu

# MSIX para envio ao Partner Center
uv run build.py --msix
```

O pipeline da tag `v0.2.1` instalou, autoverificou e removeu os instaladores Windows NVIDIA/CPU e
o pacote DEB em runners limpos. Os cinco binários publicados foram baixados novamente após a
release e conferidos contra os arquivos SHA-256.

## Estrutura do repositório

```text
whisper_desktop/
├── .github/workflows/       # qualidade e publicação por tag
├── app/
│   ├── core/                # FFmpeg, worker Whisper e exportação
│   └── ui/                  # janela, drop zone, tema e componentes
├── assets/                  # ícones e FFmpeg por plataforma
├── docs/                    # requisitos, arquitetura, operação e evidências
├── installer/               # definição Inno Setup para Windows
├── packaging/linux/         # metadados e atalho do pacote DEB
├── requirements/            # perfil CPU reproduzível usado no CI
├── store/                   # manifesto MSIX e atalho da Microsoft Store
├── tests/                   # testes unitários e pytest-qt
├── build.py                 # PyInstaller, Inno Setup e MSIX
├── main.py                  # GUI e autodiagnóstico
├── pyproject.toml
└── uv.lock
```

## Documentação

- [Requisitos do produto](docs/PRD.md)
- [Arquitetura técnica](docs/ARQUITETURA_TECNICA.md)
- [Design system](docs/DESIGN_SYSTEM_GUI.md)
- [Implementação concluída](docs/Implementação%20completa%20do%20Whisper%20Transcriber%20Desktop.md)
- [Preparação do ambiente](docs/MEMORANDO_PREPARACAO_AMBIENTE.md)
- [Validação de qualidade e segurança](docs/VALIDACAO_QUALIDADE_SEGURANCA.md)
- [Publicação na Microsoft Store](docs/PUBLICACAO_MICROSOFT_STORE.md)
- [Avisos de terceiros](docs/THIRD_PARTY_NOTICES.md)

## Limitações conhecidas

- somente um arquivo MP3/M4A por transcrição;
- sem diarização, gravação de microfone, tradução ou processamento em lote;
- pesos do modelo não são incorporados aos instaladores;
- anexos Windows do GitHub ainda não possuem Authenticode e podem ser bloqueados pelo Smart App
  Control; não desative a proteção do Windows;
- o canal Microsoft Store depende da certificação/publicação da Microsoft;
- AMD ROCm e Intel XPU exigem builds PyTorch próprios e não estão nos anexos v0.2.1.
