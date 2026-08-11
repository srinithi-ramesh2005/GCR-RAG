"""
Relationship Graph - The HEART of relationship preservation.
Builds a rich graph of document relationships.
"""

import json
import pickle
from typing import List, Dict, Optional
from collections import defaultdict
import networkx as nx

class RelationshipGraph:
    """Comprehensive relationship graph for documents."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.element_to_node = {}
        self.node_to_element = {}
    
    def build_from_elements(self, elements: List[Dict], relationships: List[Dict]):
        """Build relationship graph from parsed elements."""
        for elem in elements:
            node_id = elem['element_id']
            self.element_to_node[elem['element_id']] = node_id
            self.node_to_element[node_id] = elem
            
            self.graph.add_node(
                node_id,
                type=elem.get('element_type', 'text'),
                content=elem.get('content', '')[:100],
                page=elem.get('page_number', 0),
                section=elem.get('section', ''),
                heading_level=elem.get('heading_level', 0)
            )
        
        for rel in relationships:
            source = rel.get('source')
            target = rel.get('target')
            rel_type = rel.get('type', 'NEIGHBOR')
            strength = rel.get('strength', 0.8)
            
            if source in self.element_to_node and target in self.element_to_node:
                self.graph.add_edge(
                    self.element_to_node[source],
                    self.element_to_node[target],
                    type=rel_type,
                    strength=strength,
                    metadata=rel.get('metadata', {})
                )
        
        self._add_semantic_relationships(elements)
        self._add_spatial_relationships(elements)
        
        print(f"✅ Built relationship graph with {self.graph.number_of_nodes()} nodes "
              f"and {self.graph.number_of_edges()} edges")
    
    def _add_semantic_relationships(self, elements: List[Dict], threshold: float = 0.7):
        """Add relationships based on content similarity."""
        for i, elem1 in enumerate(elements):
            words1 = set(elem1.get('content', '').lower().split())
            words1 = {w for w in words1 if len(w) > 4}
            if not words1:
                continue
            
            for j, elem2 in enumerate(elements[i+1:], i+1):
                words2 = set(elem2.get('content', '').lower().split())
                words2 = {w for w in words2 if len(w) > 4}
                if not words2:
                    continue
                
                intersection = words1 & words2
                union = words1 | words2
                similarity = len(intersection) / len(union) if union else 0
                
                if similarity > threshold and len(intersection) >= 2:
                    source = self.element_to_node[elem1['element_id']]
                    target = self.element_to_node[elem2['element_id']]
                    self.graph.add_edge(
                        source, target,
                        type='SEMANTIC',
                        strength=similarity,
                        metadata={'common_words': list(intersection)[:5]}
                    )
    
    def _add_spatial_relationships(self, elements: List[Dict]):
        """Add relationships based on spatial proximity."""
        page_elements = defaultdict(list)
        for elem in elements:
            page = elem.get('page_number', 0)
            page_elements[page].append(elem)
        
        for page, elems in page_elements.items():
            sorted_elems = sorted(elems, key=lambda x: x.get('position', 0))
            
            for i in range(len(sorted_elems) - 1):
                for j in range(i+1, min(i+3, len(sorted_elems))):
                    source = self.element_to_node[sorted_elems[i]['element_id']]
                    target = self.element_to_node[sorted_elems[j]['element_id']]
                    distance = j - i
                    strength = 1.0 / (distance + 1)
                    
                    self.graph.add_edge(
                        source, target,
                        type='SPATIAL',
                        strength=strength,
                        metadata={'distance': distance, 'page': page}
                    )
    
    def get_element_context(self, element_id: str, depth: int = 2) -> Dict:
        """Get comprehensive context for an element."""
        if element_id not in self.element_to_node:
            return None
        
        node_id = self.element_to_node[element_id]
        
        context = {
            'self': self.node_to_element.get(node_id),
            'parents': [],
            'children': [],
            'siblings': [],
            'neighbors': [],
            'semantic_related': [],
            'spatial_related': []
        }
        
        current = node_id
        for _ in range(depth):
            predecessors = list(self.graph.predecessors(current))
            for pred in predecessors:
                edge_data = self.graph.get_edge_data(pred, current)
                if edge_data and edge_data.get('type') == 'PARENT_CHILD':
                    context['parents'].append(self.node_to_element.get(pred))
                    current = pred
                    break
            else:
                break
        
        for succ in self.graph.successors(node_id):
            edge_data = self.graph.get_edge_data(node_id, succ)
            if edge_data and edge_data.get('type') == 'PARENT_CHILD':
                context['children'].append(self.node_to_element.get(succ))
        
        if context['parents']:
            parent_id = self.element_to_node.get(context['parents'][0].get('element_id'))
            if parent_id:
                for succ in self.graph.successors(parent_id):
                    if succ != node_id:
                        edge_data = self.graph.get_edge_data(parent_id, succ)
                        if edge_data and edge_data.get('type') == 'PARENT_CHILD':
                            context['siblings'].append(self.node_to_element.get(succ))
        
        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph.get_edge_data(node_id, neighbor)
            if edge_data:
                if edge_data.get('type') == 'NEIGHBOR':
                    context['neighbors'].append(self.node_to_element.get(neighbor))
                elif edge_data.get('type') == 'SEMANTIC':
                    context['semantic_related'].append(self.node_to_element.get(neighbor))
                elif edge_data.get('type') == 'SPATIAL':
                    context['spatial_related'].append(self.node_to_element.get(neighbor))
        
        return context
    
    def get_full_context(self, chunk: Dict, expand_by: int = 2) -> Dict:
        """Get full context for a chunk including all related elements."""
        element_ids = chunk.get('element_ids', [])
        if isinstance(element_ids, str):
            element_ids = json.loads(element_ids)
        
        all_context = {
            'chunk': chunk,
            'elements': [],
            'parents': [],
            'children': [],
            'neighbors': [],
            'semantic_related': [],
            'spatial_related': []
        }
        
        for elem_id in element_ids:
            context = self.get_element_context(elem_id, depth=2)
            if context:
                all_context['elements'].append(context['self'])
                all_context['parents'].extend(context['parents'])
                all_context['children'].extend(context['children'])
                all_context['neighbors'].extend(context['neighbors'])
                all_context['semantic_related'].extend(context['semantic_related'])
                all_context['spatial_related'].extend(context['spatial_related'])
        
        for key in ['parents', 'children', 'neighbors', 'semantic_related', 'spatial_related']:
            seen = set()
            unique = []
            for item in all_context[key]:
                if item:
                    elem_id = item.get('element_id')
                    if elem_id and elem_id not in seen:
                        seen.add(elem_id)
                        unique.append(item)
            all_context[key] = unique
        
        return all_context
    
    def save(self, filepath: str):
        """Save the graph to disk."""
        with open(filepath, 'wb') as f:
            pickle.dump({
                'graph': self.graph,
                'element_to_node': self.element_to_node,
                'node_to_element': self.node_to_element
            }, f)
    
    def load(self, filepath: str):
        """Load the graph from disk."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.graph = data['graph']
            self.element_to_node = data['element_to_node']
            self.node_to_element = data['node_to_element']