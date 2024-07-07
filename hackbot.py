# hackbot.py
# channel_id = 1259192643162738799
import discord
from discord.ext import commands
from discord.ui import Select, Button, View
import json
from db.db_managment import (
     get_path_id, add_path, add_channel_to_path, add_topic, add_task, get_user_week, get_topics,
    get_tasks, get_user_tasks, mark_user_task, get_all_paths, get_weeks_for_path, get_path_duration, get_topics_by_path, get_path_by_channel
)

# Configura el bot
intents = discord.Intents.default()
intents.messages = True
# bot = commands.Bot(command_prefix='!', intents=intents)
bot = commands.Bot(command_prefix= "!", intents = discord.Intents.all())

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    
    
@bot.command()
async def checklist(ctx):
    user_id = ctx.author.id
    channel_id = ctx.channel.id
    path = get_path_by_channel(channel_id)
    
    if path is None:
        await ctx.send("This channel is not associated with any path.")
        return
    
    path_id, path_name = path
    
    # response += '\n'
    response = f'\n**Path {path_name}**'
    response += '```\n'
    response += '{:<7} {:<20} {:<35}\n'.format('Week', 'Topic', 'Task')
    response += '-' * 60 + '\n'
    
    weeks = get_weeks_for_path(path_id)
    for week in weeks:
        topics = get_topics(path_id, week)
        for topic_id, topic in topics:
            tasks = get_tasks(topic_id)
            for task_id, task in tasks:
                response += '{:<7} {:<20} {:<35}\n'.format(week, topic, task)
    
    response += '```'
    
    await ctx.send(response)
    # await ctx.send(f"```\n{response}\n```")


@bot.command()
async def complete(ctx):
    user_id = ctx.author.id
    channel_id = ctx.channel.id
    path_id = get_path_id(channel_id)

    if path_id is None:
        await ctx.send("This channel is not associated with any path.")
        return
    
    # Get all weeks
    all_weeks = range(1, get_path_duration(path_id) + 1)
    # Filter weeks that have incomplete tasks
    weeks_with_incomplete_tasks = [
        week for week in all_weeks
        if any(
            not any(
                ut[0] == task_id and ut[2]
                for ut in get_user_tasks(user_id, path_id)
            )
            for topic_id, topic in get_topics(path_id, week)
            for task_id, task in get_tasks(topic_id)
        )
    ]
    
    if not weeks_with_incomplete_tasks:
        await ctx.send("You have no incomplete tasks.")
        return

    class WeekButton(Button):
        def __init__(self, week):
            super().__init__(label=f"Week {week}", style=discord.ButtonStyle.primary)
            self.week = week

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.send_message(f"Selected Week {self.week}. Loading tasks...")

            incomplete_tasks = [
                (task_id, task)
                for topic_id, topic in get_topics(path_id, self.week)
                for task_id, task in get_tasks(topic_id)
                if not any(
                    ut[0] == task_id and ut[2]
                    for ut in get_user_tasks(user_id, path_id)
                )
            ]

            if not incomplete_tasks:
                await interaction.followup.send("No incomplete tasks found for this week.")
                return

            class TaskButton(Button):
                def __init__(self, task_id, task_name):
                    super().__init__(label=task_name, style=discord.ButtonStyle.secondary)
                    self.task_id = task_id
                    self.task_name = task_name

                async def callback(self, task_interaction: discord.Interaction):
                    await task_interaction.response.send_message(f"Please provide the proof URL for the task '{self.task_name}':")

                    def check_url(msg):
                        return msg.author == ctx.author and msg.channel == ctx.channel

                    proof_msg = await bot.wait_for("message", check=check_url)
                    proof_url = proof_msg.content

                    try:
                        mark_user_task(user_id, self.task_id, True, proof_url)
                        await task_interaction.followup.send(f'Task "{self.task_name}" marked as completed with proof URL: {proof_url}!')
                    except Exception as e:
                        await task_interaction.followup.send(f"An error occurred: {str(e)}")

            task_view = View()
            for task_id, task_name in incomplete_tasks:
                task_view.add_item(TaskButton(task_id, task_name))

            await interaction.followup.send("Please select a task to mark as completed:", view=task_view)

    week_view = View()
    for week in weeks_with_incomplete_tasks:
        week_view.add_item(WeekButton(week))

    await ctx.send("Please select a week:", view=week_view)
    
    
