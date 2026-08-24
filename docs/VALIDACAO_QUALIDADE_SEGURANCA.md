# Validação de Qualidade e Segurança

> Autor e desenvolvedor: **Lucas Dias — Estudante de Ciência da Computação**.

## Validação final v0.3.0

A v0.3.0 foi aceita localmente em 24/08/2026. A tag/release e a submissão Pro permanecem etapas de
publicação posteriores aos portões deste documento. Foram
adicionados testes para PCM/WAV incremental, buffer de baixa latência, pausa com endpoint ativo,
telemetria, formatos FFmpeg, publicação atômica, recuperação, perfis de modelo, contexto, segunda
passagem, links do player e estados da GUI.

O candidato reduzido atual mantém `medium` e `turbo` incorporados e move `large-v3` para download
explícito. Também acrescenta as prioridades Velocidade, Equilibrada e Maior fidelidade; esta última
usa busca 5, `patience=1.2` e segunda passagem com margem temporal. A tabela histórica identificada
como candidato anterior ainda descreve o pacote que incorporava três checkpoints e permanece
separada da evidência final reduzida a seguir.

### Candidato final reduzido de 24/08/2026

Os builds Windows foram gerados novamente após a limpeza dos diretórios intermediários. Ruff,
`git diff --check` e **131 testes** passaram. Os dois ZIPs foram lidos integralmente sem erro de
CRC e o manifesto `SHA256SUMS-v0.3.0-FINAL.txt` foi recalculado e conferido arquivo a arquivo.
Os bundles foram reempacotados depois da definição da Licença MIT. As instalações finais CPU e
CUDA contêm `LICENSE` e `THIRD_PARTY_NOTICES.md`; ambas retornaram autodiagnóstico `ok` e foram
desinstaladas após o aceite.

| Bundle final | Bytes | SHA-256 |
| --- | ---: | --- |
| `WhisperTranscriber-Setup-Windows-x64-Offline.zip` | 4.951.754.218 | `20daa4953e12c6373fc1c5bf6ed3775971c1b8d0c79437d1051cb12e4443a304` |
| `WhisperTranscriber-Setup-Windows-x64-CPU-Offline.zip` | 3.373.852.644 | `bb3d2a53cfae631731cb21db7596374748052fe2f33378497d7c0b2c3ac6827d` |

A variante CPU foi instalada em diretório isolado, retornou runtime `CPU`, autodiagnóstico `ok`
e foi removida sem resíduos. A variante CUDA foi instalada como atualização principal, retornou
`NVIDIA CUDA 13.0`, identificou a `NVIDIA GeForce RTX 5070 Laptop GPU` e manteve `medium` e
`turbo` incorporados. O instalador migrou o checkpoint legado `large-v3` íntegro para o cache do
usuário, preservando seus 3.087.371.615 bytes sem exigir novo download.

A separação das fatias CUDA e CPU recebeu regressão automatizada: cada launcher seleciona apenas
arquivos numerados que compartilham exatamente seu nome-base. O ciclo instalado confirmou que a
variante CPU encontra as duas fatias corretas mesmo quando os artefatos CUDA estão na mesma pasta.

Na revisão de segurança, os downloads de modelos e FFmpeg permanecem em HTTPS, com SHA-256 e
publicação atômica; respostas acima do tamanho esperado agora são interrompidas antes de ocupar
espaço indefinido. Nenhum subprocesso usa shell, e as ações externas dos workflows foram fixadas
por commit imutável. A varredura do conteúdo publicável não encontrou credenciais, chaves privadas
ou referências de autoria automatizada.

A auditoria de dependências não encontrou achado crítico ou alto alcançável pelo aplicativo. O
alerta `PYSEC-2026-3447` em `setuptools 81.0.0` trata da geração de `sdist` em APFS/HFS+ no macOS;
o produto empacotado atende Windows/Linux e não gera pacotes-fonte em execução. O PyTorch exige
`setuptools<82`, portanto uma troca isolada quebraria a resolução oficial. O alerta baixo
`CVE-2025-3000` envolve `torch.jit.script`, API que a aplicação não chama; checkpoints aceitos são
os oficiais fixados e validados por tamanho e SHA-256. Esses itens devem ser reavaliados junto da
próxima atualização compatível do PyTorch, sem trocar o runtime desta candidata já aceita.

