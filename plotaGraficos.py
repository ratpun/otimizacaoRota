import matplotlib.pyplot as plt
import osmnx as ox
from criaGrafoCondominio import cria_grafo_condominio

G = cria_grafo_condominio()

def plot_grafo_condominio(grafo):
    fig, ax = plt.subplots(figsize=(10, 10))
    ox.plot_graph(grafo, ax=ax)
    plt.show()
    