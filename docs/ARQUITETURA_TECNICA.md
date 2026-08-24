# Especificação de Arquitetura Técnica

> Autor e desenvolvedor: **Lucas Dias — Estudante de Ciência da Computação**.

## 1. Escopo e versão

Esta especificação descreve a versão final **v0.3.0** do Whisper Transcriber Desktop, aceita
localmente em 24/08/2026.
O produto é um monólito desktop para Windows 10/11 x64 e Debian/Ubuntu x86-64.

A thread principal pertence ao Qt. Download, decodificação, carregamento do modelo e inferência
ocorrem em `TranscriberWorker(QThread)`, com comunicação exclusivamente por sinais e slots.

```text
QApplication / MainWindow
  ├── gravação, DropZone e seleção de arquivo
  ├── estado dos botões, progresso e log
  ├── QSplitter, editor Markdown e visualização expansível
  ├── player e revisão por timestamp
  └── ações de copiar e salvar
          │ sinais/slots Qt
          ├──────────────► RecorderController / QAudioSource
          │                   └── AudioEncodingWorker / FFmpeg
          ▼
TranscriberWorker (QThread)
  ├── FFmpegFinder
  ├── whisper.load_audio
  ├── ModelManager / checkpoint local validado
  ├── whisper.load_model(caminho_local)
  ├── model.transcribe
  └── TranscriptionResult
          │
          ▼
MarkdownExporter
```

## 2. Estrutura de módulos

```text
whisper_desktop/
├── app/
│   ├── core/
│   │   ├── exporter.py
│   │   ├── ffmpeg_finder.py
│   │   ├── model_catalog.py
│   │   ├── recorder.py
│   │   └── transcriber.py
│   └── ui/
│       ├── components.py
│       ├── main_window.py
│       └── styles.py
├── assets/
│   └── ffmpeg/<windows|linux>/
├── installer/WhisperTranscriber.iss
├── packaging/linux/
├── store/
├── tests/
├── build.py
└── main.py
```

Responsabilidades:

- `main.py`: normaliza `stdout`/`stderr` em builds `--windowed`, executa o autodiagnóstico e inicia
  a GUI.
- `app/core/ffmpeg_finder.py`: resolve, valida, baixa e disponibiliza o FFmpeg.
- `app/core/model_catalog.py`: catálogo dos seis modelos, disponibilidade, integridade, download
  explícito e resolução incorporado/cache.
- `app/core/recorder.py`: captura PCM, estados, nível, recuperação e encoding atômico.
- `app/core/transcriber.py`: detecta o backend, executa o Whisper, calcula métricas e controla o
  cancelamento.
- `app/core/exporter.py`: renderiza o Markdown e faz escrita UTF-8 atômica.
- `app/ui/components.py`: zona de drag-and-drop e componentes reutilizáveis.
- `app/ui/main_window.py`: orquestra seleção, worker, estados, editor, prévia, cópia e salvamento.
- `app/ui/styles.py`: folha QSS canônica do tema escuro.
- `build.py`: PyInstaller, preparação do FFmpeg, autoverificação, Inno Setup e MSIX.
- `.github/workflows/ci.yml`: lint, testes, FFmpeg e autodiagnóstico em Windows/Linux.
- `.github/workflows/release.yml`: builds NVIDIA CUDA/CPU, instalação real, checksums e release.

## 3. Contratos públicos

### 3.1 `TranscriberWorker`

Sinais:

- `status_changed(str)`;
- `progress_changed(int)`, com `-1` para progresso indeterminado;
- `segment_decoded(str)`;
- `completed(object)`, contendo `TranscriptionResult`;
- `failed(str)`;
- `cancelled(str)`.
- `device_detected(str, str)`, com backend e descrição do hardware efetivamente usado.

Métodos relevantes:

- `cancel()`: solicita interrupção cooperativa;
- `detect_device()`: retorna `cuda`, `rocm`, `xpu` ou `cpu`;
- `device_description()`: apresenta backend e nome real do dispositivo;
- `runtime_description()`: identifica o runtime PyTorch incorporado;
- `model_cache_root()`: separa o cache do modelo por aplicação.

### 3.2 Tipos de resultado

`TranscriptionResult` é imutável e contém:

- nome do arquivo de origem, sem caminho absoluto;
- duração total e duração processada;
- texto integral e segmentos;
- modelo, idioma, dispositivo e data com fuso;
- confiança média, quantidade de palavras e palavras abaixo de 50%.

Propriedades calculadas expõem cobertura, fim da última fala e total de palavras de baixa
confiança.

### 3.3 `MarkdownExporter`

- `render(result) -> str`: função pura e testável;
- `save(markdown, path)`: grava em arquivo temporário no mesmo volume, faz `fsync` e substituição
  atômica;
