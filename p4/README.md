# Project 4: Pac-Man Capture the Flag

<p align="center">
    <img alt="Pac-Man with Ghosts" src="images/capture-default.webp" width="800px">
    </br>
    Enough of defense,</br>
    Onto enemy terrain.</br>
    Capture all their food!
</p>

## Introduction

The final project involves a multi-player capture-the-flag variant of Pac-Man,
where agents control both Pac-Man and ghosts in coordinated team-based strategies.
Your team will try to eat the food on the far side of the map, while defending the food on your home side.

The project will consist of three phases:

1. The first phase will consist of forming a team (3 people) and an initial test of the tournament.
   Students must submit a functioning team of agents.
   For this phase we only evaluate that your team runs and do not care about how well it performs.
   (So for this phase, you can just submit a team full of
   [DummyAgents](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/agents/dummy.html#DummyAgent) that just sits there.)
   When you submit your team to the autograder, it will run basic checks on your team.
   Full points from the autograder means that your team passes all the basic checks.
   For this phase, your agent needs to run, but does not need to get full points from the autograder.
2. The second phase will consist of daily round-robin style tournaments.
   During this phase students should improve their agents, while looking for weaknesses in their opponents' submissions.
   Only teams with agents that are getting full points from the autograder will participate in the tournament.
3. The final phase will be a round-robin style tournament, in which students show their best.
   Your agent's performance in this last tournament will affect your grade.
   This is students' final chance to shine, winner takes all!

All of the deadlines for these events will exist on **Canvas**.
Make sure you check early, **do not** miss a deadline!

We will evaluate your submissions based on a short written report (2-3 pages) that should detail your modeling of the problem and agent design,
as well as your performance against the baseline agent, the staff agents, and your classmates in tournament play.

### Submission

To enter into the nightly tournaments, your team's agents and all relevant functions must be defined in
[pacai.student.capture.py](https://github.com/edulinq/pacai/blob/v2.0.1/pacai/student/capture.py).

Every team must have a unique name,
consisting only of [alphanumeric](https://en.wikipedia.org/wiki/Alphanumericals) characters (any other characters, including whitespace, will be not allowed).

Instructions for forming groups (using Google Forms) will be posted on Canvas in the lead-up to the assignment.
You must submit your team info (team name, motto and list of members).

In every submission to the autograder (linked below),
you must include a file [capture-team.txt](https://github.com/edulinq/pacai/blob/v2.0.1/pacai/student/capture-team.txt) in which you will write only your unique team name.
**Do not** include other extraneous text in this file.
Only your team name will be displayed to the rest of the class.
You will fill in portions of `pacai/student/capture.py` during this assignment.
You should **only** submit these two files.

For instructions on submission,
refer back to the [P0 README](../p0/README.md).
for example, you may submit with the command:
```sh
python3 -m autograder.run.submit pacai/student/capture.py pacai/student/capture-team.txt
```

The most recent submission of any team member before the tournament begins will become the whole team's agent and will represent your team in the tournament.

For your **report submission**, upload a file named `[your team name].pdf` that contains your write-up to Canvas.
Please make sure that this document contains the names of all members of your team clearly stated at the top.

### Evaluation

The contest will count as your final project, worth 40 points.
20 of these points will be the result of a written report you submit with your agent describing your approach.
The remaining 20 points will be awarded based on your agent's performance in the final tournament.

The written report should be 2-3 pages **(no more)**.
Through this report we expect you to demonstrate your ability to constructively solve AI problems by identifying:
 - The fundamental problems you are trying to solve.
 - How you modeled these problems.
 - The computational strategy used to solve each problem.
 - Algorithmic choices you made in your implementation.
 - Any obstacles you encountered while solving the problem.
 - Evaluation of your agent.
 - Lessons learned during the project.

<!-- TODO(Batu, Niloofar): Review the grading scheme. -->
## Points & Teams
A portion of your grade will be based on performance against the following staff agents:
 - `staff_baseline`
 - `staff_SlugRush`
 - `staff_PhantomSlug`

Points are also awarded as follows:
 - If you lose to the dummy agent, zero points will be awarded for this section.
 - +5 points for beating the `staff_baseline` agent as red.
 - +5 points for beating the `staff_baseline` agent as blue.
 - +2.5 points for beating one additional staff agent as red.
 - +2.5 points for beating one additional staff agent as blue.
 - +2.5 points for beating a second additional staff agent as red.
 - +2.5 points for beating a second additional staff agent as blue.
 - +1 Extra Credit point for being the number one team.

For the purposes of the points system, we define "beating" an agent as winning against that agent both when playing as red and as blue.
<!-- How we compute the percentiles based on the ranking of the teams is described below in [Contest Details](#contest-details). -->

### Academic Dishonesty

We will be checking your code against other submissions in the class for logical redundancy.
If you copy someone else's code and submit it with minor changes, we will know.
These cheat detectors are quite hard to fool, so please don't try.
We trust you all to submit your own work only; _please_ don't let us down.
If you do, we will pursue the strongest consequences available to us.

In the case of malicious submissions we will pursue the strongest consequences available to us.

### Getting Help

You are not alone!
If you find yourself stuck on something, contact the course staff for help.
Office hours, section, and discussion boards are there for your support; please use them.
If you can't make our office hours, let us know and we will schedule more.
We want these projects to be rewarding and instructional, not frustrating and demoralizing.
One more piece of advice: if you don't know what a variable does or what kind of values it takes, print it out.

## Pac-Man Capture the Flag

Your peaceful (and sometimes spooky) Pac-Man board is now a battlefield:
red vs blue!
In capture, there are two teams of agents: red (on the left) and blue (on the right).
The goal is to eat all the food on your opponent's side of the map.
When an agent is on their own side of the map, they will be a ghost with the ability to eat invaders.
When an agent in on their opponent's side of the map, they will be a Pac-Man that can eat their opponent's food.

You can try out a game of capture with dummy agents using:
```sh
python3 -m pacai.capture --agent-arg 0::name=agent-user-input
```

Just like in Pac-Man, a wealth of options are available to you:
```sh
python3 -m pacai.capture --help
```

### Board

As with Pac-Man, there are several capture boards to choose from:
 - `capture-alley`
 - `capture-blox`
 - `capture-crowded`
 - `capture-default`
 - `capture-distant`
 - `capture-fast`
 - `capture-jumbo`
 - `capture-medium` (default)
 - `capture-office`
 - `capture-strategic`
 - `capture-test`
 - `capture-tiny`

In addition, you can also use `random` to construct a random capture board:
```sh
python3 -m pacai.capture --agent-arg 0::name=agent-user-input --board random
```

If you do this a few times, you will likely see a wide variety in the types of boards that can be generated.
You can choose a specific random seed (and therefore board) by appending a dash and int to `random`.
For example:
```sh
python3 -m pacai.capture --agent-arg 0::name=agent-user-input --board random-6
```

Tournament games will be played on the following boards:

| Board             | Number of Games |
|-------------------|-----------------|
| `capture-default` | 5               |
| `random`          | 6               |

### Scoring

When a Pac-Man eats a food dot, the food is permanently removed and one point is scored for that Pac-Man's team.
Red team scores are negative, while Blue team scores are positive.
Here are the point values associated with different actions.

| Action                 | Points | Notes |
|------------------------|--------|-------|
| Nothing                | 0      | Unlike classic Pac-Man, there is no continual point loss. |
| Eating a Food Pellet   | 10     | The game ends when all of a team's food is eaten. |
| Eating a Power Capsule | 0      | Opponents will now be scared for a set duration (but only when ghosts). |
| Eating a Pac-Man       | 0      | The invader will respawn back at their starting location on their next turn. |
| Eating a Ghost         | 0      | The defender will respawn back at their starting location on their next turn and is no longer scared. |
| Game End               | 0      | No additional points are given for winning/losing (ending the game). |

### Limitations

There are several limitations imposed on capture games.
Encountering any of these actions will cause a game to stop,
and may result in a team forfeiting the game.
The actions and their outcomes are listed below.

| Action | Count | Outcome |
|----------------------------------------|------------|---------|
| Combined Agent Actions                 | 1200 Moves | The game ends and is scored normally. |
| Single Agent Starting Computation Time | 15 Seconds | The team with the offending agent loses. |
| Single Agent Action Computation Time   | 3 Seconds  | The team with the offending agent loses. |
| Total Game Time                        | 60 Seconds | The game ends in a tie. |

## Getting Started

You can set specific Capture teams for red/blue with the respective `--red` and `--blue` flags.
For example, you can make red use the provided random team with:
```sh
python3 -m pacai.capture --red capture-team-random
```

A [simple, baseline team](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/team.html#create_team_baseline) has been provided for you.
This team represents the minimum bar that your team should eventually end up beating 99% of the time.
Watch this team crush the random team:
```sh
python3 -m pacai.capture --red capture-team-random --blue capture-team-baseline --fps 30
```

Note how the [baseline team](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/team.html#create_team_baseline) splits its agents into defensive and offensive agents.
You are not obligated to make your own agent anything similar to the baseline agent,
but you will probably see that thinking about both offense and defense will generally serve you well.

Your student team (created by [pacai.student.capture.create_team()](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/student/capture.html#create_team)) has the alias `capture-team-student`.
So, you can play the baseline team on your own using:
```sh
python3 -m pacai.capture --red capture-team-student --blue capture-team-baseline --fps 30
```

Just like Pac-Man, you can play multiple games more quickly by disabling the GUI:
```sh
python3 -m pacai.capture --red capture-team-student --blue capture-team-baseline --ui null --num-games 10
```

When creating your agent,
make sure to thoroughly examine the Capture game state class ([pacai.capture.gamestate.GameState](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/gamestate.html#GameState)).
There are many function that you may find useful.

<!-- TODO(Batu): Update the tournament link.. -->
### Official Tournaments

Round-robin contests will be run using nightly automated tournaments on the course server,
with the final tournament deciding the final contest outcomes.
See the submission instructions for details of how to enter a team into the tournaments.
Tournaments are run every night (refer to Canvas for nightly cut off) and include all teams that have been submitted
(either earlier in the day or on a previous day) as of the start of the tournament.
Currently, each team is matched up with every other team two times (each matchup consists of 11 games).
In the first match, one team is `red` and the other is `blue`.
In the second match, they switch sides (the `red` team plays as `blue`, and the `blue` team plays as `red`).
This ensures you don't hard-code any color specific behavior or assumptions.

The boards used in the tournament will be drawn from both the default board (5 games),
as well as randomly generated boards (6 games).
All boards are symmetric, and the team that moves first is randomly chosen.
The results for a nightly tournaments can be found **TBD**, where you can view overall rankings and scores for each match.
You can also download replays, the boards used, and the stdout / stderr logs for each agent.
When examining replay JSON files, the CLI of json [module](https://docs.python.org/3/library/json.html#module-json.tool) may be helpful.

## Designing Agents

Unlike the other projects,
an agent now has the more complex job of trading off offense versus defense and effectively functioning as both a ghost and a Pac-Man in a team setting.
Furthermore, the limited information provided to your agent will likely necessitate some probabilistic tracking.
Finally, the added time limit of computation introduces new challenges.

### Baseline Team

To kick-start your agent design, we have provided you with a team of baseline agents,
defined in [pacai.capture.team.create_team_baseline](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/team.html#create_team_baseline).
They are both quite bad, but get the job dome.
The [pacai.capture.agents.OffensiveAgent](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/agents.html#OffensiveAgent)
moves toward the closest food on the opposing side.
The [pacai.capture.agents.DefensiveAgent](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/agents.html#DefensiveAgent)
wanders around on its own side and tries to chase down invaders it happens to see.

### File naming

For the purpose of testing or running games locally,
you can define a team of agents in any arbitrarily-named python file.
When submitting to the nightly tournament, however,
you must define your agents in [pacai.student.capture.py](https://github.com/edulinq/pacai/blob/v2.0.1/pacai/student/capture.py)
(and you must also create a [capture-team.txt](https://github.com/edulinq/pacai/blob/v2.0.1/pacai/student/capture-team.txt) file that specifies your team name).

When the tournament is run, your file will be moved/renamed (so we can run multiple teams at the same time).
Do not hard-code any file paths that reference your agent classes in your `pacai/student/capture.py`.

See the example below for a starting point that **avoids** hard-coding the agent class path:
```py
import pacai.core.action
import pacai.core.agent
import pacai.core.agentinfo
import pacai.core.gamestate

def create_team() -> list[pacai.core.agentinfo.AgentInfo]:
    """
    Get the agent information that will be used to create a capture team.
    """

    agent1_info = pacai.core.agentinfo.AgentInfo(name = f"{__name__}.MyAgent1")
    agent2_info = pacai.core.agentinfo.AgentInfo(name = f"{__name__}.MyAgent2")

    return [agent1_info, agent2_info]

class MyAgent1(pacai.core.agent.Agent):
    """ An agent that just takes random (legal) action. """

    def get_action(self, state: pacai.core.gamestate.GameState) -> pacai.core.action.Action:
        """ Choose a random action. """

        legal_actions = state.get_legal_actions()
        return self.rng.choice(legal_actions)

class MyAgent2(pacai.core.agent.Agent):
    """ An agent that just takes random (legal) action. """

    def get_action(self, state: pacai.core.gamestate.GameState) -> pacai.core.action.Action:
        """ Choose a random action. """

        legal_actions = state.get_legal_actions()
        return self.rng.choice(legal_actions)
```

### Distance Calculation

If you need to calculate distance in your agent,
we recommend looking into how the baseline agents do it.

### Useful Functions

Below are some code points that you may find useful.

 - [pacai.capture.gamestate.GameState.get_normalized_score](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/gamestate.html#GameState.get_normalized_score)
 - [pacai.capture.gamestate.GameState.is_ghost](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/gamestate.html#GameState.is_ghost)
 - [pacai.capture.gamestate.GameState.is_pacman](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/gamestate.html#GameState.is_pacman)
 - [pacai.capture.gamestate.GameState.is_scared](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/gamestate.html#GameState.is_scared)
 - [pacai.capture.gamestate.GameState.food_count](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/gamestate.html#GameState.food_count)
 - [pacai.capture.gamestate.GameState.get_food](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/gamestate.html#GameState.get_food)
 - [pacai.capture.gamestate.GameState.get_team_positions](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/gamestate.html#GameState.get_team_positions)
 - [pacai.capture.gamestate.GameState.get_opponent_positions](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/gamestate.html#GameState.get_opponent_positions)
 - [pacai.capture.gamestate.GameState.get_invader_positions](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/capture/gamestate.html#GameState.get_invader_positions)
 - [pacai.search.distance.DistancePreComputer](https://edulinq.github.io/pacai/docs/v2.0.1/pacai/search/distance.html#DistancePreComputer)

### Restrictions

The use of qualified imports is not allowed.
If you submit a file with qualified imports, the autograder will heavily penalize your score.

You are free to design any agent you want.
However, you will need to respect the provided APIs if you want to participate in the tournaments.
Agents which compute during the opponent's turn will be disqualified.
In particular, any form of parallelism is disallowed,
because we have found it very hard to ensure that no computation takes place on the opponent's turn.

### Warning

If one of your agents produces any stdout/stderr output during its games in the nightly tournaments,
that output will be included in the contest results posted on the website.
Additionally, in some cases a stack trace may be shown among this output in the event that one of your agents throws an exception.
You should design your code in such a way that this does not expose any information that you wish to keep confidential.

<!-- ## Contest Details

### Teams

We highly encourage you to work in teams of four people (no more than our).

### Prizes

The performance-based portion of your grade will be based on the placement received in **the final** round-robin tournament.
Placement is determined by the number of wins
(if multiple teams have the same number of wins, it will be broken by the number of ties).

### Extra Credit

Winners in the mid-project checkpoint contest will receive points as follows:
3 points for 1st place, 2 points for 2nd place, and 1 point for third place.
-->

<p align="center">
    <img alt="Capture with Random Board" src="images/capture-random-7.webp" width="800px">
    </br>
    Have fun!</br>
    Please bring our attention to any problems you discover.
</p>
