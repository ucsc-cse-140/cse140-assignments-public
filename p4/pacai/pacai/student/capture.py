import typing

import pacai.agents.greedy
import pacai.capture.gamestate
import pacai.core.action
import pacai.core.agent
import pacai.core.agentinfo
import pacai.core.board
import pacai.core.features
import pacai.core.gamestate
import pacai.pacman.board
import pacai.search.distance

GHOST_DANGER_DISTANCE: float = 2.0


def create_team() -> list[pacai.core.agentinfo.AgentInfo]:
    """
    Get the agent information that will be used to create a capture team.
    """

    return [
        pacai.core.agentinfo.AgentInfo(name=f"{__name__}.OffensiveAgent"),
        pacai.core.agentinfo.AgentInfo(name=f"{__name__}.DefensiveAgent"),
    ]


def _get_team_modifier(agent_index: int) -> int:
    return ((agent_index % 2) * 2) - 1


def _get_border_positions(
        board: pacai.core.board.Board,
        team_modifier: int) -> list[pacai.core.board.Position]:
    """Non-wall positions on the home side near the team boundary."""

    mid_col = board.width // 2
    if team_modifier == -1:
        cols = [mid_col - 1, mid_col - 2]
    else:
        cols = [mid_col, mid_col + 1]

    positions: list[pacai.core.board.Position] = []
    for col in cols:
        if col < 0 or col >= board.width:
            continue
        for row in range(board.height):
            pos = pacai.core.board.Position(row, col)
            if not board.is_wall(pos):
                positions.append(pos)
    return positions


def _get_dead_ends(board: pacai.core.board.Board) -> set[pacai.core.board.Position]:
    """Positions with at most one non-wall neighbor (traps)."""

    dead_ends: set[pacai.core.board.Position] = set()
    for row in range(board.height):
        for col in range(board.width):
            pos = pacai.core.board.Position(row, col)
            if board.is_wall(pos):
                continue
            if len(board.get_neighbors(pos)) <= 1:
                dead_ends.add(pos)
    return dead_ends


def _min_distance(
        precomputer: pacai.search.distance.DistancePreComputer,
        origin: pacai.core.board.Position,
        targets: typing.Iterable[pacai.core.board.Position]) -> float | None:
    """Minimum maze distance from origin to any target, or None if all unreachable."""

    best: float | None = None
    for target in targets:
        dist = precomputer.get_distance(origin, target)
        if dist is not None and (best is None or dist < best):
            best = dist
    return best


# ---------------------------------------------------------------------------
# Offensive feature extractor  ("Fast Break")
# ---------------------------------------------------------------------------

def _extract_offensive_features(
        state: pacai.core.gamestate.GameState,
        action: pacai.core.action.Action,
        agent: pacai.core.agent.Agent | None = None,
        **kwargs: typing.Any) -> pacai.core.features.FeatureDict:
    off = typing.cast(OffensiveAgent, agent)
    st = typing.cast(pacai.capture.gamestate.GameState, state)
    features: pacai.core.features.FeatureDict = pacai.core.features.FeatureDict()

    pos = st.get_agent_position(off.agent_index)
    if pos is None:
        features['death_penalty'] = 1.0
        return features

    features['score'] = st.get_normalized_score(off.agent_index)
    features['stopped'] = int(action == pacai.core.action.STOP)

    past = st.get_agent_actions(off.agent_index)
    if len(past) > 1:
        features['reverse'] = int(action == st.get_reverse_action(past[-2]))

    # Food seeking
    food = st.get_food(agent_index=off.agent_index)
    if len(food) > 0:
        fd = _min_distance(off._distances, pos, food)
        if fd is not None:
            features['distance_to_food'] = fd
    else:
        features['distance_to_food'] = 0.0

    # Ghost avoidance -- only relevant when we are a Pac-Man on the enemy side.
    if st.is_pacman(agent_index=off.agent_index):
        dangerous: dict[int, pacai.core.board.Position] = {}
        for oi, op in st.get_nonscared_opponent_positions(agent_index=off.agent_index).items():
            if st.is_ghost(agent_index=oi):
                dangerous[oi] = op

        gd: float | None = None
        if len(dangerous) > 0:
            gd = _min_distance(off._distances, pos, dangerous.values())

        if gd is not None and gd <= GHOST_DANGER_DISTANCE:
            proximity = GHOST_DANGER_DISTANCE - gd
            features['ghost_proximity'] = proximity
            features['ghost_proximity_sq'] = proximity ** 2

            if pos in off._dead_ends:
                features['dead_end_threat'] = 1.0

            # Capsule strategy -- head for a capsule when under threat.
            capsules = st.board.get_marker_positions(pacai.pacman.board.MARKER_CAPSULE)
            tm = _get_team_modifier(off.agent_index)
            mid = st.board.width / 2.0
            enemy_caps = ([c for c in capsules if c.col >= mid]
                          if tm == -1
                          else [c for c in capsules if c.col < mid])
            if len(enemy_caps) > 0:
                cd = _min_distance(off._distances, pos, enemy_caps)
                if cd is not None:
                    features['capsule_distance'] = cd

            # Retreat toward home border when threatened.
            if len(off._border_positions) > 0:
                hd = _min_distance(off._distances, pos, off._border_positions)
                if hd is not None:
                    urgency = (GHOST_DANGER_DISTANCE - gd) / GHOST_DANGER_DISTANCE
                    features['retreat_distance'] = hd * (1.0 + urgency)

    # Hunt scared ghosts (safe to approach from anywhere).
    scared = st.get_scared_opponent_positions(agent_index=off.agent_index)
    if len(scared) > 0:
        sd = _min_distance(off._distances, pos, scared.values())
        if sd is not None:
            features['scared_ghost_distance'] = sd

    return features


