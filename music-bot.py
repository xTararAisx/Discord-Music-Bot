#!/usr/bin/env python3
import os
import re
import sys
import time
import shutil
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union

import discord
from discord.ext import commands
import yt_dlp
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("musicbot")


class MusicBot:
    """Discord Music Bot for playing audio from YouTube in voice channels."""

    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.token = os.getenv("BOT_TOKEN")
        self.prefix = os.getenv("BOT_PREFIX", ".")
        self.print_stack_trace = os.getenv("PRINT_STACK_TRACE", "1").lower() in ("true", "t", "1")
        self.report_command_not_found = os.getenv("BOT_REPORT_COMMAND_NOT_FOUND", "1").lower() in ("true", "t", "1")
        self.report_dl_error = os.getenv("BOT_REPORT_DL_ERROR", "0").lower() in ("true", "t", "1")
        self.skip_in_progress = set()  # Track servers with skip operations in progress

        try:
            self.color = int(os.getenv("BOT_COLOR", "915cbf"), 16)
        except ValueError:
            logger.warning("Invalid BOT_COLOR in .env, using default (ff0000).")
            self.color = 0x915CBF

        # Setup intents
        intents = discord.Intents.default()
        intents.voice_states = True
        intents.message_content = True
        intents.guild_messages = True
        intents.guilds = True

        # Create bot
        self.bot = commands.Bot(
            command_prefix=self.prefix,
            intents=intents,
            case_insensitive=True,
        )

        # Remove the default help command
        self.bot.remove_command('help')

        # Queue data: {server_id: {'queue': [(path, info_dict), ...], 'loop': bool, 'volume': float}}
        self.queues = {}

        # Lock for queue modifications
        self.queue_lock = asyncio.Lock()

        # Modified command processing flag to prevent duplicates
        self.active_commands = set()

        # Create download directory
        os.makedirs("./dl", exist_ok=True)

        # Register commands and events
        self._register_commands()
        self._register_events()

    def _register_commands(self):
        """Register bot commands."""

        @self.bot.command(name="queue", aliases=["lista", "q"])
        async def cmd_queue(ctx: commands.Context):
            """Show the current queue for this server."""
            # Dedupe command processing
            if ctx.message.id in self.active_commands:
                return
            self.active_commands.add(ctx.message.id)

            try:
                await self.handle_queue(ctx)
            finally:
                self.active_commands.discard(ctx.message.id)

        @self.bot.command(name="skip", aliases=["s", "siguiente", "pasar", "next"])
        async def cmd_skip(ctx: commands.Context, *args):
            """Skip 1 or more tracks. Usage: .skip [n] or .skip all"""
            # Dedupe command processing
            if ctx.message.id in self.active_commands:
                return
            self.active_commands.add(ctx.message.id)

            try:
                await self.handle_skip(ctx, args)
            finally:
                self.active_commands.discard(ctx.message.id)

        @self.bot.command(name="play", aliases=["p"])
        async def cmd_play(ctx: commands.Context, *, query: str = None):
            """Play a given search query or URL from YouTube."""
            # Dedupe command processing
            if ctx.message.id in self.active_commands:
                return
            self.active_commands.add(ctx.message.id)

            try:
                await self.handle_play(ctx, query)
            finally:
                self.active_commands.discard(ctx.message.id)

        @self.bot.command(name="loop", aliases=["l"])
        async def cmd_loop(ctx: commands.Context):
            """Toggle looping of the current queue."""
            # Dedupe command processing
            if ctx.message.id in self.active_commands:
                return
            self.active_commands.add(ctx.message.id)

            try:
                await self.handle_loop(ctx)
            finally:
                self.active_commands.discard(ctx.message.id)

        @self.bot.command(name="nowplaying", aliases=["np", "sonando"])
        async def cmd_now_playing(ctx: commands.Context):
            """Display information about the currently playing track."""
            # Dedupe command processing
            if ctx.message.id in self.active_commands:
                return
            self.active_commands.add(ctx.message.id)

            try:
                await self.handle_now_playing(ctx)
            finally:
                self.active_commands.discard(ctx.message.id)

        @self.bot.command(name="pause", aliases=["pa", "parar", "pausa"])
        async def cmd_pause(ctx: commands.Context):
            """Pause the currently playing track."""
            # Dedupe command processing
            if ctx.message.id in self.active_commands:
                return
            self.active_commands.add(ctx.message.id)

            try:
                await self.handle_pause(ctx)
            finally:
                self.active_commands.discard(ctx.message.id)

        @self.bot.command(name="resume", aliases=["r", "continuar", "unpausar"])
        async def cmd_resume(ctx: commands.Context):
            """Resume the paused track."""
            # Dedupe command processing
            if ctx.message.id in self.active_commands:
                return
            self.active_commands.add(ctx.message.id)

            try:
                await self.handle_resume(ctx)
            finally:
                self.active_commands.discard(ctx.message.id)

        @self.bot.command(name="volume", aliases=["v"])
        async def cmd_volume(ctx: commands.Context, volume: str = None):
            """Set the volume (0-100). Usage: .volume [level]"""
            # Dedupe command processing
            if ctx.message.id in self.active_commands:
                return
            self.active_commands.add(ctx.message.id)

            try:
                await self.handle_volume(ctx, volume)
            finally:
                self.active_commands.discard(ctx.message.id)

        @self.bot.command(name="cleanup", aliases=["clean"])
        async def cmd_cleanup(ctx: commands.Context):
            """Clean up downloaded files."""
            # Dedupe command processing
            if ctx.message.id in self.active_commands:
                return
            self.active_commands.add(ctx.message.id)

            try:
                await self.handle_cleanup(ctx)
            finally:
                self.active_commands.discard(ctx.message.id)

        @self.bot.command(name="help", aliases=["h"])
        async def cmd_help(ctx: commands.Context):
            """Show help information."""
            # Dedupe command processing
            if ctx.message.id in self.active_commands:
                return
            self.active_commands.add(ctx.message.id)

            try:
                await self.handle_help(ctx)
            finally:
                self.active_commands.discard(ctx.message.id)

        # Add this to your _register_commands method:
        @self.bot.command(name="ayuda", aliases=["a"])
        async def cmd_ayuda(ctx: commands.Context):
            """Muestra información de ayuda en español."""
            # Dedupe command processing
            if ctx.message.id in self.active_commands:
                return
            self.active_commands.add(ctx.message.id)

            try:
                await self.handle_ayuda(ctx)
            finally:
                self.active_commands.discard(ctx.message.id)

    def _register_events(self):
        """Register bot events."""

        @self.bot.event
        async def on_ready():
            logger.info(f"Logged in successfully as {self.bot.user.name}")

            # Clean up download directory on startup
            for server_dir in Path("./dl").glob("*"):
                if server_dir.is_dir():
                    try:
                        shutil.rmtree(server_dir)
                    except Exception as e:
                        logger.warning(f"Failed to clean up directory {server_dir}: {e}")

            # Clean active commands set
            self.active_commands.clear()

            # Update presence in a loop
            async def heartbeat():
                while not self.bot.is_closed():
                    activity_text = "Music 🎵 | " + self.prefix + "help"
                    await self.bot.change_presence(activity=discord.Game(activity_text))
                    await asyncio.sleep(20)

            self.bot.loop.create_task(heartbeat())

        @self.bot.event
        async def on_command_error(ctx: commands.Context, error: commands.CommandError):
            """Handle errors gracefully."""
            # Dedupe command processing
            if ctx.message.id in self.active_commands:
                return
            self.active_commands.add(ctx.message.id)

            try:
                await self.handle_command_error(ctx, error)
            finally:
                self.active_commands.discard(ctx.message.id)

        @self.bot.event
        async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
            """Handle voice state changes."""
            await self.handle_voice_state_update(member, before, after)

    async def handle_queue(self, ctx: commands.Context):
        """Show the current queue for this server."""
        if not await self.sense_checks(ctx):
            return

        server_id = ctx.guild.id

        # Add check if server exists in queues
        if server_id not in self.queues:
            await ctx.send("The bot isn't playing anything right now.")
            return

        track_queue = self.queues[server_id].get("queue", [])

        if not track_queue:
            await ctx.send("The bot isn't playing anything right now.")
            return

        def fmt(i_title):
            i, (_, info) = i_title
            title = info.get("title", "Unknown")
            duration = info.get("duration", 0)
            duration_str = time.strftime("%M:%S", time.gmtime(duration)) if duration else "Unknown"

            if i == 0:
                return f"▷ {title} [{duration_str}]\n\n"
            else:
                return f"**{i}:** {title} [{duration_str}]\n"

        queue_items = enumerate(track_queue)
        queue_str = "".join(map(fmt, queue_items))

        # Calculate total duration
        total_duration = sum(info.get("duration", 0) for _, info in track_queue)
        total_duration_str = time.strftime("%H:%M:%S", time.gmtime(total_duration)) if total_duration else "Unknown"

        # Create embed
        embed = discord.Embed(color=self.color, title="Music Queue")
        embed.add_field(name="Now playing:", value=queue_str, inline=False)
        embed.add_field(name="Total duration:", value=total_duration_str, inline=True)
        embed.add_field(name="Tracks in queue:", value=str(len(track_queue)), inline=True)

        # Show loop status
        loop_status = self.queues.get(server_id, {}).get("loop", False)
        embed.add_field(name="Loop:", value="Enabled" if loop_status else "Disabled", inline=True)

        await ctx.send(embed=embed)

    async def handle_skip(self, ctx: commands.Context, args):
        """Skip 1 or more tracks."""
        if not await self.sense_checks(ctx):
            return

        server_id = ctx.guild.id

        # Check if server exists in queues
        if server_id not in self.queues:
            await ctx.send("The bot isn't playing anything.")
            return

        queue_data = self.queues[server_id]
        if not queue_data or not queue_data.get("queue"):
            await ctx.send("The bot isn't playing anything.")
            return

        track_queue = queue_data["queue"]

        # Determine how many tracks to skip
        n_skips = 1
        if args:
            if args[0].isdigit():
                n_skips = int(args[0])
            elif args[0].lower() == "all":
                n_skips = len(track_queue)

        if n_skips >= len(track_queue):
            msg = "Skipping all remaining tracks."
            n_skips = len(track_queue)
        elif n_skips == 1:
            msg = "Skipping track."
        else:
            msg = f"Skipping {n_skips} of {len(track_queue)} tracks."

        await ctx.send(msg)

        # Get voice client
        voice_client = self.get_voice_client_from_channel_id(ctx.author.voice.channel.id)
        if not voice_client:
            await ctx.send("Not connected to a voice channel.")
            return

        self.skip_in_progress.add(server_id)

        # Handle skipping all tracks
        if n_skips >= len(track_queue):
            # Stop current playback
            if voice_client and voice_client.is_playing():
                voice_client.stop()
                await asyncio.sleep(0.5)

            # Store paths to remove
            files_to_remove = [path for path, _ in track_queue]

            # Clear queue
            track_queue.clear()

            # Disconnect
            await voice_client.disconnect()

            # Remove from queues
            self.queues.pop(server_id, None)

            # Remove files
            for path in files_to_remove:
                self._try_remove_file(path)
            return

        # Store paths to remove
        files_to_remove = []

        # Remove tracks from queue
        files_to_remove = []
        for _ in range(n_skips):
            if track_queue:
                path, _ = track_queue.pop(0)
                if all(path != item[0] for item in track_queue):
                    files_to_remove.append(path)

        # If queue is now empty, disconnect
        if not track_queue:
            voice_client.stop()
            await voice_client.disconnect()
            self.queues.pop(server_id, None)

            # Remove files
            for path in files_to_remove:
                self._try_remove_file(path)
            return

        # Otherwise, stop current playback and let the callback handle playing the next track
        if voice_client.is_playing():
            voice_client.stop()

        # Remove files
        for path in files_to_remove:
            self._try_remove_file(path)

    async def handle_play(self, ctx: commands.Context, query: str = None):
        """Play a given search query or URL from YouTube."""
        # Perform basic checks
        if not await self.sense_checks(ctx):
            return

        # Handle resume if no query is provided
        if not query:
            voice_client = self.get_voice_client_from_channel_id(ctx.author.voice.channel.id)
            if voice_client and voice_client.is_paused():
                voice_client.resume()
                await ctx.send("Playback resumed.")
                return
            else:
                await ctx.send("Please provide a song name or URL.")
                return

        query = query.strip()
        if not query:
            await ctx.send("Please provide a song name or URL.")
            return

        server_id = ctx.guild.id

        # Create download directory for this server
        os.makedirs(f"./dl/{server_id}", exist_ok=True)

        # Send a message and store it for later editing
        status_message = await ctx.send(f"Looking for `{query}`...")

        try:
            # Extract info and download
            with yt_dlp.YoutubeDL({
                "format": "bestaudio[ext=webm]/bestaudio",
                "source_address": "0.0.0.0",
                "default_search": "ytsearch",
                "outtmpl": f"./dl/{server_id}/%(id)s.%(ext)s",
                "noplaylist": True,
                "socket_timeout": 10,
                "retries": 3,
                "quiet": True
            }) as ydl:
                # First, extract info without downloading
                info = ydl.extract_info(query, download=False)
                if "entries" in info:
                    if not info["entries"]:
                        await status_message.edit(content="Couldn't find any results for your query.")
                        return
                    info = info["entries"][0]

                # Download the file
                ydl.download([info["webpage_url"]])

            await status_message.edit(content=f"Added to queue: `{info['title']}`")

            path = f"./dl/{server_id}/{info['id']}.{info['ext']}"

            # Verify file exists
            if not os.path.exists(path):
                await status_message.edit(content="Download failed. Please try again.")
                return

            # Insert into the queue
            if server_id not in self.queues:
                self.queues[server_id] = {
                    "queue": [],
                    "loop": False,
                    "volume": 1.0
                }
            track_queue = self.queues[server_id]["queue"]
            track_queue.append((path, info))

            # If this is the only track, start playing
            if len(track_queue) == 1:
                # Connect to voice if not connected
                connection = self.get_voice_client_from_channel_id(ctx.author.voice.channel.id)
                if not connection or not connection.is_connected():
                    try:
                        connection = await ctx.author.voice.channel.connect()
                        await asyncio.sleep(1.0)  # Wait for connection to establish
                    except Exception as e:
                        logger.error(f"Error connecting to voice: {e}")
                        connection = self.get_voice_client_from_channel_id(ctx.author.voice.channel.id)

                if connection and connection.is_connected():
                    # Create audio source
                    audio = discord.FFmpegOpusAudio(
                        path,
                        options="-ac 2 -b:a 96k -vbr on",
                    )

                    # Play the track
                    connection.play(
                        audio,
                        after=lambda e: self._after_track(e, connection, server_id)
                    )
                else:
                    await ctx.send("Failed to connect to voice channel.")

        except Exception as err:
            logger.error(f"Error in play command: {err}")
            await status_message.edit(content=f"An error occurred: {str(err)}")
            if self.print_stack_trace:
                import traceback
                traceback.print_exc()

    async def handle_loop(self, ctx: commands.Context):
        """Toggle looping of the current queue."""
        if not await self.sense_checks(ctx):
            return

        server_id = ctx.guild.id
        if server_id not in self.queues:
            await ctx.send("The bot isn't playing anything.")
            return

        qdata = self.queues[server_id]
        if not qdata or not qdata["queue"]:
            await ctx.send("The bot isn't playing anything.")
            return

        qdata["loop"] = not qdata["loop"]

        # Create embed response
        embed = discord.Embed(
            title="Loop Mode",
            description=f"Looping is now {'**ON**' if qdata['loop'] else '**OFF**'}",
            color=self.color
        )
        await ctx.send(embed=embed)

    async def handle_now_playing(self, ctx: commands.Context):
        """Display information about the currently playing track."""
        if not await self.sense_checks(ctx):
            return

        server_id = ctx.guild.id
        if server_id not in self.queues:
            await ctx.send("The bot isn't playing anything.")
            return

        queue_data = self.queues[server_id]
        if not queue_data or not queue_data.get("queue"):
            await ctx.send("The bot isn't playing anything.")
            return

        # Get current track info
        _, info = queue_data["queue"][0]

        title = info.get("title", "Unknown")
        uploader = info.get("uploader", "Unknown")
        duration = info.get("duration", 0)
        duration_str = time.strftime("%M:%S", time.gmtime(duration)) if duration else "Unknown"
        thumbnail = info.get("thumbnail", None)

        # Create embedded message
        embed = discord.Embed(title="Now Playing", color=self.color)
        embed.add_field(name="Title", value=title, inline=False)
        embed.add_field(name="Uploader", value=uploader, inline=True)
        embed.add_field(name="Duration", value=duration_str, inline=True)

        # Set volume info
        volume = int(queue_data.get("volume", 1.0) * 100)
        embed.add_field(name="Volume", value=f"{volume}%", inline=True)

        # Add thumbnail if available
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        await ctx.send(embed=embed)

    async def handle_pause(self, ctx: commands.Context):
        """Pause the currently playing track."""
        if not await self.sense_checks(ctx):
            return

        voice_client = self.get_voice_client_from_channel_id(ctx.author.voice.channel.id)
        if not voice_client or not voice_client.is_playing():
            await ctx.send("Nothing is playing right now.")
            return

        if voice_client.is_paused():
            await ctx.send("The bot is already paused.")
            return

        voice_client.pause()
        await ctx.send("Playback paused.")

    async def handle_resume(self, ctx: commands.Context):
        """Resume the paused track."""
        if not await self.sense_checks(ctx):
            return

        voice_client = self.get_voice_client_from_channel_id(ctx.author.voice.channel.id)
        if not voice_client:
            await ctx.send("The bot isn't in a voice channel.")
            return

        if not voice_client.is_paused():
            await ctx.send("The bot is not paused.")
            return

        voice_client.resume()
        await ctx.send("Playback resumed.")

    async def handle_volume(self, ctx: commands.Context, volume: str = None):
        """Set the volume level (0-100)."""
        if not await self.sense_checks(ctx):
            return

        server_id = ctx.guild.id
        if server_id not in self.queues:
            await ctx.send("The bot isn't playing anything.")
            return

        queue_data = self.queues[server_id]
        if not queue_data or not queue_data.get("queue"):
            await ctx.send("The bot isn't playing anything.")
            return

        # Show current volume if no argument provided
        if volume is None:
            current_vol = int(queue_data.get("volume", 1.0) * 100)
            await ctx.send(f"Current volume: {current_vol}%")
            return

        # Set new volume if provided
        try:
            vol = int(volume)
            if vol < 0 or vol > 100:
                await ctx.send("Volume must be between 0 and 100.")
                return

            # Update queue data
            queue_data["volume"] = vol / 100.0

            # Update current playback if possible
            voice_client = self.get_voice_client_from_channel_id(ctx.author.voice.channel.id)
            if voice_client and hasattr(voice_client, "source") and hasattr(voice_client.source, "volume"):
                voice_client.source.volume = queue_data["volume"]

            await ctx.send(f"Volume set to {vol}%")

        except ValueError:
            await ctx.send("Please provide a valid number between 0 and 100.")

    async def handle_cleanup(self, ctx: commands.Context):
        """Clean up downloaded files for this server."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("This command requires administrator permissions.")
            return

        server_id = ctx.guild.id
        server_dir = f"./dl/{server_id}"

        # Check if directory exists
        if not os.path.exists(server_dir):
            await ctx.send("No files to clean up.")
            return

        # Don't remove files that are in the current queue
        queue_files = set()
        if server_id in self.queues and self.queues[server_id].get("queue"):
            queue_files = {item[0] for item in self.queues[server_id]["queue"]}

        # Count files that will be removed
        files_removed = 0
        for file_path in Path(server_dir).glob("*"):
            if str(file_path) not in queue_files:
                try:
                    os.remove(file_path)
                    files_removed += 1
                except (PermissionError, FileNotFoundError) as e:
                    logger.warning(f"Failed to remove {file_path}: {e}")

        await ctx.send(f"Cleaned up {files_removed} files.")

    async def handle_help(self, ctx: commands.Context):
        """Show help information."""
        commands_list = [
            (f"{self.prefix}play [query]", "Play a song from YouTube"),
            (f"{self.prefix}queue", "Show the current music queue"),
            (f"{self.prefix}skip [n]", "Skip a number of tracks"),
            (f"{self.prefix}nowplaying", "Show information about the current track"),
            (f"{self.prefix}pause", "Pause the current track"),
            (f"{self.prefix}resume", "Resume playback"),
            (f"{self.prefix}volume [0-100]", "Set the playback volume"),
            (f"{self.prefix}loop", "Toggle queue looping"),
            (f"{self.prefix}cleanup", "Clean up downloaded files (admin only)")
        ]

        embed = discord.Embed(
            title="Music Bot Help",
            description="Here are the available commands:",
            color=self.color
        )

        for command, description in commands_list:
            embed.add_field(name=command, value=description, inline=False)

        await ctx.send(embed=embed)

    # Add this method to your MusicBot class:
    async def handle_ayuda(self, ctx: commands.Context):
        """Show help information in Spanish."""
        commands_list = [
            (f"{self.prefix}play, {self.prefix}p", "Reproduce una canción de YouTube. Puedes agregar una busqueda o una URL. Por ejemplo .play aire jose merce, o .play https://www.youtube.com/watch?v=xzxyefhCQXg, ambas combinaciones funcionan"),
            (f"{self.prefix}queue, {self.prefix}lista, {self.prefix}q", "Muestra la cola de reproducción actual"),
            (f"{self.prefix}skip, {self.prefix}s, {self.prefix}siguiente, {self.prefix}pasar, {self.prefix}next [n]",
             "Salta una o más canciones, por ejemplo si la lista tiene 10 canciones y quieres pasar a la cuarta, .siguiente 3, esto salta 3 canciones"),
            (f"{self.prefix}nowplaying, {self.prefix}np, {self.prefix}sonando",
             "Muestra información sobre la canción actual"),
            (f"{self.prefix}pause, {self.prefix}pa, {self.prefix}parar, {self.prefix}pausa", "Pausa la canción actual"),
            (f"{self.prefix}resume, {self.prefix}r, {self.prefix}continuar, {self.prefix}unpausar",
             "Reanuda la reproducción"),
            (f"{self.prefix}volume, {self.prefix}v [0-100]", "Ajusta el volumen de reproducción"),
            (f"{self.prefix}loop, {self.prefix}l", "Activa/desactiva la reproducción en bucle"),
            (f"{self.prefix}cleanup, {self.prefix}clean", "Limpia los archivos descargados (solo administradores)")
        ]

        embed = discord.Embed(
            title="Ayuda del Bot de Música",
            description="Aquí están los comandos disponibles:",
            color=self.color
        )

        for command, description in commands_list:
            embed.add_field(name=command, value=description, inline=False)

        await ctx.send(embed=embed)

    async def handle_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle errors gracefully."""
        # If command doesn't exist
        if isinstance(error, commands.CommandNotFound):
            if self.report_command_not_found:
                await ctx.send(f"Command not recognized. Type `{self.prefix}help` to see commands.")
            return

        # Otherwise log the error
        if self.print_stack_trace:
            import traceback
            traceback.print_exc()

        logger.error(f"Command error: {error}")
        await ctx.send("An unexpected error occurred. Check logs for details.")

    async def handle_voice_state_update(self, member: discord.Member, before: discord.VoiceState,
                                        after: discord.VoiceState):
        """Handle voice state changes."""
        if member != self.bot.user:
            return

        # Bot joined a channel
        if before.channel is None and after.channel is not None:
            return

            # Bot left a channel
        if before.channel is not None and after.channel is None:
            server_id = before.channel.guild.id

            # Clean up data
            self.queues.pop(server_id, None)
            self.skip_in_progress.discard(server_id)  # Clear skip flag

            # Clean up downloads for this server in a separate task
            server_dir = f"./dl/{server_id}/"
            if os.path.exists(server_dir):
                self.bot.loop.create_task(self._delayed_directory_cleanup(server_dir))

    # -----------------------------------------------------------------
    #                    PLAYBACK & HELPER METHODS
    # -----------------------------------------------------------------

    def _after_track(self, error, connection, server_id):
        """Called after a track finishes."""
        if error:
            logger.error(f"Playback error: {error}")

        # Run after_track_async in event loop
        asyncio.run_coroutine_threadsafe(
            self._after_track_async(error, connection, server_id),
            self.bot.loop
        )

    async def _after_track_async(self, error, connection, server_id):
        """Async version of after_track to properly handle async operations."""
        try:
            # Wait briefly for system to stabilize
            await asyncio.sleep(0.5)

            # Check if server still in queues
            if server_id not in self.queues:
                logger.info(f"Server {server_id} no longer in queues, ending playback")
                self.skip_in_progress.discard(server_id)  # Clear flag
                return

            # Check if connection is still valid
            if not connection or not hasattr(connection, 'is_connected') or not connection.is_connected():
                logger.warning("Connection no longer valid")
                self.queues.pop(server_id, None)
                return

            track_queue = self.queues[server_id]["queue"]
            loop_enabled = self.queues[server_id]["loop"]

            if not track_queue:
                # Empty queue - disconnect
                logger.info("Queue empty, disconnecting")
                await connection.disconnect()
                self.queues.pop(server_id, None)
                return

            # Get current track before modifying queue
            current_track = track_queue[0]
            last_path = current_track[0]

            # Check if skip is in progress
            is_skip = server_id in self.skip_in_progress
            if is_skip:
                # Clear the skip flag
                self.skip_in_progress.discard(server_id)
                logger.info("Skip in progress, not removing track from queue")
            else:
                # Only remove track if NOT a skip operation and not looping
                if not loop_enabled:
                    track_queue.pop(0)

            # If queue is now empty, disconnect
            if not track_queue:
                logger.info("No more tracks, disconnecting")
                await connection.disconnect()
                self.queues.pop(server_id, None)

                # Clean up the last file
                if not loop_enabled:
                    self._try_remove_file(last_path)
                return

            # Check if we should remove the last file
            if not loop_enabled and all(last_path != item[0] for item in track_queue):
                self._try_remove_file(last_path)

            # Get next track
            next_path = track_queue[0][0]

            # Check if file exists
            if not os.path.exists(next_path):
                logger.error(f"File not found: {next_path}")
                track_queue.pop(0)

                if track_queue:
                    # Try next track
                    await self._after_track_async(None, connection, server_id)
                else:
                    # No more tracks
                    await connection.disconnect()
                    self.queues.pop(server_id, None)
                return

            # Wait a moment to ensure clean state
            await asyncio.sleep(0.5)

            # Try to play next track
            try:
                audio = discord.FFmpegOpusAudio(
                    next_path,
                    options="-ac 2 -b:a 96k -vbr on",
                )

                connection.play(
                    audio,
                    after=lambda e: self._after_track(e, connection, server_id)
                )
            except Exception as e:
                logger.error(f"Error playing next track: {e}")
                # Try to recover
                track_queue.pop(0)
                if track_queue:
                    await self._after_track_async(None, connection, server_id)
                else:
                    await connection.disconnect()
                    self.queues.pop(server_id, None)

        except Exception as err:
            logger.error(f"Error in _after_track_async: {err}")
            # Try to disconnect
            try:
                if connection and connection.is_connected():
                    await connection.disconnect()
                self.queues.pop(server_id, None)
            except:
                pass

    async def _delayed_directory_cleanup(self, directory_path, delay=5.0):
        """Clean up a directory after a delay to avoid file lock issues."""
        try:
            await asyncio.sleep(delay)
            if os.path.exists(directory_path):
                # First try to remove individual files
                for file_path in Path(directory_path).glob("*"):
                    try:
                        os.remove(file_path)
                    except:
                        pass

                # Then try to remove the directory
                try:
                    shutil.rmtree(directory_path)
                except Exception as e:
                    logger.warning(f"Failed to remove directory {directory_path}: {e}")
        except Exception as e:
            logger.error(f"Error in directory cleanup: {e}")

    def _try_remove_file(self, path: str):
        """Try to remove a file, with retries."""
        for _ in range(5):
            try:
                if os.path.exists(path):
                    os.remove(path)
                return True
            except (PermissionError, FileNotFoundError):
                time.sleep(1)
        return False

    async def _safe_disconnect(self, connection: discord.VoiceClient):
        """Gracefully disconnect if still connected."""
        try:
            if connection and hasattr(connection, 'is_connected') and connection.is_connected():
                # Stop any playing audio first
                if connection.is_playing() or connection.is_paused():
                    connection.stop()

                # Wait a moment for ffmpeg processes to terminate
                await asyncio.sleep(0.5)

                # Now disconnect
                await connection.disconnect()
        except Exception as e:
            logger.error(f"Error in safe disconnect: {e}")

    async def _notify_about_failure(self, ctx: commands.Context, err: yt_dlp.utils.DownloadError, status_message=None):
        """Handle download errors."""
        if self.report_dl_error:
            sanitized = re.compile(r"\x1b[^m]*m").sub("", err.msg).strip()
            if sanitized.lower().startswith("error"):
                sanitized = sanitized[5:].strip(" :")

            error_msg = f"Failed to download due to error: {sanitized}"
            if status_message:
                await status_message.edit(content=error_msg)
            else:
                await ctx.send(error_msg)
        else:
            error_msg = "Sorry, failed to download this video."
            if status_message:
                await status_message.edit(content=error_msg)
            else:
                await ctx.send(error_msg)

    def get_voice_client_from_channel_id(self, channel_id: int):
        """Return the voice client connected to `channel_id`, or None."""
        for vc in self.bot.voice_clients:
            if vc.channel and vc.channel.id == channel_id:
                return vc
        return None

    async def sense_checks(self, ctx: commands.Context) -> bool:
        """Perform basic checks for voice commands."""
        author_voice = ctx.author.voice
        if not author_voice:
            await ctx.send("You must be in a voice channel to use this command.")
            return False

        # Check if bot is in a channel at all
        vc = self.get_voice_client_from_channel_id(author_voice.channel.id)

        # If the bot isn't in the user's channel, but is playing somewhere else
        if vc and vc.channel != author_voice.channel:
            await ctx.send("You must be in the same voice channel as the bot.")
            return False

        return True

    def run(self):
        """Start the bot."""
        if not self.token:
            logger.error("No token provided. Please put BOT_TOKEN in .env")
            sys.exit(1)

        try:
            self.bot.run(self.token)
        except discord.LoginFailure:
            logger.error("Invalid token. Check your BOT_TOKEN in .env")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            if self.print_stack_trace:
                import traceback
                traceback.print_exc()
            sys.exit(1)


# -----------------------------------------------------------------
#                          MAIN FUNCTION
# -----------------------------------------------------------------
def main():
    """Main entry point for the bot."""
    bot = MusicBot()
    bot.run()


if __name__ == "__main__":
    main()