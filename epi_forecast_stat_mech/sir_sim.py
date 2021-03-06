"""# Data Simulation
(from [edklein's Colab](https://colab.sandbox.google.com/drive/1jFozxrQeOmvxfnqzv7q-CUdD5Yqh5Hnj#scrollTo=yOJ3cS758hOT))
(last copied 20200406 12pm PST)

# Discrete SIR Model

Write a function that generates a single discrete time SIR model.
"""

import numpy as np
from scipy import stats
import pandas as pd
import collections


meta_data = collections.namedtuple('meta_data', [
    'num_epidemics', 'epidemic_id', 'frac_estimate_of_total',
    'percent_infected', 'pop_size', 'beta', 'gamma'
])
"""A named tuple to hold a single disease metadata.

num_epidemics: an int representing the total number of epidemics to simulate
epidemic_id: an int representing the identifier of this epidemic
frac_estimate_of_total: a float representing fraction of the infection we've
seen so far (i.e. 1/2)
percent_infected: a float representing the percent of the population that has
been infected at this point in time, for each epidemic
pop_size: an int representing the population size
beta: a float representing the growth rate of the disease
gamma: a float representing the recovery rate of the disease
"""

disease_trajectory = collections.namedtuple(
    'disease_trajectory',
    [
        'unique_id',
        'simulation_number',
        'epidemic_number',
        'num_new_infections_over_time',
        'estimated_infections',
        'ground_truth_infections_over_time',
        'total_infections',
        'v',
        'alpha',
        'metadata',
        #@@hack
        't',
        'ground_truth_t',
        'cumulative_infections_over_time',
        'ground_truth_cumulative_infections_over_time'
    ])
"""A named tuple to hold a single disease trajectory and all relevant metadata.

unique_id: an int representing the unique identifier of each trajectory
simulation_number: an int representing the simulation we generated this
trajectory in, only useful for debugging
epidemic_number: an int representing the epidemic we generated this trajectory
in, only useful for debugging
num_new_infections_over_time: a np.array of length T representing the number of
new infections at each time step up to a threshold
total_estimated_infections: an int representing our estimate of the total
infections
ground_truth_infections_over_time: a np.array of length TT representing the
*ground truth* number of new infections at each time step
total_infections: an int representing the ground truth number of total
infections
total_infections: an int representing the total *ground truth* number of
infections
v: a np.array of shape (num_epidemics, num_covariates) and type float
representing the covariates used for each epidemic
alpha: a np.array of shape (num_covariates,) and type float representing the
weights of each covariate
meta_data: a named tuple of type meta_data
t: a np.array of shape (T,) representing the simulation time of each point in
the epidemic
ground_truth_t: a np.array of shape (TT,) representing the simulation time of
each point in the ground truth simulation
cumulative_infections_over_time: a np.array representing the "non-predictive"
cumsum of the epidemic
ground_truth_cumulative_infections_over_time: a np.array representing the
"non-predictive" cumsum of the ground truth simulation
"""

def generate_ground_truth_SIR_curve(pop_size, beta, gamma):
  """
  A function that generates a single epidemic curve through time.
  We assume that the epidemic starts with a single case at time 0.  
  Simulates the number of infected individuals as a function of time, until the 
  number of infected individuals is 0. This is the epidemic curve.
  Returns the epidemic curves as a function of time.

  Args:
    pop_size: an int representing the population size
    beta: a float representing the growth rate of the disease
    gamma: a float representing the recovery rate of the disease
  
  Returns:
    list_of_new_infections: a np.array of shape (T,) representing the ground
                            truth number of infected individuals as a function of time
  """
  num_infected = 1 # always start with one infection at time 0
  num_recovered = 0
  num_susceptible = int(pop_size - num_infected - num_recovered)

  list_of_new_infections = np.array([num_infected])

  #While there are still infected people
  while num_infected > 0: 
    #Calculate the probability that a person becomes infected
    #Python3 doesn't seem to work, so force a float 
    frac_pop_infected = float(num_infected) / pop_size
    prob_infected = 1 - np.exp(-beta*frac_pop_infected)
    
    #Determine the number of new infections
    #By drawing from a binomial distribution 
    num_new_infections = stats.binom.rvs(num_susceptible, prob_infected)

    #Calculate the probability that a person recovers
    prob_recover = 1 - np.exp(-gamma)

    #Determine the number of recoveries
    #by drawing from a binomial distribution
    num_new_recoveries = stats.binom.rvs(num_infected, prob_recover)

    #Record the number of infections that occured at this time point
    list_of_new_infections = np.append(list_of_new_infections, num_new_infections)

    #update counts for next iteration
    #sum of all counts is constant and equal to population size
    num_infected = num_infected + num_new_infections - num_new_recoveries
    num_recovered += num_new_recoveries
    num_susceptible -= num_new_infections

  return list_of_new_infections

