import os
import json
import osmnx as ox
import networkx as nx
import pulp
import geopandas as gpd
from shapely.geometry import Polygon

def carregar_configuracao(arquivo_config):
    try:
        with open(arquivo_config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"Configuração lida com sucesso do arquivo '{arquivo_config}'.")
        return config
    except FileNotFoundError:
        print(f"ERRO: Arquivo de configuração '{arquivo_config}' não encontrado.")
        return None
    except json.JSONDecodeError:
        print(f"ERRO: O arquivo '{arquivo_config}' não contém um JSON válido.")
        return None

def main():    
    config = carregar_configuracao('config.json')
    if not config:
        return

    polygon_coords = config['polygon_coords']
    no_inicio = config['no_inicio']
    no_fim = config['no_fim']
    C_LITRO = config['custo_litro']
    KM_LITRO = config['km_por_litro']
    TIME_LIMIT = config.get('solver_timelimit_segundos', 600) # Padrão de 600s se não for encontrado

    polygon_geom = Polygon(polygon_coords)
    if not polygon_geom.is_valid:
        print("ERRO: O polígono definido em 'config.json' é inválido."); return
    print("Polígono criado com sucesso e é válido! 👍")
    G_raw = ox.graph_from_polygon(polygon_geom, network_type="all")
    print(f"Grafo original gerado com {G_raw.number_of_nodes()} nós e {G_raw.number_of_edges()} arestas.")
    G_solver = G_raw.copy()
    self_loops = list(nx.selfloop_edges(G_solver)); G_solver.remove_edges_from(self_loops)
    G_solver = nx.Graph(G_solver)
    print(f"Grafo simplificado para o solver com {G_solver.number_of_nodes()} nós e {len(G_solver.edges())} ruas.")
    print("-" * 30)
    
    nomes_cruzamentos = {}
    for node in G_raw.nodes():
        ruas_conectadas = set()
        for _, _, data in G_raw.edges(node, data=True):
            nome_rua_valor = data.get('name', None)
            if nome_rua_valor:
                if isinstance(nome_rua_valor, list): nome_final = nome_rua_valor[0]
                else: nome_final = nome_rua_valor
                ruas_conectadas.add(nome_final)
        ruas_conectadas = sorted(list(ruas_conectadas))
        if len(ruas_conectadas) == 0: nomes_cruzamentos[node] = f"Ponto {node}"
        elif len(ruas_conectadas) == 1: nomes_cruzamentos[node] = f"Final da {ruas_conectadas[0]}"
        elif len(ruas_conectadas) == 2: nomes_cruzamentos[node] = f"Esquina da {ruas_conectadas[0]} com {ruas_conectadas[1]}"
        else: nomes_cruzamentos[node] = f"Cruzamento da {', '.join(ruas_conectadas[:-1])} e {ruas_conectadas[-1]}"

    C_KM = C_LITRO / KM_LITRO
    V = list(G_solver.nodes()); E = list(G_solver.edges()); A = []
    costs = {}
    for i, j in E:
        edge_data = G_raw.get_edge_data(i, j)
        if edge_data is None: edge_data = G_raw.get_edge_data(j, i)
        dist_m = edge_data[0]['length']
        dist_km = dist_m / 1000.0; cost = C_KM * dist_km
        A.extend([(i, j), (j, i)]); costs[(i, j)] = cost; costs[(j, i)] = cost
    print(f"Parâmetros definidos. Custo por km: R${C_KM:.2f}")

