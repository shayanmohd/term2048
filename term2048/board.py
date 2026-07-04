# -*- coding: UTF-8 -*-

"""
Board-related things
"""

import random

# PY3 compat
try:
    xrange
except NameError:
    xrange = range


class Board(object):
    """
    A 2048 board
    """

    UP, DOWN, LEFT, RIGHT, PAUSE = 1, 2, 3, 4, 5

    GOAL = 2048
    WIDTH = 8
    HEIGHT = 4
    # legacy square-size constant kept for backward compatibility
    SIZE = 4

    # sentinel for an immovable blocker tile
    BLOCKER = 'X'

    # number of blocker tiles placed at the start of a game
    BLOCKER_COUNT = 2

    # probability that a freshly spawned tile is anti-matter (negative)
    ANTIMATTER_CHANCE = 0.2

    def __init__(self, goal=GOAL, width=None, height=None, size=None,
                 blockers=BLOCKER_COUNT, antimatter_chance=ANTIMATTER_CHANCE,
                 **_kwargs):
        if size is not None:
            # legacy square-board argument
            self.__width = size
            self.__height = size
        else:
            self.__width = width if width is not None else Board.WIDTH
            self.__height = height if height is not None else Board.HEIGHT
        self.__x_range = xrange(0, self.__width)
        self.__y_range = xrange(0, self.__height)
        self.__goal = goal
        self.__won = False
        self.__antimatter_chance = antimatter_chance
        self.cells = [[0] * self.__width for _ in xrange(self.__height)]

        for _ in xrange(blockers):
            self.addBlocker()

        self.addTile()
        self.addTile()

    def width(self):
        """return the board width (number of columns)"""
        return self.__width

    def height(self):
        """return the board height (number of rows)"""
        return self.__height

    def size(self):
        """return the board size (legacy, assumes a square board)"""
        return self.__width

    def goal(self):
        """return the board goal"""
        return self.__goal

    def won(self):
        """
        return True if the board contains at least one tile with the board goal
        """
        return self.__won

    def canMove(self):
        """
        test if a move is possible
        """
        if not self.filled():
            return True

        for y in self.__y_range:
            for x in self.__x_range:
                c = self.getCell(x, y)
                if c == Board.BLOCKER:
                    continue
                if x < self.__width - 1:
                    r = self.getCell(x + 1, y)
                    if r != Board.BLOCKER and (c == r or c == -r):
                        return True
                if y < self.__height - 1:
                    d = self.getCell(x, y + 1)
                    if d != Board.BLOCKER and (c == d or c == -d):
                        return True

        return False

    def filled(self):
        """
        return true if the game is filled
        """
        return len(self.getEmptyCells()) == 0

    def addBlocker(self):
        """
        place a permanent blocker tile on a random empty cell that does not
        share a row or a column with any existing blocker, so that blockers
        can never line up and wall off a section of the board
        """
        used_cols = set()
        used_rows = set()
        for y in self.__y_range:
            for x in self.__x_range:
                if self.getCell(x, y) == Board.BLOCKER:
                    used_cols.add(x)
                    used_rows.add(y)

        candidates = [(x, y) for (x, y) in self.getEmptyCells()
                      if x not in used_cols and y not in used_rows]
        if candidates:
            x, y = random.choice(candidates)
            self.setCell(x, y, Board.BLOCKER)

    def addTile(self, value=None, choices=None):
        """
        add a random tile in an empty cell
          value: value of the tile to add.
          choices: a list of possible choices for the value of the tile. if
                   ``None`` (the default), it uses
                   ``[2, 2, 2, 2, 2, 2, 2, 2, 2, 4]``.

        There is an ``antimatter_chance`` probability that the spawned tile
        is negative (anti-matter).
        """
        if choices is None:
            choices = [2] * 9 + [4]

        if value:
            choices = [value]

        v = random.choice(choices)
        if random.random() < self.__antimatter_chance:
            v = -v
        empty = self.getEmptyCells()
        if empty:
            x, y = random.choice(empty)
            self.setCell(x, y, v)

    def getCell(self, x, y):
        """return the cell value at x,y"""
        return self.cells[y][x]

    def setCell(self, x, y, v):
        """set the cell value at x,y"""
        self.cells[y][x] = v

    def getLine(self, y):
        """return the y-th line, starting at 0"""
        return self.cells[y]

    def getCol(self, x):
        """return the x-th column, starting at 0"""
        return [self.getCell(x, i) for i in self.__y_range]

    def setLine(self, y, l):
        """set the y-th line, starting at 0"""
        self.cells[y] = l[:]

    def setCol(self, x, l):
        """set the x-th column, starting at 0"""
        for i in xrange(0, self.__height):
            self.setCell(x, i, l[i])

    def getEmptyCells(self):
        """return a (x, y) pair for each empty cell"""
        return [(x, y)
                for x in self.__x_range
                for y in self.__y_range if self.getCell(x, y) == 0]

    def __collapseSegment(self, line, d):
        """
        Merge tiles in a blocker-free segment according to a direction and
        return a tuple with the new line and the score for the move on this
        segment.

        Two equal tiles merge into their double (this holds for negative
        tiles too, e.g. -2 and -2 become -4). A positive tile and its exact
        negative counterpart annihilate into an empty cell and score 0.
        """
        n = len(line)
        if (d == Board.LEFT or d == Board.UP):
            inc = 1
            rg = xrange(0, n - 1, inc)
        else:
            inc = -1
            rg = xrange(n - 1, 0, inc)

        pts = 0
        for i in rg:
            if line[i] == 0:
                continue
            if line[i] == line[i + inc]:
                v = line[i] * 2
                if v == self.__goal:
                    self.__won = True

                line[i] = v
                line[i + inc] = 0
                pts += abs(v)
            elif line[i] == -line[i + inc]:
                # matter / anti-matter annihilation: both tiles vanish, but
                # award the absolute value of the destroyed pair since the
                # player spent moves building them up
                pts += abs(line[i])
                line[i] = 0
                line[i + inc] = 0

        return (line, pts)

    def __moveSegment(self, line, d):
        """
        Move a blocker-free segment to a given direction (d)
        """
        nl = [c for c in line if c != 0]
        if d == Board.UP or d == Board.LEFT:
            return nl + [0] * (len(line) - len(nl))
        return [0] * (len(line) - len(nl)) + nl

    def __processSegment(self, seg, d):
        """move + collapse + move a single blocker-free segment"""
        moved = self.__moveSegment(seg, d)
        collapsed, pts = self.__collapseSegment(moved, d)
        return self.__moveSegment(collapsed, d), pts

    def __processLineOrCol(self, line, d):
        """
        Split a line/column on blocker tiles, process each segment
        independently (so tiles cannot slide through or merge across a
        blocker), then stitch the result back together with the blockers in
        their original positions.
        """
        result = []
        pts = 0
        seg = []
        for c in line:
            if c == Board.BLOCKER:
                new_seg, p = self.__processSegment(seg, d)
                result.extend(new_seg)
                result.append(Board.BLOCKER)
                pts += p
                seg = []
            else:
                seg.append(c)
        new_seg, p = self.__processSegment(seg, d)
        result.extend(new_seg)
        pts += p
        return result, pts

    def move(self, d, add_tile=True):
        """
        move and return the move score
        """
        if d == Board.LEFT or d == Board.RIGHT:
            chg, get, rg = self.setLine, self.getLine, self.__y_range
        elif d == Board.UP or d == Board.DOWN:
            chg, get, rg = self.setCol, self.getCol, self.__x_range
        else:
            return 0

        moved = False
        score = 0

        for i in rg:
            # save the original line/col
            origin = get(i)
            # move + merge, treating blockers as fixed walls
            new, pts = self.__processLineOrCol(list(origin), d)
            # set it back in the board
            chg(i, new)
            # did it change?
            if origin != new:
                moved = True
            score += pts

        # don't add a new tile if nothing changed
        if moved and add_tile:
            self.addTile()

        return score