- caminhos absolutos nunca são incluídos no documento.

### 3.4 Gravação e opções de qualidade

- `RecordingFormat`: extensão, codec, bitrate, muxer e argumentos FFmpeg conhecidos;
- `RecordingState`: `ready`, `starting`, `recording`, `paused` e `finalizing`;
- `RecordingResult`: destino final, WAV temporário, microfone, duração, pico e avisos;
- `ModelSpec`: identificador, arquivo, tamanho, SHA-256, parâmetros, VRAM, velocidade, fidelidade,
  disponibilidade inicial e busca;
- `ModelAvailability`: `bundled`, `cached`, `download_required`, `downloading` e `invalid`;
- `TranscriptionOptions`: um dos seis modelos, idioma, contexto, prioridade e revisão seletiva;
- `TranscriptionPriority`: `fast`, `balanced` ou `max_fidelity`, sem duplicar checkpoints;
- `DecodingProfile`: busca, `best_of`, paciência e margem da segunda passagem;
- `RecorderController`: sinais de estado, tempo, nível, conclusão e falha recuperável;
- `AudioEncodingWorker`: conversão em `QThread` e publicação atômica.

## 4. Fluxo da transcrição

1. A GUI valida extensão e existência do arquivo.
2. O worker resolve o FFmpeg e importa PyTorch/Whisper sob demanda, fora da thread da GUI.
3. O backend é detectado e comunicado à interface antes de carregar o modelo.
4. `whisper.load_audio()` decodifica o áudio uma única vez em memória.
5. A duração é calculada por amostras divididas por `whisper.audio.SAMPLE_RATE`.
6. `ModelManager` resolve incorporado e depois cache validado; a transcrição nunca inicia rede.
7. `whisper.load_model(caminho)` recebe os alignment heads oficiais preservados.
8. `model.transcribe()` recebe `language="pt"`, `task="transcribe"`, busca adaptada à prioridade,
   `condition_on_previous_text=True`, `word_timestamps=True` e o controle nativo de alucinação em
   silêncio. Em maior fidelidade, todos usam busca 5 e `patience=1.2`.
9. A revisão reforçada reprocessa somente trechos suspeitos com margem temporal, busca 10 e recorta
   palavras fora do intervalo original antes de comparar confiança, silêncio e compressão.
10. A saída incremental é convertida em trechos e progresso por timestamp.
11. Segmentos e probabilidades por palavra são normalizados em tipos imutáveis.
12. A GUI recebe o resultado completo, renderiza o Markdown e vincula timestamps ao player.

### 4.1 Fluxo da gravação

1. A GUI enumera `QMediaDevices.audioInputs()` e solicita permissão somente após **Gravar**.
2. `RecorderController` negocia PCM Int16, priorizando 48 kHz e até dois canais.
3. `QAudioSource.start()` usa dica de buffer PCM de 40 ms e fornece um `QIODevice`; a GUI drena
   blocos por `readyRead` para WAV e só confirma **Gravando** após preservar o primeiro bloco.
4. Pausa mantém o endpoint ativo e descarta seus blocos; retomar é imediato e não inclui o
   intervalo pausado nem dados antigos do buffer.
5. Ao parar, o WAV é fechado e `AudioEncodingWorker` executa o FFmpeg sem `shell=True`.
6. O destino `.part` vira MP3/M4A por `os.replace()`; falhas preservam o WAV.
7. A GUI habilita **Salvar áudio como...** e **Iniciar transcrição**, sem ação automática.
8. Ao transcrever, `TranscriberWorker` recebe o WAV e um nome público separado para o Markdown.
9. O cache é removido ao substituir a captura ou fechar normalmente a aplicação.

GPU usa FP16. CPU usa FP32. Em erro de memória do acelerador, o cache correspondente é liberado,
o coletor é executado e a transcrição reinicia automaticamente em CPU.
Após sucesso, um único modelo pode permanecer em cache por cinco minutos para evitar reler até
3,1 GB do disco em uma transcrição consecutiva. Falha, cancelamento, troca de perfil, expiração do
temporizador ou fechamento liberam o modelo, executam o coletor e esvaziam o cache do acelerador.
A janela ociosa inicial não importa PyTorch/Whisper.

## 5. Cancelamento e ciclo de vida

O cancelamento combina `threading.Event` e `QThread.requestInterruption()`. Pontos seguros existem
antes/depois de validação, FFmpeg, decodificação, carregamento, inferência e emissão do resultado.
Durante a inferência, `_WhisperOutputStream.write()` verifica a solicitação a cada saída incremental.

Não são usados `QThread.terminate()` nem resultados parciais. A interface:

- desabilita nova transcrição enquanto o worker está ativo;
- habilita somente o botão de cancelamento;
- impede fechamento inseguro da janela;
- restaura os controles após conclusão, falha ou cancelamento.

