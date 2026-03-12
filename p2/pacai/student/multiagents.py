"""
Note:
The following functions were implemented by Ayush Bandopadhyay for P2.
Code was written by Ayush Bandopadhyay. An LLM was used to help understand bugs
and to recommend certain routes of solving the problems when I was stuck with lower win.
"""

import math
import typing

import pacai.agents.greedy
import pacai.agents.minimax
import pacai.core.action
import pacai.core.gamestate
import pacai.pacman.board

class ReflexAgent(pacai.agents.greedy.GreedyAgent):
    """
    A simple agent based on pacai.agents.greedy.GreedyAgent.

    You job is to make this agent better (it is pretty bad right now).
    You can change whatever you want about it,
    but it should still be a child of pacai.agents.greedy.GreedyAgent
    and be a "reflex" agent.
    This means that it shouldn't do any formal planning or searching,
    instead it should just look at the state of the game and try to make a good choice in the moment.
    You can make a great agent just by implementing a custom evaluate_state() method
    (and maybe add to the constructor if you want).
    """

    def __init__(self, **kwargs: typing.Any) -> None:
        super().__init__(**kwargs)

        # Put code here if you want.

    def evaluate_state(self,
            state: pacai.core.gamestate.GameState,
            action: pacai.core.action.Action | None = None,
            **kwargs: typing.Any) -> float:
        import pacai.pacman.gamestate as pgs
        pstate = typing.cast(pgs.GameState, state)

        pacman_pos = pstate.get_agent_position(pgs.PACMAN_AGENT_INDEX)

        # Dead = Loss
        if pacman_pos is None:
            return -math.inf

        score = float(pstate.score)

        # Where is food?
        food_positions = pstate.get_food()
        if food_positions:
            min_food_dist = min(
                abs(pacman_pos.row - fp.row) + abs(pacman_pos.col - fp.col)
                for fp in food_positions
            )
            score += 1.0 / (min_food_dist + 1)

        # Ghost check
        for ghost_index, ghost_pos in pstate.get_ghost_positions().items():
            dist = abs(pacman_pos.row - ghost_pos.row) + abs(pacman_pos.col - ghost_pos.col)

            if pstate.is_scared(ghost_index):
                score += 2.0 / (dist + 1)
            else:
                if dist <= 2:
                    score -= 500.0

        return score

class MyMinimaxLikeAgent(pacai.agents.minimax.MinimaxLikeAgent):
    """
    An agent that implements all the required methods for the minimax family of algorithms.
    Default implementations are supplied, so the agent should run right away,
    but it will not be very good.

    To implement minimax, minimax_step_max() and minimax_step_min() are required
    (you can ignore alpha and beta).

    To implement minimax with alpha-beta pruning,
    minimax_step_max() and minimax_step_min() with alpha and beta are required.

    To implement expectimax, minimax_step_max() and minimax_step_expected_min() are required.

    You are free to implement/override any methods you need to.
    """

    def __init__(self, **kwargs: typing.Any) -> None:
        super().__init__(**kwargs)

        # You can use the constructor if you need to.

    def minimax_step_max(self,
            state: pacai.core.gamestate.GameState,
            ply_count: int,
            legal_actions: list[pacai.core.action.Action],
            alpha: float,
            beta: float,
            ) -> tuple[list[pacai.core.action.Action], float]:
        best_score = -math.inf
        best_actions = []

        # check all actions possible
        for action in legal_actions:
            successor = state.generate_successor(action, self.rng)
            _, score = self.minimax_step(successor, ply_count, alpha, beta)

            # simple score comparison
            if score > best_score:
                best_score = score
                best_actions = [action]
            elif score == best_score:
                best_actions.append(action)

            # Alpha-beta
            if self.alphabeta_prune:
                if best_score > beta:
                    return best_actions, best_score
                alpha = max(alpha, best_score)

        return best_actions, best_score

    def minimax_step_min(self,
            state: pacai.core.gamestate.GameState,
            ply_count: int,
            legal_actions: list[pacai.core.action.Action],
            alpha: float,
            beta: float,
            ) -> tuple[list[pacai.core.action.Action], float]:
        best_score = math.inf
        best_actions = []

        # check all actions possible
        for action in legal_actions:
            successor = state.generate_successor(action, self.rng)
            _, score = self.minimax_step(successor, ply_count, alpha, beta)

            # simple score comparison
            if score < best_score:
                best_score = score
                best_actions = [action]
            elif score == best_score:
                best_actions.append(action)

            # alpha-beta
            if self.alphabeta_prune:
                if best_score < alpha:
                    return best_actions, best_score
                beta = min(beta, best_score)

        return best_actions, best_score

    def minimax_step_expected_min(self,
            state: pacai.core.gamestate.GameState,
            ply_count: int,
            legal_actions: list[pacai.core.action.Action],
            alpha: float,
            beta: float,
            ) -> float:
        total = 0.0

        for action in legal_actions:
            successor = state.generate_successor(action, self.rng)
            _, score = self.minimax_step(successor, ply_count, alpha, beta)
            total += score

        return total / len(legal_actions)

