# Otimizador de Rota de Coleta de Lixo com Programação Linear

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Libraries](https://img.shields.io/badge/Libraries-OSMnx%20%7C%20PuLP%20%7C%20GeoPandas-orange.svg)

## 1. Resumo do Projeto

Este projeto implementa um otimizador de rotas para um serviço de coleta de lixo em um condomínio fechado, utilizando técnicas de Pesquisa Operacional e Programação Linear Inteira (PLI). A partir de uma área geográfica definida, o script modela a rede de ruas como um grafo, formula um problema de otimização para garantir a cobertura de todas as ruas com o menor custo possível e gera duas saídas: um roteiro de direções, passo a passo, e um mapa interativo dos cruzamentos para referência visual.

## 2. Descrição do Problema

O desafio é determinar a rota mais eficiente (em termos de distância e custo de combustível) para um veículo de coleta que precisa percorrer todas as alamedas de um condomínio. O veículo parte de um ponto de origem específico (a residência do operador) e, após cobrir todas as ruas, finaliza em um ponto de destino (local de descarte ou saída).

Este problema foi modelado como uma variação do **Problema do Carteiro Chinês (PCC)**, onde o objetivo é encontrar um tour que atravesse todas as arestas de um grafo pelo menos uma vez, com o menor custo total.

## 3. Metodologia e Tecnologias

A solução foi desenvolvida em Python e se baseia em um conjunto de bibliotecas especializadas em análise geoespacial e otimização matemática.

* **Modelagem do Problema:** Programação Linear Inteira (PLI).
* **Algoritmo de Rota:** Caminho Euleriano, aplicado sobre o grafo tornado Euleriano pela solução do PLI.
* **Bibliotecas Principais:**
    * **OSMnx:** Para baixar os dados da rede de ruas a partir de uma área poligonal definida, convertendo o mapa em uma estrutura de grafo.
    * **NetworkX:** Para a manipulação do grafo (remoção de laços, arestas paralelas) e para a geração do caminho Euleriano.
    * **PuLP:** Para a formulação e resolução do modelo de Programação Linear Inteira, determinando o número ótimo de travessias para cada rua.
    * **GeoPandas & Shapely:** Para a manipulação da geometria do polígono e para a geração dos mapas interativos.

## 4. Como Executar o Projeto

Siga os passos abaixo para configurar e executar o otimizador.

### 4.1. Pré-requisitos

* Python 3.10 ou superior.
* `pip` (gerenciador de pacotes do Python).

### 4.2. Instalação das Dependências

1.  Crie um arquivo chamado `requirements.txt` na pasta do seu projeto com o seguinte conteúdo:
    ```txt
    osmnx
    networkx
    pulp
    geopandas
    shapely
    collections-extended
    ```

2.  Abra um terminal na pasta do projeto e execute o comando abaixo para instalar todas as bibliotecas necessárias:
    ```bash
    pip install -r requirements.txt
    ```

### 4.3. Configuração do Script Principal

Antes de rodar o otimizador, você precisa ajustar alguns parâmetros no arquivo `resolveRota.py`:

1.  **`polygon_coords`**: Se desejar mudar a área do condomínio, você pode gerar uma nova lista de coordenadas no site [geojson.io](http://geojson.io/). Desenhe um polígono ao redor da área desejada e copie as coordenadas.

2.  **`no_inicio` e `no_fim`**: Estes são os IDs dos cruzamentos de partida e chegada. Se você mudar o polígono ou quiser usar outros pontos, precisará descobrir os novos IDs. Para isso, você pode usar o mapa interativo gerado pelo próprio script. Na primeira execução, o script usará os valores padrão e gerará o `mapa_referencia_cruzamentos.html`. Abra este arquivo, encontre os pontos desejados, anote os IDs (que aparecem ao passar o mouse) e atualize as variáveis no código.

3.  **Parâmetros de Custo**: Ajuste os valores de `C_LITRO` e `KM_LITRO` para refletir os custos e a eficiência do veículo real.

### 4.4. Execução

Após a instalação e configuração, execute o script principal pelo terminal:

```bash
python resolveRota.py