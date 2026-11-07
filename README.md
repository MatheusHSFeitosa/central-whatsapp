# Central Chats

Aplicativo comunitário para Linux: vários perfis de WhatsApp Web, Telegram e Chatwoot G3 dentro da mesma janela, com uma lista lateral para alternar entre contas. Feito em Python + PySide6 / Qt WebEngine (Chromium), sem Electron. Não é afiliado aos serviços integrados.

**Versão 0.10.0.** Validado no Pop!_OS 22.04 x86_64 até as telas de entrada dos três serviços. Login com conta real, mensagens, chamadas e notificações reais ainda precisam de teste pelo usuário. Não há promessa de menor consumo que um navegador comum.

## Serviços

Em **Configurações (engrenagem) > Adicionar perfil**, escolha WhatsApp, Telegram ou Chatwoot G3 e dê um nome ao perfil. É possível criar várias contas de cada serviço. O Chatwoot abre `https://chatwoot.g3pi.app.br/`; o Telegram usa o cliente Web A oficial. Cada perfil mantém cookies e armazenamento próprios. Perfis antigos continuam sendo WhatsApp, com as mesmas sessões.

O serviço de um perfil existente fica fixo: para outro serviço, adicione outro perfil. Fotos do computador e ícones funcionam em todos; foto automática está disponível somente no WhatsApp. Notificações dependem do suporte do serviço e da autorização no aplicativo e no sistema. Login, chamadas e notificações de contas reais precisam de validação pelo usuário.

## Contas e notificações na barra

Clique com o botão direito em um perfil para editar nome/ícone, escolher foto, recarregar, arquivar ou silenciar avisos do sistema. Isso abre as opções sem trocar a conversa visível. A engrenagem reúne adicionar/restaurar perfis, o menu Grupos, preferências gerais e sair.

Nas barras superior e inferior os títulos ficam em uma linha e o botão de expansão é oculto. A preferência de recolhimento é preservada para quando a barra voltar à esquerda.

Uma bolinha laranja indica que a central recebeu uma notificação para aquele perfil enquanto ele não estava sendo visualizado. A engrenagem também recebe o indicador quando há algum perfil com notificação. Silenciar os avisos do sistema mantém essa sinalização. O indicador é limpo ao visualizar o perfil em uma janela ativa ou pelo menu do botão direito. Ele representa notificações recebidas nesta execução, não uma contagem de mensagens não lidas. Depende de o serviço enviar notificações e da permissão concedida; não lê conversas nem consulta mensagens por fora da sessão.

## Identidade visual e navegação

O visual usa ícones simbólicos próprios e uniformes, cabeçalhos de grupo separados da seleção e a mesma paleta nos menus e formulários. As abas superiores ficam integradas à barra de título, com nome ao lado do avatar e indicador de notificação separado. A barra inferior ocupa 48 pixels. As abas mantêm nomes em uma linha e largura limitada. Preferências, confirmações e seletores de arquivo/cor usam cabeçalhos da Central. Quando houver mais contas do que espaço, use as setas, a rolagem ou o teclado. Os nomes completos continuam nas dicas e nos rótulos acessíveis.

Os perfis mantêm as mesmas sessões ao alternar layout. O menu do botão direito também pode ser aberto com a tecla Menu ou Shift+F10. Ajustar uma conta inativa por esse menu não a carrega em segundo plano.

A logo aprovada, **Encontro**, representa dois balões azuis. O nome interno do arquivo do ícone e os identificadores de instalação foram mantidos para compatibilidade.

## Aparência e organização

Em **Configurações > Preferências**, escolha tema claro, escuro ou automático conforme o GNOME; posição da barra à esquerda, acima ou abaixo; e agrupamento sem grupos, por serviço ou personalizado. O menu **Configurações > Grupos** lista os grupos existentes e oferece **Novo grupo**. Na criação ou edição de perfil, escolha o grupo e a foto; novos perfis começam com a logo do serviço. Use **botão direito no perfil > Grupos** para mudar sua associação. No cabeçalho do grupo, o botão direito oferece renomear, escolher a cor do marcador e adicionar abas. A cor aparece em um pequeno marcador ao lado do título do grupo. Clique no título para recolher ou expandir; grupos vazios são preservados. Perfis sem nome de grupo ficam em “Sem grupo”. A mudança de posição preserva as contas abertas. O tema das páginas de conversa é escolhido dentro de cada serviço.

