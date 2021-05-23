![](assets/shadowhawk.png)

# ShadowHawk

An overseeing userbot that has multiple accounts and a slave attached

## Features

 - Advanced logging of many events on telegram
 - Multi-account capable
 - Query most anti-spam organizations on telegram
 - Advanced administrative tools for group moderation
 - Useful commands to query wikipedia, urban dictionary, google translate, or convert from metric to imperial

### Installation Instructions
1. Install:
    - `python3` (this is in python after all)
    - `postgresql` (or similar async-capable database)
2. `pip3 install -r requirements.txt`
3. Copy example-config.yaml to config.yaml and edit it
4. `mkdir sessions`

No this cannot be deployed to heroku, yes you need a database.

### Start
`python3 -m shadowhawk`  
After that, send .help somewhere and have fun :D

### Extras
There are extra modules more specific to me that may interest developers and advanced users. They can be found [here](https://gitlab.com/Justasic/shadowhawk-extras).

### Bugs/Support/Whatever
Join my [personal chat](https://t.me/NightShadowsHangout) I guess

## Special Thanks
 - [Kneesocks](https://gitlab.com/blankX/): [Original implementation](https://gitlab.com/blankX/sukuinote) and help along the way
 - [Dank-del](https://gitlab.com/Dank-del): For giving me ideas and helping out