O áudio físico praticamente silencioso (-90,3 dBFS) inicialmente produziu `Obrigado.` no `turbo`.
A proteção objetiva de -72 dBFS descartou a hipótese; depois do ajuste, `turbo` e `large-v3`
retornaram texto vazio e registraram um descarte sobre silêncio, ambos usando CUDA.

Na medição da candidata v0.3.0, a janela ociosa usou 129,4 MB de working set e 82,2 MB de memória
privada. CPU/RAM do processo e, em NVIDIA, GPU/VRAM total permanecem visíveis no monitor sem
carregar PyTorch na abertura.

Os executáveis pré-instalador passaram no autodiagnóstico CUDA e CPU. O candidato MSIX técnico
`1.3.4.0` foi assinado com certificado de teste local, instalado e registrado pelo Windows com
status `Ok`. A versão pública exibida continua `0.3.0`. Esse certificado serve somente para aceite
nesta máquina; a edição Pro precisa receber assinatura confiável do canal de distribuição antes de
ser disponibilizada a terceiros.

O autodiagnóstico do MSIX instalado retornou `status: ok`, FFmpeg empacotado, gravação disponível,
`NVIDIA GeForce RTX 5070 Laptop GPU` e runtime `NVIDIA CUDA 13.0`. A interface instalada foi aberta
com êxito em 23/08/2026; gravação e transcrição reais permanecem sob aceite manual do usuário.

O MSIX técnico `1.3.4.0` e os instaladores Inno Setup usam versão pública `0.3.0` e desenvolvedor
`Lucas Dias`. O MSIX e os launchers dos instaladores foram assinados e verificados sem erro com o
certificado de teste autorizado nesta máquina. O MSIX foi atualizado com status `Ok`; os
instaladores CUDA e CPU foram instalados, autoverificados e removidos sequencialmente. Ao final, a
variante CUDA foi reinstalada em `%LOCALAPPDATA%\Programs\Whisper Transcriber Desktop` para o teste
visual do usuário.

| Artefato local v0.3.0 anterior, com `large-v3` incorporado | Bytes | SHA-256 |
| --- | ---: | --- |
| `WhisperTranscriber-Setup-Windows-x64-Offline.zip` | 8.039.128.687 | `2d966df8e9a34adf09a046800cdbd56d7b5a4ff99896178694dccee33fe893ca` |
| `WhisperTranscriber-Setup-Windows-x64-CPU-Offline.zip` | 6.461.217.448 | `0b5bd25af74e2ee95bedcebf4119a596cf61725a0592ead6672535c2f8ed9566` |
| `WhisperTranscriber-Windows-x64.zip` | 7.175.094.636 | `e70840704733e0647749e6fa02e474688f6283284591966584c2acb8c4751200` |
| `WhisperTranscriber-Desktop-0.3.0-Windows-x64.msix` | 7.896.794.378 | `8ecd815dcdea63f9e80b0b16caf1bf815a52c80cbf951437352b5a8200b7519c` |
| `WhisperTranscriber-Linux-x64.tar.gz` | 6.465.728.539 | `bbd41865763b1143a6b4beef429a9dbf317272d98f2d254aab5b9db2ded54125` |
| `WhisperTranscriber-Setup-Linux-x64.deb` | 6.465.250.906 | `3a864e035d4192359c6011d945719ae3b0bae2d9156c24f9594e08149ec48381` |

No candidato anterior, **114 testes** passaram no Windows; os 112 casos anteriores às duas proteções
extras de benchmark/DPI também passaram em Debian 12. Uma inferência curta e real
sobre silêncio autorizado confirmou, sem rede, os três modelos então incorporados em CUDA e CPU e os três
modelos opcionais em CUDA. Os resultados vazios confirmam o controle contra alucinação em silêncio;
essa amostra valida carregamento, backend e cobertura temporal, não precisão linguística. WER/CER
continua exigindo um corpus pt-BR com áudio e referência textual autorizados.

