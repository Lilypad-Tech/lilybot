import os
import random
import subprocess
import datetime
import time
import asyncio
import aiohttp
from dotenv import load_dotenv
from pathlib import Path
import discord
from discord.ext import commands, tasks

# Load environment variables
load_dotenv()
web3_private_key = os.getenv('WEB3_PRIVATE_KEY')
discord_token = os.getenv('DISCORD_TOKEN')
discord_channel_id = int(os.getenv('DISCORD_CHANNEL_ID'))
heartbeat_url = os.getenv('HEARTBEAT_URL')
personality = os.getenv('PERSONALITY')

# Initialize counters
success_count, fail_count = 0, 0
last_success_count, last_fail_count = 0, 0
late_job = False

# Set up the Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='>', intents=intents)

@bot.event
async def on_ready():
    global channel
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    channel = bot.get_channel(discord_channel_id)
    msg = "Lilybot is now running!"
    print("Loading personality core.")
    if personality:
        msg += " " + personality
    print("Sending msg: " + msg)
    await channel.send(msg)
    asyncio.create_task(run_lilypad())  # Start lilypad task concurrently
    report_stats.start()  # Start scheduled reporting

async def send_heartbeat():
    async with aiohttp.ClientSession() as session:
        async with session.post(heartbeat_url) as response:
            if response.status == 200:
                print('Heartbeat sent successfully')
            else:
                print(f'Failed to send heartbeat. Status code: {response.status}')

@tasks.loop(hours=12)
async def report_stats():
    global last_success_count, last_fail_count

    # Calculate total successes and failures
    total_count = success_count + fail_count
    success_rate = success_count / total_count * 100 if total_count > 0 else 0

    # Calculate successes and failures since the last report
    recent_successes = success_count - last_success_count
    recent_fails = fail_count - last_fail_count
    recent_total = recent_successes + recent_fails
    recent_success_rate = recent_successes / recent_total * 100 if recent_total > 0 else 0

    msg = f"[SDXL] Hey Lilycrew! It's been 12 hours, here are our new stats:\n" \
          f"🚀 Overall success rate: {success_rate:.2f}% ({success_count}/{total_count})\n" \
          f"📖 Last 12 hours success rate: {recent_success_rate:.2f}% ({recent_successes}/{recent_total})"
    print("Sending msg: " + msg)
    await channel.send(msg)

    # Update last counters
    last_success_count = success_count
    last_fail_count = fail_count

@report_stats.before_loop
async def before_report_stats():
    print("Initial delay for 12 hours before starting the report_stats loop.")
    await asyncio.sleep(43200)  # Sleep for 12 hours (12 hours * 3600 seconds/hour)

async def run_lilypad():
    global success_count, fail_count, channel, late_job

    while True:  # Loop continuously
        # Print the current date and time in UTC
        utc_now = datetime.datetime.utcnow()
        print(f"[SDXL] Current date and time in UTC: {utc_now}")

        # Generate five random words and combine them into a single string
        with open('/usr/share/dict/words', 'r') as file:
            words = random.sample(file.read().splitlines(), 5)
        random_words = ' '.join(words).replace("'", "")
        print(f"[SDXL] Generated words: {random_words}")

        # Start the timer
        start_time = datetime.datetime.now()

        # Run lilypad with the generated words
        print("[SDXL] Running lilypad with generated words...")
        cmd = f"lilypad run sdxl-pipeline:v1.0-base-lilypad3 -i Prompt='{random_words}' -i Seed=42"
        # Run the command asynchronously
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={"WEB3_PRIVATE_KEY": web3_private_key}
        )

        # Set up timers for warning and timeout
        warning_timeout = 600  # 10 minutes in seconds
        max_timeout = 1200  # 20 minutes in seconds
        warning_sent = False

        while True:
            try:
                await asyncio.wait_for(process.wait(), timeout=1)
                break  # Process completed within 1 second check
            except asyncio.TimeoutError:
                elapsed_time = datetime.datetime.now() - start_time
                elapsed_seconds = elapsed_time.total_seconds()

                if elapsed_seconds > warning_timeout and not warning_sent:
                    # Job has run for over 10 minutes and warning has not been sent yet
                    msg = f"[SDXL] WARNING: Job running for over 10 minutes. Elapsed time: {elapsed_time}"
                    print("Sending msg: " + msg)
                    await channel.send(msg)
                    warning_sent = True
                    # Mark the job as late
                    late_job = True

                if elapsed_seconds > max_timeout:
                    # Job has exceeded the maximum timeout (20 minutes)
                    msg = f"[SDXL] ERROR: Job exceeded maximum timeout of 20 minutes. TERMINATING the job. Elapsed time: {elapsed_time}"
                    print("Sending msg: " + msg)
                    await channel.send(msg)
                    process.kill()  # Kill the job process
                    exit_code = 1337
                    time.sleep(10)
                    break

        # Stop the timer
        end_time = datetime.datetime.now()
        duration = end_time - start_time

        # Check the exit code and validate output
        success, cid = False, ''
        if exit_code == 0:
            output_lines = stdout.decode().splitlines()
            for line in output_lines:
                if "open" in line:
                    path = line.split()[1]  # Extract the path
                    cid = path.split('/')[-1]  # Extract CID from the path
                    if Path(path).exists():
                        outputs_dir = Path(f"{path}/outputs")
                        if outputs_dir.is_dir():
                            png_files = list(outputs_dir.glob("*.png"))
                            if png_files and all(file.stat().st_size > 0 for file in png_files):
                                exit_code_path = Path(f"{path}/exitCode")
                                if exit_code_path.is_file() and exit_code_path.read_text().strip() == '0':
                                    success = True
                                    break  # Exit for loop on first success

            if success:
                success_count += 1
                msg = f"[SDXL] SUCCESS [{success_count}/{success_count + fail_count} succeeded] {cid} [Time taken: {duration}]"
                print(msg)
                if late_job:
                    msg = f"[SDXL] WARNING: {cid} was late."
                    print(msg)
                # In debug mode, we should output even during successful runs
                # await channel.send(msg)
                asyncio.create_task(send_heartbeat())
                time.sleep(1)
                late_job = False
            else:
                fail_count += 1
                msg = f"[SDXL] FAIL [validation failed] [{success_count}/{success_count + fail_count} succeeded] [Time taken: {duration}]"
                print("Sending msg: " + msg)
                await channel.send(msg)
                time.sleep(1)
                late_job = False
        else:
            fail_count += 1
            msg = f"[SDXL] FAIL [exit code: {exit_code}] [{success_count}/{success_count + fail_count} succeeded] [Time taken: {duration}]"
            if exit_code == 1337:
                msg += "\n This job timed out and was forcibly killed. [FAIL]"
            print("Sending msg: " + msg)
            await channel.send(msg)
            time.sleep(3)
            late_job = False

# Run the lilypad task and the Discord bot concurrently
async def main():
    # asyncio.create_task(run_lilypad())
    await bot.start(discord_token)

if __name__ == '__main__':
    asyncio.run(main())
