# homismart-client Architecture

## System Overview

```
+-----------------------------------------------------------------------------------+
|  Home Assistant (ha-homismart integration)                                        |
|                                                                                   |
|  +------------------+     +-------------------+     +--------------------------+  |
|  | config_flow.py   |     | coordinator.py    |     | Platforms                |  |
|  | (validates creds)|     | (event bridge)    |---->| light.py / cover.py /   |  |
|  +--------+---------+     +--------+----------+     | switch.py               |  |
|           |                        |                 +--------------------------+  |
+-----------+------------------------+----------------------------------------------+
            |                        |
            v                        v
+-----------------------------------------------------------------------------------+
|  homismart-client library                                                         |
|                                                                                   |
|  +----------------------------------+                                             |
|  | HomismartClient                  |  <--- Main entry point                      |
|  |                                  |                                             |
|  |  connect()  -----> WebSocket ----|-------> wss://prom.homismart.com:443        |
|  |  disconnect()      connection    |              /homismartmain/websocket        |
|  |  send_command_raw()              |                                             |
|  |                                  |                                             |
|  |  +-----------+  +------------+   |                                             |
|  |  | _login()  |  | _receive   |   |                                             |
|  |  |           |  | _loop()    |   |                                             |
|  |  +-----------+  +-----+------+   |                                             |
|  |                       |          |                                             |
|  |  +------------+       |          |                                             |
|  |  | _send      |       |          |                                             |
|  |  | _heartbeats|       |          |                                             |
|  |  +------------+       |          |                                             |
|  +-----------------------+----------+                                             |
|                          |                                                        |
|                          v                                                        |
|  +----------------------------------+                                             |
|  | HomismartSession                 |  <--- State & event management              |
|  |                                  |                                             |
|  |  dispatch_message(prefix, data)  |                                             |
|  |        |                         |                                             |
|  |        +---> "0003" login resp   |                                             |
|  |        +---> "0005" device list  |                                             |
|  |        +---> "0009" device push  |                                             |
|  |        +---> "9999" server error |                                             |
|  |        +---> "0039" redirect     |                                             |
|  |                                  |                                             |
|  |  _devices: {id: Device}          |                                             |
|  |  _hubs:    {id: Hub}             |                                             |
|  |  _event_listeners: {name: [...]} |                                             |
|  +-----------+----------------------+                                             |
|              |                                                                    |
|              v                                                                    |
|  +----------------------------------+    +-------------------+                    |
|  | Devices                          |    | HomismartCommand  |                    |
|  |                                  |    | Builder           |                    |
|  |  HomismartDevice (base)          |    |                   |                    |
|  |    +-- SwitchableDevice          |    | _build_message()  |                    |
|  |    |     turn_on/off/toggle()    |    | prefix + JSON     |                    |
|  |    +-- CurtainDevice             |    +-------------------+                    |
|  |    |     set_level/open/close()  |                                             |
|  |    +-- LockDevice                |                                             |
|  |    |     lock/unlock()           |                                             |
|  |    +-- HomismartHub              |                                             |
|  +----------------------------------+                                             |
+-----------------------------------------------------------------------------------+
```

## Connection Lifecycle

```
  connect() called
       |
       v
  +--------------------+
  | while _keep_running|<------------------------------------------+
  +--------+-----------+                                           |
           |                                                       |
           v                                                       |
  websockets.connect()                                             |
  (open_timeout=10s)                                               |
           |                                                       |
     +-----+------+                                                |
     |            |                                                |
   success     failure ----> log error ---> sleep(10-20s) ---------+
     |                                                             |
     v                                                             |
  _on_open()                                                       |
     |                                                             |
     +---> _login()  -------> SEND "0002" {username, md5(pass)}    |
     |                                                             |
     +---> _send_heartbeats() started as background task           |
     |       (every 30s if idle)                                   |
     |                                                             |
     v                                                             |
  _receive_loop()                                                  |
     |                                                             |
     |  async for message in websocket:                            |
     |     parse prefix + JSON                                     |
     |     session.dispatch_message()                              |
     |                                                             |
     +--- on disconnect/error -----> cleanup ---> sleep(10s) ------+
```

## Message Protocol

