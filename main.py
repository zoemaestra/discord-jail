import json
import discord
from matplotlib import pyplot as plt
import time
import random
import openai

from pathlib import Path
from discord.ext import commands, tasks


config = json.loads(open("config.json").read())
if config["openaikey"] != "":
    client = OpenAI(api_key=config["openaikey"])

messages = []
votetime = 0

"""
config.json format (keep the curly brackets!!)
You can restrict role usage and channel usage using discord's native settings for slash command bots

{
    "token": "YOUR TOKEN HERE",
    "application-id": "YOUR APPLICATION ID HERE",
    "guild": "YOUR GUILD ID HERE"
    "jail": "YOUR JAIL CHANNEL ID HERE"
    "announce": "YOUR ANNOUNCEMENT CHANNEL ID HERE"
    "muterole": "YOUR MUTE ROLE ID HERE"
    "adminrole": "YOUR ADMIN/MOD ROLE ID HERE (used for command syncs)"
    "votetime": "TIME (IN SECONDS) THAT A MESSAGE VOTE SHOULD BE HELD FOR"
    "openaikey": "KEY FOR OPENAI MODERATION (leave empty quotes if you don't want to use openAI moderation)"
}
"""

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="~", intents=intents)


@bot.tree.command(
    name="postmessage",
    description="Suggest a message to post into the jail channel"
)
async def postmessage(interaction: discord.Interaction, msg: str):
    global messages, votetime
    proposal = {"author": interaction.user.id,
                "proposal": 1 + len(messages),
                "content": msg,
                "votes": [1189967653700382811]}

    logchannel = bot.get_channel(int(config["announce"]))
    
    if votetime == 0:
        messages.append(proposal)
        votetime = time.time()
        embed=discord.Embed(title="New jail message vote started", description=f"A new vote to post a message in the jail has begun.\nProposal {proposal['proposal']}:\n {msg} (by {interaction.user.mention})\n\nYou can suggest messages with `/postmessage <msg>`, view proposals with `/props` and vote on proposals with `/vote <proposal number>`")
        await logchannel.send(embed=embed)
        await interaction.response.send_message(f"Message proposed under proposal no. {proposal['proposal']}!", ephemeral=True)

    else:
        newmessages = messages

        for message in messages:
            if message["author"] == interaction.user.id:
                newmessages.remove(message)
        
        messages = newmessages
        messages.append(proposal)
        embed=discord.Embed(title=f"New proposal no. {proposal['proposal']}", description=f'"{msg}"\n by <@!{message["author"]}>')
        await logchannel.send(embed=embed)
        await interaction.response.send_message(f"Message proposed under proposal no. {proposal['proposal']}! Any previous proposals you made for this vote have been auto deleted, along with any votes it had.", ephemeral=True)


@bot.tree.command(
    name="vote",
    description="Vote on a message to go into the jail channel"
)
async def vote(interaction: discord.Interaction, vote: int):
    logchannel = bot.get_channel(int(config["announce"]))
    
    if votetime == 0:
        await interaction.response.send_message(f"There are no messages proposals to vote on right now", ephemeral=True)

    else:
        proposal = {}
        for message in messages:
            if interaction.user.id in message["votes"]:
                message["votes"].remove(interaction.user.id)
            if message["proposal"] == vote:
                proposal = message

        if proposal != {}:
            if proposal["author"] == interaction.user.id:
                await interaction.response.send_message(f"You cannot vote for yourself", ephemeral=True)
            else:
                proposal["votes"].append(interaction.user.id)
                await interaction.response.send_message(f"Successfully voted for proposal {message['proposal']}", ephemeral=True)
        else:
            await interaction.response.send_message(f"No such proposal exists, check with `/props` to see which number you can vote for.", ephemeral=True)

@bot.tree.command(
    name="props",
    description="View current message proposals"
)
async def props(interaction: discord.Interaction):  
    if votetime == 0:
        await interaction.response.send_message(f"There are no messages proposals to vote on right now", ephemeral=True)

    else:
        timeleft = (votetime + int(config["votetime"])) - time.time()
        timeleft = round(max(0, timeleft))

        embed=discord.Embed(title="Jail message proposals")
        for message in messages:
            embed.add_field(name=f"{message['proposal']} ({len(message['votes'])} votes):", value=f"{message['content']} (by <@!{message['author']}>)", inline=True)
        
        if timeleft < 10:
            embed.set_footer(text=f"Vote closes in {timeleft} seconds")
        else:
            embed.set_footer(text=f"Vote closes in a few seconds")

        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(
    name="help",
    description="View help about the jail bot"
)
async def props(interaction: discord.Interaction):  
    embed=discord.Embed(title="Jail message proposals")
    embed.add_field(name="/postmessage <msg>",value="Proposes a message to send to the jail channel and starts a vote timer if one wasn't already started")
    embed.add_field(name="/vote <prop>",value="Votes on a proposal, with `<prop>` being the number of the proposal you are voting for. You cannot vote for your own message and if you have already voted, your vote will be removed from what you last voted for and added to the new proposal")
    embed.add_field(name="/props",value="Posts a list of vote proposals for your viewing pleasure")
    embed.add_field(name="Additional info",value=f"Votes last {config['votetime']} seconds and the message will only be posted once the timer has elapsed. Only messages with votes will be posted and if there is a tie, a message in the tie will be randomly chosen.")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.command()
