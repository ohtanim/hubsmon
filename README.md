# Mozilla Hubs - Presence monitor

When you hold events in Mozilla Hubs rooms, this tool will help you if you want to know the following:
1. How many participants in the room or lobby
2. How many participants who use mobile device to acccess
3. How many participants who use HMD device to access
4. Time change of the number of participants at constant intervals.
5. Presence event log for each participant

## Prerequisites
* Python 3.7 or above

## Setup
```bash
pip install -r requirements.txt
```

## WebSocket protocol
hubsmon.py will establish the websocket connection to the reticulum.io server and monitor the following 2 types of incoming message to know the current status of presense.
### presence_state
```bash
[
  null,
  null,
  "hub:M9mbZkM",
  "presence_state",
  {
    "8a879467-c5d8-4e58-a319-3c2cd630e44e": {
      "metas": [
        {
          "context": {
            "embed": false,
            "mobile": false
          },
          "permissions": {
            "close_hub": false,
            "embed_hub": false,
            "fly": false,
            "join_hub": true,
            "kick_users": false,
            "mute_users": false,
            "pin_objects": true,
            "spawn_and_move_media": true,
            "spawn_camera": true,
            "spawn_drawing": false,
            "spawn_emoji": true,
            "update_hub": false,
            "update_hub_promotion": false,
            "update_roles": false
          },
          "phx_ref": "tHv+IR5+3Yo=",
          "presence": "lobby",
          "profile": {
            "avatarId": "gVgSB4W",
            "displayName": "Presence Monitor"
          },
          "roles": {
            "creator": false,
            "owner": false,
            "signed_in": false
          }
        }
      ]
    }
  }
]
```
### presence_diff
```bash
[
  null,
  null,
  "hub:M9mbZkM",
  "presence_diff",
  {
    "joins": {},
    "leaves": {
      "94e42cad-7516-4268-ab7f-d676b920d1e3": {
        "metas": [
          {
            "context": {
              "embed": false,
              "mobile": false
            },
            "permissions": {
              "close_hub": false,
              "embed_hub": false,
              "fly": false,
              "join_hub": true,
              "kick_users": false,
              "mute_users": false,
              "pin_objects": true,
              "spawn_and_move_media": true,
              "spawn_camera": true,
              "spawn_drawing": false,
              "spawn_emoji": true,
              "update_hub": false,
              "update_hub_promotion": false,
              "update_roles": false
            },
            "phx_ref": "GSAOswK+dbQ=",
            "phx_ref_prev": "nD7SwKRXDEY=",
            "presence": "room",
            "profile": {
              "avatarId": "8DugdXZ",
              "displayName": "Ringed-Teal-15373"
            },
            "roles": {
              "creator": false,
              "owner": false,
              "signed_in": false
            }
          }
        ]
      }
    }
  }
]
```

### How to start monitor
You need to create a json file which contains a list of rooms to be monitored like below. See rooms.json as reference.

```bash
{
    "rooms": [
        "https://hubs.mozilla.com/jccsqWd/tec-j-annual-poster-room-1",
        "https://hubs.mozilla.com/wo3JVKv/tec-j-annual-poster-room-2",
        "https://hubs.mozilla.com/K5n4WCC/tec-j-annual-poster-room-3",
        "https://hubs.mozilla.com/oZWYyum/tec-j-annual-poster-room-4",
        "https://hubs.mozilla.com/LPqiUdf/tec-j-annual-poster-room-5",
        "https://hubs.mozilla.com/dy7xeYh/tec-j-annual-poster-room-6",
        "https://hubs.mozilla.com/8RmG9Nf/tec-j-annual-poster-room-7"
    ]
}
```

Then, run this monitor tool like below:
```bash
% python hubsmon.py -h
usage: hubsmon.py [-h] [-n NAME] rooms_file

hubsmon - A tool to monitor the presence status of each Mozilla Hubs rooms.

positional arguments:
  rooms_file            a JSON file contains a list of room URLs.

optional arguments:
  -h, --help            show this help message and exit
  -n NAME, --name NAME  display name of monitor (optional)

```
For example, 
```bash
python hubsmon.py rooms.json -n "Event monitor"
```

This monitor program will print the presence events on the console like below. 

```bash
2020-11-21 02:16:41 jccsqWd Common-Shelduck-19971  ['mobile'] joins lobby
2020-11-21 02:16:55 jccsqWd Common-Shelduck-19971  ['mobile'] joins room
2020-11-21 02:16:55 jccsqWd Common-Shelduck-19971  ['mobile'] leaves lobby
2020-11-21 02:17:27 jccsqWd Common-Shelduck-19971  ['mobile'] leaves room
```

Columns are:
* event timestamp
   * YYYY-MM-DD hh:mm:ss formated string
* hub_id
   * You know hub_id from your hubs room URL. For example, 'jccsqWd' is <hub_id> in the following URL: https://hubs.mozilla.com/jccsqWd/tec-j-annual-poster-room-1
* user's display name
   * display name specified when selecting avator at login time.
* device types 
   * mobile: participant uses mobile device such as iPhone to access. 
   * hmd: participant uses head-mount display such as Oculus Quest to access.
   * empty array indicates participant uses PC browser (including iPad) to access.
* event name
   * in: already in that place.
   * joins: joins to that place.
   * leaves: leaves from that place.
* place where this event occurred. Mozilla hubs have 2 types of place like below.
   * lobby: Hubs lobby
   * room: Hubs room
  
This monitor program will also generate a CSV file (filename is <hub_id>.csv) under the current directory. This file will contain the presence events like below, send from hubs websocket server. 

```bash
"Timestamp","Display name","Event type","Room or lobby","Access from HMD","Access from Mobile"
"2020-11-13 14:50:30","Presence Monitor","joins","lobby","False","False"
"2020-11-13 14:50:30","Presence Monitor","in","lobby","False","False"
"2020-11-13 15:21:08","Common-Shelduck-19971","joins","lobby","False","False"
"2020-11-13 15:21:21","Common-Shelduck-19971","joins","lobby","False","False"
"2020-11-13 15:21:21","Common-Shelduck-19971","leaves","lobby","False","False"
"2020-11-13 15:21:24","Common-Shelduck-19971","joins","lobby","False","False"
"2020-11-13 15:21:24","Common-Shelduck-19971","leaves","lobby","False","False"
"2020-11-13 15:21:27","Common-Shelduck-19971","joins","room","False","False"
"2020-11-13 15:21:27","Common-Shelduck-19971","leaves","lobby","False","False"
"2020-11-13 15:21:47","Common-Shelduck-19971","leaves","room","False","False"
```

### How to stop monitor

Ctrl + C on the console where this monitor program is running.

## References
* mozilla hubs (https://hubs.mozilla.com/)
