# Avisos de terceiros

O Whisper Transcriber Desktop utiliza e, nos artefatos binários, distribui componentes de
terceiros. Este arquivo deve acompanhar os instaladores.

## OpenAI Whisper

- Projeto: <https://github.com/openai/whisper>
- Versão Python: `20250625`
- Licença do código: MIT
- Modelo utilizado: `turbo`
- Os pesos são baixados no primeiro uso e não são incorporados ao repositório ou instaladores.

## PyTorch

- Projeto: <https://pytorch.org/>
- Versão: `2.12.1`
- Licença: BSD 3-Clause
- Perfis distribuídos: CUDA 13 no instalador NVIDIA e CPU nos demais pacotes.
- ROCm/XPU não estão incorporados aos anexos v0.2.1.

## Qt for Python / PySide6

- Projeto: <https://doc.qt.io/qtforpython-6/>
- Faixa utilizada: `>=6.8,<7`
- Licenciamento: LGPLv3/GPLv3 ou comercial, conforme os termos do Qt.
- O aplicativo usa carregamento dinâmico das bibliotecas fornecidas pelo pacote PySide6.

## FFmpeg

- Projeto: <https://ffmpeg.org/>
- Build estático: <https://github.com/BtbN/FFmpeg-Builds>
- Versão: `8.1.2-34-g9b6c8969e0`
- Release: `autobuild-2026-07-31-14-10`
- Variante: LGPL
- O executável permanece um programa separado, invocado por subprocesso sem `shell=True`.

## PyInstaller

- Projeto: <https://pyinstaller.org/>
- Faixa utilizada: `>=6.16,<7`
- Licença: GPL com exceção específica para distribuição de aplicações empacotadas.
- Usado somente no processo de build.

## Inno Setup

- Projeto: <https://jrsoftware.org/isinfo.php>
- Usado para criar os instaladores offline Windows com desinstalador e atalhos.
- Os termos oficiais acompanham a distribuição do Inno Setup; seu compilador não é incorporado ao
  aplicativo instalado.

## uv

- Projeto: <https://docs.astral.sh/uv/>
- Usado para resolução, lock e execução do ambiente de desenvolvimento/CI.
- Não é necessário para executar os instaladores publicados.

## Obrigações de distribuição

- conservar este arquivo nos pacotes instaláveis;
- não remover avisos/licenças presentes nos componentes;
- manter FFmpeg e pesos do modelo separados conforme descrito;
- consultar os textos integrais nos projetos oficiais antes de redistribuir uma variante alterada;
- revisar o licenciamento novamente ao trocar versão, codec, build FFmpeg ou perfil PyTorch.
