# Copyright 2021 The Brax Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Brax Gym wrapper for single and batched environments."""

import gym
from gym import spaces
from gym.vector import utils
import jax
import numpy as np
from brax.envs import env


class GymWrapper(gym.Env):
  """A wrapper that converts Brax Env to one that follows Gym API."""

  def __init__(self, environment: env.Env, seed: int = 0):
    self._environment = environment
    self.seed(seed)

    # action_space = None
    obs_high = np.inf * np.ones(self._environment.observation_size)
    self.observation_space = spaces.Box(-obs_high, obs_high, dtype=np.float32)

    action_high = np.ones(self._environment.action_size)
    self.action_space = spaces.Box(-action_high, action_high, dtype=np.float32)

    self._state = None

    def reset(key):
      key1, key2 = jax.random.split(key)
      state = self._environment.reset(key2)
      return state, state.obs, key1
    self._reset = jax.jit(reset)

    def step(state, action):
      state = self._environment.step(state, action)
      return state, state.obs, state.reward, state.done
    self._step = jax.jit(step, backend='cpu')

  def reset(self):
    self._state, obs, self._key = self._reset(self._key)
    return obs

  def step(self, action):
    self._state, obs, reward, done = self._step(self._state, action)
    return obs, reward, done, {}

  def seed(self, seed: int = 0):
    self._key = jax.random.PRNGKey(seed)


class VectorGymWrapper(gym.vector.VectorEnv):
  """A wrapper that converts batched Brax Env to one that follows Gym VectorEnv API."""

  def __init__(self, environment: env.Env, seed: int = 0):
    self._environment = environment
    if not self._environment.batch_size:
      raise ValueError('underlying environment must be batched')

    self.num_envs = self._environment.batch_size
    self._key_size = self.num_envs + 1
    self.seed(seed)

    obs_high = np.inf * np.ones(self._environment.observation_size)
    self.single_observation_space = spaces.Box(
        -obs_high, obs_high, dtype=np.float32)
    self.observation_space = utils.batch_space(self.single_observation_space,
                                               self.num_envs)

    action_high = np.ones(self._environment.action_size)
    self.single_action_space = spaces.Box(
        -action_high, action_high, dtype=np.float32)
    self.action_space = utils.batch_space(self.single_action_space,
                                          self.num_envs)
    self._state = None

    def reset(key):
      keys = jax.random.split(key, self._key_size)
      state = self._environment.reset(keys[1:])
      return state, state.obs, keys[0]
    self._reset = jax.jit(reset)

    def step(state, action):
      state = self._environment.step(state, action)
      return state, state.obs, state.reward, state.done
    self._step = jax.jit(step, backend='cpu')

  def reset(self):
    self._state, obs, self._key = self._reset(self._key)
    return obs

  def step(self, action):
    self._state, obs, reward, done = self._step(self._state, action)
    return obs, reward, done, {}

  def seed(self, seed: int = 0):
    self._key = jax.random.PRNGKey(seed)
