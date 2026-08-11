import pickle
import networkx as nx
import matplotlib.pyplot as plt
import os

def visualize_graph(graph_path, output_path=None):
    """
    Visualize the relationship graph with colors for different node types.
    """
    
    # Load the graph
    with open(graph_path, 'rb') as f:
        data = pickle.load(f)
    
    graph = data['graph']
    node_to_element = data.get('node_to_element', {})
    
    print(f"📊 Visualizing graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
    
    # Create a figure
    plt.figure(figsize=(20, 16))
    
    # Use spring layout for better visualization
    pos = nx.spring_layout(graph, k=1, iterations=50)
    
    # Color nodes by type
    node_colors = []
    node_types = {}
    
    for node in graph.nodes():
        node_type = graph.nodes[node].get('type', 'unknown')
        node_types[node] = node_type
    
    # Map types to colors
    color_map = {
        'document': 'lightblue',
        'heading': 'orange',
        'paragraph': 'lightgreen',
        'table': 'red',
        'figure': 'purple',
        'unknown': 'gray'
    }
    
    node_colors = [color_map.get(node_types.get(n, 'unknown'), 'gray') for n in graph.nodes()]
    
    # Draw the graph
    nx.draw(graph, pos, 
            node_color=node_colors,
            node_size=500,
            with_labels=False,
            edge_color='gray',
            alpha=0.6)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=color_map['document'], label='Document'),
        Patch(facecolor=color_map['heading'], label='Heading'),
        Patch(facecolor=color_map['paragraph'], label='Paragraph'),
        Patch(facecolor=color_map['table'], label='Table'),
        Patch(facecolor=color_map['figure'], label='Figure'),
    ]
    plt.legend(handles=legend_elements, loc='upper left')
    
    plt.title(f"Relationship Graph: {os.path.basename(graph_path)}", fontsize=16)
    plt.axis('off')
    
    # Save or show
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✅ Saved visualization to: {output_path}")
    else:
        plt.show()

def visualize_all_graphs():
    """Visualize all graph files in the graphs folder."""
    
    graphs_folder = "graphs"
    
    if not os.path.exists(graphs_folder):
        print("❌ No 'graphs' folder found!")
        return
    
    graph_files = [f for f in os.listdir(graphs_folder) if f.endswith('.pkl')]
    
    if not graph_files:
        print("❌ No graph files found!")
        return
    
    print(f"📁 Found {len(graph_files)} graph files:\n")
    for i, filename in enumerate(graph_files, 1):
        print(f"   {i}. {filename}")
    
    try:
        choice = int(input("\nSelect a file to visualize (enter number): ")) - 1
        if 0 <= choice < len(graph_files):
            graph_path = os.path.join(graphs_folder, graph_files[choice])
            output_path = f"visualization_{graph_files[choice].replace('.pkl', '.png')}"
            visualize_graph(graph_path, output_path)
        else:
            print("❌ Invalid selection!")
    except ValueError:
        print("❌ Please enter a valid number!")

if __name__ == "__main__":
    visualize_all_graphs()