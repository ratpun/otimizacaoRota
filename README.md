# Otimizador de Rota de Coleta de Lixo com Programação Linear

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Solver](https://img.shields.io/badge/Solver-GLPK%2FCBC-brightgreen.svg)
![Libraries](https://img.shields.io/badge/Libraries-OSMnx%20%7C%20PuLP%20%7C%20GeoPandas-orange.svg)

## 1. Resumo do Projeto

Este projeto implementa um otimizador de rotas para um serviço de coleta de lixo em um condomínio fechado, utilizando técnicas de Pesquisa Operacional e Programação Linear Inteira (PLI). A partir de uma área geográfica e parâmetros definidos em um arquivo de configuração, o script modela a rede de ruas como um grafo, formula um problema de otimização para garantir a cobertura de todas as ruas com o menor custo possível e gera duas saídas: um roteiro de direções em um arquivo de texto e um mapa interativo dos cruzamentos para referência visual.

## 2. Descrição do Problema

O desafio é determinar a rota mais eficiente (em termos de distância e custo de combustível) para um veículo de coleta que precisa percorrer todas as alamedas de um condomínio. O veículo parte de um ponto de origem específico e, após cobrir todas as ruas, finaliza em um ponto de destino. Este problema foi modelado como uma variação do **Problema do Carteiro Chinês (PCC)**.

## 3. Funcionalidades

* **Busca de Dados Geoespaciais:** Utiliza o OSMnx para baixar dados atualizados da rede de ruas a partir de um polígono de coordenadas.
* **Limpeza e Preparação de Dados:** Processa o grafo para remover inconsistências como laços (self-loops) e arestas paralelas, preparando os dados para o modelo matemático.
* **Geração de Nomes Descritivos:** Cria nomes legíveis para cada cruzamento com base nas ruas que se conectam a ele (ex: "Esquina da Alameda A com Alameda B").
* **Otimização Matemática:** Formula e resolve um modelo de Programação Linear Inteira via PuLP, utilizando o solver GLPK/CBC para encontrar a rota de custo mínimo, com um tempo limite configurável.
* **Geração de Rota Sequencial:** Constrói um caminho Euleriano a partir da solução ótima para gerar uma sequência de passos executável.
* **Exportação de Resultados:** Salva o roteiro detalhado em um arquivo de texto (`roteiro_final.txt`) e gera um mapa interativo (`mapa_referencia.html`) para análise visual.

## 4. Estrutura do Projeto

Recomenda-se a seguinte estrutura de arquivos:

/projeto_coleta_lixo/
|-- resolveRota.py            # Script principal
|-- config.json               # Arquivo de configuração com os parâmetros
|-- requirements.txt          # Lista de dependências Python
|-- roteiro_final.txt         # Arquivo de saída com o resultado (gerado pelo script)
|-- mapa_referencia.html      # Mapa interativo de saída (gerado pelo script)


## 5. Como Executar

### 5.1. Instalação das Dependências

Com o arquivo `requirements.txt` na pasta do projeto, abra um terminal e instale as bibliotecas necessárias:
```bash
pip install -r requirements.txt
```

### 5.2. Configuração
Ajuste os valores no config.json:

polygon_coords: Defina a área geográfica de interesse. Você pode obter novas coordenadas em geojson.io.

no_inicio e no_fim: Defina os IDs dos nós de partida e chegada. Para descobrir os IDs de uma nova área, execute o script uma vez; ele gerará o mapa interativo mapa_referencia.html, onde você poderá passar o mouse sobre os pontos para ver seus IDs.

custo_litro e km_por_litro: Ajuste os parâmetros de custo do veículo.

solver_timelimit_segundos: Defina o tempo máximo (em segundos) que o solver pode rodar. Um valor entre 300 (5 minutos) e 600 (10 minutos) é recomendado para um bom equilíbrio entre tempo e qualidade da solução.

### 5.3. Execução
Com o arquivo config.json devidamente configurado, execute o script principal pelo terminal:

```bash
python resolveRota.py
```

O programa irá ler a configuração, resolver o problema dentro do tempo limite estipulado e gerar os arquivos de saída.

## 6. Saídas do Programa
### 6.1. roteiro_final.txt
Um arquivo de texto com o relatório da solução e o roteiro passo a passo.

Exemplo:

--- ROTEIRO DA ROTA OTIMIZADA ---
Custo Total: R$ 9.56
Distância Total: 8.24 km

Passo 1: Comece em 'Final da Alameda 38' e siga pela Alameda 38 (em direção a: Esquina da Alameda 38 com Alameda 34)
Passo 2: Vire na Alameda 34 (em direção a: Cruzamento da Alameda 34, Alameda 35 e Alameda 36)
...
--- FIM DA ROTA ---
A rota tem 150 passos e termina em: 'Esquina da Avenida Onze com Avenida Nove'.
6.2. mapa_referencia.html
Um arquivo de mapa interativo. Ao abri-lo em um navegador, você verá todos os cruzamentos do condomínio como pontos. Ao passar o mouse sobre cada ponto, o nome descritivo do cruzamento será exibido. Marcadores especiais indicam o início e o fim da rota.