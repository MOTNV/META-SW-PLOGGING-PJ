import numpy as np
import random
import torch
import torch.nn as nn
import torch.optim as optim

# 환경 설정
GRID_SIZE = 4
ACTIONS = ['up', 'down', 'left', 'right']
ACTION_IDX = {a: i for i, a in enumerate(ACTIONS)}
GOAL_STATE = (3, 3)

EPISODES = 800
GAMMA = 0.9
LAMBDA = 0.95  # GAE λ
BATCH_SIZE = 64  # PPO batch 크기
EPOCHS = 4  # PPO Epoch

ALPHA = 0.001  # Actor learning rate
BETA = 0.003   # Critic learning rate
CLIP = 0.2

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# 환경 함수
def get_next_state(state, action):
    i, j = state

    if action == 'up' and i > 0:
        i -= 1
    elif action == 'down' and i < GRID_SIZE - 1:
        i += 1
    elif action == 'left' and j > 0:
        j -= 1
    elif action == 'right' and j < GRID_SIZE - 1:
        j += 1

    return (i, j)

def get_reward(state):
    return 1 if state == GOAL_STATE else 0

def is_terminal(state):
    return state == GOAL_STATE

def state_to_tensor(state):
    return torch.FloatTensor([
        state[0] / (GRID_SIZE - 1),
        state[1] / (GRID_SIZE - 1)
    ]).to(device)

# Actor
class Actor(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(2, 32),
            nn.ReLU(),
            nn.Linear(32, 4),
            nn.Softmax(dim=-1)
        )

    def forward(self, x):
        return self.model(x)

# Critic
class Critic(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = nn.Sequential(
            nn.Linear(2, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        return self.model(x)

# 행동 선택
def choose_action(actor, state):
    s = state_to_tensor(state).unsqueeze(0)
    probs = actor(s)
    action_idx = torch.multinomial(probs, 1).item()
    return action_idx, probs[0, action_idx].item()

# GAE Advantage 계산
def compute_gae(rewards, values, next_values, dones):
    advantages = []
    gae = 0
    for t in reversed(range(len(rewards))):
        delta = rewards[t] + GAMMA * next_values[t] * (1 - dones[t]) - values[t]
        gae = delta + GAMMA * LAMBDA * (1 - dones[t]) * gae
        advantages.insert(0, gae)
    return advantages

# PPO 학습
def train_PPO():
    actor = Actor().to(device)
    critic = Critic().to(device)

    optimizerA = optim.Adam(actor.parameters(), lr=ALPHA)
    optimizerC = optim.Adam(critic.parameters(), lr=BETA)

    for episode in range(EPISODES):

        # ---- [Step 1] Trajectory Batch 수집 ----
        batch_states = []
        batch_actions = []
        batch_old_probs = []
        batch_rewards = []
        batch_dones = []
        batch_values = []

        state = (0, 0)

        while not is_terminal(state):
            action_idx, prob = choose_action(actor, state)
            next_state = get_next_state(state, ACTIONS[action_idx])
            reward = get_reward(next_state)

            # 저장
            batch_states.append(state_to_tensor(state))
            batch_actions.append(action_idx)
            batch_old_probs.append(prob)
            batch_rewards.append(reward)
            batch_dones.append(is_terminal(next_state))
            batch_values.append(critic(state_to_tensor(state).unsqueeze(0)).item())

            state = next_state
            if len(batch_states) >= BATCH_SIZE:
                break

        next_values = [critic(s.unsqueeze(0)).item() for s in batch_states[1:]]
        next_values.append(0)  # last is terminal

        # ---- GAE Advantage ----
        advantages = compute_gae(batch_rewards, batch_values, next_values, batch_dones)
        advantages = torch.FloatTensor(advantages).to(device)

        returns = advantages + torch.FloatTensor(batch_values).to(device)

        # ---- [Step 2-3] PPO Epoch 반복 ----
        for _ in range(EPOCHS):
            for i in range(len(batch_states)):
                s = batch_states[i].unsqueeze(0)
                a = torch.LongTensor([batch_actions[i]]).to(device)
                old_prob = torch.FloatTensor([batch_old_probs[i]]).to(device)

                probs = actor(s)
                new_prob = probs[0, a]

                ratio = new_prob / old_prob

                # Clipped surrogate loss
                surr1 = ratio * advantages[i]
                surr2 = torch.clamp(ratio, 1 - CLIP, 1 + CLIP) * advantages[i]
                actor_loss = -torch.min(surr1, surr2)

                # Critic MSE loss
                value = critic(s)
                critic_loss = (value - returns[i]).pow(2)

                # 업데이트
                optimizerA.zero_grad()
                actor_loss.backward()
                optimizerA.step()

                optimizerC.zero_grad()
                critic_loss.backward()
                optimizerC.step()

        # ---- [Step 4] batch 삭제 ----
        del batch_states, batch_actions, batch_old_probs
        del batch_rewards, batch_dones, batch_values

    return actor, critic
# 최적 경로 찾기
def get_optimal_path(actor, start=(0, 0)):
    path = [start]
    state = start
    while not is_terminal(state):
        state_tensor = state_to_tensor(state).unsqueeze(0)
        probs = actor(state_tensor)
        action_idx = torch.argmax(probs).item()
        next_state = get_next_state(state, ACTIONS[action_idx])
        if next_state == state:
            break
        path.append(next_state)
        state = next_state
    return path

# 실행
if __name__ == "__main__":
    actor, critic = train_PPO()
    path = get_optimal_path(actor)
    print("\n[PPO 기반 최적 경로]")
    for s in path:
        print(s, end=" -> ")
    print("Goal")
