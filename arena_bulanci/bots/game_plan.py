from typing import Tuple, Dict, List, Optional

from arena_bulanci.bots.plan_item import PlanItem
from arena_bulanci.core.config import MAP_WIDTH, MAP_HEIGHT
from arena_bulanci.core.game import Game
from arena_bulanci.core.utils import step_from, rotate_180

_UNREACHABLE_POSITIONS = set(Game.get_positions_unreachable_for_players())

class GamePlan(object):
    def __init__(self):
        self.board: Dict[Tuple[int, int], Optional[PlanItem]] = {}
        for unreachable in Game.get_positions_unreachable_for_players():
            self.board[unreachable] = None

        self._worklist = None
        self._handled = None

    @classmethod
    def available_positions_around(cls, position: Tuple[int, int], radius: int) -> List[Tuple[int, int]]:
        result = []
        for x in range(max(0, position[0] - radius), min(MAP_WIDTH, position[0] + radius + 1)):
            for y in range(max(0, position[1] - radius), min(MAP_HEIGHT, position[1] + radius + 1)):
                new_position = x, y

                if new_position in _UNREACHABLE_POSITIONS:
                    continue

                result.append(new_position)

        return result

    @classmethod
    def plan_route_to_targets(cls, targets: List[Tuple[int, int]],
                              allowed_positions: Optional[List[Tuple[int, int]]] = None,
                              stop_position: Optional[Tuple[int, int]] = None) -> 'GamePlan':
        """
        Creates GamePlan leading to the closest of given targets
        """
        plan = GamePlan()
        plan._worklist = list(map(PlaningTask, targets))
        plan._handled = set(plan.board.keys())
        plan._handled.update(plan._worklist)

        plan.calculate(allowed_positions, stop_position)

        return plan

    def calculate(
            self,
            allowed_positions: Optional[List[Tuple[int, int]]] = None,
            stop_position: Optional[Tuple[int, int]] = None
    ) -> 'GamePlan':

        while self._worklist:
            task = self._worklist.pop(0)

            for i in range(4):
                direction = (i + task.incoming_direction) % 4

                next_position = step_from(task.position, direction)
                if next_position in self._handled:
                    continue  # already included

                if allowed_positions:
                    if next_position not in allowed_positions:
                        continue

                self._worklist.append(PlaningTask(next_position, direction))
                self._handled.add(next_position)
                next_position_item = PlanItem()
                next_position_item.move_direction = rotate_180(direction)
                self.board[next_position] = next_position_item
                if next_position == stop_position:
                    return self

        return self


class PlaningTask(object):
    def __init__(self, position, incoming_direction=0):
        self.position = position
        self.incoming_direction = incoming_direction
