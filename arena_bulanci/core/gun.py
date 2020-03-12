from typing import Optional


class Gun(object):
    def __init__(self, id: str, full_ammo_count: int, cooldown_time: int, reload_time: Optional[int]):
        self.id = id
        self.full_ammo_count = full_ammo_count
        self.reload_time = reload_time
        self.cooldown_time = cooldown_time
        self.ammo_count = self.full_ammo_count

        self._cooldown_start = None

    def can_shoot(self, game: 'Game'):
        if self.ammo_count <= 0:
            return False

        if self._cooldown_start is None:
            return True

        if self._cooldown_start + self.cooldown_time > game.tick:
            return False

        return True

    def can_reload(self, game: 'Game'):
        if self.ammo_count != 0 or self.reload_time is None:
            return False

        if self._cooldown_start + self.reload_time > game.tick:
            return False

        return True
