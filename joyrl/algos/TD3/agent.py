#!/usr/bin/env python
# coding=utf-8
'''
Author: JiangJi
Email: johnjim0816@gmail.com
Date: 2021-12-22 10:40:05
LastEditor: JiangJi
LastEditTime: 2022-12-06 23:25:31
Discription: 
'''
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from common.memories import ReplayBufferQue
class Actor(nn.Module):
	
	def __init__(self, n_states, n_actions, hidden_dim = 256):	
		super(Actor, self).__init__()

		self.l1 = nn.Linear(n_states, hidden_dim)
		self.l2 = nn.Linear(hidden_dim, hidden_dim)
		self.l3 = nn.Linear(hidden_dim, n_actions)
	
	def forward(self, state):
		
		x = F.relu(self.l1(state))
		x = F.relu(self.l2(x))
		x = torch.tanh(self.l3(x))
		return x

class Critic(nn.Module):
	def __init__(self, n_states, n_actions, hidden_dim = 256):
		super(Critic, self).__init__()

		self.l1 = nn.Linear(n_states + n_actions, 256)
		self.l2 = nn.Linear(hidden_dim, hidden_dim)
		self.l3 = nn.Linear(hidden_dim, 1)

	def forward(self, state, action):
		sa = torch.cat([state, action], 1)
		q = F.relu(self.l1(sa))
		q = F.relu(self.l2(q))
		q = self.l3(q)
		return q