def generate_observed_SIR_curves(percent_infected, pop_size, beta, gamma):
  """
  Generate the epidemic curve observed to date using the SIR model.

  Args:
    percent_infected: a float representing the percent of the population that 
                      has been infected at this point in time, for each epidemic
    pop_size: an int representing the population size
    beta: a float representing the growth rate of the disease
    gamma: a float representing the recovery rate of the disease
  
  Returns:
    observed_infections: a np.array of shape (T,) representing the number of
                         newly infected individuals as a function of time, 
                         up to the current time
    ground_truth_infections: an np.array of shape(TT,) representing the number 
                             of newly infectecd individuals over the course of 
                             the *whole* epidemic
  """
  # We require that the total number of infections is >10
  # to eliminate stochastic fadeouts
  total_infections = 0
  # also have a count limit to avoid an infinite loop
  count = 0
    
  while total_infections < 10 and count<5000:
    ground_truth_infections = generate_ground_truth_SIR_curve(pop_size, beta, gamma)
    total_infections = np.sum(ground_truth_infections)
    count += 1

  # calculate the target size for this epidemic
  target_size = total_infections * percent_infected

  # Find the current time, this is when the cumulative size of the model is still smaller than the target size
  # must be at least 2
  cumulative_infections = np.cumsum(ground_truth_infections)
  current_time = np.max([np.max(np.where(cumulative_infections < target_size)), 2])

  # Save list of infected individuals up until we reach the target_size
  # This is the 'history' of the epidemic up until the current time
  observed_infections = ground_truth_infections[:current_time]

  return observed_infections, ground_truth_infections

def generate_SIR_simulations(gen_beta_fn, beta_gen_parameters, num_simulations, 
                             num_epidemics, constant_gamma=0.33, constant_pop_size=10000,
                             const_estimate_of_total=0.5):
  """
  Generate many simulations of SIR curves.
  Each simulation contains num_epidemics.
  The epidemics may have different covariates, and thus different trajectories.
  However between simulations the covariates are the same, so the only difference 
  is statistical.

  Args:
    gen_beta_fn: a function to generate the beta values for each epidemic
    beta_gen_parameters: a tuple containing all the parameters needed by gen_beta_fn
    num_simulations: an int representing the number of simulations to run
    num_epidemics: an int representing the number of epidemics to run in each simulation
    constant_gamma: a float representing the constant recovery rate (default 0.33)
    constant_pop_size: an int representing the constant population size (default 10000)
    const_estimate_of_total: a float representing the estimated fraction of the infection we've seen so far (default 1/2)
  Returns:
    list_of_disease_trajectory: a list of disease_trajectory named tuples
  """
  list_of_meta_data = [] 
  list_of_disease_trajectory = [] 

  # generate growth rate for all simulations,
  # this is constant between simulations 
  beta, v, alpha = gen_beta_fn(*beta_gen_parameters)

  # randomly generate the percentage of infected people for each epidemic
  # this is constant between simulations
  percent_infected = np.random.uniform(0.05, 1.0, num_epidemics)
  
  # generate meta data for each epidemic
  # TODO: do better
  for i in range(num_epidemics):
    md = meta_data(num_epidemics, i, const_estimate_of_total, percent_infected[i],
                   constant_pop_size, beta[i], constant_gamma)
    # I guess technically v and alpha should be in meta data...
    list_of_meta_data.append(md)

  unique_id = 0
  for j in range(num_simulations):
    for k in range(num_epidemics):
      observed_infections, ground_truth_infections = generate_observed_SIR_curves(*list_of_meta_data[k][3:])
      estimated_infections = np.sum(observed_infections)/list_of_meta_data[k].frac_estimate_of_total
      total_infections = np.sum(ground_truth_infections)

      t = np.arange(len(observed_infections))
      ground_truth_t = np.arange(len(ground_truth_infections))
      # previous day cumsums
      cumulative_infections_over_time = np.cumsum(np.concatenate(([0.], observed_infections)))[:-1]
      ground_truth_cumulative_infections_over_time = np.cumsum(np.concatenate(([0.], ground_truth_infections)))[:-1]
      # these are "non-predictive" cumsums.
      # cumulative_infections_over_time = np.cumsum(observed_infections)
      # ground_truth_cumulative_infections_over_time = np.cumsum(ground_truth_infections)
      dt = disease_trajectory(unique_id=unique_id, 
                              simulation_number=j, 
                              epidemic_number=k, 
                              num_new_infections_over_time=observed_infections, 
                              estimated_infections=estimated_infections,
                              ground_truth_infections_over_time=ground_truth_infections,
                              total_infections=total_infections, 
                              v = v[:, k], 
                              alpha = alpha, 
                              metadata=list_of_meta_data[k],
                              t=t,
                              ground_truth_t = ground_truth_t,
                              cumulative_infections_over_time=cumulative_infections_over_time,
                              ground_truth_cumulative_infections_over_time=ground_truth_cumulative_infections_over_time)
      list_of_disease_trajectory.append(dt)
      unique_id += 1
  
  return list_of_disease_trajectory

