import osmnx as ox
import networkx as nx
import pulp
import geopandas as gpd
import json
from shapely.geometry import Polygon

# CRIAÇÃO E LIMPEZA DO GRAFO

try:
    with open("dados_poligono.txt", "r") as f:
        polygon_coords = json.load(f)
    print("Dados do polígono lidos do arquivo com sucesso.")
except FileNotFoundError:
    print("ERRO: Arquivo 'dados_poligono.txt' não encontrado.")
    exit()

polygon_geom = Polygon(polygon_coords)

if not polygon_geom.is_valid:
    print("ERRO: O polígono é inválido.")
    exit()

print("Polígono criado com sucesso e é válido!")
G_raw = ox.graph_from_polygon(polygon_geom, network_type="all")
print(
    f"Grafo original gerado com {G_raw.number_of_nodes()} nós e {G_raw.number_of_edges()} arestas."
)

G_solver = G_raw.copy()
self_loops = list(nx.selfloop_edges(G_solver))
G_solver.remove_edges_from(self_loops)
G_solver = nx.Graph(G_solver)
print(
    f"Grafo simplificado para o solver com {G_solver.number_of_nodes()} nós e {len(G_solver.edges())} ruas."
)
print("-" * 30)

# DEFINIÇÃO DOS NÓS DE INÍCIO E FIM
no_inicio = 3503367399
no_fim = 3379729736
print(f"Nó de início definido: {no_inicio}")
print(f"Nó de fim definido: {no_fim}")

# GERAR NOMES DESCRITIVOS PARA OS CRUZAMENTOS
nomes_cruzamentos = {}
for node in G_raw.nodes():
    ruas_conectadas = set()
    for u, v, data in G_raw.edges(node, data=True):
        nome_rua_valor = data.get("name", None)
        if nome_rua_valor:
            if isinstance(nome_rua_valor, list):
                nome_final = nome_rua_valor[0]
            else:
                nome_final = nome_rua_valor
            ruas_conectadas.add(nome_final)
    ruas_conectadas = sorted(list(ruas_conectadas))
    if len(ruas_conectadas) == 0:
        nomes_cruzamentos[node] = f"Ponto {node}"
    elif len(ruas_conectadas) == 1:
        nomes_cruzamentos[node] = f"Final da {ruas_conectadas[0]}"
    elif len(ruas_conectadas) == 2:
        nomes_cruzamentos[node] = (
            f"Esquina da {ruas_conectadas[0]} com {ruas_conectadas[1]}"
        )
    else:
        nomes_cruzamentos[node] = (
            f"Cruzamento da {', '.join(ruas_conectadas[:-1])} e {ruas_conectadas[-1]}"
        )
print("Nomes descritivos para os cruzamentos foram gerados.")
print("-" * 30)

# DEFINIÇÃO DOS PARÂMETROS DO MODELO
C_LITRO = 5.80
KM_LITRO = 5.0
C_KM = C_LITRO / KM_LITRO
V = list(G_solver.nodes())
E = list(G_solver.edges())
A = []
costs = {}
for i, j in E:
    edge_data = G_raw.get_edge_data(i, j)
    if edge_data is None:
        edge_data = G_raw.get_edge_data(j, i)
    dist_m = edge_data[0]["length"]
    dist_km = dist_m / 1000.0
    cost = C_KM * dist_km
    A.extend([(i, j), (j, i)])
    costs[(i, j)] = cost
    costs[(j, i)] = cost
print(f"Parâmetros definidos. Custo por km: R${C_KM:.2f}")
print("-" * 30)

# MODELAGEM E RESOLUÇÃO COM PULP
model = pulp.LpProblem("Otimizacao_Rota_Coleta", pulp.LpMinimize)

# Definição das Variáveis de Decisão (x_ij)
# A linha abaixo implementa a RESTRIÇÃO 3 (Domínio das Variáveis) do LaTeX.
# cat='Integer' garante que x_ij seja um número inteiro.
# lowBound=0 garante que x_ij seja não negativo (>= 0).
x = pulp.LpVariable.dicts("x", A, lowBound=0, cat="Integer")

# Definição da Função Objetivo
# A linha abaixo implementa a Função Objetivo do LaTeX.
# Equação: Minimizar Z = Soma(c_ij * x_ij)
model += pulp.lpSum([costs[i, j] * x[i, j] for (i, j) in A]), "Custo_Total"

# Adicionando as Restrições ao Modelo ---

# RESTRIÇÃO 1: COBERTURA DE TODAS AS RUAS
# Garante que cada rua (aresta em E) seja percorrida pelo menos uma vez, em qualquer sentido.
# Equação LaTeX: x_ij + x_ji >= 1, para todo {i, j} in E
for i, j in E:
    model += x[i, j] + x[j, i] >= 1, f"Cobertura_Rua_{i}_{j}"

# RESTRIÇÃO 2: CONSERVAÇÃO DE FLUXO
# Garante que a rota seja contínua, balanceando as entradas e saídas de cada nó.
for k in V:
    # Soma dos arcos que entram no nó k
    fluxo_entrada = pulp.lpSum([x[i, k] for i, j in A if j == k])
    # Soma dos arcos que saem do nó k
    fluxo_saida = pulp.lpSum([x[k, j] for i, j in A if i == k])

    # Sub-restrição 2.1: Nó de Início
    # O fluxo de saída deve ser 1 unidade maior que o de entrada.
    # Equação LaTeX: Soma(x_sj) - Soma(x_is) = 1
    if k == no_inicio:
        model += fluxo_saida - fluxo_entrada == 1, f"Fluxo_Inicio_{k}"

    # Sub-restrição 2.2: Nó de Fim
    # O fluxo de entrada deve ser 1 unidade maior que o de saída.
    # Equação LaTeX: Soma(x_it) - Soma(x_tj) = 1
    elif k == no_fim:
        model += fluxo_entrada - fluxo_saida == 1, f"Fluxo_Fim_{k}"

    # Sub-restrição 2.3: Nós Intermediários
    # O fluxo de entrada deve ser igual ao de saída.
    # Equação LaTeX: Soma(x_ik) - Soma(x_kj) = 0
    else:
        model += fluxo_entrada - fluxo_saida == 0, f"Fluxo_Intermediario_{k}"