# #############################################################################
    # --- PASSO 4: MODELAGEM E RESOLUÇÃO COM PULP ---
    # #############################################################################
    print("\n--- Iniciando Passo 4: Otimização com PuLP ---")

    # Inicializa o modelo, definindo o objetivo como Minimização.
    model = pulp.LpProblem("Otimizacao_Rota_Coleta", pulp.LpMinimize)

    # =============================================================================
    # VARIÁVEIS DE DECISÃO (x_ij)
    # =============================================================================
    # A linha abaixo implementa a RESTRIÇÃO 3 (Domínio das Variáveis) do LaTeX.
    # Cria um dicionário de variáveis chamado 'x', onde cada chave é um arco (i, j).
    # cat='Integer' garante que x_ij seja um número inteiro.
    # lowBound=0 garante que x_ij seja não negativo (>= 0).
    x = pulp.LpVariable.dicts("x", A, lowBound=0, cat="Integer")

    # =============================================================================
    # FUNÇÃO OBJETIVO
    # =============================================================================
    # A linha abaixo implementa a Função Objetivo do LaTeX.
    # O objetivo é minimizar o custo total, que é a soma do custo de cada arco
    # multiplicado pelo número de vezes que ele é percorrido.
    # Equação LaTeX: Minimizar Z = Σ(c_ij * x_ij)
    model += pulp.lpSum([costs[i, j] * x[i, j] for (i, j) in A]), "Custo_Total"

    # =============================================================================
    # RESTRIÇÕES
    # =============================================================================

    # RESTRIÇÃO 1: COBERTURA DE TODAS AS RUAS
    # Garante que cada rua (aresta em E) seja percorrida pelo menos uma vez, 
    # somando as travessias nos dois sentidos.
    # Equação LaTeX: x_ij + x_ji >= 1, para todo {i, j} in E
    for i, j in E:
        model += x[i, j] + x[j, i] >= 1, f"Cobertura_Rua_{i}_{j}"

    # RESTRIÇÃO 2: CONSERVAÇÃO DE FLUXO
    # Garante que a rota seja contínua, balanceando as entradas e saídas de cada nó.
    for k in V:
        # Soma dos arcos que entram no nó k (fluxo de entrada)
        fluxo_entrada = pulp.lpSum([x[i, j] for i, j in A if j == k])
        # Soma dos arcos que saem do nó k (fluxo de saída)
        fluxo_saida = pulp.lpSum([x[i, j] for i, j in A if i == k])
        
        # Sub-restrição 2.1: Nó de Início
        # O fluxo de saída deve ser 1 unidade maior que o de entrada.
        # Equação LaTeX: Σ(x_sj) - Σ(x_is) = 1
        if k == no_inicio:
            model += fluxo_saida - fluxo_entrada == 1, f"Fluxo_Inicio_{k}"
        
        # Sub-restrição 2.2: Nó de Fim
        # O fluxo de entrada deve ser 1 unidade maior que o de saída.
        # Equação LaTeX: Σ(x_it) - Σ(x_tj) = 1
        elif k == no_fim:
            model += fluxo_entrada - fluxo_saida == 1, f"Fluxo_Fim_{k}"

        # Sub-restrição 2.3: Nós Intermediários
        # O fluxo de entrada deve ser igual ao de saída (o que entra, sai).
        # Equação LaTeX: Σ(x_ik) - Σ(x_kj) = 0
        else:
            model += fluxo_entrada - fluxo_saida == 0, f"Fluxo_Intermediario_{k}"
        
    print(f"Modelo montado. Iniciando o solver com um limite de {TIME_LIMIT} segundos...")
    model.solve(pulp.GLPK_CMD(msg=True, timeLimit=TIME_LIMIT))
    status = pulp.LpStatus[model.status]
    print(f"Status da Solução: {status}")

    if status == "Optimal" or status == "Feasible":
        custo_minimo = pulp.value(model.objective)
        distancia_total_km = custo_minimo / C_KM
        print("\n--- SOLUÇÃO ENCONTRADA ---")
        print(f"Custo total da rota: R$ {custo_minimo:.2f}")
        print(f"Distância total a ser percorrida: {distancia_total_km:.2f} km")

        solucao_x = {}
        for i, j in A:
            if x[i, j].varValue > 0: solucao_x[(i, j)] = int(x[i, j].varValue)

        G_euleriano = nx.MultiDiGraph()
        for (u, v), num_travessias in solucao_x.items():
            for _ in range(num_travessias): G_euleriano.add_edge(u, v)
        
        if nx.has_eulerian_path(G_euleriano, source=no_inicio):
            rota_em_arestas = list(nx.eulerian_path(G_euleriano, source=no_inicio))
                        
            script_dir = os.path.dirname(os.path.abspath(__file__))
            roteiro_texto = []
            nome_rua_anterior = None
            for i, (u, v) in enumerate(rota_em_arestas):
                edge_data = G_raw.get_edge_data(u, v)
                if edge_data is None: edge_data = G_raw.get_edge_data(v, u)
                nome_rua_valor = edge_data[0].get('name', 'Rua sem nome')
                if isinstance(nome_rua_valor, list): nome_rua_atual = nome_rua_valor[0]
                else: nome_rua_atual = nome_rua_valor
                nome_cruzamento_destino = nomes_cruzamentos.get(v, f"Ponto {v}")
                if nome_rua_atual == nome_rua_anterior: acao = "Continue pela"
                else:
                    if i == 0: acao = f"Comece em '{nomes_cruzamentos.get(u)}' e siga pela"
                    else: acao = "Vire na"
                roteiro_texto.append(f"Passo {i+1}: {acao} {nome_rua_atual} (em direção a: {nome_cruzamento_destino})")
                nome_rua_anterior = nome_rua_atual
            
            roteiro_filepath = os.path.join(script_dir, 'roteiro_final.txt')
            with open(roteiro_filepath, 'w', encoding='utf-8') as f:
                f.write("--- ROTEIRO DA ROTA OTIMIZADA ---\n")
                f.write(f"Custo Total: R$ {custo_minimo:.2f}\n")
                f.write(f"Distância Total: {distancia_total_km:.2f} km\n\n")
                for linha in roteiro_texto:
                    f.write(linha + '\n')
            print(f"Roteiro em texto salvo em '{roteiro_filepath}'")

            nodes_gdf = ox.graph_to_gdfs(G_raw, nodes=True, edges=False)
            nodes_gdf['nome_descritivo'] = nodes_gdf.index.map(nomes_cruzamentos)
            mapa_dos_pontos = nodes_gdf.explore(
                tooltip='nome_descritivo', tiles="cartodbdarkmatter",
                marker_kwds={'radius': 5, 'color': 'cyan', 'fill': True, 'fill_opacity': 0.8},
                style_kwds={'stroke': False}
            )
            start_gdf = gpd.GeoDataFrame({'label': ['INÍCIO']}, geometry=[nodes_gdf.loc[no_inicio].geometry], crs=nodes_gdf.crs)
            end_gdf = gpd.GeoDataFrame({'label': ['FIM']}, geometry=[nodes_gdf.loc[no_fim].geometry], crs=nodes_gdf.crs)
            start_gdf.explore(m=mapa_dos_pontos, marker_kwds={'icon': 'play', 'marker_color': 'green'}, tooltip='label')
            end_gdf.explore(m=mapa_dos_pontos, marker_kwds={'icon': 'stop', 'marker_color': 'red'}, tooltip='label')
            
            map_filename = os.path.join(script_dir, 'mapa_referencia.html')
            mapa_dos_pontos.save(map_filename)
            print(f"Mapa interativo de referência salvo em '{map_filename}'")

        else:
            print("\nERRO: Não foi possível gerar um caminho Euleriano a partir da solução.")
    else:
        print("\nNão foi possível encontrar uma solução ótima.")

if __name__ == '__main__':
    main()