"""# Generate Betas

Three different ways of generating betas, depending on covariates
"""

def generate_betas_from_single_random_covariate(num_epidemics):
  """
  Betas depend on a single covariate that is randomly generated for each epidemic

  Args:
    num_epidemics: an int representing the number of epidemics to simulate
  Returns:
    beta: a np.array of shape (num_epidemics,) consisting of the growth rate for each epidemic
    v: a np.array of shape (1, num_epidemics) consisting of the randomly generated covariate for each epidemic
    alpha: a np.array of shape (num_covariates,) consisting of the weights for each covariate
  """
  v = np.random.uniform(0.0, 1.0, (1, num_epidemics))
  alpha = np.ones(1)
  beta = 0.4*np.exp(np.matmul(alpha, v))

  return beta, v, alpha

def generate_betas_effect_mod(num_epidemics):
  '''Generate vector of betas depending on 2 discrete effects.
  Args: 
    num_epidemics: number of betas generated
  Returns:
    betas: a np.array of shape (num_epidemics,) consisting of the growth rate for each epidemic
    v: a np.array of shape (2, num_epidemics) consisting of the randomly generated covariate for each epidemic
    alpha: an empty np.array, consisting of the weights for each covariate
    #TODO: alpha should probably be ~identitiy to match form below
  '''
  v = np.random.binomial(1, 0.5, size=(2, num_epidemics))
  hd = v[0, :]
  ws = v[1, :]
  beta = np.exp(np.log(1.5) + np.log(2.0) * (hd == 1) * (ws == 0))

  return beta, v, np.array([])

def generate_betas_many_cov2(num_epidemics, num_pred, num_not_pred):
  '''Generate vector of betas with a real valued vector of covariates.
  Args: 
    num_epidemics: number of betas generated.
    num_pred: number of covariates that affect beta
    num_no_pred: number of covariates that do not affect beta
  Returns:
    betas: a np.array of shape (num_epidemics,) consisting of the growth rate for each epidemic
    v: a np.array of shape (num_covariates, num_epidemics) consisting of the randomly generated covariate for each epidemic
    alpha: np.array of shape (num_covariate,s) consisting of the weights for each covariate
  '''
  #generate random covariates
  #sample from range -1, 1 uniformly
  v = np.random.uniform(low=-1.0, high=1.0, size=(num_pred + num_not_pred, num_epidemics))

  #construct weights for each covariate
  alpha_1 = np.ones(num_pred)
  alpha_0 = np.zeros(num_not_pred)
  alpha = np.concatenate((alpha_1, alpha_0), axis=0)

  #this has a different functional form than we've seen before
  beta = 1 + np.exp(np.matmul(alpha,v))

  return beta, v, alpha