# ---------------------------------------------------------------------------
# Defensive feature extractor  ("Zone Defense")
# ---------------------------------------------------------------------------

def _extract_defensive_features(
        state: pacai.core.gamestate.GameState,
        action: pacai.core.action.Action,
        agent: pacai.core.agent.Agent | None = None,
        **kwargs: typing.Any) -> pacai.core.features.FeatureDict:
    dfa = typing.cast(DefensiveAgent, agent)
    st = typing.cast(pacai.capture.gamestate.GameState, state)
    features: pacai.core.features.FeatureDict = pacai.core.features.FeatureDict()

    pos = st.get_agent_position(dfa.agent_index)
    if pos is None:
        features['death_penalty'] = 1.0
        return features

    features['on_home_side'] = int(st.is_ghost(agent_index=dfa.agent_index))
    features['stopped'] = int(action == pacai.core.action.STOP)

    past = st.get_agent_actions(dfa.agent_index)
    if len(past) > 1:
        features['reverse'] = int(action == st.get_reverse_action(past[-2]))

    invaders = st.get_invader_positions(agent_index=dfa.agent_index)
    features['num_invaders'] = len(invaders)
    scared = st.is_scared(agent_index=dfa.agent_index)

    if len(invaders) > 0:
        inv_d = _min_distance(dfa._distances, pos, invaders.values())
        if inv_d is not None:
            if scared:
                features['scared_flee_distance'] = inv_d
            else:
                features['invader_distance'] = inv_d
    elif len(dfa._patrol_positions) > 0:
        pd = _min_distance(dfa._distances, pos, dfa._patrol_positions)
        if pd is not None:
            features['patrol_distance'] = pd

    return features


# ---------------------------------------------------------------------------
# Agent classes
# ---------------------------------------------------------------------------

class OffensiveAgent(pacai.agents.greedy.GreedyFeatureAgent):
    """
    Basketball-inspired 'Fast Break' offensive agent.

    Rushes food aggressively when defenders are far away (fast break),
    plays methodically when threatened (half-court offense),
    retreats under pressure, and hunts scared ghosts.
    """

    def __init__(self, **kwargs: typing.Any) -> None:
        kwargs['feature_extractor_func'] = _extract_offensive_features
        super().__init__(**kwargs)

        self._distances: pacai.search.distance.DistancePreComputer = (
            pacai.search.distance.DistancePreComputer()
        )
        self._border_positions: list[pacai.core.board.Position] = []
        self._dead_ends: set[pacai.core.board.Position] = set()

        self.weights['score'] = 200.0
        self.weights['distance_to_food'] = -5.0
        self.weights['ghost_proximity'] = -8.0
        self.weights['ghost_proximity_sq'] = -4.0
        self.weights['dead_end_threat'] = -100.0
        self.weights['capsule_distance'] = -1.0
        self.weights['retreat_distance'] = -0.5
        self.weights['scared_ghost_distance'] = -4.0
        self.weights['stopped'] = -100.0
        self.weights['reverse'] = -2.0
        self.weights['death_penalty'] = -500.0

    def game_start(self, initial_state: pacai.core.gamestate.GameState) -> None:
        self._distances.compute(initial_state.board)
        tm = _get_team_modifier(self.agent_index)
        self._border_positions = _get_border_positions(initial_state.board, tm)
        self._dead_ends = _get_dead_ends(initial_state.board)


class DefensiveAgent(pacai.agents.greedy.GreedyFeatureAgent):
    """
    Basketball / Football-inspired 'Zone Defense' agent.

    Patrols the border zone near the densest food cluster when clear,
    switches to man-to-man chase when invaders appear,
    and runs a prevent-defense evasion when scared.
    """

    def __init__(self, **kwargs: typing.Any) -> None:
        kwargs['feature_extractor_func'] = _extract_defensive_features
        super().__init__(**kwargs)

        self._distances: pacai.search.distance.DistancePreComputer = (
            pacai.search.distance.DistancePreComputer()
        )
        self._patrol_positions: list[pacai.core.board.Position] = []

        self.weights['on_home_side'] = 200.0
        self.weights['num_invaders'] = -1000.0
        self.weights['invader_distance'] = -20.0
        self.weights['scared_flee_distance'] = 15.0
        self.weights['patrol_distance'] = -5.0
        self.weights['stopped'] = -100.0
        self.weights['reverse'] = -2.0
        self.weights['death_penalty'] = -500.0

    def game_start(self, initial_state: pacai.core.gamestate.GameState) -> None:
        self._distances.compute(initial_state.board)
        tm = _get_team_modifier(self.agent_index)
        border = _get_border_positions(initial_state.board, tm)

        cap_state = typing.cast(pacai.capture.gamestate.GameState, initial_state)
        our_food = cap_state.get_food(team_modifier=-tm)

        if len(our_food) > 0 and len(border) > 0:
            avg_row = sum(p.row for p in our_food) / len(our_food)
            avg_col = sum(p.col for p in our_food) / len(our_food)
            self._patrol_positions = sorted(
                border,
                key=lambda p: abs(p.row - avg_row) + abs(p.col - avg_col)
            )[:3]
        else:
            self._patrol_positions = border[:3] if border else []