O pacote DEB anterior de 6.465.250.906 bytes foi criado em Debian 12, instalado, executou o autodiagnóstico
com `medium`, `turbo` e `large-v3` marcados como `bundled`, e foi removido. O portátil Linux também
passou no mesmo autodiagnóstico CPU. PipeWire não estava presente no contêiner, portanto a captura
física Linux permanece um aceite de hardware, sem evidência simulada.

Uma segunda instalação do DEB foi executada em Debian 12 e teve a rede do contêiner desconectada
antes da inferência. Os checkpoints foram lidos diretamente de `/opt/whisper-transcriber/_internal/
assets/models`: `medium` concluiu em 9,334 s, `turbo` em 14,260 s e `large-v3` em 65,204 s. Todos
processaram 100% do WAV silencioso de 1 s e retornaram texto vazio em CPU. O contêiner foi removido
depois da evidência.

| Inferência real em WAV silencioso de 1 s | CUDA RTX 5070 | CPU forçada |
| --- | ---: | ---: |
| `medium` incorporado | 9,446 s | 9,405 s |
| `turbo` incorporado | 6,075 s | 16,482 s |
| `large-v3` incorporado no candidato anterior | 15,539 s | 22,440 s |
| `tiny` opcional | 7,651 s | — |
| `base` opcional | 5,208 s | — |
| `small` opcional | 1,354 s | — |

Os seis resultados tiveram cobertura temporal de 100% e texto vazio. Os tempos incluem custos de
carregamento e não devem ser comparados como benchmark definitivo de velocidade relativa; o
objetivo desta execução curta foi provar checkpoint íntegro, inferência local e controle de
silêncio.

O Windows App Certification Kit `10.0.19041.5609` concluiu a execução integral (`PARTIAL_RUN=false`)
com resultado geral `WARNING`. Assinatura, UAC, manifesto MSIX, recursos, segurança, arquitetura,
identidade visual e metadados passaram. O teste opcional **Executáveis bloqueados** marcou `FAIL`
porque Python, Qt, PyTorch e o próprio aplicativo referenciam `CreateProcess`/`ShellExecute`, usados
legitimamente para o FFmpeg e integrações locais; o mesmo teste terminou com `OverflowException` do
WACK ao analisar o pacote com checkpoint de 3,1 GB. Remover essas APIs quebraria a conversão de
áudio e não representa correção válida.

O executável foi reconstruído com `PerMonitorV2,PerMonitor`, `asInvoker` e `longPathAware`; o
manifesto incorporado foi extraído e conferido com `mt.exe`. Mesmo assim, o WACK registrou que não
conseguiu processar o binário PyInstaller e manteve um aviso de DPI. A evidência fica em
`dist/validation/WACK-v0.3.0-final.xml`; a certificação definitiva continua pertencendo ao Partner
Center.

O pacote local contém `ffmpeg.exe`, mas não `ffprobe.exe`. A validação equivalente decodificou com
FFmpeg os três arquivos gerados e confirmou MP3 192 kbps, MP3 320 kbps e M4A/AAC-LC com alvo de
256 kbps; a verificação nominal com FFprobe permanece pendente onde o binário estiver disponível.

Após o teste do usuário, a transcrição automática foi removida, a gravação passou a permanecer em
cache até salvamento/transcrição manual e o desligamento do dispositivo passou a desconectar
`readyRead` antes de fechar o WAV. PyTorch/Whisper agora são carregados sob demanda. Na mesma
máquina, a janela ociosa caiu de aproximadamente 685 MB para 126 MB de memória residente.

Portões executados antes de considerar a versão local concluída:

- Ruff, pytest e `git diff --check`;
- `--self-check-output` nos executáveis NVIDIA e CPU;
- FFmpeg real gerando MP3 192, MP3 320 e M4A AAC 256 a partir de WAV conhecido;
- instalação/desinstalação sequencial dos dois instaladores;
- captura física somente quando o endpoint puder ser aberto pelo sistema.

Na sessão de desenvolvimento de 2026-08-23, o Windows enumerou e abriu `Grupo de microfones
(Realtek(R) Audio)` com Qt, gravou PCM 48 kHz estéreo e gerou MP3 192 kbps válido. A captação de
fala e os hardwares Linux/USB/Bluetooth ainda dependem de aceite físico do usuário e não são
declarados como validados por simulação.

