# Gravação de áudio e máxima fidelidade — v0.3.0

> Autor e desenvolvedor: **Lucas Dias — Estudante de Ciência da Computação**.

## Objetivo e viabilidade

A v0.3.0 inclui captura local dos microfones reconhecidos pelo Windows 10/11 ou pelo ambiente de
áudio do Debian/Ubuntu. Microfone interno, matriz integrada, USB, headset e Bluetooth usam o mesmo
contrato `QAudioDevice`; hardware sem driver, bloqueado pela privacidade do sistema ou ocupado em
modo exclusivo não pode ser aberto pela aplicação.

Áudio do sistema/loopback não faz parte deste escopo. Nenhum áudio, vocabulário ou transcrição é
enviado a uma API.

## Fluxo do usuário

1. Selecione o microfone, o formato e o modelo de transcrição.
2. Opcionalmente informe nomes, siglas ou termos técnicos no campo de contexto.
3. Clique em **Gravar** e autorize o microfone quando solicitado.
4. Observe o cronômetro e o medidor. Corrija microfone distante, sinal baixo ou clipping antes de
   uma fala importante.
5. Use **Pausar/Retomar**; o tempo pausado não é inserido no arquivo.
6. Clique em **Parar**. O áudio é finalizado e convertido atomicamente no cache privado da sessão.
7. Use **Salvar áudio como...** para escolher nome/destino e/ou **Iniciar transcrição** manualmente.
8. A transcrição usa o WAV/PCM sem perdas mantido no cache, não o arquivo comprimido.
9. Revise as palavras de baixa confiança clicando nos timestamps para ouvir o trecho correspondente.

Estados canônicos:

```text
Pronto -> Ativando -> Gravando <-> Pausado -> Finalizando -> Pronto para salvar/transcrever
                                                       -> Transcrevendo -> Revisão
```

## Captura e encoding

- `QMediaDevices.audioInputs()` enumera as entradas e notifica conexão/remoção.
- `RecorderController` negocia PCM Int16, priorizando 48 kHz e até dois canais.
- `QAudioSource` fornece um `QIODevice`; blocos são lidos e gravados progressivamente em WAV.
- O buffer solicitado equivale a 40 ms de PCM e o estado **Gravando** só aparece após o primeiro
  bloco real, que já é preservado no WAV.
- Durante **Pausar**, o endpoint continua ativo e os blocos são drenados e descartados. Retomar não
  reinicializa o hardware, não reaproveita áudio antigo e não insere o intervalo pausado.
- O pico absoluto é convertido para dBFS. Menos de 5% gera aviso de sinal baixo; 98% ou mais gera
  aviso de possível clipping.
- O arquivo escolhido só é publicado após o FFmpeg concluir em um arquivo temporário no mesmo
  volume e `os.replace()` efetuar a substituição atômica.

| Opção da interface | Codec | Container | Bitrate |
| --- | --- | --- | --- |
| MP3 192 kbps | `libmp3lame` | MP3 | 192 kbit/s |
| MP3 320 kbps | `libmp3lame` | MP3 | 320 kbit/s |
| M4A AAC 256 kbps | AAC-LC | MPEG-4/M4A | 256 kbit/s |

Se o encoding falhar, o WAV permanece disponível e a GUI oferece **Salvar WAV recuperado**. Se a
transcrição falhar ou for cancelada, o cache de áudio permanece disponível durante a sessão.

## Estratégia de fidelidade

O modelo padrão é Whisper `large-v3` (1.550 milhões de parâmetros). `turbo` (809 milhões) permanece
como alternativa rápida. Todos usam idioma `pt`, transcrição literal, timestamps por palavra e
contexto entre janelas. A prioridade **Equilibrada** usa busca 3 no `turbo` e busca 5 nos demais;
**Velocidade** reduz a busca conforme o porte do modelo; **Maior fidelidade** usa busca 5,
`patience=1.2` e revisão reforçada. O
`hallucination_silence_threshold=1.0`
nativo do Whisper reduz hipóteses espúrias em pausas e no fim do arquivo sem aplicar VAD externo.

Além deles, a v0.3.0 oferece `medium` incorporado e `tiny`, `base`, `small` e `large-v3` por download
explícito. `medium` e `turbo` funcionam desde a instalação sem internet; os demais funcionam
offline depois da validação SHA-256 e publicação atômica no cache. Retirar `large-v3` dos pacotes
reduz 3.087.371.615 bytes de checkpoint em cada artefato sem alterar seu conteúdo ou precisão.
O contexto opcional é limitado a 1.000
caracteres, enviado como `initial_prompt` e não persistido.