A versão 0.10.0 está disponível em [Releases](https://github.com/MatheusHSFeitosa/central-whatsapp/releases/tag/v0.10.0), com pacote DEB para Pop!_OS / Ubuntu 22.04 amd64.

## Recursos

- Visual inspirado no GNOME, lateral retrátil e seis ícones prontos por perfil.
- Adicionar perfis, editar nome/ícone, arquivar e restaurar a mesma sessão.
- Gravação atômica: erros ao salvar preservam o estado anterior e mostram um aviso.
- Estados de carregamento e erro por conta; comandos disponíveis conforme a seleção.
- Armazenamento independente por perfil e cookies persistentes.
- Carregamento sob demanda: cada conta abre ao ser selecionada e continua carregada enquanto a central estiver aberta.
- Pedidos de permissão para notificações, câmera e microfone.
- Downloads com seleção de destino.
- Proteção contra duas instâncias usando simultaneamente o mesmo conjunto de perfis.
- Preferências para continuar em segundo plano ao fechar a janela, iniciar na sessão Linux, escolher perfis carregados e silenciar notificações por conta.
- Abrir o atalho novamente traz a instância existente de volta; Menu > Sair da central encerra as contas.

## Foto do perfil

Selecione uma conta e abra **botão direito no perfil > Foto do perfil**:

- **Usar foto automática do WhatsApp**: tenta ler a própria foto já carregada no controle de perfil da conta. Não abre conversas, não consulta contatos e não faz downloads por fora da sessão. A detecção aceita controles de navegação acessíveis, inclusive abas e elementos role=button. Se o navegador bloquear leitura pelo canvas, pode usar uma captura local recortada da própria foto visível, sem capturar conversas ou mudar de conta. A detecção é experimental: mudanças de layout ou bloqueios do navegador podem impedir a leitura; nesse caso permanece o ícone (ou a última foto automática disponível).
- **Usar foto do computador**: escolha PNG, JPEG ou WebP de até 10 MB. A central recorta o centro, normaliza para 256×256 e exibe um avatar circular na lateral expandida ou recolhida.
- **Usar somente ícone**: volta ao ícone predefinido. Fotos armazenadas continuam locais; arquivar/restaurar mantém o mesmo perfil.

As imagens ficam em `avatars/<uuid>.png` dentro da pasta de dados da central, com acesso restrito ao usuário. Não são enviadas a nenhum servidor próprio. A foto automática só é consultada para contas já carregadas, em intervalos de 30 segundos. A configuração guarda apenas o modo da foto, sem caminhos externos ou URLs. Quando solicitada pelo menu, uma falha de detecção agora mostra uma explicação em vez de permanecer silenciosa. A extração e a captura recortada foram testadas em telas sintéticas; uma conta autenticada ainda precisa confirmar a compatibilidade do layout real.

## Segundo plano e inicialização

Abra **Menu > Preferências** para escolher:

- **Iniciar ao entrar no sistema**: cria uma entrada de autostart da sessão gráfica Linux, não um serviço de sistema. A instalação não ativa isso automaticamente.
- **Iniciar com a janela oculta**: vale para o início automático; abrir pelo atalho sempre mostra a janela.
- **Ao fechar a janela**: continuar em segundo plano ou sair.
- **Carregar ao iniciar**: todos, somente os perfis marcados, ou nenhum. Contas não carregadas não emitem notificações.
- **Avisos do sistema por perfil**: use o botão direito no perfil > Silenciar avisos do sistema. Sons de conversas e chamadas são controlados pelo próprio serviço. Receber avisos depende de a conta estar carregada, conectada e com as permissões concedidas.

Padrões novos: início automático e oculto desativados, nenhum perfil pré-selecionado para carga e fechamento em segundo plano quando há meio de retorno. Não há suspensão dos perfis carregados ao ocultar: eles continuam consumindo recursos para receber mensagens.

A bandeja pode não estar disponível no GNOME/Pop!_OS. Nesse caso, o mesmo atalho **Central Chats** do menu reabre a janela por comunicação local entre instâncias. Se não houver bandeja nem esse caminho confirmado, o aplicativo mantém a janela visível e explica como sair. Use **Menu > Sair da central** para encerrar de verdade.

As preferências ficam em `settings.json` dentro da pasta de dados, e o início automático local/DEB em `$XDG_CONFIG_HOME/autostart/central-whatsapp.desktop` (padrão `~/.config/autostart/`). A remoção local só apaga a entrada com o marcador de propriedade desta central. A remoção do DEB preserva dados do usuário; desative o início automático pelas Preferências antes de desinstalar.

A inicialização automática no **Flatpak** fica indisponível até implementar e validar o portal apropriado. A receita Flatpak continua experimental.

## Instalar com APT a partir de um arquivo DEB

Baixe o `.deb` da versão desejada em **Releases** deste repositório. Em Pop!_OS / Ubuntu **22.04 amd64**, na pasta do arquivo:

```sh
sudo apt install ./central-whatsapp_0.5.0_amd64.deb
```

Abra **Central Chats** no menu. Em **Configurações > Adicionar perfil**, escolha o serviço e informe um nome. Entre na conta pela tela do serviço; cada perfil mantém uma sessão independente.

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

Feche a central antes de executar instalação ou remoção: os scripts bloqueiam a operação se houver uma instância ativa usando os dados. As sessões são mantidas nas atualizações.

O instalador usa ambiente Python separado e obtém PySide6 do PyPI. No Ubuntu/Pop!_OS, também baixa `libxcb-cursor0` e `libnotify-bin` dos repositórios APT configurados, extraindo-os apenas na pasta da aplicação, sem alterar pacotes do sistema. Outras dependências gráficas devem estar disponíveis no sistema.

```sh
sh scripts/uninstall-user.sh
```

## Flatpak

Há uma receita em `packaging/io.github.MatheusHSFeitosa.CentralWhatsApp.json`, baseada em KDE 6.11 e PySide BaseApp. **Ainda não foi compilada nem validada; não há publicação no Flathub.** Ela é uma base para os próximos testes, não um instalador pronto.

Com `flatpak-builder` instalado e Flathub configurado:

```sh
sh scripts/build-flatpak.sh
flatpak install --user ./dist/central-whatsapp_0.5.0_x86_64.flatpak
```

São necessários KDE SDK 6.11 e PySide BaseApp 6.11; o construtor pode obtê-los do Flathub. O teste precisa confirmar especialmente sandbox do Qt WebEngine, notificações e diálogos de arquivos. Não há instrução para desativar o sandbox. Chamadas de vídeo e câmera no Flatpak ainda não foram habilitadas/validadas.

## Compilar e testar

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python tests/refined_ui_smoke.py
.venv/bin/python tests/context_notifications_smoke.py
.venv/bin/python tests/layout_smoke.py
.venv/bin/python tests/services_smoke.py
.venv/bin/python tests/smoke.py
.venv/bin/python tests/activation_smoke.py
.venv/bin/python tests/avatar_smoke.py
sh scripts/build-deb.sh
```

O teste precisa de uma sessão gráfica e das bibliotecas Qt, mas não usa login nem contas reais. Testa criação/edição e arquivamento/restauração, caminhos separados, falhas de gravação, preferências, ícones, lateral retrátil, notificações silenciadas e fechamento seguro. O teste IPC usa dois processos isolados para reabrir uma janela oculta e encerrar pelo comando de saída. Em ambiente sem tela, use `xvfb-run -a .venv/bin/python tests/smoke.py`.

O fluxo GitHub Actions executa os testes de armazenamento e da interface sem login, gera o DEB em Ubuntu 22.04 e o disponibiliza como artefato. A geração de pacote no CI, isoladamente, não confirma a compatibilidade do WhatsApp. As bibliotecas Qt incluídas no DEB precisam ser atualizadas em novos lançamentos do aplicativo.

## Dados, privacidade e limites

- Instalação local/DEB: `~/.local/share/central-whatsapp-data`, ou `$XDG_DATA_HOME/central-whatsapp-data` quando configurado.
- Flatpak: dados ficam no diretório XDG privado da aplicação.
- `profiles.json` contém nomes e identificadores; cada UUID possui sua pasta `sessions/<uuid>`.
- Sessões são dados de autenticação: não envie essas pastas ao GitHub, nem compartilhe cópias.
- Arquivar preserva o perfil e seu UUID. Use **Restaurar perfil** para abrir a mesma sessão; isso não desvincula o dispositivo no celular.
- Perfis que foram removidos pela versão 0.1.0 já não possuem referência na configuração. Esta versão não tenta associar automaticamente pastas antigas a nomes de contas.
- Para revogar uma sessão do WhatsApp, use **Aparelhos conectados** no celular; para os demais serviços, encerre a sessão nas configurações da própria conta.
- As contas acessam diretamente os servidores de cada serviço. A central não tem servidor próprio nem coleta própria de telemetria.
- O identificador `QtWebEngine` é removido do User-Agent para compatibilidade; a versão real do Chromium é mantida.
- RAM/CPU crescem com o número de contas carregadas e a atividade de cada conta. Não foram medidos comparativos.
- Notificações exigem permissão do site, suporte do sistema e a conta carregada no processo da central, visível ou em segundo plano. Em GNOME utiliza libnotify ou D-Bus, com alternativa pela bandeja quando disponível.
- A sessão persistente foi configurada e o isolamento dos caminhos foi testado. A persistência de uma conta autenticada só pode ser confirmada após login e reabertura pelo usuário.

## Licenças

O código deste projeto está sob MIT. PySide6, Qt, Chromium e demais componentes mantêm suas próprias licenças; consulte os avisos distribuídos com as dependências. O nome WhatsApp identifica o serviço acessado e pertence aos seus titulares.

### Runtime validado

Esta versão fixa PySide6 6.11.3. A combinação local PySide6 6.12.0 + Python 3.10.12 apresentou erro de contagem de referências mesmo em chamadas mínimas de widgets, causando falha ao encerrar após várias mudanças de aparência. Os mesmos casos e o teste completo de layout encerraram normalmente com 6.11.3. Instalação por usuário e pacote DEB usam a versão fixada em `requirements.txt`.

## Novidades locais 0.6.0

A logo na lateral troca para o controle de expansão quando o cursor passa sobre ela. O nome Central Chats aparece completo apenas com a lateral expandida. O nome do aplicativo foi mantido até existir uma escolha diferente aprovada.

As preferências estão em três abas. Clique no título de um grupo para recolher ou expandir; o contador mostra o total de perfis, sem desconectá-los. Grupos recolhidos mantêm a sinalização de notificações.

Se o Telegram não abrir, a central tenta recuperar falhas iniciais de rede/arquivos até duas vezes. A tela de carregamento permite tentar novamente ou trocar o cliente; a opção também fica no botão direito do perfil > Cliente do Telegram. Web A e Web K usam a mesma origem e o mesmo armazenamento do perfil, sem apagá-lo, mas podem solicitar conexão à conta separadamente. Não existe promessa de corrigir indisponibilidade externa ou de rede.

### Áudio e vídeo

Foram usados arquivos sintéticos, sem contas reais: WAV, MP3, Ogg/Opus e WebM/VP8+Opus avançaram a reprodução; o vídeo mostrou frames. O teste foi silenciado para não emitir som na máquina, portanto não comprova a saída física dos alto-falantes. Entrada e saída de tela cheia passaram.

MP4 com H.264/AAC retornou formato não suportado. Essa limitação permanece: o suporte depende dos codecs da compilação do [Qt WebEngine](https://doc.qt.io/qt-6/qtwebengine-features.html#audio-and-video-codecs), não apenas de instalar um programa FFmpeg no sistema. Os testes não acessaram mensagens, áudios ou vídeos privados.