def better_state_eval(
        state: pacai.core.gamestate.GameState,
        agent: typing.Any | None = None,
        action: pacai.core.action.Action | None = None,
        **kwargs: typing.Any) -> float:
    """
    Better state evaluation for MyMinimaxLikeAgent.

    I used the following components to create my state evaluation function based off of recomendations from an LLM.
    Code was writted by me. Recommendations and concept solidified by the LLM.

    Components:
    - Base: current game score (preserves all point rewards already in the state)
    - Food proximity: reciprocal of distance to nearest food pellet (encourages eating)
    - Food count penalty: small penalty per remaining food item (encourages clearing board)
    - Ghost danger: large penalty when a non-scared ghost is within 2 tiles
    - Ghost opportunity: bonus for proximity to scared ghosts (encourages eating them)
    - Capsule proximity: small bonus for being near a capsule (encourages power-up use)

    Reasonings used to create the function:
    - Use reciprocals in order to normalize the values betwen 0 and 1.
    - Reward for being close to food.
    - Penalty for having too much food on the board.
    - Reward for being close to scared ghosts.
    - Penalty for being close to non-scared ghosts.
    - Reward for being close to a capsule.
    """

    import pacai.pacman.gamestate as pgs
    pstate = typing.cast(pgs.GameState, state)

    pacman_pos = pstate.get_agent_position(pgs.PACMAN_AGENT_INDEX)

    # Pac-Man is off the board = Loss
    if pacman_pos is None:
        return -math.inf

    # No food left = Win
    food_positions = pstate.get_food()
    if not food_positions:
        return math.inf

    score = float(pstate.score)

    # Where is food?
    min_food_dist = min(
        abs(pacman_pos.row - fp.row) + abs(pacman_pos.col - fp.col)
        for fp in food_positions
    )
    score += 10.0 / (min_food_dist + 1)

    # Fewer food items = better
    score -= 4.0 * len(food_positions)

    # Ghost check
    for ghost_index, ghost_pos in pstate.get_ghost_positions().items():
        dist = abs(pacman_pos.row - ghost_pos.row) + abs(pacman_pos.col - ghost_pos.col)

        if pstate.is_scared(ghost_index):
            score += 200.0 / (dist + 1)
        else:
            if dist <= 1:
                score -= 1000.0
            elif dist <= 2:
                score -= 200.0

    # Where is the capsule?
    capsule_positions = pstate.board.get_marker_positions(pacai.pacman.board.MARKER_CAPSULE)
    if capsule_positions:
        min_cap_dist = min(
            abs(pacman_pos.row - cp.row) + abs(pacman_pos.col - cp.col)
            for cp in capsule_positions
        )
        score += 5.0 / (min_cap_dist + 1)

    return score