PyTorch e Whisper são importados somente dentro do worker ao iniciar a transcrição. Na medição
local da v0.3.0, a janela ociosa caiu de aproximadamente 685 MB para 126 MB de memória residente.
Após uma conclusão bem-sucedida, somente o modelo usado permanece em cache por cinco minutos para
acelerar uma transcrição consecutiva; ao expirar, falhar, cancelar, trocar de modelo ou fechar, ele
é liberado e a RAM/VRAM é recuperada. O nome da GPU/CPU efetivamente escolhida aparece na interface.

Na RTX 5070 Laptop desta máquina, um WAV de 10 segundos no `large-v3` levou 21,56 segundos no
caminho frio, incluindo a leitura do checkpoint de 3,1 GB, e 6,17 segundos com o modelo já em
cache. A medição comprova uso CUDA, mas é um teste de desempenho com sinal sintético, não uma
medição de WER/CER.

O texto não recebe correção generativa posterior: uma reescrita gramatical poderia alterar o que
foi realmente dito. A aplicação mostra confiança, baixa confiança, cobertura e links de áudio para
permitir correção humana verificável.

Depois da inferência, uma proteção determinística descarta somente hipóteses cujo intervalo inteiro
tenha pico igual ou inferior a -72 dBFS. A remoção é contabilizada no resultado/Markdown; não usa
vocabulário proibido, não corrige frases e preserva fala baixa acima desse limiar elétrico.

A **Revisão seletiva** é opt-in nas prioridades Velocidade/Equilibrada e obrigatória em Maior
fidelidade. Quando ativada:

- segmentos com confiança média abaixo de 55%, `avg_logprob < -1.0` ou taxa de compressão acima de
  2,4 são candidatos;
- os trechos são reprocessados com margem de 0,5 a 0,75 segundo, `beam_size` 8 ou 10 e
  `patience=1.2`; palavras da margem são removidas antes da comparação para não duplicar falas;
- a nova hipótese só substitui a anterior se estiver preenchida, tiver compressão válida e superar
  a pontuação original em pelo menos 0,05, sem piorar a probabilidade de ausência de fala;
- o Markdown identifica cada segmento efetivamente substituído.

Redução de ruído, normalização agressiva, VAD externo e separação de voz não são aplicados por
padrão: podem remover fala baixa ou reforçar ruído. Um candidato só pode virar padrão se WER e CER
agregados não piorarem, uma métrica melhorar ao menos 2%, as alucinações em silêncio não aumentarem
e nenhuma fala válida desaparecer.

## Benchmark opt-in

O manifesto é JSONL, uma amostra autorizada por linha:

```json
{"audio":"amostras/reuniao.mp3","reference":"Texto literal esperado.","context":"OpenAI, PySide6","terms":["OpenAI","PySide6"]}
```

Execução:

```powershell
uv run --no-sync python -m scripts.benchmark_accuracy `.\benchmarks\amostras.jsonl `
  --models turbo large-v3 --priorities fast balanced max_fidelity `
  --include-selective-review --output benchmark-result.json
```

O relatório inclui WER, CER, acerto dos termos declarados, tempo, dispositivo e hipóteses por
amostra. Áudios privados devem ficar em `benchmarks/private/`, ignorado pelo Git. Nenhum corpus é
baixado implicitamente nem incluído nos instaladores.

## Permissões, recuperação e fechamento

- A permissão de microfone é consultada somente após **Gravar**.
- O MSIX declara exclusivamente `microphone`, além do `runFullTrust` já necessário ao pacote.
- Ausência de microfone, permissão negada, formato incompatível, dispositivo desconectado, falha de
  disco e falha do FFmpeg produzem mensagens distintas.
- A janela não fecha durante gravação, finalização ou transcrição.
- O cache da gravação é removido ao substituí-la ou fechar o aplicativo; salvar cria uma cópia no
  destino escolhido. Uma captura com falha é mantida até a decisão de recuperação.

## Critérios de aceite local

- lint, testes e `git diff --check` aprovados;
- os três formatos gerados e reconhecidos pelo FFmpeg;
- pausa não adiciona silêncio;
- gravação concluída habilita salvamento e transcrição manuais, sem iniciar modelo automaticamente;
- cancelamento preserva o áudio;
- player busca os links `audio://seek/<segundos>`;
- instaladores NVIDIA e CPU passam em `--self-check-output`;
- captura física só é marcada como aprovada quando um endpoint real puder ser aberto, sem simulação
  ou alteração automática das configurações de privacidade.

## Limitações honestas

Nenhum reconhecedor garante fidelidade perfeita. Ruído, reverberação, falas simultâneas, distância,
sotaques, nomes raros e clipping continuam exigindo revisão. Diarização, tradução, loopback do
sistema, macOS e ARM permanecem fora da v0.3.0.
