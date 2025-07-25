from graphviz import Digraph
import os

def visualize_workflow(workflow, output_path='workflow.png'):
    dot = Digraph(comment=workflow.get('name', 'Workflow'))
    for node in workflow['nodes']:
        dot.node(node['id'], f"{node['id']}\n{node['type']}")
    for conn in workflow['connections']:
        dot.edge(conn['from'], conn['to'], label=conn.get('condition', ''))
    dot.render(output_path, format='png', cleanup=True)
    print(f"流程图已生成: {output_path}.png") 