@bot.command()
async def progress(ctx):
    user_id = ctx.author.id
    channel_id = ctx.channel.id
    path = get_path_by_channel(channel_id)
    
    if path is None:
        await ctx.send("This channel is not associated with any path.")
        return
    
    path_id, path_name = path
    
    response = f'**Path {path_name}**'
    response += '```\n'
    # response += '{:<5} {:<10} {:<20} {:<35} {:<8}\n'.format('Week', 'Topic', 'Task', 'Proof URL', 'Status')
    response += '{:<5} {:<18} {:<53} {:<8}\n'.format('Week', 'Task', 'Proof URL', 'Status')
    
    response += '-' * 90 + '\n'
    
    weeks = get_weeks_for_path(path_id)
    for week in weeks:
        topics = get_topics(path_id, week)
        for topic_id, topic in topics:
            tasks = get_tasks(topic_id)
            for task_id, task in tasks:
                result = next((ut for ut in get_user_tasks(user_id, path_id) if ut[0] == task_id), None)
                status = '✅' if result and result[2] else '❌'
                proof_url = result[3] if result else ''
                # proof_link = f'[Work Link]({proof_url})' if proof_url else ''
                # proof_link = f'<{proof_url}>' if proof_url else ''
                response += '{:<5} {:<18} {:<53} {:<12}\n'.format(week, task, proof_url, status)
    
    response += '```'
    
    await ctx.send(response)
    # await ctx.send(f"```\n{response}\n```")
    