## 6. Resolução segura do FFmpeg

Ordem efetiva:

1. `sys._MEIPASS/assets/ffmpeg/<os>/` em PyInstaller;
2. `assets/ffmpeg/<os>/` no checkout;
3. executável encontrado no `PATH`;
4. cache local previamente validado;
5. download HTTPS do artefato fixado.

A versão fixada é `8.1.2-34-g9b6c8969e0`, release BtbN
`autobuild-2026-07-31-14-10`, variante LGPL. O SHA-256 é verificado antes da extração. Somente o
membro esperado `bin/ffmpeg(.exe)` é extraído; não há `extractall` nem `shell=True`. O binário é
validado executando `ffmpeg -version` com timeout.

## 7. Backends de processamento

PyTorch distribui CPU, CUDA, ROCm e XPU em wheels distintas. O detector só escolhe um backend
quando a API correspondente está disponível e funcional.

- CUDA: GPU NVIDIA, API `torch.cuda`.
- ROCm: GPU AMD no Linux, identificada por `torch.version.hip`; o nome de dispositivo continua
  `cuda` por compatibilidade PyTorch.
- XPU: GPU Intel, API `torch.xpu`.
- CPU: fallback universal.

Os anexos v0.3.0 incluem um runtime NVIDIA CUDA 13 e runtimes CPU. O código suporta ROCm/XPU, mas
esses runtimes não estão incorporados nos instaladores desta entrega.

## 8. Interface e exportação

A `MainWindow` mantém uma única fonte Markdown editável. A visualização é derivada dessa fonte,
evitando divergência entre conteúdo copiado, salvo e exibido. A confirmação de sobrescrita pertence
à camada de interface; persistência e formatação permanecem no núcleo.

Um `QSplitter` vertical separa controles/logs do painel de resultado. O botão de foco oculta apenas
o painel superior; `Esc`/Restaurar recuperam os tamanhos anteriores sem reconstruir widgets, por
isso edição, aba, rolagem e estado do player permanecem intactos.

O arquivo sugerido segue `<nome-do-audio>_transcricao.md`. A exportação inclui:

- data, arquivo, duração, modelo, idioma e processamento;
- cobertura, duração processada, última fala e confiança;
- texto integral;
- lista de segmentos com timestamps `HH:MM:SS`;
- lista opcional de palavras com confiança inferior a 50%.

## 9. Empacotamento e distribuição

O PyInstaller recebe `--windowed`, ícone próprio, FFmpeg via `--add-binary` e coleta completa de
`whisper` e `torch`.

| Artefato | Modo | Runtime |
| --- | --- | --- |
| Windows NVIDIA | `--onedir` dentro do Inno Setup | PyTorch CUDA 13 |
| Windows CPU instalável | `--onedir` dentro do Inno Setup | PyTorch CPU |
| Windows portátil | ZIP do diretório `--onedir` | PyTorch CPU |
| Linux portátil | `tar.gz` do diretório `--onedir` | PyTorch CPU |
| Linux DEB | diretório instalado em `/opt` | PyTorch CPU |
| Microsoft Store | `--onedir` dentro de MSIX | PyTorch CUDA 13 |

O Inno Setup usa `DiskSpanning=yes` porque o conteúdo comprimido pode exceder 4,2 GB. O bundle ZIP
mantém o launcher e todas as fatias `.bin` juntos; o MSIX permanece um único pacote.
Na atualização do candidato anterior, o Inno move um `large-v3.pt` íntegro da antiga pasta
incorporada para `%LOCALAPPDATA%\WhisperTranscriber\models`; se um cache íntegro já existir, remove
somente a cópia redundante instalada. Assim o usuário não baixa novamente o modelo.

Não há cross-compilation: cada pacote é construído no sistema operacional alvo. O MSIX local é
destinado ao Partner Center. A assinatura confiável do canal Store é aplicada pela Microsoft após
certificação. Os instaladores Inno Setup da release não possuem Authenticode e podem ser bloqueados
por Smart App Control.

## 10. Autodiagnóstico

`main.py --self-check` valida imports, FFmpeg, dispositivo, runtime e presença dos dois modelos
offline sem abrir a janela ou baixar conteúdo. `--self-check-output <arquivo>` grava o mesmo resultado em JSON e é usado em executáveis
`--windowed`, instaladores e CI.

## 11. Portões de qualidade

- Ruff;
- testes `pytest`/`pytest-qt` no candidato final v0.3.0;
- `git diff --check`;
- autodiagnóstico Windows/Linux;
- instalação, execução e desinstalação reais dos instaladores Windows;
- instalação, execução e remoção reais do DEB;
- SHA-256 publicado e validado novamente após a release.
