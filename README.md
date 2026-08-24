# Whisper Transcriber Desktop

Aplicativo desktop local para gravar o áudio do ambiente ou transcrever um arquivo `.mp3`/`.m4a`
em Português do Brasil. A v0.3.0 usa Whisper `large-v3` por padrão, oferece seis modelos
multilíngues e inclui `medium` e `turbo` para uso totalmente offline desde a instalação. O
`large-v3` usa download explícito e, depois de validado, também funciona totalmente offline.

Versão final: **v0.3.0**. Homologação local concluída em 24/08/2026; a publicação no GitHub e a
submissão da edição Pro à Microsoft Store seguem os portões descritos neste repositório.

Desenvolvido por **Lucas Dias**, Estudante de Ciência da Computação.

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
- [Autor, licença e citação](#autor-licença-e-citação)

## Downloads

Os anexos da versão final ficam na
[release v0.3.0](https://github.com/lucasitdias/whisper_desktop/releases/tag/v0.3.0). A edição
gratuita anteriormente publicada permanece disponível separadamente na Microsoft Store.

| Plataforma | Pacote | Finalidade |
| --- | --- | --- |
| Windows 10/11 x64 + NVIDIA | `WhisperTranscriber-Setup-Windows-x64.exe` + partes `.bin` | Instalador offline recomendado; inclui PyTorch CUDA 13 e fallback para CPU. Baixe o launcher e todas as partes CUDA da release na mesma pasta. |
| Windows 10/11 x64 | `WhisperTranscriber-Setup-Windows-x64-CPU.exe` + partes `.bin` | Instalador offline para máquinas sem NVIDIA CUDA. Baixe o launcher e todas as partes CPU na mesma pasta. |
| Windows 10/11 x64 portátil | `WhisperTranscriber-Windows-x64.zip.part-*` | Partes numeradas do pacote portátil CPU; reconstrua o ZIP conforme a documentação da entrega. |
| Debian/Ubuntu x86-64 | `WhisperTranscriber-Setup-Linux-x64.deb.part-*` | Partes numeradas do DEB offline; reconstrua o arquivo, confira o hash e instale com `dpkg`. |
| Linux x86-64 portátil | `WhisperTranscriber-Linux-x64.tar.gz.part-*` | Partes numeradas do portátil CPU. |
| Microsoft Store gratuita | [Produto `9PHWS6MM59BG`](https://apps.microsoft.com/detail/9PHWS6MM59BG) | Edição gratuita anterior, mantida em `1.2.4.0`. |
| Microsoft Store Pro | [Produto `9NJN8VV2N833`](https://apps.microsoft.com/detail/9NJN8VV2N833) | Edição paga v0.3.0 configurada por R$ 26,95; a aquisição será liberada somente após a certificação. |
| Código-fonte | [ZIP](https://github.com/lucasitdias/whisper_desktop/archive/refs/tags/v0.3.0.zip) / [TAR.GZ](https://github.com/lucasitdias/whisper_desktop/archive/refs/tags/v0.3.0.tar.gz) | Fontes correspondentes à tag `v0.3.0`. |

Checksums publicados:

- [Windows NVIDIA CUDA](https://github.com/lucasitdias/whisper_desktop/releases/download/v0.3.0/SHA256SUMS-Windows-NVIDIA-CUDA.txt)
- [Windows CPU](https://github.com/lucasitdias/whisper_desktop/releases/download/v0.3.0/SHA256SUMS-Windows-CPU.txt)
- [Linux CPU](https://github.com/lucasitdias/whisper_desktop/releases/download/v0.3.0/SHA256SUMS-Linux.txt)

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

Os instaladores v0.3.0 incluem aplicação, PySide6, PyTorch, Whisper, FFmpeg e os checkpoints
`medium` e `turbo`. Eles funcionam sem internet desde a primeira execução. A edição Pro da Store é
um produto separado da gratuita e só será identificada como publicada após a certificação.

| Modelo v0.3.0 | Parâmetros | VRAM aproximada | Velocidade relativa | Disponibilidade |
| --- | ---: | ---: | ---: | --- |
| `tiny` | 39M | ~1 GB | ~10x | download explícito; depois offline |
| `base` | 74M | ~1 GB | ~7x | download explícito; depois offline |
| `small` | 244M | ~2 GB | ~4x | download explícito; depois offline |
| `medium` | 769M | ~5 GB | ~2x | incorporado/offline |
| `turbo` | 809M | ~6 GB | ~8x | incorporado/offline |
| `large-v3` | 1.550M | ~10 GB | 1x | padrão; download explícito; depois offline |

Não há download silencioso: `tiny`, `base`, `small` e `large-v3` só usam rede após **Baixar
modelo**, exibem
progresso/cancelamento, validam SHA-256 e publicam o cache por substituição atômica.
Ao atualizar um candidato antigo, um `large-v3.pt` íntegro que já estava no aplicativo é migrado
para o mesmo cache persistente, evitando perda do modelo ou novo download.

Como os pacotes offline são grandes, o instalador tradicional v0.3.0 usa um launcher `.exe` e
fatias `.bin`; todos os arquivos da mesma variante devem permanecer na mesma pasta. O GitHub limita
cada anexo de release a menos de 2 GiB, portanto portáteis e pacotes Linux grandes também são
publicados em partes numeradas. O MSIX da Store continua sendo um pacote único.

## Funcionalidades

- gravação de microfone com pausa, cronômetro, nível e alerta de clipping;
- saída MP3 192/320 kbps ou M4A AAC 256 kbps, mantida em cache até a decisão do usuário;
- seleção única de MP3 ou M4A por diálogo ou arrastar e soltar;
- processamento local em `QThread`, sem congelar a interface;
- seis modelos multilíngues, com `large-v3` padrão, tarefa `transcribe` e idioma fixado em `pt`;
- contexto opcional, três prioridades de decodificação, revisão seletiva e player com navegação
  por timestamps;
- **Velocidade** reduz a busca, **Equilibrada** usa o perfil recomendado por modelo e **Maior
  fidelidade** aplica busca 5, paciência ampliada e revisão automática dos trechos duvidosos;
- todos preservam timestamps por palavra, contexto entre janelas e controle nativo de alucinação
  em silêncio;
- hipóteses em intervalos abaixo de -72 dBFS são descartadas objetivamente e contabilizadas no
  relatório, sem reescrever fala válida;
- prioridade automática para o backend de GPU disponível no runtime PyTorch instalado;
- identificação visível do fabricante, backend e nome real da GPU usada;
- monitor em tempo real do tempo, CPU e RAM do aplicativo e, em NVIDIA, GPU total e VRAM;
- PyTorch e Whisper carregados sob demanda, reduzindo a memória usada apenas para abrir a janela;
- fallback automático para CPU/FP32 quando não há acelerador ou quando falta memória de GPU;
- FFmpeg 8.1.2 estático incorporado nos pacotes e validado por SHA-256;
- progresso por etapa e por timestamps, com trechos decodificados exibidos durante a transcrição;
- cancelamento cooperativo, sem encerrar a thread à força e sem salvar resultado parcial;
- Markdown com metadados, texto integral, timestamps, cobertura, última fala e confiança estimada;
- editor Markdown e visualização sincronizada;
- divisor vertical redimensionável e modo **Expandir resultado**, restaurado pelo botão ou `Esc`;
- cópia para a área de transferência e salvamento UTF-8 atômico;
- confirmação antes de sobrescrever um arquivo;
- tema escuro, interface em pt-BR, suporte High-DPI e ícone próprio;
- autodiagnóstico por linha de comando sem abrir a janela nem baixar o modelo.

## Como usar

1. Para gravar, escolha microfone/formato e clique em **Gravar**. O cache é local e temporário.
2. Use **Pausar/Retomar** quando necessário e **Parar** para finalizar o áudio.
3. Escolha **Salvar áudio como...** e/ou **Iniciar transcrição**. Nenhuma transcrição começa
   automaticamente.
4. Para um arquivo existente, arraste um `.mp3`/`.m4a` ou clique na área de seleção.
5. Escolha um dos seis modelos. Se `tiny`, `base`, `small` ou `large-v3` ainda não estiver local,
   use **Baixar modelo**; sem internet, escolha `medium` ou `turbo`.
6. Escolha **Velocidade**, **Equilibrada** ou **Maior fidelidade**. A última inclui revisão
   automática e demora mais, sem aumentar o tamanho instalado.
7. Acompanhe tempo, CPU, RAM, GPU/VRAM e os trechos reconhecidos no log.
8. Clique nos timestamps para ouvir e corrigir os pontos de baixa confiança.
9. Use **Copiar Markdown** ou **Salvar transcrição**. O aplicativo sugere
   `<nome-do-audio>_transcricao.md`, mas nunca salva automaticamente.

A aba Markdown permanece editável. Qualquer alteração feita nela é refletida na visualização.
Arraste o divisor para ampliar o resultado ou use **Expandir resultado**; texto, aba, rolagem,
edição e reprodução são preservados ao restaurar.

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

| Backend | Detecção no código | Disponível nos anexos v0.3.0 |
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
- A permissão do microfone só é solicitada após a ação explícita de gravar.
- A captura PCM sem perdas é temporária e removida após a transcrição, salvo em recuperação.
- O FFmpeg dos instaladores é local; no código-fonte, pode ser obtido do cache ou baixado com
  checksum fixado.
- Nos instaladores v0.3.0, `medium` e `turbo` são lidos diretamente do pacote; `tiny`, `base`,
  `small` e `large-v3` só são baixados após ação explícita do usuário.
- Windows: `%LOCALAPPDATA%\WhisperTranscriber\models`.
- Linux: `${XDG_CACHE_HOME:-~/.cache}/WhisperTranscriber/models`.
- Transcrições só são gravadas quando o usuário escolhe **Salvar como**.

## Executar pelo código-fonte

Requisitos:

- Windows 10/11 x64 ou Linux x86-64;
- Python 3.11;
- [`uv`](https://docs.astral.sh/uv/);
- conexão para preparar FFmpeg/checkpoints ao executar pelo código-fonte; os pacotes prontos já
  incluem FFmpeg, `medium` e `turbo`;
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

A suíte v0.3.0 cobre captura contínua, pausa sem reativação do endpoint, telemetria, silêncio,
encoding,
qualidade, player e regressões. O CI executa lint, testes,
preparação do FFmpeg e
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

O pipeline da tag `v0.3.0` instala, autoverifica e remove os instaladores Windows NVIDIA/CPU e o
pacote DEB em runners limpos antes de criar a release. Os anexos precisam ser conferidos novamente
contra os manifestos SHA-256 depois da publicação.

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
- [Gravação e máxima fidelidade v0.3.0](docs/IMPLEMENTACAO_GRAVACAO_AUDIO_V030.md)
- [Publicação na Microsoft Store](docs/PUBLICACAO_MICROSOFT_STORE.md)
- [Entrega e publicação da v0.3.0](docs/ENTREGA_E_PUBLICACAO_V030.md)
- [Avisos de terceiros](docs/THIRD_PARTY_NOTICES.md)

## Autor, licença e citação

**Lucas Dias** — Estudante de Ciência da Computação.

O código é disponibilizado sob a [Licença MIT](LICENSE). Cópias ou partes substanciais devem
preservar o aviso de copyright e o texto da licença, garantindo o crédito legal ao autor. Os
componentes de terceiros permanecem sujeitos aos termos listados em
[THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md).

Para trabalhos acadêmicos, artigos ou redistribuições, use também os metadados de
[CITATION.cff](CITATION.cff).

## Limitações conhecidas

- somente um arquivo MP3/M4A por transcrição;
- sem diarização, tradução, áudio do sistema/loopback ou processamento em lote;
- os quatro modelos opcionais exigem internet apenas no download explícito inicial;
- anexos Windows do GitHub ainda não possuem Authenticode e podem ser bloqueados pelo Smart App
  Control; não desative a proteção do Windows;
- o canal Microsoft Store depende da certificação/publicação da Microsoft;
- AMD ROCm e Intel XPU exigem builds PyTorch próprios e não estão nos anexos v0.3.0.
