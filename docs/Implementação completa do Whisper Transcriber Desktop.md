# Implementação completa do Whisper Transcriber Desktop

## Status da entrega

A implementação da versão pública **v0.3.0** foi concluída e aceita localmente em 24/08/2026.
Código, documentação e metadados identificam **Lucas Dias — Estudante de Ciência da Computação**
como autor e desenvolvedor. A publicação no GitHub e a submissão da edição Pro seguem os portões de
[entrega e publicação](ENTREGA_E_PUBLICACAO_V030.md).

## Funcionalidades entregues

- gravação em tempo real por microfones reconhecidos pelo sistema, com pausa sem inserir silêncio;
- salvamento manual em MP3 192/320 kbps ou M4A AAC 256 kbps e recuperação do PCM/WAV;
- transcrição manual de gravações ou arquivos MP3/M4A, sem congelar a interface;
- catálogo multilíngue `tiny`, `base`, `small`, `medium`, `turbo` e `large-v3`;
- `medium` e `turbo` incorporados e offline; demais modelos por download explícito e verificado;
- prioridades Velocidade, Equilibrada e Maior fidelidade, contexto opcional e revisão seletiva;
- timestamps por palavra, proteção contra alucinação em silêncio e revisão assistida pelo player;
- detecção de NVIDIA CUDA, AMD ROCm, Intel XPU ou CPU conforme o runtime instalado;
- fallback GPU para CPU e monitor de tempo, CPU, RAM, GPU e VRAM;
- Markdown editável, visualização sincronizada, salvamento atômico e resultado expansível;
- FFmpeg estático validado por SHA-256, autodiagnóstico e cancelamento cooperativo;
- instaladores Windows NVIDIA/CPU, portáteis Windows/Linux, DEB Linux e MSIX para Partner Center;
- CI Windows/Linux, instalação/desinstalação real, checksums e publicação por tag.

## Dependências e versões

| Componente | Versão/perfil |
| --- | --- |
| Aplicação | `0.3.0` |
| MSIX de homologação | `1.3.4.0` |
| Python | `>=3.11,<3.12` |
| OpenAI Whisper | `20250625` |
| PyTorch | `2.12.1` |
| Ambiente Windows principal | CUDA 13.0 |
| PySide6 | `>=6.8,<7` |
| PyInstaller | `>=6.16,<7` |
| FFmpeg | `8.1.2-34-g9b6c8969e0` |
| Gerenciador | `uv` + `uv.lock` |

CUDA, ROCm, XPU e CPU são distribuições separadas do PyTorch. Os pacotes oficiais v0.3.0 oferecem
NVIDIA CUDA 13 e CPU; ROCm/XPU continuam disponíveis no código quando o ambiente usa a wheel
correspondente.

## Artefatos aceitos localmente

| Bundle de homologação | Bytes | SHA-256 |
| --- | ---: | --- |
| `WhisperTranscriber-Setup-Windows-x64-Offline.zip` | 4.951.754.218 | `20daa4953e12c6373fc1c5bf6ed3775971c1b8d0c79437d1051cb12e4443a304` |
| `WhisperTranscriber-Setup-Windows-x64-CPU-Offline.zip` | 3.373.852.644 | `bb3d2a53cfae631731cb21db7596374748052fe2f33378497d7c0b2c3ac6827d` |

Na GitHub Release, o launcher e as fatias Inno são anexos separados e os demais arquivos acima de
2 GiB são divididos em partes numeradas. Isso respeita o limite do canal sem alterar o instalador
testado. Os manifestos SHA-256 registram a integridade do arquivo completo.

## Validação concluída

- Ruff, `git diff --check` e 131 testes aprovados no candidato final aceito;
- autodiagnóstico dos runtimes NVIDIA CUDA 13 e CPU;
- instalação, execução e desinstalação sequencial dos dois instaladores Windows;
- inferência real em CUDA e CPU, controle de silêncio e fallback;
- gravação física Realtek em PCM 48 kHz e conversão MP3 válida;
- integridade CRC dos bundles e SHA-256 recalculado;
- auditoria de dependências, segredos, arquivos versionáveis e ações do CI;
- MSIX técnico instalado e autodiagnosticado com certificado local de homologação.

Evidências detalhadas permanecem em [VALIDACAO_QUALIDADE_SEGURANCA.md](VALIDACAO_QUALIDADE_SEGURANCA.md).

## Distribuição e licença

- A edição gratuita da Store permanece no produto `9PHWS6MM59BG`, versão `1.2.4.0`.
- A edição Pro v0.3.0 deve usar outro produto e preço brasileiro de R$ 25,99.
- O MSIX de homologação com identidade gratuita não pode ser submetido como Pro.
- Instaladores GitHub sem Authenticode podem ser bloqueados; a proteção do Windows não deve ser
  desativada.
- O projeto é licenciado sob MIT, com copyright de Lucas Dias. Cópias ou partes substanciais devem
  preservar o aviso e o texto de `LICENSE`.
- Dependências e pesos seguem também os termos de `THIRD_PARTY_NOTICES.md`.

## Limites assumidos

- sem diarização, tradução, processamento em lote ou captura de áudio do sistema;
- somente MP3/M4A e um arquivo por vez;
- Windows/Linux x86-64; sem macOS/ARM;
- nenhum reconhecedor automático garante fidelidade literal para todo áudio;
- publicação e aquisição na Store dependem da certificação externa da Microsoft.

## Histórico

A v0.2.1 permanece como marco histórico da edição gratuita. Ela não representa o conjunto de
recursos, modelos nem os artefatos finais da v0.3.0.
