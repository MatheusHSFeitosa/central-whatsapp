# Compatibilidade e evidências

## Base validada

- Python 3.10 no ambiente anterior Pop!_OS 22.04; Python 3.12 no Pop!_OS 24.04 atual.
- PySide6 Essentials 6.11.3 para a interface.
- CEF 152.0.6 / Chromium 152.0.7977.83, build amd64 com codecs.
- Qt em `xcb` e CEF com `--ozone-platform=x11`, inclusive dentro de sessões Wayland.
- GLib processa os eventos nativos do CEF. Cada perfil conserva um processo e um
  armazenamento próprios; os painéis não recriam ou reparentam o navegador.

## Testes automáticos locais

- Persistência, restauração, validação de URLs, grupos e permissões de arquivos.
- Oito regiões de redimensionamento; controles preservam cliques normais.
- Viewport nativo em dois tamanhos, clique e digitação via X11.
- Visibilidade de apenas um perfil na aba individual; pixel de duas páginas
  fictícias confirma a troca real do conteúdo mostrado.
- Divisão em dois e quatro painéis, perfis de grupos diferentes, geometria sem
  sobreposição, estabilidade dos pais nativos e dos processos, linhas/colunas,
  ajuste da divisão e retorno da tela cheia.
- Download, anexo fictício, link externo, notificações e restauração da sessão.
- Arquivo MP4 H.264/AAC decodificado; duas conexões WebRTC recebem áudio Opus e
  frames H.264 nos dois sentidos, usando dispositivos simulados.
- Renderer com isolamento `NoNewPrivs=1` / `Seccomp=2`; não usamos `--no-sandbox`.

O GitHub Actions executa a matriz Ubuntu 22.04/24.04 em Xvfb com Openbox. Essa
matriz verifica eventos e mídia simulados, **não faz login nem liga para contatos**.

## Validação humana e limitações

O autor confirmou chamadas de saída e entrada, áudio e vídeo nos dois sentidos,
com a própria conta WhatsApp no laboratório do motor CEF. Os novos layouts usam
o mesmo motor. Não há afirmação de testes reais autenticados de chamadas em
Telegram, Chatwoot ou qualquer outro servidor personalizado.

Os serviços podem alterar a compatibilidade, a disponibilidade de chamadas ou a
interface. As contas precisam estar carregadas para receber chamadas e avisos.
Notificações exclusivas de service workers ainda não têm composição/roteamento
personalizado confirmado.

Wayland nativo, Flatpak, Windows, macOS e ARM permanecem fora da matriz validada.
A versão DEB amd64 destina-se a Pop!_OS/Ubuntu 22.04 e 24.04, com Python 3.10–3.12.
Não se promete redução de uso de memória em relação a um navegador comum.

## AppArmor no Ubuntu 24.04

Algumas instalações Ubuntu restringem namespaces de usuário por AppArmor. O DEB
contém um perfil específico para o host **root-owned** em
`/opt/central-whatsapp/cef-runtime/central-cef-host` e o carrega quando o kernel
e o parser suportam a regra. Ele permite `userns` para esse executável; não
altera a política global do sistema e não desativa a sandbox do Chromium.

A matriz Ubuntu 24.04 carrega a mesma regra para o caminho exato do host do
runner. O teste continua exigindo isolamento do renderer e ausência de
`--no-sandbox`. Essa configuração segue a
[documentação do Chromium sobre AppArmor e namespaces](https://chromium.googlesource.com/chromium/src/+/main/docs/security/apparmor-userns-restrictions.md).

Para instalações por código em um Ubuntu que aplique essa restrição, prefira o
DEB. Um administrador pode adaptar o perfil ao caminho exato do host; a
instalação no usuário não modifica automaticamente a política AppArmor.