print("Modelo montado. Iniciando o solver...")
model.solve(pulp.GLPK_CMD(msg=True))
status = pulp.LpStatus[model.status]
print(f"Status da Solução: {status}")

if status == "Optimal":
    custo_minimo = pulp.value(model.objective)
    distancia_total_km = custo_minimo / C_KM
    print("\n--- SOLUÇÃO ÓTIMA ENCONTRADA ---")
    print(f"Custo total mínimo da rota: R$ {custo_minimo:.2f}")
    print(f"Distância total a ser percorrida: {distancia_total_km:.2f} km")

    solucao_x = {}
    for i, j in A:
        if x[i, j].varValue > 0:
            solucao_x[(i, j)] = int(x[i, j].varValue)

    # GERAÇÃO DA ROTA FINAL (CAMINHO EULERIANO)
    G_euleriano = nx.MultiDiGraph()
    for (u, v), num_travessias in solucao_x.items():
        for _ in range(num_travessias):
            G_euleriano.add_edge(u, v)

    if nx.has_eulerian_path(G_euleriano, source=no_inicio):
        rota_em_arestas = list(nx.eulerian_path(G_euleriano, source=no_inicio))

        # IMPRESSÃO DO ROTEIRO DE RUAS
        print("\n\n>>> ROTEIRO DA ROTA OTIMIZADA (LISTA DE RUAS) <<<\n")
        roteiro_final = []
        nome_rua_anterior = None
        for i, (u, v) in enumerate(rota_em_arestas):
            edge_data = G_raw.get_edge_data(u, v)
            if edge_data is None:
                edge_data = G_raw.get_edge_data(v, u)
            nome_rua_valor = edge_data[0].get("name", "Rua sem nome")
            if isinstance(nome_rua_valor, list):
                nome_rua_atual = nome_rua_valor[0]
            else:
                nome_rua_atual = nome_rua_valor
            nome_cruzamento_destino = nomes_cruzamentos.get(v, f"Ponto {v}")
            if nome_rua_atual == nome_rua_anterior:
                acao = "Continue pela"
            else:
                if i == 0:
                    acao = f"Comece em '{nomes_cruzamentos.get(u)}' e siga pela"
                else:
                    acao = "Vire na"
            roteiro_final.append(
                f"Passo {i+1}: {acao} **{nome_rua_atual}** (em direção a: **{nome_cruzamento_destino}**)"
            )
            nome_rua_anterior = nome_rua_atual

        roteiro_final.append(f"\n--- FIM DA ROTA ---")
        destino_final = nomes_cruzamentos.get(rota_em_arestas[-1][1])
        roteiro_final.append(
            f"A rota tem {len(rota_em_arestas)} passos e termina em: '{destino_final}'."
        )

        try:
            with open("roteiro_final.txt", "w", encoding="utf-8") as f:
                f.write("--- ROTEIRO DA ROTA OTIMIZADA ---\n")
                f.write(f"Custo Total: R$ {custo_minimo:.2f}\n")
                f.write(f"Distância Total: {distancia_total_km:.2f} km\n\n")
                for linha in roteiro_final:
                    f.write(linha + "\n")
            print("Roteiro final exportado com sucesso para 'roteiro_final.txt'")
        except Exception as e:
            print(f"Erro ao salvar o roteiro: {e}")

        # GERAÇÃO DO MAPA INTERATIVO DOS CRUZAMENTOS
        nodes_gdf = ox.graph_to_gdfs(G_raw, nodes=True, edges=False)
        nodes_gdf["nome_descritivo"] = nodes_gdf.index.map(nomes_cruzamentos)
        mapa_dos_pontos = nodes_gdf.explore(
            tooltip="nome_descritivo",
            tiles="cartodbdarkmatter",
            marker_kwds={
                "radius": 5,
                "color": "cyan",
                "fill": True,
                "fill_opacity": 0.8,
            },
            style_kwds={"stroke": False},
        )
        start_gdf = gpd.GeoDataFrame(
            {"label": ["INÍCIO"]},
            geometry=[nodes_gdf.loc[no_inicio].geometry],
            crs=nodes_gdf.crs,
        )
        end_gdf = gpd.GeoDataFrame(
            {"label": ["FIM"]},
            geometry=[nodes_gdf.loc[no_fim].geometry],
            crs=nodes_gdf.crs,
        )
        start_gdf.explore(
            m=mapa_dos_pontos,
            marker_kwds={"icon": "play", "marker_color": "green"},
            tooltip="label",
        )
        end_gdf.explore(
            m=mapa_dos_pontos,
            marker_kwds={"icon": "stop", "marker_color": "red"},
            tooltip="label",
        )
        map_filename = "mapa_referencia_cruzamentos.html"
        mapa_dos_pontos.save(map_filename)
        print(f"\nMAPA DE REFERÊNCIA GERADO: '{map_filename}'")
        print(
            "Abra este arquivo no seu navegador para ver todos os pontos e seus nomes."
        )

    else:
        print(
            "\nERRO: Não foi possível gerar um caminho Euleriano a partir da solução."
        )
else:
    print("\nNão foi possível encontrar uma solução ótima.")
