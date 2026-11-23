# Créditos, IA e referências

## Autoria e participação de IA

**Matheus Feitosa** — ideia, direção do produto, escolhas visuais, aprovação das
funcionalidades e testes de uso com contas reais.

**OpenAI Codex** — assistência de IA na implementação Python/C++, investigação de
falhas, construção de testes, organização da documentação e preparação dos
mockups. O apoio de IA não substitui a revisão humana. Este projeto foi feito
com IA e declara essa participação publicamente.

A identidade **Encontro** (dois balões azuis) foi escolhida pelo autor e construída
como vetor original do projeto com apoio de IA. Os símbolos da interface são
vetores próprios; a referência de estilo foi uma interface Linux sóbria e compacta.

## Referências e componentes

| Referência / componente | Uso e crédito |
| --- | --- |
| [GNOME Human Interface Guidelines](https://developer.gnome.org/hig/) | Referência de hierarquia, cabeçalhos, simplicidade e controles. A interface usa Qt; não é um app GTK/Libadwaita nem uma implementação certificada da HIG. |
| [Qt for Python / PySide6](https://doc.qt.io/qtforpython-6/) | Interface, eventos de janela, formulários e ícones SVG. Licenças próprias do Qt/PySide6. |
| [QWindow](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QWindow.html) | APIs de movimento e redimensionamento integradas ao gerenciador de janelas. |
| [Chromium Embedded Framework](https://github.com/chromiumembedded/cef) | Motor de conteúdo web. BSD e demais avisos do Chromium. |
| [tobagin/Karere — CEF 152.0.6 com codecs](https://github.com/tobagin/karere/releases/tag/cef-152.0.6-proprietary-codecs) | Origem do binário CEF com H.264/AAC, fixado por SHA-256. Não copiamos a interface nem o código de aplicação Karere. |
| [JSON for Modern C++](https://github.com/nlohmann/json) | JSON no host C++; MIT, Niels Lohmann e colaboradores. |
| [D-Bus / dbus-next](https://github.com/altdesktop/python-dbus-next) | Integração de notificações com o desktop. |
| [GLib](https://gitlab.gnome.org/GNOME/glib) e X11/XWayland | Eventos nativos do CEF e incorporação dos painéis na janela Qt. |

As licenças CEF, os créditos Chromium e a procedência do binário acompanham o
runtime em `cef-runtime/`. Veja também `cef/THIRD-PARTY.md`.

## Marcas e imagens

Os nomes WhatsApp, Telegram e Chatwoot identificam serviços de seus respectivos
titulares. Os símbolos de identificação em `service-icons` possuem origem e
licença documentadas em [service-icons/README.md](service-icons/README.md).
Não há patrocínio, afiliação ou endosso desses serviços.

As imagens de `docs/images` mostram a interface real da Central com páginas de
chat de demonstração. São **mockups com dados fictícios**, não capturas de contas
ou mensagens reais, e não prometem reproduzir a aparência atual de cada serviço.
Para reproduzi-las, execute `tests/cef_split_smoke.py` com
`CENTRAL_DEMO_OUTPUT=$PWD/docs/images`.

Os textos de licença Qt/PySide6, dbus-next e nlohmann/json acompanham o pacote
em `licenses/` (instalação no usuário) ou
`/usr/share/doc/central-whatsapp/licenses/` (DEB). As bibliotecas mantêm suas
licenças originais e são distribuídas separadamente do código MIT da Central.
Código-fonte e histórico dos componentes: [Qt 6.11.3](https://github.com/qt/qtbase/tree/v6.11.3),
[Qt for Python](https://code.qt.io/cgit/pyside/pyside-setup.git/),
[dbus-next 0.2.3](https://github.com/altdesktop/python-dbus-next/tree/v0.2.3) e
[JSON 3.12.0](https://github.com/nlohmann/json/tree/v3.12.0).
