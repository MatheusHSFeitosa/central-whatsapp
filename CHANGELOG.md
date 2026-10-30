# Alterações

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
