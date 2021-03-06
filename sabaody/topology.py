# Sabaody
# Copyright 2018 Shaik Asifullah and J Kyle Medley
from __future__ import print_function, division, absolute_import

from .pygmo_interf import Island

import networkx as nx
import pygmo as pg

from itertools import chain
from abc import ABC, abstractmethod
from uuid import uuid4
import collections
from random import choice, randint
from typing import Union, Callable

class AlgorithmCtorFactory(ABC):
    '''
    A base class for constructing algorithms.
    If the algorithm you wish to use depends on properties
    of the topology (such as node degree etc.), you can
    derive from this class to construct your own algorithm
    per island.
    It is called during topology creation with the node (island)
    and topology.
    '''
    @abstractmethod
    def __call__(self,island,topology):
        pass

class Topology(nx.Graph):
    '''
    nx.Graph with additional convenience methods.
    '''

    def neighbor_ids(self, id):
        return tuple(self.neighbors(id))

    def outgoing_ids(self, id):
        '''
        For an undirected topology, the outgoing ids are just
        the neighbor ids.
        '''
        return tuple(self.neighbors(id))



    def neighbor_islands(self, id):
        return tuple(self.nodes[n]['island'] for n in self.neighbors(id))

    def outgoing_islands(self, id):
        return self.neighbor_islands(id)


class DiTopology(nx.DiGraph,Topology):
    '''
    nx.DiGraph with additional convenience methods.
    '''

    def outgoing_ids(self, id):
        '''
        For a directed topology, the outgoing ids can be
        different from the incomming ids.
        '''
        return tuple(self.successors(id))

    def outgoing_islands(self, id):
        return tuple(self.nodes[n]['island'] for n in self.successors(id))

    def neighbor_ids(self, id):
        return tuple(chain(self.successors(id),self.predecessors(id)))

    def incoming_ids(self , id):
        node_list = []
        for each_node in list(self.nodes):
            if id in list(self.neighbors(each_node)):
                node_list.append(each_node)
        return node_list

    def neighbor_islands(self, id):
        return tuple(self.nodes[n]['island'] for n in chain(self.successors(id),self.predecessors(id)))


