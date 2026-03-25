# PoE - Auto Map Craft

Ferramenta de automação para craftar mapas no Path of Exile. Aplica Orb of Alchemy e Orb of Scouring automaticamente em todos os mapas da stash até que todos fiquem craftados.

## Download

Baixe o executável pronto na [página de Releases](../../releases/latest) — não precisa instalar Python.

## Como funciona

O app usa reconhecimento de imagem (OpenCV) para localizar a Orb of Alchemy na tela e detecção de cor (HSV) para identificar quais mapas já estão craftados. A posição dos mapas é calculada matematicamente a partir de uma calibração de 3 pontos na stash.

**Fluxo do craft:**
1. Clica com botão direito na Alchemy (pega o item)
2. Segura Shift + clica com esquerdo em cada mapa cinza (aplica Alchemy)
3. Detecta quais mapas ainda estão cinzas
4. Clica com direito na Alchemy + segura Shift + Alt + clica nos cinzas (aplica Scouring)
5. Repete até todos ficarem craftados

## Requisitos

- Windows 10/11
- Path of Exile rodando em modo janela ou janela sem bordas
- Resolução qualquer (a calibração se adapta)

## Antes de usar

1. Coloque as **Orb of Alchemy** no inventário do personagem
2. Coloque os **mapas** na stash tab
3. No campo **Highlight Items** da stash, digite o regex para filtrar apenas os mapas que deseja craftar (ex: `t16`)
4. A tela deve mostrar apenas os mapas filtrados e a alchemy no inventário

### Para usar o .exe (recomendado)

Nenhuma instalação necessária. Baixe o `AutoCraft.exe` da [página de Releases](../../releases/latest) e execute.

### Para rodar via Python

```bash
pip install -r requirements.txt
python autocraft.py
```

### Para gerar o .exe

```bash
pip install -r requirements.txt
build.bat
```

O executável será gerado em `dist/AutoCraft.exe`.

## Tutorial

### 1. Capturar Templates

Abra o PoE com a stash visível e clique em **Capturar Templates** no app.

O app vai pedir 3 capturas (aperte **F2** com o mouse posicionado em cada item):

| Passo | O que fazer |
|-------|-------------|
| 1/3 | Posicione o mouse sobre a **Orb of Alchemy** no inventário e aperte F2 |
| 2/3 | Posicione sobre um **mapa cinza** (normal) na stash e aperte F2 |
| 3/3 | Posicione sobre um **mapa vermelho** (já craftado) na stash e aperte F2 |

### 2. Calibrar Grid

Clique em **Calibrar Grid** e aperte **F2** em 3 posições:

| Passo | O que fazer |
|-------|-------------|
| 1/3 | F2 no **primeiro mapa** (canto superior esquerdo da stash) |
| 2/3 | F2 no **mapa ao lado** (segunda coluna, mesma linha) |
| 3/3 | F2 no **último mapa** (canto inferior direito da stash) |

O app calcula automaticamente a grid completa a partir desses 3 pontos.

### 3. Testar Grid

Clique em **Testar Grid** para verificar se o mouse passa por todos os slots corretamente. Se não estiver alinhado, recalibre.

### 4. Iniciar Craft

Clique em **INICIAR CRAFT**. O app vai:
- Detectar mapas cinzas e craftados automaticamente
- Aplicar Alchemy nos cinzas
- Aplicar Scouring nos que não ficaram craftados
- Repetir até todos ficarem craftados

Aperte **ESC** a qualquer momento para cancelar.

## Interface

O painel superior mostra em tempo real:
- **Fase atual** — Alchemy (dourado) ou Scouring (azul)
- **Ciclo** — número da iteração atual
- **Contadores** — total de mapas, craftados e cinzas

## Notas

- A janela do app fica sempre no topo para não atrapalhar
- A configuração da grid é salva em `autocraft_config.json` (mesmo diretório do .exe)
- Funciona com qualquer resolução de tela
- O log de execução é salvo em `autocraft_log.txt` para debug
