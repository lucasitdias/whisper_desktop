# Documento de Requisitos de Produto (PRD)

> Autor e desenvolvedor: **Lucas Dias — Estudante de Ciência da Computação**.

## 1. Identificação

- **Produto:** Whisper Transcriber Desktop
- **Versão documentada:** v0.3.0 final
- **Plataformas:** Windows 10/11 x64 e Debian/Ubuntu x86-64
- **Idioma da interface e transcrição:** Português do Brasil
- **Status:** implementado e aceito localmente; publicação controlada pelos portões da entrega
- **Autor:** Lucas Dias — Estudante de Ciência da Computação

## 2. Visão do produto

O Whisper Transcriber Desktop grava microfones reconhecidos pelo sistema ou transforma um arquivo
MP3/M4A em Markdown sem enviar o áudio para um serviço. O produto prioriza privacidade, fidelidade,
interface responsiva, aproveitamento do hardware e revisão humana orientada pelo áudio.

Público principal:

- participantes de reuniões e entrevistas;
- estudantes e professores;
- produtores de conteúdo e podcasts;
- usuários de notas de voz;
- profissionais que precisam de um rascunho local com timestamps.

## 3. Objetivos

1. Transcrever integralmente um áudio compatível sem congelar a GUI.
2. Usar GPU quando o runtime instalado realmente suportar o dispositivo e CPU caso contrário.
3. Permitir cancelamento seguro de operações longas.
4. Entregar Markdown editável, copiável e persistido com segurança.
5. Tornar a cobertura e os pontos de baixa confiança visíveis para revisão.
6. Disponibilizar opções instaláveis e portáteis para Windows/Linux.
7. Gravar, pausar, retomar e finalizar áudio ambiente nos formatos MP3/M4A.
8. Manter a captura PCM sem perdas em cache e transcrevê-la somente após ação explícita do usuário.

## 4. Requisitos funcionais

| ID | Requisito | Critério de aceite v0.3.0 |
| --- | --- | --- |
| RF01 | Seleção de áudio | Aceitar exatamente um `.mp3` ou `.m4a` por diálogo ou drag-and-drop, sem diferenciar maiúsculas. |
| RF02 | Modelo e idioma | Oferecer `tiny`, `base`, `small`, `medium`, `turbo` e `large-v3` (padrão), com `task="transcribe"` e `language="pt"`. |
| RF03 | GPU/CPU | Detectar CUDA/ROCm/XPU quando o runtime permitir, mostrar o dispositivo real e usar CPU caso contrário. |
| RF04 | Primeiro uso | Usar `medium` e `turbo` incorporados; baixar `tiny`, `base`, `small` e `large-v3` somente após ação explícita, com progresso e cancelamento. |
| RF05 | Assincronismo | Executar decodificação, modelo e inferência em `QThread`. |
| RF06 | Progresso | Exibir etapa, percentual calculado pelos timestamps e trechos incrementais. |
| RF07 | Markdown | Gerar metadados, texto integral, indicadores e segmentos temporais. |
| RF08 | Resultado | Permitir editar, visualizar, copiar e salvar `.md`. |
| RF09 | Persistência | Confirmar sobrescrita e usar gravação UTF-8 atômica. |
| RF10 | Cancelamento | Interromper cooperativamente, sem `terminate()` e sem publicar resultado parcial. |
| RF11 | Integridade | Exibir duração processada, cobertura, última fala e confiança estimada por palavra. |
| RF12 | Fallback | Reiniciar em CPU após falta de memória no acelerador. |
| RF13 | Diagnóstico | Expor `--self-check` e `--self-check-output` sem abrir a GUI ou baixar o modelo. |
| RF14 | Distribuição | Gerar instaladores/portáteis Windows e Linux com FFmpeg e runtime declarados. |
| RF15 | Segurança de fechamento | Impedir fechamento silencioso enquanto o worker está ativo. |
| RF16 | Microfones | Enumerar entradas do sistema e atualizar conexão/remoção. |
| RF17 | Gravação | Iniciar, pausar/retomar sem silêncio e parar captura PCM progressiva. |
| RF18 | Encoding | Gerar MP3 192/320 kbps ou M4A AAC 256 kbps por escrita atômica. |
| RF19 | Controle | Após parar, manter o áudio em cache e oferecer salvamento e transcrição manuais. |
| RF20 | Qualidade | Mostrar nível, clipping, contexto opcional, prioridades Velocidade/Equilibrada/Maior fidelidade e pontos de baixa confiança. |
| RF21 | Revisão | Reproduzir o áudio e buscar timestamps a partir da visualização. |
| RF22 | Recuperação | Preservar WAV quando a conversão falhar e o áudio final ao cancelar texto. |
| RF23 | Integridade de modelo | Resolver incorporado, cache validado ou download autorizado; usar `.part`, SHA-256 e publicação atômica. |
| RF24 | Resultado expansível | Permitir redimensionar o resultado e focá-lo sem perder texto, aba, rolagem, edição ou reprodução. |

