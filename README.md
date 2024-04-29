# usage
* Install python3-pip
* Create a user, lilypad-test
* Become that user
`pip3 install discord.py --break-system-packages`
* Copy .env.example to .env and fill it out

Then:

in screen or tmux, run

`python3 -u lilybot.py | tee /var/log/lilypad-test/out-sdxl.log`

Or copy the systemd unit to /etc/systemd/system/lilybot.service && `systemctl enable --now lilybot`

Done!

Bonus points: Set up Vector logging.
