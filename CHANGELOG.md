# Alterações

## 0.10.0 — 07/11/2026

- Cabeçalhos próprios em preferências, edição de perfil, confirmação, seleção de arquivo e escolha de cor.
- Menus, submenus e formulários seguem a mesma paleta clara/escura e a mesma família de ícones.
- Controles de janela simbólicos, restauração do estado maximizado e cantos retos em tela cheia.
- Abas superiores integradas à barra de título, nome ao lado do avatar e notificação separada.
- Fluxos de aceitar/cancelar e verificações de transparência e alinhamento exercitados com dados isolados.

## 0.8.0 — validação local

- Links externos acionados pelo usuário abrem no navegador padrão, inclusive links que pedem nova aba.
- Vídeos baixados podem ser abertos no player do sistema.
- Grupos usam um marcador no título em vez de moldura nas abas.
- Avisos do sistema incluem a identidade da Central e do perfil, restauram a janela e encaminham o clique ao serviço de origem.

## 0.7.0 — validação local (não publicada)

- Menu Grupos lista grupos existentes e permite criar novos, inclusive vazios.
- Grupo e foto podem ser escolhidos ao criar ou editar um perfil; novos perfis usam a logo do serviço por padrão.
- Botão direito no grupo permite renomear, escolher a cor da borda e adicionar abas.
- Borda colorida contorna somente as abas do grupo; cabeçalhos sem seta mantêm recolhimento por clique e contador.
- Migração reconhece grupos antigos e preserva sessões e fotos existentes.

## 0.6.0 — validação local (não publicada)

- Logo na lateral; o controle muda ao passar o cursor e o nome aparece somente com a lateral expandida.
- Preferências organizadas em Aparência, Inicialização e Segundo plano.
- Grupos recolhidos/expandidos por clique no título, com contador de perfis e preferência persistente.
- Recolher grupos preserva contas carregadas e recebimento de notificações.
- Telegram com indicação de carregamento, recuperação limitada de falhas iniciais e escolha entre Web A e Web K, mantendo o perfil local.
- Tela cheia habilitada para os players web, com restauração da janela ao sair.
- Mídia sintética verificada: WAV, MP3, Opus e WebM reproduziram; MP4/H.264 não é suportado pelo runtime atual.

## 0.5.0 — 30/10/2026

- Visual aprovado com família simbólica uniforme, controles alinhados e grupos fora da seleção.
- Barra horizontal reduzida a 52 px, abas de largura limitada e setas para percorrer perfis.
- Menu de perfil com cabeçalho, hierarquia de ações e acesso por Menu/Shift+F10.
- Ajustes de contas inativas pelo menu preservam seu carregamento sob demanda.
- Logo Encontro, com dois balões azuis, aprovada e integrada.

- Runtime fixado em PySide6 6.11.3 após comparação local reproduzir falha de referências em 6.12.0 com Python 3.10.
- Barras horizontais sem expansão, títulos em linha única e faixa mais compacta.
- Menu do botão direito por perfil, com foto, edição, recarregar, arquivar e silenciamento.
- Indicador de notificações recebidas por conta e na engrenagem, inclusive com aviso do sistema silenciado.
- Preservação de grupos, silenciamento e inicialização de perfis arquivados ao salvar preferências.
- Notificações aceitam nomes de perfil começando com hífen.

- Configurações no rodapé da barra e adicionar perfil dentro das configurações.
- Ícone próprio de conversas, temas claro/escuro/automático GNOME e barra à esquerda, acima ou abaixo.
- Agrupamento por serviço ou nomes de grupos personalizados definidos por perfil.

- Perfis de WhatsApp, Telegram Web A e Chatwoot G3 na mesma central.
- Seleção de serviço na criação, com sessões independentes e migração compatível dos perfis existentes.
- Navegação e permissões restritas à origem HTTPS de cada serviço.
- Fotos locais e ícones em todos os serviços; busca automática exclusiva do WhatsApp.

## 0.4.2 — 30/10/2026

- Detecção da própria foto compatível com botões acessíveis e barras de abas.
- Alternativa de captura local recortada quando a imagem visível bloqueia leitura pelo canvas.
- Falha de busca explícita pelo menu mostra uma explicação.
- Testes incluem variantes de controles, rejeição de fotos de contatos e captura de pixels da própria foto.

## 0.4.1 — 30/10/2026

- Nome de exibição Central Chats, preservando IDs e pastas existentes.
- Menu, controle da lateral e adicionar apenas com ícone na própria barra lateral.
- Cabeçalho acima do WhatsApp e texto de rodapé removidos para liberar a área das conversas.
- Recarregar conta fica no menu lateral.

## 0.4.0 — 30/10/2026

- Fotos circulares por perfil, com imagem local e retorno ao ícone.
- Tentativa automática restrita ao controle da própria conta no WhatsApp, com fallback e sem requisições externas adicionais.
- Normalização local de imagens, limites de tamanho e arquivos privados por UUID.
- Compatibilidade com perfis existentes e testes para não selecionar fotos de contatos.
- Detecção automática ainda experimental; compatibilidade com conta autenticada não foi confirmada.

## 0.3.1 — 30/10/2026

- Contorno do ícone centralizado e proporções corrigidas, mantendo as cores e o estilo.

## 0.3.0 — 30/10/2026

- Interface inspirada no GNOME, lateral retrátil, ações no menu e seis ícones por perfil.
- Preferências persistentes para início automático, início oculto, comportamento do X e carga de contas.
- Contas carregadas permanecem ativas em segundo plano; notificações podem ser silenciadas por perfil.
- Atalho reabre a mesma instância por comunicação local, inclusive sem bandeja.
- Sair da central encerra o processo; ocultação é bloqueada sem um caminho de retorno confirmado.
- Compatibilidade com perfis e sessões existentes; os novos campos têm valores padrão.
- Início automático não é ativado na instalação; fica indisponível no Flatpak sem portal validado.

## 0.2.0 — 30/10/2026

- Arquivar e restaurar perfis conserva o identificador e a sessão original.
- Falhas ao gravar não alteram a lista, o nome nem a página aberta.
- Configuração validada e gravada por substituição atômica, com testes de erro de escrita.
- Indicadores de carregamento e erro são preservados ao alternar contas.
- Comandos sem perfil selecionado ficam desabilitados; nomes completos aparecem no tooltip.
- Erros na pasta de sessão e em downloads interrompidos recebem aviso.
- Instaladores verificam se a central está aberta antes de modificar o runtime.
- Empacotamentos incluem o novo módulo de persistência e a versão centralizada.
- CI passa a incluir testes de armazenamento e da interface sem login.

Validação local: sete testes de armazenamento, smoke da interface com navegação simulada e proteção de instância ativa passaram. Dois perfis chegaram à tela de QR Code no teste inicial da versão 0.1.0. Login persistente, notificações e chamadas com contas reais ainda dependem de teste do usuário; não há medição comparativa de RAM/CPU. A receita Flatpak continua sem compilação e teste.
