# Validação de Qualidade e Segurança

## 1. Escopo da evidência

Este documento consolida a validação da versão **v0.2.1**, commit
`7fe798c622e8a47c029edf529866268be9934ab8`.

- Release: <https://github.com/lucasitdias/whisper_desktop/releases/tag/v0.2.1>
- Pull request final: <https://github.com/lucasitdias/whisper_desktop/pull/5>
- Workflow final: <https://github.com/lucasitdias/whisper_desktop/actions/runs/32487388099>

## 2. Portões automatizados

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

## 3. Matriz de testes

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

## 4. Evidências de inferência real

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

## 5. Artefatos finais da release

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

## 6. MSIX da Microsoft Store

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

## 7. Controles de segurança

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

## 8. Smart App Control e assinatura

Os instaladores Windows GitHub não possuem Authenticode. Em runners Windows limpos, os pacotes
foram instalados, autoverificados e removidos. Em uma máquina local com Smart App Control ativo, o
Windows pode bloquear o novo hash antes da inicialização com código 4551.

Esse comportamento não deve ser contornado desativando a proteção. A solução confiável é:

- assinatura Authenticode por identidade reconhecida; ou
- aquisição do MSIX assinado pela Microsoft Store após publicação.

## 9. Aceitação manual

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