O benchmark usa somente manifestos e áudios autorizados. Resultados e amostras privadas são
ignorados pelo Git. A revisão seletiva permanece opcional em Velocidade/Equilibrada e é obrigatória
em Maior fidelidade; a aceitação definitiva dos parâmetros continua condicionada a WER/CER no
corpus autorizado da especificação v0.3.0.

## Histórico de validação da v0.2.1

As seções abaixo preservam a evidência da edição gratuita v0.2.1 e não substituem os resultados
finais v0.3.0 apresentados acima.

### 1. Escopo da evidência

Este documento consolida a validação da versão **v0.2.1**, commit
`7fe798c622e8a47c029edf529866268be9934ab8`.

- Release: <https://github.com/lucasitdias/whisper_desktop/releases/tag/v0.2.1>
- Pull request final: <https://github.com/lucasitdias/whisper_desktop/pull/5>
- Workflow final: <https://github.com/lucasitdias/whisper_desktop/actions/runs/32487388099>

### 2. Portões automatizados

Todo push e pull request executa em Windows e Linux:

1. Python 3.11;
2. perfil PyTorch CPU reproduzível;
3. `ruff check .`;
4. 55 testes `pytest`/`pytest-qt` com Qt offscreen;
5. download e verificação do FFmpeg;
6. `main.py --self-check`.

A tag `v0.2.1` acrescentou:

- build Windows NVIDIA CUDA 13;
- build Windows CPU instalável e portátil;
- build Linux CPU portátil e DEB;
- instalação, autodiagnóstico e desinstalação dos dois instaladores Windows;
- instalação, autodiagnóstico e remoção do DEB;
- autodiagnóstico dos portáteis;
- geração de três manifestos SHA-256;
- publicação de nove anexos.

Resultado do workflow final: **aprovado**.

### 3. Matriz de testes

### FFmpeg

- precedência PyInstaller, checkout, `PATH` e cache;
- plataforma não suportada;
- checksum correto/incorreto;
- download atômico;
- extração restrita sem path traversal;
- validação por `ffmpeg -version`;
- fallback e cache verificado.

### Worker Whisper

- CUDA, ROCm, XPU e CPU simulados;
- nome real do dispositivo e runtime incorporado;
- parâmetros de qualidade;
- progresso por timestamps;
- segmentos incrementais;
- palavras/confiança;
- falta de memória e reinício CPU;
- erro de driver;
- falha de download;
- cancelamento antes/durante inferência;
- sinais `completed`, `failed` e `cancelled`.

### Exportador

- Unicode e nomes com caracteres especiais;
- remoção de caminho absoluto;
- duração e timestamps acima de uma hora;
- segmentos vazios;
- cobertura, confiança e baixa confiança;
- escrita UTF-8 atômica e limpeza após falha.

### Interface

- seleção por diálogo e drag-and-drop;
- extensões em diferentes caixas;
- estados dos botões;
- execução não bloqueante;
- botão de cancelamento;
- proteção de fechamento;
- abas Markdown/Visualização;
- sincronização após edição;
- cópia, salvamento, extensão `.md` e confirmação de sobrescrita;
- mensagens em pt-BR.

### Build e arquivos do projeto

- identidade/versão do MSIX;
- nomes distintos dos instaladores NVIDIA/CPU;
- inclusão dos downloads/checksums no workflow;
- pacote DEB e atalho da Store;
- ausência de padrões de branch não permitidos no CI.

### 4. Evidências de inferência real

Validação local em Windows 11 com NVIDIA GeForce RTX 5070 Laptop GPU:

- FFmpeg estático 8.1.2 validado;
- runtime `NVIDIA CUDA 13.0` detectado;
- MP3 autorizado de 60 segundos processado integralmente;
- cancelamento durante carregamento aprovado sem resultado parcial;
- cancelamento durante inferência de áudio longo aprovado após saída incremental;
- GPU e CPU produziram o mesmo texto na amostra de regressão;
- 22 segmentos, 146 palavras e última fala em 00:59,980;
- GPU: 13,71 s e confiança média estimada de 90,83%;
- CPU: 51,37 s e confiança média estimada de 90,80%.