```
  All messages: [4-char prefix][JSON payload]

  ============ OUTGOING (Client -> Server) ============

  "0002" LOGIN        {"username": "...", "password": "md5hash"}
  "0004" LIST_DEVICES {}
  "0006" TOGGLE_PROP  {full device state with updated fields}
  "0014" DELETE       {"devid": "..."}
  "0016" MODIFY       {"devid": "...", "name": "...", ...}
  "0030" SET_LED      {"devid": "...", "ledDevice": 0-100}
  "0072" HEARTBEAT    {}
  "0144" CURTAIN_CAL  {"deviceSN": "...", "closedPosition": 1-10}
  "0222" ACCEPT_TOS   {}

  ============ INCOMING (Server -> Client) ============

  "0003" LOGIN_RESP   {"result": true/false}
  "0005" DEVICE_LIST  [{device}, {device}, ...]
  "0009" DEVICE_PUSH  {single device state}
  "0013" ADD_RESP     {"result": true/false, "status": {...}}
  "0015" DELETE_RESP  {"result": true/false, "status": {"id": "..."}}
  "0039" REDIRECT     {"ip": "...", "port": "..."}
  "9999" ERROR        {"code": N, "info": "..."}
```

## Event Flow (Device Command)

```
  User calls device.turn_on()
       |
       v
  SwitchableDevice.turn_on()
       |
       +---> _execute_control_command({power: true, lastOn: now})
                  |
                  +---> merge into full device state
                  +---> set updateTime = now (ms)
                  +---> session._send_command_for_device()
                              |
                              +---> map "toggle_property" -> "0006"
                              +---> client.send_command_raw("0006", payload)
                                         |
                                         +---> CommandBuilder._build_message()
                                         +---> websocket.send("0006{...}")
                                                    |
                                              [ HomiSmart Cloud ]
                                                    |
                                              server sends back "0009"
                                                    |
                                         _receive_loop() picks it up
                                                    |
                                         session.dispatch_message("0009", data)
                                                    |
                                         _handle_device_update_push()
                                                    |
                                         device.update_state(new_data)
                                                    |
                                         emit("device_updated", device)
                                                    |
                                         HA coordinator._handle_device_update()
                                                    |
                                         dispatcher signal -> entity.async_write_ha_state()
                                                    |
                                         HA UI updates
```

## Device Type Hierarchy

```
  HomismartDevice (base)
  |-- id, name, is_online, is_on, pid, version
  |-- update_state(), set_name(), set_icon(), delete()
  |
  +-- SwitchableDevice
  |     Types: SOCKET(1), SWITCH(2), MULTI_GANG(6), DOUBLE(7), SOCKET_ALT(8)
  |     Methods: turn_on(), turn_off(), toggle()
  |
  +-- CurtainDevice
  |     Types: SHUTTER(4), CURTAIN(5)
  |     Methods: set_level(), open_fully(), close_fully(), stop()
  |     Props: current_level (0=open, 100=closed)
  |
  +-- LockDevice
  |     Types: DOOR_LOCK(9)
  |     Methods: lock_device(), unlock_device()
  |     Props: is_locked
  |
  +-- HomismartHub
        IDs starting with "00"
        Represents the physical hub/main unit
```

## Session Event System

```
  session._event_listeners = {
      "session_authenticated": [callback, ...],
      "session_error":         [callback, ...],
      "new_device_added":      [callback, ...],
      "device_updated":        [callback, ...],
      "device_deleted":        [callback, ...],
      "new_hub_added":         [callback, ...],
      "hub_updated":           [callback, ...],
      "hub_deleted":           [callback, ...],
  }

  Dispatch:
    1. Copy listener list (safe iteration)
    2. Call each listener with args
    3. Catch per-listener exceptions (no cascade)
```

## Known Issues

```
  [CRITICAL] connect() blocks indefinitely - no outer timeout
  [CRITICAL] No timeout on login response wait
  [CRITICAL] No timeout on receive loop (server goes silent)
  [HIGH]     No exponential backoff (fixed 10/20s delays)
  [HIGH]     State flags modified without asyncio.Lock
  [MEDIUM]   Stale devices persist after disconnect/reconnect
  [MEDIUM]   setup.py version (0.1.4) != manifest requirement (0.1.5)
```
