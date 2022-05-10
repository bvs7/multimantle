import discord
from discord.ext import commands

import random
import datetime
from typing import Dict
import logging

logging.basicConfig(level = logging.INFO)

from multimantle_game import MultimantleGame, MultimantleGameSimul, MultimantleGameType, NoWordFoundError, semantle

from wordle_track_bot import WordleTrack

with open("../multimantle_bot.tok", "r") as f:
    token = f.read().strip()

bot = commands.Bot(command_prefix="!")

semantle_start = datetime.datetime(year=2022,month=1,day=28,hour=17)

def getSemantleSecret(day = None):
    if day is None:
        now = datetime.datetime.now()
        day = (now - semantle_start).days
    with open("../semantle/static/assets/js/secretWords.js", "r") as f:
        f.readline()
        for i in range(day):
            f.readline()
        secret = f.readline()[1:-3]
    return secret, day
        
def getRandomFarSemantle():
    day = random.randint(1000,4256)
    return getSemantleSecret(day)

def fmtGuessResult(gr):
    return f"#{gr[3]} | {gr[1]} | {gr[0]:.2f} | {gr[2] or 'cold'}"

class Multimantle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Map channel id to game
        self.games : Dict[int, MultimantleGame] = {}

    @commands.command()
    async def hello(self, ctx, *, member: discord.Member = None):
        """Says hello"""
        member = member or ctx.author
        await ctx.send(f"Hello {member.name}")

    @commands.command()
    async def test_start(self, ctx, secret: str = None):
        """Test a game of multimantle using supplied secret word"""
        if secret is None:
            raise ValueError()
        game = MultimantleGame()
        game.start(secret)
        self.games[ctx.channel.id] = game
        await ctx.send(f"Starting game: ||`{game}`||")

    @commands.command()
    async def start(self, ctx, game_num = None):
        """Start a game using a random semantle word from 2025-2040"""

        game_type = MultimantleGameType.CHAOS.name
        if game_type in MultimantleGameType.__members__:
            game_type = MultimantleGameType[game_type]
        else:
            game_type = MultimantleGameType.CHAOS

        if game_num == None:
            secret, day = getRandomFarSemantle()
        else:
            try:
                game_num = int(game_num)
                if game_num <=0:
                    raise ValueError()
            except Exception as e:
                await ctx.send(f"Invalid game num: {game_num}")
                return
            secret, day = getSemantleSecret(game_num)

        if game_type == MultimantleGameType.SIMUL:
            game = MultimantleGameSimul()
            game.start(secret, game_type)
        else:
            game = MultimantleGame()
            game.start(secret, game_type)
        self.games[ctx.channel.id] = game
        await ctx.send(f"Starting ({game.game_type.name}) Semantle Game #{day}! Spoiler Warning!!!")

    @commands.command()
    async def join(self, ctx):
        """Join a current non-chaos game"""
        if not ctx.channel.id in self.games:
            await ctx.send("No Multimantle game in this channel")
            return
        
        game = self.games[ctx.channel.id]

        if not ctx.author.id in game.players:
            game.add_player(ctx.author.id)
            await ctx.send(f"Welcome to the game, {ctx.author.name}")
            return
        else:
            await ctx.send(f"{ctx.author.name} is already playing")
            return

    @commands.command()
    async def top(self, ctx, n:str='10'):
        """Get the top n results"""
        if not ctx.channel.id in self.games:
            await ctx.send("No Multimantle game in this channel")

        game = self.games[ctx.channel.id]

        try:
            n = int(n)
            if n <=0:
                raise ValueError()
        except Exception as e:
            await ctx.send(f"Invalid n: {n}")
            return

        results = game.nearby(n)
        results = [(r[1], r[0], r[2], "top") for r in results]
        msg = "\n".join([fmtGuessResult(r) for r in results])
        await ctx.send(msg)

    @commands.command()
    async def semantle_daily_start(self, ctx, game_type:str = MultimantleGameType.CHAOS.name):
        """Start a game using the daily semantle secret! Spoiler Warning!"""
        game_type = game_type.upper()
        if game_type in MultimantleGameType.__members__:
            game_type = MultimantleGameType[game_type]
        else:
            game_type = MultimantleGameType.CHAOS
        secret, day = getSemantleSecret()
        game = MultimantleGame()
        game.start(secret, game_type)
        self.games[ctx.channel.id] = game
        await ctx.send(f"Starting Semantle Game #{day}! Spoiler Warning!!!")

    @commands.command()
    async def test_status(self, ctx):
        """Show game debug info"""
        await ctx.send(f"||`{self.games}`||")

    @commands.command()
    async def status(self, ctx, n: str ='5'):
        if not ctx.channel.id in self.games:
            await ctx.send("No Multimantle game in this channel")
            return
        
        try:
            n = int(n)
            if n <=0:
                raise ValueError()
        except Exception as e:
            await ctx.send(f"Invalid n: {n}")
            return

        results = self.games[ctx.channel.id].status(n)
        msg = "\n".join([fmtGuessResult(r) for r in results])
        await ctx.send(msg)

    @commands.command()
    async def guess(self, ctx, guess: str = None):
        """Enters your Semantle Guess"""
        if not ctx.channel.id in self.games:
            await ctx.send("No Multimantle game in this channel")
            return

        try:
            guess.replace("||","")
            game = self.games[ctx.channel.id]
            if game.game_type == MultimantleGameType.CHAOS:

                result = self.games[ctx.channel.id].guess(guess)
                await ctx.send(fmtGuessResult(result))
                return

            elif game.game_type == MultimantleGameType.SIMUL:
                pass


        except NoWordFoundError as nwfe:
            await ctx.send(f"Could not find word {guess}")
            return


if __name__ == "__main__":
    bot.add_cog(Multimantle(bot))
    bot.add_cog(WordleTrack(bot))

    bot.run(token)
