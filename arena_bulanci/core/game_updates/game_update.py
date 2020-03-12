class GameUpdate(object):
    def apply_on(self, game: 'Game'):
        """
        Applies changes to the game, without any validations.
        Has to be simple (no calculations) and sendable over the network.
        """
        raise NotImplementedError("must be overridden")