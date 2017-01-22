from .Ship import Ship

class Battleship(Ship):

    def __init__(self, ship_id, x_pos, y_pos):
        self._ship_type = "Battleship"
        self._x_length = 5
        self._y_length = 1
        Ship.__init__(self, ship_id, self._ship_type, x_pos, y_pos, self._x_length, self._y_length)