class TopologyFactory:
    '''
    Has methods for constructing a variety of topologies.
    '''

    def __init__(self, problem_constructor, domain_qualifier, mc_host, mc_port=11211):
        self.problem_constructor = problem_constructor
        self.domain_qualifier = domain_qualifier
        self.mc_host = mc_host
        self.mc_port = mc_port


    def _getAlgorithmConstructor(self, algorithm_factory, node, graph):
        # type: (Union[AlgorithmCtorFactory,collections.abc.Sequence,Callable[[],pg.algorithm]], int, Union[nx.Graph,nx.DiGraph]) -> Callable[[],pg.algorithm]
        '''
        If algorithm_factory is a factory, call it with the node and graph.
        If instead it is a list of constructors, choose one at random.
        If it is simply a direct constructor for a pagmo algorithm,
        just return it.
        '''
        if isinstance(algorithm_factory, AlgorithmCtorFactory):
            return algorithm_factory(node, graph)
        elif isinstance(algorithm_factory, collections.abc.Sequence):
            return choice(algorithm_factory)
        else:
            return algorithm_factory


    def _processTopology(self,raw,algorithm_factory,island_size,topology_class):
        '''
        Converts a graph of indices (generated by nxgraph) into a topology
        of island ids.
        '''
        m = dict((k,Island(str(uuid4()),
                           self.problem_constructor,
                           self._getAlgorithmConstructor(algorithm_factory,k,raw),
                           island_size,
                           self.domain_qualifier,
                           self.mc_host,
                           self.mc_port)) for k in raw.nodes)
        g = topology_class()
        g.add_nodes_from(island.id for island in m.values())
        for k,i in m.items():
            g.nodes[m[k].id]['island'] = m[k]
        g.add_edges_from((m[u].id, m[v].id)
                         for u, nbrs in raw._adj.items()
                         for v, data in nbrs.items())
        g.island_ids = tuple(id for id in g.nodes)
        g.islands = tuple(g.nodes[i]['island'] for i in g.nodes)
        return g


    def createOneWayRing(self, algorithm_factory, number_of_islands = 100, island_size = 20):
        # type: (Union[AlgorithmCtorFactory,collections.abc.Sequence,Callable[[],pg.algorithm]], int, int) -> DiTopology
        '''
        Creates a one way ring topology.
        '''
        g = self._processTopology(nx.cycle_graph(number_of_islands, create_using=nx.DiGraph()), algorithm_factory, island_size, DiTopology)
        return g


    def createBidirRing(self, algorithm_factory, number_of_islands = 100, island_size = 20):
        # type: (Union[AlgorithmCtorFactory,collections.abc.Sequence,Callable[[],pg.algorithm]], int, int) -> DiTopology
        '''
        Creates a bidirectional ring topology.
        '''
        g = self._processTopology(nx.cycle_graph(number_of_islands, create_using=nx.Graph()), algorithm_factory, island_size, Topology)
        return g


    def createBidirChain(self, algorithm_factory, number_of_islands = 100, island_size = 20):
        # type: (Callable, int, int) -> Topology
        '''
        Creates a linear chain topology.
        '''
        g = self._processTopology(nx.path_graph(number_of_islands, create_using=nx.Graph()), algorithm_factory, island_size, Topology)
        # label head and tail nodes
        endpoints = set()
        for n in g.nodes:
            if len(tuple(g.neighbors(n))) == 1:
                endpoints.add(n)
        g.endpoints = tuple(endpoints)
        return g


    def createLollipop(self, algorithm_factory, complete_subgraph_size = 100, chain_size = 10, island_size = 20):
        # type: (Callable, int, int, int) -> Topology
        '''
        Creates a topology from a lollipop graph.
        '''
        # TODO: chain should be one-way
        g = self._processTopology(nx.lollipop_graph(complete_subgraph_size, chain_size, create_using=nx.Graph()), algorithm_factory, island_size, Topology)
        # label tail nodes
        endpoints = set()
        for n in g.nodes:
            if len(tuple(g.neighbors(n))) == 1:
                endpoints.add(n)
        g.endpoints = tuple(endpoints)
        return g


    def createRim(self, algorithm_factory, number_of_islands = 100, island_size = 20):
        # type: (Union[AlgorithmCtorFactory,collections.abc.Sequence,Callable[[],pg.algorithm]], int, int) -> Topology
        '''
        Creates a rim topology (ring with all nodes connected to a single node).
        '''
        g = self._processTopology(nx.cycle_graph(number_of_islands, create_using=nx.Graph()), algorithm_factory, island_size, Topology)
        g.hub = tuple(g.nodes)[0]
        for n in g.nodes:
            if n != g.hub:
                g.add_edge(n,g.hub)
        return g


    def create_12_Ring(self, algorithm_factory, number_of_islands = 100, island_size = 20):
        '''
        Creates a 1-2 ring, where every node in the ring is connected to
        its neighbors and the neighbors of its neighbors.
        '''
        g = nx.Graph()
        g.add_nodes_from(range(1, number_of_islands + 1))
        for each_island in range(1, number_of_islands + 1):
            for step in range(1,3):
                to_edge = each_island + step
                if to_edge > number_of_islands:
                    to_edge = to_edge % number_of_islands
                g.add_edge(each_island,to_edge)
        return self._processTopology(g)


    def create_123_Ring(self, algorithm_factory, number_of_islands = 100, island_size = 20):
        '''
        Creates a 1-2-3 ring, where every node in the ring is connected to
        its neighbors, the neighbors of its neighbors, and nodes three steps away.
        '''
        g = nx.Graph()
        g.add_nodes_from(range(1, number_of_islands + 1))
        for each_island in range(1, number_of_islands + 1):
            for step in range(1, 4):
                to_edge = each_island + step
                if to_edge > number_of_islands:
                    to_edge = to_edge % number_of_islands
                g.add_edge(each_island, to_edge)
        return self._processTopology(g)


    def createFullyConnected(self, algorithm_factory, number_of_islands = 100, island_size = 20):
        '''
        A fully connected (complete) topology.
        '''
        return  self._processTopology(nx.complete_graph(number_of_islands, create_using=nx.Graph()), algorithm_factory, island_size, Topology)


    def createBroadcast(self, algorithm_factory, number_of_islands = 100, central_node = 1, island_size = 20):
        '''
        A collection of islands not connected to each other but
        connected to a central node.
        '''
        g = nx.Graph()
        g.add_nodes_from(range(1, number_of_islands + 1))
        for each_island in range(1,number_of_islands+1):
            if central_node == each_island:
                continue
            g.add_edge(central_node,each_island)
        return self._processTopology(g)


    def createHypercube(self, algorithm_factory, dimension = 10, island_size = 20):
        # type: (Union[AlgorithmCtorFactory,collections.abc.Sequence,Callable[[],pg.algorithm]], int, int) -> Topology
        '''
        Creates a hypercube topology.
        '''
        return self._processTopology(nx.hypercube_graph(dimension), algorithm_factory, island_size, Topology)


    def createWattsStrogatz(self, algorithm_factory, num_nodes=100, k=10, p=0.1, seed = None, island_size = 20):
        # type: (Union[AlgorithmCtorFactory,collections.abc.Sequence,Callable[[],pg.algorithm]], int, int, float, int, int) -> Topology
        '''
        Creates a Watts Strogatz topology - a ring lattice (i.e. a ring of n nodes each connected to k
        neighbors) in which the rightmost k/2 nodes are rewired with probability p.
        These graphs tend to exhibit high clustering and short average path lengths.
        `See also: PaGMO's description. <http://esa.github.io/pygmo/documentation/topology.html>`_
        '''
        seed = seed or randint(0,10000)
        return self._processTopology(nx.watts_strogatz_graph(num_nodes,k,p,seed), algorithm_factory, island_size, Topology)


    def createErdosRenyi(self, algorithm_factory, num_nodes=100, p=0.1, directed = False, seed = None, island_size = 20):
        # type: (Union[AlgorithmCtorFactory,collections.abc.Sequence,Callable[[],pg.algorithm]], int, float, bool, int, int) -> Topology
        '''
        Creates a topology based on an Erdős-Rényi random graph.
        '''
        seed = seed or randint(0,10000)
        return self._processTopology(nx.erdos_renyi_graph(num_nodes,p,seed,directed), algorithm_factory, island_size, Topology)


    def createBarabasiAlbert(self, algorithm_factory, num_nodes=100, m=3, seed = None, island_size = 20):
        # type: (Union[AlgorithmCtorFactory,collections.abc.Sequence,Callable[[],pg.algorithm]], int, int, int, int) -> Topology
        '''
        Creates a topology based on a Barabási-Albert graph.
        '''
        seed = seed or randint(0,10000)
        return self._processTopology(nx.barabasi_albert_graph(num_nodes,m,seed), algorithm_factory, island_size, Topology)