async def jail(ctx, member: discord.Member):
    guild = bot.get_guild(int(config["guild"]))
    jailrole = discord.utils.get(guild.roles,id=int(config["muterole"]))
    adminrole = discord.utils.get(guild.roles,id=int(config["adminrole"]))
    jailchannel = bot.get_channel(int(config["jail"]))

    if adminrole in ctx.author.roles:
        if jailrole in member.roles:
            await ctx.channel.send(f"User is already in jail")
        else:
            await member.add_roles(jailrole)
            await ctx.channel.send(f"{member.mention} has been banished to the jail!")
            await jailchannel.send(f"{member.mention} has been banished to the jail!")

@bot.command()
async def unjail(ctx, member: discord.Member):
    guild = bot.get_guild(int(config["guild"]))
    jailrole = discord.utils.get(guild.roles,id=int(config["muterole"]))
    adminrole = discord.utils.get(guild.roles,id=int(config["adminrole"]))
    jailchannel = bot.get_channel(int(config["jail"]))

    if adminrole in ctx.author.roles:
        if jailrole not in member.roles:
            await ctx.channel.send(f"User is not in jail")
        else:
            await member.remove_roles(jailrole)
            await ctx.channel.send(f"{member.mention} has been released from jail!")
            await jailchannel.send(f"{member.mention} has been released from jail!")

@bot.command()
async def sync(ctx):
    #This is necessary to sync the command tree. Do not remove.
    guild = bot.get_guild(int(config["guild"]))
    adminrole = discord.utils.get(guild.roles,id=int(config["adminrole"]))

    if adminrole in ctx.author.roles:
        await bot.tree.sync()
        await ctx.send('Command tree synced.')

@bot.event
async def on_message(message: discord.Message):
    #This is necessary for the sync command and for jail message filtering. Do not remove.
    if message.author != bot.user and message.channel.id == int(config["jail"]) and config["openaikey"] != "":
        response = client.moderations.create(input=message.content)
        output = response.results[0]
        print(output)
        #await message.channel.send(response)

    await bot.process_commands(message)

@tasks.loop(seconds=10)
async def loop():
    global messages, votetime
    votedmessages = []
    highestvote = 0

    logchannel = bot.get_channel(int(config["announce"]))
    jailchannel = bot.get_channel(int(config["jail"]))

    if votetime != 0 and (votetime + int(config["votetime"])) <= time.time():
        for message in messages:
            if len(message["votes"]) >= 1:
                if len(message["votes"]) == highestvote or len(message["votes"]) == 1:
                    votedmessages.append(message)

                if len(message["votes"]) > highestvote:
                    highestvote = len(message["votes"])
                    votedmessages = []
                    votedmessages.append(message)

        if len(votedmessages) == 0:
                embed=discord.Embed(title="Jail message vote failed", description=f"No proposal received any votes, so nothing has been posted")
                await logchannel.send(embed=embed)

        else:
            msg = ""
            if len(votedmessages) == 1:
                embed=discord.Embed(title="Jail message vote succeeded", description=f"The winning proposal was sent to the jail channel")
                await logchannel.send(embed=embed)
                msg = votedmessages[0]["content"]
            
            if len(votedmessages) > 1:
                embed=discord.Embed(title="Jail message vote succeeded with a tie", description=f"There was a tie in votes, so the winning proposal was randomly selected from the top suggestions and posted to the jail channel")
                await logchannel.send(embed=embed)
                msg = random.choice(votedmessages)["content"]
            
            embed=discord.Embed(title="New message", description=f"{msg}")
            embed.set_footer(text=f"This message was proposed by server regulars and voted on. Messages can only be received from them once every {config['votetime']} seconds")
            await jailchannel.send(embed=embed)
        
        votetime = 0
        messages = []


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    for guild in bot.guilds:
        if guild.id != int(config["guild"]):
            print(guild.id)
            await guild.leave()
    print("If you've changed commands, make sure to sync the command tree!")
    print('------')
    await loop.start()
        
bot.run(config["token"])
