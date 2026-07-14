<div align="center">

# spotDL v4

**spotDL** encontra músicas de playlists do Spotify no YouTube e as baixa — junto com capa do álbum, letras e metadados.

[![MIT License](https://img.shields.io/github/license/spotdl/spotify-downloader?color=44CC11&style=flat-square)](https://github.com/spotDL/spotify-downloader/blob/master/LICENSE)
[![PyPI version](https://img.shields.io/pypi/pyversions/spotDL?color=%2344CC11&style=flat-square)](https://pypi.org/project/spotdl/)
[![PyPi downloads](https://img.shields.io/pypi/dw/spotDL?label=downloads@pypi&color=344CC11&style=flat-square)](https://pypi.org/project/spotdl/)
![Contributors](https://img.shields.io/github/contributors/spotDL/spotify-downloader?style=flat-square)
[![Discord](https://img.shields.io/discord/771628785447337985?label=discord&logo=discord&style=flat-square)](https://discord.gg/xCa23pwJWY)

> spotDL: O downloader de música por linha de comando mais rápido, fácil e preciso.

> **Novo:** Agora com suporte ao idioma português (pt-BR)! Use `--lang pt_BR` ou deixe a detecção automática do sistema ativar a tradução.

</div>

______________________________________________________________________

**[Leia a documentação no ReadTheDocs!](https://spotdl.readthedocs.io)** (em inglês)
______________________________________________________________________

## Instalação

Consulte nosso [Guia de Instalação](docs/installation.md) para mais detalhes.

### Python (Método Recomendado)

- O _spotDL_ pode ser instalado executando `pip install spotdl`.
- Para atualizar o spotDL execute `pip install --upgrade spotdl`

  > Em alguns sistemas pode ser necessário trocar `pip` por `pip3`.

<details>
    <summary style="font-size:1.25em"><strong>Outras opções</strong></summary>

- Executável pré-compilado
  - Você pode baixar a versão mais recente na
    [aba de Releases](https://github.com/spotDL/spotify-downloader/releases)
- No Termux
  - `curl -L https://raw.githubusercontent.com/spotDL/spotify-downloader/master/scripts/termux.sh | sh`
- Arch
  - Existe um [pacote AUR (Arch User Repository)](https://aur.archlinux.org/packages/spotdl/) para o spotDL.
- Docker
  - Construir imagem:

    ```bash
    docker build -t spotdl .
    ```

  - Iniciar container com parâmetros do spotDL (veja seção abaixo). Você precisa criar um volume mapeado para acessar os arquivos de música:

    ```bash
    docker run --rm -v $(pwd):/music spotdl download [trackUrl]
    ```

  - Para Docker Compose e downloads Docker com gerenciamento de permissões, veja
    [a seção Docker em `/docs/index.md`](docs/index.md#docker).

  - Compilar do código fonte

    ```bash
    git clone https://github.com/spotDL/spotify-downloader && cd spotify-downloader
    pip install uv
    uv sync
    uv run scripts/build.py
    ```

    Um executável é criado em `spotify-downloader/dist/`.

</details>

### Instalando o FFmpeg

O FFmpeg é obrigatório para o spotDL. Se for usar o FFmpeg apenas para o spotDL, você pode instalá-lo no diretório de instalação do spotDL:
`spotdl --download-ffmpeg`

Recomendamos a opção acima, mas se quiser instalar o FFmpeg no sistema,
siga estas instruções:

- [Tutorial Windows](https://windowsloop.com/install-ffmpeg-windows-10/)
- OSX — `brew install ffmpeg`
- Linux — `sudo apt install ffmpeg` ou use o gerenciador de pacotes da sua distribuição

### Instalando o Deno

Recomendamos fortemente instalar o Deno. O spotDL usa yt-dlp para downloads do YouTube, e alguns
vídeos exigem Deno para baixar com sucesso. Sem o Deno, o spotDL pode falhar ao baixar algumas
músicas, incluindo vídeos marcados como "made for kids".

Se for usar o Deno apenas para o spotDL, instale-o no diretório do spotDL:
`spotdl --download-deno`

Se preferir instalar o Deno no sistema, siga o
[guia oficial de instalação do Deno](https://docs.deno.com/runtime/getting_started/installation/).

## Uso

Usando o SpotDL sem opções:

```sh
spotdl [urls]
```

Você pode executar o _spotDL_ como um pacote se executá-lo como script não funcionar:

```sh
python -m spotdl [urls]
```

Uso geral:

```sh
spotdl [operação] [opções] CONSULTA
```

Existem diferentes **operações** que o spotDL pode executar. A _padrão_ é `download`, que simplesmente baixa as músicas do YouTube e incorpora metadados.

A **consulta** para o spotDL geralmente é uma lista de URLs do Spotify, mas para algumas operações como **sync**, apenas um único link ou arquivo é necessário.
Para uma lista de todas as **opções** use ```spotdl -h```

<details>
<summary style="font-size:1em"><strong>Operações suportadas</strong></summary>

- `save`: Salva apenas os metadados do Spotify sem baixar nada.
    - Uso:
        `spotdl save [consulta] --save-file {nome_do_arquivo}.spotdl`

- `web`: Inicia uma interface web em vez de usar a linha de comando. No entanto, possui recursos limitados e só suporta download de músicas individuais.

- `url`: Obtém a URL amigável para cada música da consulta.
    - Uso:
        `spotdl url [consulta]`

- `sync`: Atualiza diretórios. Compara o diretório com o estado atual da playlist. Músicas novas serão baixadas e músicas removidas serão excluídas. Nenhuma outra música será baixada e nenhum outro arquivo será excluído.

    - Uso:
        `spotdl sync [consulta] --save-file {nome_do_arquivo}.spotdl`

        Isso cria um novo arquivo **sync**. Para atualizar o diretório no futuro, use:

        `spotdl sync {nome_do_arquivo}.spotdl`

- `meta`: Atualiza metadados dos arquivos de música fornecidos.

</details>

## Idioma (Português pt-BR)

O spotDL agora oferece suporte ao idioma português! Para usar:

```sh
spotdl --lang pt_BR [operação] [urls]
```

Se o seu sistema estiver configurado em português, a tradução é ativada automaticamente.

## Origem das Músicas e Qualidade de Áudio

O spotDL usa o YouTube como fonte para downloads de música. Este método é usado para evitar quaisquer problemas relacionados ao download de música do Spotify.

> **Nota**
> Os usuários são responsáveis por suas ações e possíveis consequências legais. Não apoiamos o download não autorizado de material protegido por direitos autorais e não nos responsabilizamos pelas ações dos usuários.

### Qualidade de Áudio

O spotDL baixa música do YouTube e é projetado para sempre baixar o maior bitrate possível; que é 128 kbps para usuários regulares e 256 kbps para usuários premium do YouTube Music.

Consulte a página de [Formatos de Áudio](docs/usage.md#audio-formats-and-quality) para mais informações.

## Contribuindo

Interessado em contribuir? Confira nosso [CONTRIBUTING.md](docs/CONTRIBUTING.md) para encontrar
recursos sobre contribuição junto com um guia sobre como configurar um ambiente de desenvolvimento.

### Junte-se à nossa incrível comunidade como contribuidor de código

<a href="https://github.com/spotDL/spotify-downloader/graphs/contributors">
  <img class="dark-light" src="https://contrib.rocks/image?repo=spotDL/spotify-downloader&anon=0&columns=25&max=100&r=true" />
</a>

## Licença

Este projeto está licenciado sob a licença [MIT](/LICENSE).
