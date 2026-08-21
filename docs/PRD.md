# Documento de Requisitos de Produto (PRD)

## 1. Identificação

- **Produto:** Whisper Transcriber Desktop
- **Versão documentada:** v0.2.1
- **Plataformas:** Windows 10/11 x64 e Debian/Ubuntu x86-64
- **Idioma da interface e transcrição:** Português do Brasil
- **Status:** implementado, validado e publicado no GitHub Releases

## 2. Visão do produto

O Whisper Transcriber Desktop transforma um arquivo MP3/M4A em Markdown sem enviar o áudio para um
serviço de transcrição. O produto prioriza privacidade, simplicidade, interface responsiva,
aproveitamento do hardware disponível e informações que facilitem a revisão humana.

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

## 4. Requisitos funcionais

| ID | Requisito | Critério de aceite v0.2.1 |
| --- | --- | --- |
| RF01 | Seleção de áudio | Aceitar exatamente um `.mp3` ou `.m4a` por diálogo ou drag-and-drop, sem diferenciar maiúsculas. |
| RF02 | Modelo e idioma | Usar Whisper `turbo`, `task="transcribe"` e `language="pt"`. |
| RF03 | GPU/CPU | Detectar CUDA/ROCm/XPU quando o runtime permitir, mostrar o dispositivo real e usar CPU caso contrário. |
| RF04 | Primeiro uso | Resolver/baixar FFmpeg e baixar o modelo quando ausentes, com status indeterminado. |
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
- nenhum arquivo é salvo automaticamente;
- áudios, modelos, ambientes e binários gerados são ignorados pelo Git.

### Compatibilidade

- Python `>=3.11,<3.12` no código-fonte;
- Windows 10/11 x64 e Debian/Ubuntu x86-64;
- PyTorch 2.12.1;
- anexos Windows: NVIDIA CUDA 13 e CPU;
- anexos Linux: CPU;
- ROCm/XPU dependem de builds PyTorch específicos não publicados na v0.2.1.

## 6. Estratégia de qualidade do reconhecimento

Parâmetros canônicos:

```python
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
)
```

Os parâmetros são iguais entre backends, exceto a precisão FP16/FP32. Cobertura de 100% confirma o
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
- `WhisperTranscriber-Windows-x64.exe`: Windows CPU portátil;
- `WhisperTranscriber-Setup-Linux-x64.deb`: Debian/Ubuntu CPU instalável;
- `WhisperTranscriber-Linux-x64`: Linux CPU portátil;
- MSIX: envio ao Partner Center, não distribuição direta;
- checksums separados por plataforma/runtime.

O modelo `turbo` permanece fora dos pacotes e é baixado no primeiro uso.

## 9. Fora do escopo

- gravação de microfone;
- processamento em lote;
- diarização de locutores;
- tradução;
- formatos diferentes de MP3/M4A;
- edição de áudio;
- macOS, ARM e outras distribuições Linux;
- inclusão dos pesos do modelo no instalador;
- garantia de transcrição perfeita palavra por palavra.

## 10. Critérios de aceite final

- 55 testes e lint aprovados;
- GUI abre em tema escuro e aceita MP3/M4A;
- thread permanece responsiva durante transcrição;
- cancelamento conclui sem resultado parcial;
- dispositivo realmente usado aparece na interface/Markdown;
- Markdown pode ser editado, visualizado, copiado e salvo;
- instaladores Windows e DEB instalam, executam o autodiagnóstico e desinstalam;
- portáteis executam o autodiagnóstico;
- anexos publicados conferem com SHA-256;
- limitações de assinatura e runtime são informadas sem promessas indevidas.
