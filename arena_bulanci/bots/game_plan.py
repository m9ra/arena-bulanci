from typing import Tuple, Dict, List, Optional

from arena_bulanci.bots.plan_item import PlanItem
from arena_bulanci.core.game import Game
from arena_bulanci.core.utils import step_from, rotate_180


class GamePlan(object):
    def __init__(self):
        self.board: Dict[Tuple[int, int], Optional[PlanItem]] = {}
        for unreachable in Game.get_positions_unreachable_for_players():
            self.board[unreachable] = None

    @classmethod
    def plan_route_to_targets(cls, targets: List[Tuple[int, int]], allow_shooting=True):
        """
        Creates GamePlan leading to the closest of given targets
        """
        plan = GamePlan()
        worklist = list(map(PlaningTask, targets))
        handled = set(plan.board.keys())
        handled.update(worklist)

        while worklist:
            task = worklist.pop(0)

            for i in range(4):
                direction = (i + task.incoming_direction) % 4

                next_position = step_from(task.position, direction)
                if next_position in handled:
                    continue  # already included

                worklist.append(PlaningTask(next_position, direction))
                handled.add(next_position)
                next_position_item = PlanItem()
                next_position_item.can_shoot = allow_shooting
                next_position_item.move_direction = rotate_180(direction)
                plan.board[next_position] = next_position_item

        return plan


class PlaningTask(object):
    def __init__(self, position, incoming_direction=0):
        self.position = position
        self.incoming_direction = incoming_direction
