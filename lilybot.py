import os
import random
import subprocess
import datetime
import time
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()
web3_private_key = os.getenv('WEB3_PRIVATE_KEY')

# Initialize counters
success_count, fail_count = 0, 0

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
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env={"WEB3_PRIVATE_KEY": web3_private_key})
    stdout, stderr = process.communicate()
    exit_code = process.returncode

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
            print(f"[SDXL] SUCCESS [{success_count}/{success_count + fail_count} succeeded] {cid} [Time taken: {duration}]")
            time.sleep(1)
        else:
            fail_count += 1
            print(f"[SDXL] FAIL [validation failed] [{success_count}/{success_count + fail_count} succeeded] [Time taken: {duration}]")
            time.sleep(1)
    else:
        fail_count += 1
        print(f"[SDXL] FAIL [exit code: {exit_code}] [{success_count}/{success_count + fail_count} succeeded] [Time taken: {duration}]")
        time.sleep(3)

