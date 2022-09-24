
from enum import Enum, auto
import math
from typing import List

import struct
import sqlite3

import logging


def expand_bfloat(vec, half_length=600):
    """
    expand truncated float32 to float32
    """
    if len(vec) == half_length:
        vec = b"".join((b"\00\00" + bytes(pair)) for pair in zip(vec[::2], vec[1::2]))
    return vec

class SemantleError(Exception):
    pass

class NoWordFoundError(SemantleError):
    def __init__(self, guess, *args):
        self.guess = guess
        super().__init__(*args)

class PlayerNotPlayingError(SemantleError):
    def __init__(self, player_id, *args):
        self.player_id = player_id
        super().__init__(*args)

class Semantle:
    def __init__(self, db_name):
        self.db_name = db_name

    def word(self,word) -> List[float]:
        """Given word, returns semantics vector"""
        logging.debug(f"Semantle get word: {word}")
        try:
            con = sqlite3.connect(self.db_name)
            cur = con.cursor()
            res = cur.execute("SELECT vec FROM word2vec WHERE word = ?", (word,))
            res = cur.fetchone()
            logging.debug("word RES: ", str(res[0]))
            con.close()
            if not res:
                raise NoWordFoundError(word)
            return list(struct.unpack("300f", expand_bfloat(res[0])))
        except NoWordFoundError as nwfe:
            raise nwfe
        except Exception as e:
            logging.error(str(e))
            return []

    def model2(self,secret,word):
        try:
            con = sqlite3.connect(self.db_name)
            cur = con.cursor()
            res = cur.execute(
                "SELECT vec, percentile FROM word2vec left outer join nearby on nearby.word=? and nearby.neighbor=? WHERE word2vec.word = ?",
                (secret, word, word),
            )
            row = cur.fetchone()
            if row:
                row = list(row)
            con.close()
            if row == None:
                raise NoWordFoundError(word)
            vec = row[0]
            result = {"vec": list(struct.unpack("300f", expand_bfloat(vec)))}
            if row[1]:
                result["percentile"] = row[1]
            return result
        except Exception as e:
            logging.error(str(e))
            raise e

    def similarity(self, word):
        try:
            con = sqlite3.connect(self.db_name)
            cur = con.cursor()
            res = cur.execute(
                "SELECT top, top10, rest FROM similarity_range WHERE word = ?", (word,)
            )
            res = list(cur.fetchone())
            con.close()
            if not res:
                return ""
            return {"top": res[0], "top10": res[1], "rest": res[2]}
        except Exception as e:
            logging.error(str(e))
            raise e

    def nearby(self, word, n):
        try:
            con = sqlite3.connect(self.db_name)
            cur = con.cursor()
            res = cur.execute(
                f"SELECT * FROM nearby WHERE word = ? order by percentile desc limit {n} offset 1",
                (word,),
            )
            rows = cur.fetchall()
            con.close()
            if not rows:
                return ""
            return [row[1:] for row in rows]
        except Exception as e:
            logging.error(str(e))
            raise e

semantle = Semantle("../word2vec.db")


def genRandSecret():
    return "random"

def mag(a):
    return math.sqrt(sum([v*v for v in a]))

def dot(a, b):
    return sum([na*nb for na,nb in zip(a,b)])

def getCosSim(a,b):
    if mag(a) * mag(b) != 0:
        return dot(a,b)/(mag(a)*mag(b))
    else:
        return -1

def plus(v1,v2):
    return [a+b for a,b in zip(v1,v2)]

def minus(v1,v2):
    return [a-b for a,b in zip(v1,v2)]

def scale(v, k):
    return [k*a for a in v]

def project_along(v1, v2, t):
    v = minus(v2, v1)
    num = dot(minus(t,v1), v)
    denom = dot(v,v)
    return num/denom

class MultimantleGameType(Enum):
    CHAOS=auto()
    SIMUL=auto()
    TURNS=auto()

class MultimantleGame:

    def __init__(self):

        self.started = False
        self.players = set()
        self.secret = None
        self.secret_data = None
        self.game_type = None
        self.guess_list = []
        self.guess_results = []
        self.guess_count = 0

    def __repr__(self):
        return f'{self.__class__.__name__} "{self.secret}": {self.game_type.name}, {self.guess_results}'

    def join(self, player_id):
        self.players.add(player_id)

    def start(self, secret=None, game_type=MultimantleGameType.CHAOS):
        if secret == None:
            self.secret = genRandSecret()
        else:
            self.secret = secret

        self.secret_data = {"vec":semantle.word(self.secret)}
        logging.info(self.secret_data)
        self.game_type = game_type

        self.started = True

    def guess(self, guess, player_id = None):
        logging.debug(f"Game guess: {guess}")
        guess = guess.lower()
        try:
            guess_data = semantle.model2(self.secret, guess)
        except NoWordFoundError as nwfe:
            raise nwfe
        guess_vec = guess_data["vec"]
        percentile = guess_data["percentile"] if "percentile" in guess_data else None
        similarity = getCosSim(guess_vec, self.secret_data["vec"]) * 100.0
        if not guess in self.guess_list:
            self.guess_list.append(guess)
            guess_result = [similarity, guess, percentile, len(self.guess_list)]
            self.guess_results.append(guess_result)
            self.guess_results.sort(key=(lambda a:a[0]), reverse=True)
        else:
            guess_result = [g for g in self.guess_results if g[1] == guess][0]


        return guess_result

    def status(self, n):
        n = min(n,len(self.guess_results))
        return self.guess_results[0:n]

    def nearby(self, n):
        results = semantle.nearby(self.secret, n)
        return results

class MultimantleGameSimul(MultimantleGame):

    def __init__(self):
        super().__init__(self)
        self.player_guesses = {}

    def start(self, secret=None, game_type=MultimantleGameType.CHAOS, players=None):
        super().start(secret, game_type)

        if players is None:
            players = []
        for player in players:
            self.players.add(player)
            self.player_guesses[player] = None

    def add_player(self, player_id):
        self.players.add(player_id)
        self.player_guesses[player_id] = None
        
    def guess(self, guess, player_id):

        if not player_id in self.players:
            raise PlayerNotPlayingError(player_id)
        
        self.player_guesses[player_id] = guess

        if all([v is not None for k,v in self.player_guesses.items()]):
            results = []
            for player_id, guess in self.player_guesses.items():
                results.append((player_id, super().guess(guess)))
            return results