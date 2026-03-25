# PRD: AutoCraft - Automação de Craft para Path of Exile

## Introdução

Ferramenta para automatizar o processo de craft no Path of Exile. O programa localiza currency items (Orb of Alchemy, Orb of Scouring) na tela do jogo usando reconhecimento de imagem, clica com o botão direito para "pegar" a currency, e depois aplica em todos os mapas T16 e T16-5 visíveis na tela usando shift+click esquerdo.

## Goals

- Automatizar o uso de Alchemy e Scouring em mapas T16/T16-5
- Interface simples com botões para cada tipo de currency
- Reconhecimento de imagem para localizar elementos na tela do jogo
- Operação rápida: encontrar e clicar em todos os mapas visíveis de uma vez

## User Stories

### US-001: Estrutura base do projeto e dependências
**Descrição:** Como desenvolvedor, preciso da estrutura base do projeto com as dependências de reconhecimento de imagem e automação de mouse/teclado.

**Critérios de aceite:**
- [ ] requirements.txt com pyautogui, opencv-python, Pillow, keyboard
- [ ] Estrutura de pastas organizada (image/ já existe com as imagens de referência)
- [ ] Script principal autocraft.py importando as dependências

### US-002: Função de reconhecimento de imagem na tela
**Descrição:** Como usuário, preciso que o programa consiga localizar imagens de referência na tela do jogo para saber onde clicar.

**Critérios de aceite:**
- [ ] Função que recebe o caminho de uma imagem e retorna a posição (x, y) na tela
- [ ] Função que encontra TODAS as ocorrências de uma imagem na tela (para múltiplos mapas)
- [ ] Confiança (confidence) configurável para lidar com variações visuais
- [ ] Retorna None/lista vazia se não encontrar

### US-003: Função de craft (click direito na currency + shift+click esquerdo nos mapas)
**Descrição:** Como usuário, quero que ao acionar o craft, o programa clique com botão direito na currency e depois aplique em todos os mapas encontrados.

**Critérios de aceite:**
- [ ] Recebe o tipo de currency (alchemy ou scouring) como parâmetro
- [ ] Localiza a imagem da currency na tela e clica com botão direito
- [ ] Localiza todas as imagens t16.png e t16-5.png na tela
- [ ] Segura shift e clica com botão esquerdo em cada mapa encontrado
- [ ] Delay configurável entre cliques para não ser rápido demais
- [ ] Mensagem de erro se não encontrar a currency ou os mapas

### US-004: Interface gráfica com botões
**Descrição:** Como usuário, quero uma janela com botões para acionar cada tipo de craft sem precisar usar o terminal.

**Critérios de aceite:**
- [ ] Janela tkinter simples e compacta
- [ ] Botão "Alchemy" que executa o craft com alchemy.png
- [ ] Botão "Scouring" que executa o craft com scouring.png
- [ ] Janela fica sempre no topo (topmost) para não ser coberta pelo jogo
- [ ] Feedback visual indicando que está executando (botão desabilitado durante execução)

### US-005: Empacotamento como executável
**Descrição:** Como usuário, quero um .exe para abrir direto sem precisar ter Python instalado.

**Critérios de aceite:**
- [ ] Script/comando de build com PyInstaller
- [ ] Executável .exe funcional que abre a GUI
- [ ] Imagens da pasta image/ incluídas no executável
- [ ] Arquivo .spec ou comando documentado para rebuild

## Requisitos Funcionais

- FR-1: Localizar imagens na tela usando template matching (OpenCV)
- FR-2: Clicar com botão direito na currency encontrada
- FR-3: Segurar shift e clicar com botão esquerdo em cada mapa T16/T16-5
- FR-4: Suportar múltiplas ocorrências de mapas na tela
- FR-5: Interface com botões Alchemy e Scouring
- FR-6: Janela always-on-top para não sumir atrás do jogo
- FR-7: Executável .exe standalone

## Fora de Escopo

- Não vai ler stats dos mapas ou decidir quais mapas craftar
- Não vai detectar resultados do craft (se deu mapa bom ou ruim)
- Não vai rodar em loop automático (só executa quando o botão é clicado)
- Não vai ter hotkeys por enquanto (só botões na GUI)

## Considerações Técnicas

- Python + pyautogui para controle de mouse/teclado
- OpenCV (cv2) para template matching na tela
- tkinter para GUI (leve, sem dependências extras)
- PyInstaller para gerar .exe
- As imagens de referência ficam em craft-map/image/
- O jogo Path of Exile precisa estar visível na tela (não funciona minimizado)

## Métricas de Sucesso

- O programa encontra e clica em todos os mapas visíveis em menos de 2 segundos
- Funciona de forma confiável com a resolução do monitor do usuário
- O .exe abre e funciona sem Python instalado

## Questões em Aberto

- Qual a resolução do monitor? (afeta o confidence do template matching)
- Precisa de delay entre o clique na currency e o clique nos mapas?
