import discord
from discord.ext import commands

import sqlite3

import datetime
from dateutil import parser as dateutil_parser
from typing import Dict
import logging
logging.basicConfig(level = logging.DEBUG)

WORDLE_TRACK_DB_FNAME = "../../wordle/wordle_track.db"

wordle_start = datetime.datetime(year=2021, month=6, day=19)

def getDate(date: datetime.datetime = None):
    if not date:
        date = datetime.datetime.now()
    return (date - wordle_start).days
# Tables:
# Results:
# [date id] name score word1 word2 word3 word4 word5 word6
# Words:
# [date] word
# Notes
# [noteno] name id date note

def formatEntry(entry):
    words = [e for e in entry[4:] if not e == None]
    wordstr = "\n".join(words)
    return f"Game #{entry[1]} ({entry[2]})\nScore: {entry[3]}\n{wordstr}"

def formatScore(entry):
    return f"{entry[2]}: {entry[3]}"

class WordleTrack(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db_name = WORDLE_TRACK_DB_FNAME

    @commands.command()
    async def result(self, ctx : commands.Context, *words):
        """Submit your results, with each word separated by a space"""
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("Please submit results via DM")
            return

        if len(words) > 6 or len(words) == 0:
            await ctx.send(f"Invalid number of words: {len(words)}")
            return

        if any([len(word)!=5 for word in words]):
            await ctx.send(f"Invalid entry. Words must be 5 letters")
            return

        user_id = ctx.channel.recipient.id
        date = date = getDate()

        name = ctx.channel.recipient.name
        score = len(words)
        words = list(words)
        # Create database entry
        entry = [user_id, date, name, score] + words

        word_col_names = ["word1","word2","word3","word4","word5","word6"]
        word_cols = ",".join(word_col_names[0:len(words)])
        nvals = ",?" * len(words)
        insert = f"INSERT OR REPLACE INTO results(id,date,name,score,{word_cols}) "
        values = f"VALUES (?,?,?,?{nvals})"

        con = sqlite3.connect(self.db_name)
        cur = con.cursor()
        cur.execute(insert+values, entry)
        con.commit()
        con.close()

        # TODO: check if all in lobby have finished

        await ctx.send(formatEntry(entry))

    @commands.command()
    async def show(self, ctx : commands.Context, date:str = None):
        """Reveal all scores or games"""
        con = sqlite3.connect(self.db_name)
        cur = con.cursor()
        if not date == None:
            try:
                date = dateutil_parser.parse(date)
            except ValueError:
                await ctx.send(f"Invalid date: {date}")
                return
            date = getDate(date)
        else: 
            date = getDate()
        select = f"SELECT * FROM results WHERE date={date}"

        res = cur.execute(select)

        rows = list(cur.fetchall())
        con.close()

        if len(rows) == 0:
            await ctx.send(f"No results for Game #{date}")
            return

        # TODO: make check if everyone is done, not just if n people finished
        if len(rows) == 6 or isinstance(ctx.channel, discord.DMChannel):
            responses = [formatEntry(entry) for entry in rows]
        else:
            responses = [formatScore(entry) for entry in rows]

        await ctx.send("\n".join(responses))

    @commands.command()
    async def wordle(self, ctx : commands.Context, word):
        """Enter today's correct answer"""
        con = sqlite3.connect(self.db_name)
        cur = con.cursor()
        date = getDate()
        insert = "INSERT OR REPLACE INTO words(date, word) VALUES (?,?)"
        cur.execute(insert, (date,word))
        con.commit()
        con.close()

        await ctx.send(f"Updated Game #{date} word: {word}")


"""
CREATE TABLE results(
    id INT NOT NULL,
    date INT NOT NULL,
    name TEXT NOT NULL,
    score INT NOT NULL,
    word1 CHAR(5),
    word2 CHAR(5),
    word3 CHAR(5),
    word4 CHAR(5),
    word5 CHAR(5),
    word6 CHAR(5),
    PRIMARY KEY(id, date)
);

CREATE TABLE words(
    date INT PRIMARY KEY NOT NULL,
    word CHAR(5) NOT NULL
);

CREATE TABLE notes(
    id INT NOT NULL,
    date INT NOT NULL,
    name TEXT NOT NULL,
    note TEXT,
    PRIMARY KEY(id, date)
);

"""

