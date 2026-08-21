# Especificação de Arquitetura Técnica

## 1. Visão geral

A aplicação é um monólito desktop standalone. A GUI PySide6 ocupa a thread principal; um
`TranscriberWorker(QThread)` executa FFmpeg, carregamento do modelo e inferência. A comunicação usa
somente sinais/slots Qt.

```text
MainWindow
  ├─ DropZone / editor / prévia
  └─ sinais e slots
       ↓
TranscriberWorker (QThread)
  ├─ FFmpegFinder
  ├─ whisper.load_audio
  ├─ whisper.load_model("turbo")
  └─ MarkdownExporter
```

## 2. Módulos

- `main.py`: bootstrap Qt e `--self-check`.
- `app/core/ffmpeg_finder.py`: resolução, download, SHA-256, extração e PATH.
- `app/core/transcriber.py`: tipos de resultado, progresso, CUDA/CPU e sinais Qt.
- `app/core/exporter.py`: Markdown e escrita UTF-8 atômica.
- `app/ui/main_window.py`: seleção, execução, editor, prévia, cópia e salvamento.
- `app/ui/styles.py`: tokens e folha QSS.
- `build.py`: FFmpeg, PyInstaller, autoverificação JSON, MSIX da Store e Inno Setup interno.
- `store/AppxManifest.xml.in`: identidade MSIX reservada e capacidade `runFullTrust`.
- `installer/WhisperTranscriber.iss`: instalação Windows interna, atalhos e desinstalador.

## 3. Contratos

`TranscriberWorker` expõe:

- `status_changed(str)`;
- `progress_changed(int)`, usando `-1` para estado indeterminado;
- `segment_decoded(str)`;
- `completed(TranscriptionResult)`;
- `failed(str)`;
- `cancelled(str)`.

`TranscriptionResult` contém nome de origem, duração total/processada, texto, segmentos, palavras de
baixa confiança, modelo, idioma, dispositivo e data com fuso. `MarkdownExporter.render()` é puro e
`save()` usa arquivo temporário no mesmo volume seguido de substituição atômica.

## 4. FFmpeg

Ordem de resolução:

1. `sys._MEIPASS/assets/ffmpeg/<os>/`;
2. `assets/ffmpeg/<os>/` no checkout;
3. `ffmpeg` no `PATH`;
4. cache local verificado;
5. download HTTPS da release mensal fixada, com SHA-256 antes da extração.

Somente o membro `bin/ffmpeg(.exe)` é lido do arquivo; não há `extractall` nem `shell=True`.

## 5. Transcrição e fallback

O áudio é decodificado uma vez com `whisper.load_audio`. A duração deriva da quantidade de amostras.
O modelo usa FP16 em CUDA e FP32 em CPU. A saída incremental do Whisper fornece trechos e timestamps
para o progresso. Em erro de memória CUDA, o cache é liberado e a operação reinicia em CPU.
O cancelamento usa um evento thread-safe e `requestInterruption()`. Pontos seguros verificam a
solicitação entre FFmpeg, decodificação, carregamento e inferência; durante a inferência, a saída de
segmentos interrompe cooperativamente o loop. Não são usados `terminate()` nem resultados parciais.

`word_timestamps=True` fornece probabilidades por palavra. O resultado registra cobertura da
duração decodificada, último timestamp de fala, confiança média e quantidade de palavras abaixo de
50%. Essas métricas ajudam a revisão, mas não constituem garantia de exatidão linguística.

## 6. Empacotamento

O PyInstaller recebe `--windowed`, `--add-binary`, `--collect-all whisper` e `--collect-all torch`.
O Linux portátil usa `--onefile`; o MSIX Windows usa `--onedir` para manter DLLs CUDA junto ao
executável. O build deve ser executado separadamente em Windows e Linux; não existe
cross-compilation. Tags `v*` publicam o executável Linux CPU, checksum, atalho da Store e os
arquivos-fonte gerados pelo GitHub.

No canal oficial Windows, o diretório PyInstaller é empacotado como MSIX com a identidade reservada
no Partner Center. A Microsoft valida, assina e distribui o pacote pela Store. O Inno Setup pode
compactar o mesmo diretório para testes internos, mas não é publicado sem Authenticode. O aplicativo
empacotado é executado com `--self-check-output` antes da compactação, pois builds `--windowed` não
possuem console. O bootstrap substitui `stdout` e `stderr` ausentes por fluxos graváveis, inclusive
para o progresso de download do Whisper.