@bot.command()
async def addpath(ctx):
    await ctx.send("Please provide the name of the path:")

    def check_name(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    name_msg = await bot.wait_for("message", check=check_name)
    name = name_msg.content

    await ctx.send("Please provide the duration in weeks:")

    def check_duration(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.isdigit()

    duration_msg = await bot.wait_for("message", check=check_duration)
    duration_weeks = int(duration_msg.content)

    path_id = add_path(name, duration_weeks)
    await ctx.send(f'Path "{name}" added with ID {path_id} and duration {duration_weeks} weeks.')

@bot.command()
async def addtopic(ctx):
    paths = get_all_paths()
    if not paths:
        await ctx.send("No paths available.")
        return

    class PathButton(Button):
        def __init__(self, path_id, path_name):
            super().__init__(label=path_name, style=discord.ButtonStyle.primary)
            self.path_id = path_id
            self.path_name = path_name

        async def callback(self, interaction: discord.Interaction):
            duration_weeks = get_path_duration(self.path_id)
            existing_weeks = get_weeks_for_path(self.path_id)
            all_weeks = list(range(1, duration_weeks + 1))
            available_weeks = [week for week in all_weeks if week not in existing_weeks]

            if not available_weeks:
                await interaction.response.send_message(f'All weeks for path "{self.path_name}" already have topics.')
                return

            class WeekButton(Button):
                def __init__(self, week, path_id, path_name):
                    super().__init__(label=f"Week {week}", style=discord.ButtonStyle.secondary)
                    self.week = week
                    self.path_id = path_id
                    self.path_name = path_name

                async def callback(self, week_interaction: discord.Interaction):
                    await week_interaction.response.send_message("Please provide the topic:")

                    def check_topic(msg):
                        return msg.author == ctx.author and msg.channel == ctx.channel

                    topic_msg = await bot.wait_for("message", check=check_topic)
                    topic = topic_msg.content

                    topic_id = add_topic(self.path_id, self.week, topic)
                    await week_interaction.followup.send(f'Topic "{topic}" added to path "{self.path_name}", week {self.week} with ID {topic_id}.')

            week_view = View()
            for week in available_weeks:
                week_view.add_item(WeekButton(week, self.path_id, self.path_name))
            
            await interaction.response.send_message("Please select a week:", view=week_view)

    path_view = View()
    for path_id, path_name in paths:
        path_view.add_item(PathButton(path_id, path_name))
    
    await ctx.send("Please select a path:", view=path_view)

@bot.command()
async def addtask(ctx):
    paths = get_all_paths()
    if not paths:
        await ctx.send("No paths available.")
        return

    class PathButton(Button):
        def __init__(self, path_id, path_name):
            super().__init__(label=path_name, style=discord.ButtonStyle.primary)
            self.path_id = path_id
            self.path_name = path_name

        async def callback(self, interaction: discord.Interaction):
            topics = get_topics_by_path(self.path_id)
            if not topics:
                await interaction.response.send_message(f'No topics available for path "{self.path_name}".')
                return

            class TopicButton(Button):
                def __init__(self, topic_id, topic_name):
                    super().__init__(label=topic_name, style=discord.ButtonStyle.secondary)
                    self.topic_id = topic_id
                    self.topic_name = topic_name

                async def callback(self, topic_interaction: discord.Interaction):
                    await topic_interaction.response.send_message("Please provide the task:")

                    def check_task(msg):
                        return msg.author == ctx.author and msg.channel == ctx.channel

                    task_msg = await bot.wait_for("message", check=check_task)
                    task = task_msg.content

                    task_id = add_task(self.topic_id, task)
                    await topic_interaction.followup.send(f'Task "{task}" added to topic "{self.topic_name}" with ID {task_id}.')

            topic_view = View()
            for topic_id, topic_name in topics:
                topic_view.add_item(TopicButton(topic_id, topic_name))

            await interaction.response.send_message("Please select a topic:", view=topic_view)

    path_view = View()
    for path_id, path_name in paths:
        path_view.add_item(PathButton(path_id, path_name))

    await ctx.send("Please select a path:", view=path_view)


@bot.command()
async def linkchannel(ctx):
    paths = get_all_paths()
    if not paths:
        await ctx.send("No paths available.")
        return

    class PathButton(Button):
        def __init__(self, path_id, path_name):
            super().__init__(label=path_name, style=discord.ButtonStyle.primary)
            self.path_id = path_id
            self.path_name = path_name

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.send_message("Please provide the channel ID to link:")

            def check_channel_id(msg):
                return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.isdigit()

            channel_msg = await bot.wait_for("message", check=check_channel_id)
            channel_id = int(channel_msg.content)

            try:
                add_channel_to_path(self.path_id, channel_id)
                await interaction.followup.send(f'Channel {channel_id} linked to path "{self.path_name}" with ID {self.path_id}.')
            except Exception as e:
                await interaction.followup.send(f"An error occurred: {str(e)}")

    path_view = View()
    for path_id, path_name in paths:
        path_view.add_item(PathButton(path_id, path_name))

    await ctx.send("Please select a path to link the channel:", view=path_view)
    
@bot.command()
async def channel(ctx):
    channel_name = ctx.channel.name
    await ctx.send(f'Estás en el canal: **{channel_name}**')
    

@bot.command()
async def path(ctx):
    channel_id = ctx.channel.id
    path = get_path_by_channel(channel_id)
    
    if path is None:
        await ctx.send("Este canal no está asociado con ningún path.")
        return
    
    path_name = path[1]
    await ctx.send(path_name)

@bot.command()
async def hola(ctx):
    await ctx.send("Hola ")
    

@bot.command(name='comandos')
async def comandos(ctx):
    help_text = """
    **Comandos Disponibles:**
    
    `!checklist` - Muestra checklist del path, en qué semana vas y tareas cumplidas.
    
    `!progress` - Muestra el progreso de las tareas, marcando las tareas cumplidas y no cumplidas.
    
    `!complete` - Marca una tarea como completada y agrega el URL como evidencia.
    
    `!addpath` - Agrega un nuevo path.
    
    `!addtopic` - Agrega un nuevo tema a un path existente.
    
    `!addtask` - Agrega una nueva tarea a un tema existente.
    
    `!linkchannel` - Vincula un canal a un path existente.
    
    `!channel` - Muestra el nombre y la ID del canal actual.
    
    `!path` - Muestra el nombre del path asociado al canal actual.
    """
    await ctx.send(help_text)



# Iniciar el bot con tu token
from config import DISCORD_TOKEN
bot.run(DISCORD_TOKEN)