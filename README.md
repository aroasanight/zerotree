# zerotree

# setup

this guide assumes you're using a pi zero for simplicity's sake - feel free to adapt this guide and the code to your specific pi/device. if you don't know what you're doing enough to do that then why are you even making a christmas tree with addressable lights

1. using raspberry pi imager, flash the latest version of raspbian lite onto your SD card. set it up with a hostname, your wifi SSID and password, a username and password, and enable SSH so you can SSH in without having to hook up to a monitor. I'll assume username `garlicbread` and hostname `zerotree` since that's what i'm using (if you choose something different, keep in mind to sub `garlicbread` for your username and `zerotree` for your hostname in all commands/text input boxes etc.)

2. wait. it's a pi zero it has like a 500mhz cpu so just go do... something else for a bit. i'll be using termius to connect so maybe get that downloaded and get yourself an account whilst you're waiting.

3. in termius, create a new host. set IP/Hostname to `zerotree`, and under credentials enter username `garlicbread` but not the password.

4. DON'T CONNECT YET - head to the keychain tab, and generate a new key. call it whatever you want - i'll use `zerotree key` for simplicity.

5. once generated, hit the "export to host" button and export it to the `zerotree` host which you created earlier. hit export, and when prompted for a password, enter it but hit continue instead of continue and save. this can take some time if you're using a hostname instead of a direct IP.

6. head back to the hosts page and connect. if asked for a password - hit the keys button instead, select the key and hit connect & save (yes, hit save this time). again this may take some time.

7. run `sudo nano /etc/ssh/sshd_config`. edit the following:
 - uncomment `PermitRootLogin` and change to `no`
 - uncomment `PasswordAuthentication` and change to `no`
 - set `UsePAM` to `no`

8. exit with ctrl+x, hit y to save changes and enter to save with the same filename.

9. run `sudo service sshd restart` to apply changes

10. run `sudo apt-get update && sudo apt-get upgrade`

11. run `sudo apt-get install samba git python3-pip python3-dev build-essential -y`

12. install python libraries with `sudo pip3 install rpi_ws281x adafruit-circuitpython-neopixel psutil flask --break-system-packages`

13. clone the repo with `git clone https://github.com/aroasanight/zerotree.git`

14. if your username is NOT `garlicbread`, run `sudo nano zerotree/setup/zerotree.service` and change all references of the home folder to point to your home folder.

15. run `sudo cp webserver_new/setup/zerotree.service /etc/systemd/system/zerotree.service`

16. reload services with `sudo systemctl daemon-reload`

17. enable the service with `sudo systemctl enable zerotree.service`

18. ...and start the service with `sudo systemctl start zerotree.service`

19. connect the lights using the following diagram. for coordinates - i can't be bothered right now to fix those scripts up so for now just have a play with `coordinate_finder_CAM.py` and `coordinate_finder_LED.py` in the `zerotree/setup` folder and throw the output into `zerotree/app.py`. will get to this at some point... in the next 5 years

![pin diagram photo](https://raw.githubusercontent.com/aroasanight/zerotree/refs/heads/main/setup/hdpind.jpg)