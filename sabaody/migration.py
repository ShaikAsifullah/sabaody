from __future__ import print_function, division, absolute_import

from numpy import argsort, flipud

from abc import ABC, abstractmethod

class SelectionPolicyBase(ABC):
    '''
    Selects migrants to be sent to other islands.
    '''
    @abstractmethod
    def select(self, population):
        pass

class ReplacementPolicyBase(ABC):
    '''
    Policy controlling whether to replace an individual
    in a population with a migrant.
    '''
    @abstractmethod
    def replace(self, population, candidates, candidate_f):
        pass

def sort_by_fitness(population):
    indices = argsort(population.get_f(), axis=0)
    return (population.get_x()[indices[:,0]],
            population.get_f()[indices[:,0]])

# ** Selection Policies **
class BestSPolicy(SelectionPolicyBase):
    '''
    Selection policy.
    Selects the best N individuals from a population.
    '''
    def __init__(self, pop_fraction):
        self.pop_fraction = pop_fraction

    def select(self, population):
        '''
        Selects the top pop_fraction*population_size
        individuals and returns them as a 2D array
        (different vectors are in different rows).
        Cannot be used with multiple objectives - partial
        order is requred.

        The returned array of candidates should be sorted descending
        according to best fitness value.
        '''
        indices = argsort(population.get_f(), axis=0)
        n_migrants = int(indices.size*self.pop_fraction)
        # WARNING: single objective only
        return (population.get_x()[indices[:n_migrants,0]],
                population.get_f()[indices[:n_migrants,0]])

# ** Replacement Policies **
class FairRPolicy(ReplacementPolicyBase):
    '''
    Fair replacement policy.
    Replaces the worst N individuals in the population if the
    candidates are better.
    '''

    def replace(self, population, candidates, candidate_f):
        '''
        Replaces the worst N individuals in the population if the
        candidates are better.

        :param candidates: Numpy 2D array with candidates in rows.
        '''
        indices = flipud(argsort(population.get_f(), axis=0))
        pop_f = population.get_f()
        print('len candidate_f: {}'.format(len(candidate_f)))
        for i,k,f in zip(indices[:,0],range(len(candidate_f)),candidate_f):
            if f < pop_f[i,0]:
                population.set_xf(int(i),candidates[k,:],f)