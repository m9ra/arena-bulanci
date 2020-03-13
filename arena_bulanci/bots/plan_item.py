from typing import Optional


class PlanItem(object):
    def __init__(self):
        self.can_shoot: bool = True
        self.move_direction: Optional[int] = None
