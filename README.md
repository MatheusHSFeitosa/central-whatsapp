# Central WhatsApp

Aplicativo comunitário para Linux: vários perfis do WhatsApp Web dentro da mesma janela, com uma lista lateral para alternar entre contas. Feito em Python + PySide6 / Qt WebEngine (Chromium), sem Electron. Não é afiliado ao WhatsApp ou à Meta.

**Versão 0.1.0 — experimental.** Validado no Pop!_OS 22.04 x86_64 até a tela de QR Code. Login com conta real, mensagens, chamadas e notificações reais ainda precisam de teste pelo usuário. Não há promessa de menor consumo que um navegador comum.

## Recursos

- Adicionar perfis, renomear e remover da lista.
- Armazenamento independente por perfil e cookies persistentes.
- Carregamento sob demanda: cada conta abre ao ser selecionada e continua carregada enquanto a central estiver aberta.
- Pedidos de permissão para notificações, câmera e microfone.
- Downloads com seleção de destino.
- Proteção contra duas instâncias usando simultaneamente o mesmo conjunto de perfis.
- Ao fechar a central, todas as contas param; não há serviço residente ou início automático.

## Instalar com APT a partir de um arquivo DEB

Baixe o `.deb` da versão desejada em **Releases** deste repositório. Em Pop!_OS / Ubuntu **22.04 amd64**, na pasta do arquivo:

```sh
sudo apt install ./central-whatsapp_0.1.0_amd64.deb
```

Abra **Central WhatsApp** no menu. Clique em **Adicionar perfil**, informe um nome e conecte pelo celular. Cada perfil pode usar um número diferente.

Este é um arquivo local instalado pelo APT. **Ainda não existe repositório APT assinado para atualização automática.** O pacote atual depende de Python 3.10 e não se destina a Ubuntu 24.04 ou outras versões.

Remover o DEB:

```sh
sudo apt remove central-whatsapp
```

As sessões do usuário são preservadas. Não mantenha instalações local e DEB simultâneas: a entrada local de menu tem prioridade. Antes de trocar para o DEB, feche a central e execute `sh scripts/uninstall-user.sh` na cópia do projeto.

## Instalar só para seu usuário (sem sudo)

Requer Python 3.10+, `python3-venv`, rede e bibliotecas gráficas. Em Pop!_OS 22.04:

```sh
git clone https://github.com/MatheusHSFeitosa/central-whatsapp.git
cd central-whatsapp
sh scripts/install-user.sh
```

O instalador usa ambiente Python separado e obtém PySide6 do PyPI. No Ubuntu/Pop!_OS, também baixa `libxcb-cursor0` e `libnotify-bin` dos repositórios APT configurados, extraindo-os apenas na pasta da aplicação, sem alterar pacotes do sistema. Outras dependências gráficas devem estar disponíveis no sistema.

```sh
sh scripts/uninstall-user.sh
```

## Flatpak

Há uma receita em `packaging/io.github.MatheusHSFeitosa.CentralWhatsApp.json`, baseada em KDE 6.11 e PySide BaseApp. **Ainda não foi compilada nem validada; não há publicação no Flathub.** Ela é uma base para os próximos testes, não um instalador pronto.

Com `flatpak-builder` instalado e Flathub configurado:

```sh
sh scripts/build-flatpak.sh
flatpak install --user ./dist/central-whatsapp_0.1.0_x86_64.flatpak
```

São necessários KDE SDK 6.11 e PySide BaseApp 6.11; o construtor pode obtê-los do Flathub. O teste precisa confirmar especialmente sandbox do Qt WebEngine, notificações e diálogos de arquivos. Não há instrução para desativar o sandbox. Chamadas de vídeo e câmera no Flatpak ainda não foram habilitadas/validadas.

## Compilar e testar

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tests/smoke.py
sh scripts/build-deb.sh
```

O teste precisa de uma sessão gráfica e das bibliotecas Qt, mas não usa login nem contas reais. Testa criação, renomeação e remoção, reabertura da configuração, caminhos separados e preservação dos dados. Em ambiente sem tela, use `xvfb-run -a .venv/bin/python tests/smoke.py`.

O fluxo GitHub Actions gera o DEB em Ubuntu 22.04 e o disponibiliza como artefato. A geração de pacote no CI, isoladamente, não confirma a compatibilidade do WhatsApp. As bibliotecas Qt incluídas no DEB precisam ser atualizadas em novos lançamentos do aplicativo.

## Dados, privacidade e limites

- Instalação local/DEB: `~/.local/share/central-whatsapp-data`, ou `$XDG_DATA_HOME/central-whatsapp-data` quando configurado.
- Flatpak: dados ficam no diretório XDG privado da aplicação.
- `profiles.json` contém nomes e identificadores; cada UUID possui sua pasta `sessions/<uuid>`.
- Sessões são dados de autenticação: não envie essas pastas ao GitHub, nem compartilhe cópias.
- Remover um perfil da lista preserva os dados locais; não desvincula o dispositivo na conta. O aplicativo ainda não possui função de restaurar perfis removidos.
- Para revogar uma sessão, use **WhatsApp > Aparelhos conectados** no celular.
- As contas acessam diretamente os servidores do WhatsApp. A central não tem servidor próprio nem coleta própria de telemetria.
- O identificador `QtWebEngine` é removido do User-Agent para compatibilidade; a versão real do Chromium é mantida.
- RAM/CPU crescem com o número de contas carregadas e a atividade de cada conta. Não foram medidos comparativos.
- Notificações exigem permissão do site, suporte do sistema e a aplicação aberta. Em GNOME utiliza libnotify ou D-Bus, com alternativa pela bandeja quando disponível.
- A sessão persistente foi configurada e o isolamento dos caminhos foi testado. A persistência de uma conta autenticada só pode ser confirmada após login e reabertura pelo usuário.

## Licenças

O código deste projeto está sob MIT. PySide6, Qt, Chromium e demais componentes mantêm suas próprias licenças; consulte os avisos distribuídos com as dependências. O nome WhatsApp identifica o serviço acessado e pertence aos seus titulares.