Essa evidência demonstra equivalência na amostra, não garantia de fidelidade universal. M4A real
continua fazendo parte do aceite manual por formato.

### 5. Artefatos finais da release v0.2.1

| Artefato | Bytes | SHA-256 verificado após download |
| --- | ---: | --- |
| `WhisperTranscriber-Setup-Windows-x64.exe` | 1.798.357.601 | `88d2739535156d679f36afdae5a2187b671ddc76416080c9b62d20dd9124fbbd` |
| `WhisperTranscriber-Setup-Windows-x64-CPU.exe` | 220.426.772 | `6b00c4d26a8d0686511f51090fb43e36074a327ebd039ca10f982935ae83df96` |
| `WhisperTranscriber-Windows-x64.exe` | 317.271.727 | `4824f87090e76b9f6e1800f005224ab44b80db91cd78f5c18807e4a5b8b7a0f5` |
| `WhisperTranscriber-Setup-Linux-x64.deb` | 612.959.506 | `9161ae8e30a9da0fffe62876d2a7560697ed8891f9de8c902c8cf6f85061e2db` |
| `WhisperTranscriber-Linux-x64` | 630.137.840 | `5b49c278a2663d46826afb7a8ad21ff2fb135fc251c4e1a4c4fc32705534f0ed` |

Auditoria pós-publicação:

- 9/9 anexos presentes;
- cinco binários baixados da própria release;
- todos os hashes recalculados localmente;
- todos os hashes iguais aos três manifestos publicados;
- atalho da Store contendo o produto `9PHWS6MM59BG`.

### 6. MSIX da Microsoft Store v0.2.1

- versão pública: 0.2.1;
- versão técnica: `1.2.4.0`;
- tamanho do candidato: 2.149.611.092 bytes;
- SHA-256: `199DF03410371E8C22D74B75EA49AC9278D59B2504AC63FCBBF3ADCD64ADB3F9`;
- identidade, arquitetura, manifesto e executável verificados;
- 15 testes estáticos aplicáveis do WACK com resultado `Pass`.

Pendente de evidência externa até publicação efetiva:

- página permitindo aquisição;
- instalação pela Microsoft Store;
- atualização e desinstalação pelo canal Store.

### 7. Controles de segurança

- nenhum subprocesso usa `shell=True`;
- URLs e SHA-256 do FFmpeg são fixados;
- extração limitada ao membro esperado;
- arquivos temporários usam substituição atômica;
- caminhos absolutos não entram no Markdown;
- áudio e texto permanecem locais;
- pesos, áudios, binários e ambientes são ignorados;
- nenhuma sobrescrita pela GUI sem confirmação;
- cancelamento não força encerramento da thread;
- dependências de desenvolvimento são travadas por `uv.lock`;
- CI usa permissões `contents: read`, elevando para `write` apenas no job de release.

### 8. Smart App Control e assinatura

Os instaladores Windows GitHub não possuem Authenticode. Em runners Windows limpos, os pacotes
foram instalados, autoverificados e removidos. Em uma máquina local com Smart App Control ativo, o
Windows pode bloquear o novo hash antes da inicialização com código 4551.

Esse comportamento não deve ser contornado desativando a proteção. A solução confiável é:

- assinatura Authenticode por identidade reconhecida; ou
- aquisição do MSIX assinado pela Microsoft Store após publicação.

### 9. Aceitação manual da v0.2.1

- [x] abrir a GUI em tema escuro e High-DPI;
- [x] selecionar MP3 por diálogo/drag-and-drop;
- [x] manter a GUI responsiva durante inferência;
- [x] identificar RTX 5070 como NVIDIA CUDA;
- [x] comparar a mesma amostra em GPU/CPU;
- [x] cancelar carregamento e inferência sem resultado parcial;
- [x] editar, visualizar, copiar e salvar Markdown;
- [x] validar instaladores Windows em CI limpo;
- [x] validar portátil/DEB Linux em CI limpo;
- [x] conferir todos os anexos e hashes da release;
- [ ] transcrever M4A real autorizado na versão final;
- [ ] adquirir e instalar pela Store depois da publicação Microsoft.

O modelo real não é baixado no CI para evitar custo, tráfego e uso de áudio não autorizado.