class Agent(object):
	def __init__(self,cfg):
		self.gamma = cfg.gamma
		self.actor_lr = cfg.actor_lr
		self.critic_lr = cfg.critic_lr
		self.policy_noise = cfg.policy_noise
		self.noise_clip = cfg.noise_clip
		self.expl_noise = cfg.expl_noise
		self.policy_freq = cfg.policy_freq
		self.batch_size =  cfg.batch_size 
		self.tau = cfg.tau
		self.sample_count = 0
		self.policy_freq = cfg.policy_freq
		self.explore_steps = cfg.explore_steps
		self.device = torch.device(cfg.device)
		self.n_actions = cfg.n_actions
		self.action_space = cfg.action_space
		self.action_scale = torch.tensor((self.action_space.high - self.action_space.low)/2, device=self.device, dtype=torch.float32).unsqueeze(dim=0)
		self.action_bias = torch.tensor((self.action_space.high + self.action_space.low)/2, device=self.device, dtype=torch.float32).unsqueeze(dim=0)
		self.actor = Actor(cfg.n_states, cfg.n_actions, hidden_dim = cfg.actor_hidden_dim).to(self.device)
		self.actor_target = Actor(cfg.n_states, cfg.n_actions, hidden_dim = cfg.actor_hidden_dim).to(self.device)
		self.actor_target.load_state_dict(self.actor.state_dict())

		self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr = self.actor_lr)

		self.critic_1 = Critic(cfg.n_states, cfg.n_actions, hidden_dim = cfg.critic_hidden_dim).to(self.device)
		self.critic_2 = Critic(cfg.n_states, cfg.n_actions, hidden_dim = cfg.critic_hidden_dim).to(self.device)
		self.critic_1_target = Critic(cfg.n_states, cfg.n_actions, hidden_dim = cfg.critic_hidden_dim).to(self.device)
		self.critic_2_target = Critic(cfg.n_states, cfg.n_actions, hidden_dim = cfg.critic_hidden_dim).to(self.device)
		self.critic_1_target.load_state_dict(self.critic_1.state_dict())
		self.critic_2_target.load_state_dict(self.critic_2.state_dict())
		
		self.critic_1_optimizer = torch.optim.Adam(self.critic_1.parameters(), lr = self.critic_lr)
		self.critic_2_optimizer = torch.optim.Adam(self.critic_2.parameters(), lr = self.critic_lr)
		self.memory = ReplayBufferQue(cfg.buffer_size)
		# self.memory = ReplayBuffer(n_states, n_actions)

	def sample_action(self, state):
		self.sample_count += 1
		if self.sample_count < self.explore_steps:
			return self.action_space.sample()
		else:
			state = torch.tensor(state, device=self.device, dtype=torch.float32).unsqueeze(dim=0)
			action = self.actor(state)
			action = self.action_scale * action + self.action_bias
			action = action.detach().cpu().numpy()[0]
			action_noise = np.random.normal(0, self.action_scale.cpu().numpy()[0] * self.expl_noise, size=self.n_actions)
			action = (action + action_noise).clip(self.action_space.low, self.action_space.high)
			return action

	@torch.no_grad()
	def predict_action(self, state):
		state = torch.tensor(state, device=self.device, dtype=torch.float32).unsqueeze(dim=0)
		action = self.actor(state)
		action = self.action_scale * action + self.action_bias
		return action.detach().cpu().numpy()[0]

	def update(self):
		# if len(self.memory) < self.batch_size:
		# 	return
		if len(self.memory) < self.explore_steps:
			return
		state, action, reward, next_state, done = self.memory.sample(self.batch_size)
		state = torch.tensor(np.array(state), device=self.device, dtype=torch.float32)
		action = torch.tensor(np.array(action), device=self.device, dtype=torch.float32)
		next_state = torch.tensor(np.array(next_state), device=self.device, dtype=torch.float32)
		reward = torch.tensor(reward, device=self.device, dtype=torch.float32).unsqueeze(1)
		done = torch.tensor(done, device=self.device, dtype=torch.float32).unsqueeze(1)
		# update critic
		noise = (torch.randn_like(action) * self.policy_noise).clamp(-self.noise_clip, self.noise_clip)
		next_action = (self.actor_target(next_state) + noise).clamp(-self.action_scale+self.action_bias, self.action_scale+self.action_bias)
		target_q1, target_q2 = self.critic_1_target(next_state, next_action).detach(), self.critic_2_target(next_state, next_action).detach()
		target_q = torch.min(target_q1, target_q2)
		target_q = reward + self.gamma * target_q * (1 - done)
		current_q1, current_q2 = self.critic_1(state, action), self.critic_2(state, action)
		critic_1_loss = F.mse_loss(current_q1, target_q)
		critic_2_loss = F.mse_loss(current_q2, target_q)
		self.critic_1_optimizer.zero_grad()
		critic_1_loss.backward()
		self.critic_1_optimizer.step()
		self.critic_2_optimizer.zero_grad()
		critic_2_loss.backward()
		self.critic_2_optimizer.step()
		# Delayed policy updates
		if self.sample_count % self.policy_freq == 0:
			actor_loss = -self.critic_1(state, self.actor(state)).mean()
			self.actor_optimizer.zero_grad()
			actor_loss.backward()
			self.actor_optimizer.step()
			for param, target_param in zip(self.actor.parameters(), self.actor_target.parameters()):
				target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)
			for param, target_param in zip(self.critic_1.parameters(), self.critic_1_target.parameters()):
				target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)
			for param, target_param in zip(self.critic_2.parameters(), self.critic_2_target.parameters()):
				target_param.data.copy_(self.tau * param.data + (1 - self.tau) * target_param.data)

	def save_model(self, fpath):
		from pathlib import Path
        # create path
		Path(fpath).mkdir(parents=True, exist_ok=True)
		torch.save(self.critic_1.state_dict(), f"{fpath}/critic_1.pth")
		torch.save(self.critic_2.state_dict(), f"{fpath}/critic_2.pth")
		torch.save(self.actor.state_dict(), f"{fpath}/actor.pth")


	def load_model(self, fpath):
		critic_1_ckpt = torch.load(f"{fpath}/critic_1.pth", map_location=self.device)
		critic_2_ckpt = torch.load(f"{fpath}/critic_2.pth", map_location=self.device)
		actor_ckpt = torch.load(f"{fpath}/actor.pth", map_location=self.device)
		self.critic_1.load_state_dict(critic_1_ckpt)
		self.critic_2.load_state_dict(critic_2_ckpt)
		self.actor.load_state_dict(actor_ckpt)
		