## 5. Requisitos não funcionais

### Usabilidade

- interface e mensagens operacionais em pt-BR;
- tema escuro e suporte High-DPI;
- estado dos controles coerente com o ciclo de vida do worker;
- erro técnico traduzido em mensagem acionável sempre que possível.

### Desempenho

- a GUI não pode executar inferência na thread principal;
- GPU usa FP16 e CPU usa FP32;
- o áudio deve ser decodificado apenas uma vez por tentativa;
- progresso deve refletir o tempo do áudio, não um temporizador artificial.

### Privacidade e segurança

- áudio e transcrição permanecem locais;
- nenhum subprocesso usa `shell=True`;
- binários externos têm URL e checksum fixados;
- extração de FFmpeg é limitada ao membro esperado;
- caminho absoluto do áudio não entra no Markdown;
- nenhum arquivo é salvo sem destino escolhido ou ação explícita do usuário;
- áudios, modelos, ambientes e binários gerados são ignorados pelo Git.

### Compatibilidade

- Python `>=3.11,<3.12` no código-fonte;
- Windows 10/11 x64 e Debian/Ubuntu x86-64;
- PyTorch 2.12.1;
- anexos Windows: NVIDIA CUDA 13 e CPU;
- anexos Linux: CPU;
- ROCm/XPU dependem de builds PyTorch específicos não incorporados aos anexos v0.3.0.

## 6. Estratégia de qualidade do reconhecimento

Parâmetros canônicos:

```python
model = whisper.load_model(caminho_local_validado)  # sem download implícito
model.transcribe(
    audio,
    language="pt",
    task="transcribe",
    verbose=True,
    fp16=device != "cpu",
    beam_size=5,
    best_of=5,
    condition_on_previous_text=True,
    word_timestamps=True,
    initial_prompt=contexto or None,
)
```

O exemplo representa a prioridade de maior fidelidade. A prioridade **Velocidade** reduz a busca;
**Equilibrada** aplica busca 3 no `turbo` e busca 5 nos demais; **Maior fidelidade** aplica busca 5,
`patience=1.2` e revisão seletiva obrigatória. Os parâmetros são iguais entre backends, exceto a
precisão FP16/FP32. Cobertura de 100% confirma o
processamento da duração decodificada, mas não garante equivalência literal com a fala. Revisão
humana continua obrigatória para conteúdo crítico.

## 7. Saída Markdown

Estrutura mínima:

```markdown
# Transcrição de Áudio - reunião

- **Data da Transcrição:** 2026-08-21 10:30:00 -03
- **Arquivo de Origem:** `reunião.m4a`
- **Duração do Áudio:** 00:42:17
- **Modelo Utilizado:** Whisper `turbo` (809M parâmetros)
- **Idioma Configurado:** Português do Brasil (`pt`)
- **Processamento:** GPU NVIDIA (CUDA)
- **Cobertura do Processamento:** 100.0%

---

## Transcrição Completa

Texto completo.

---

## Transcrição com Marcadores Temporais (Timestamps)

- **[00:00:00 -> 00:00:05]** Primeiro trecho.
```

Somente o nome-base do arquivo pode aparecer na saída.

## 8. Distribuição

- `WhisperTranscriber-Setup-Windows-x64.exe`: NVIDIA CUDA 13 com fallback CPU;
- `WhisperTranscriber-Setup-Windows-x64-CPU.exe`: Windows CPU instalável;
- `WhisperTranscriber-Windows-x64.zip`: diretório portátil Windows CPU;
- `WhisperTranscriber-Setup-Linux-x64.deb`: Debian/Ubuntu CPU instalável;
- `WhisperTranscriber-Linux-x64.tar.gz`: diretório portátil Linux CPU;
- MSIX: envio ao Partner Center, não distribuição direta;
- checksums separados por plataforma/runtime.

`medium` e `turbo` são incorporados aos pacotes. `tiny`, `base`, `small` e `large-v3` ficam no
cache persistente somente após download explícito e continuam válidos após atualização.

## 9. Fora do escopo

- processamento em lote;
- diarização de locutores;
- tradução;
- entrada de arquivo em formatos diferentes de MP3/M4A;
- captura do áudio reproduzido pelo computador/loopback;
- edição de áudio;
- macOS, ARM e outras distribuições Linux;
- garantia de transcrição perfeita palavra por palavra.

## 10. Critérios de aceite final

- 131 testes e lint aprovados no candidato final aceito da v0.3.0;
- GUI abre em tema escuro e aceita MP3/M4A;
- thread permanece responsiva durante transcrição;
- cancelamento conclui sem resultado parcial;
- dispositivo realmente usado aparece na interface/Markdown;
- Markdown pode ser editado, visualizado, copiado e salvo;
- instaladores Windows e DEB instalam, executam o autodiagnóstico e desinstalam;
- portáteis executam o autodiagnóstico;
- anexos publicados conferem com SHA-256;
- limitações de assinatura e runtime são informadas sem promessas indevidas.
