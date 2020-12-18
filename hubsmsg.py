# -*- coding: utf-8 -*-
""" A program to monitor presence events occurred in the specified hubs room """
import argparse
import asyncio
import json
import os
import signal
import threading
import csv
import datetime
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
from room import Room

CLOSE_CODES = {
    1000: "OK",
    1001: "going away",
    1002: "protocol error",
    1003: "unsupported type",
    # 1004 is reserved
    1005: "no status code [internal]",
    1006: "connection closed abnormally [internal]",
    1007: "invalid data",
    1008: "policy violation",
    1009: "message too big",
    1010: "extension required",
    1011: "unexpected error",
    1015: "TLS failure [internal]",
}

CHAT_TEMPLATE = '["2", "{$seq_num}", "hub:{$hub_id}", "message", {"body":"{$msg}", "type":"chat"}]'

def exit_from_event_loop_thread(loop: asyncio.AbstractEventLoop,
                                stop: "asyncio.Future[None]"
                               ) -> None:
    """
    Exit from event loop thread.

    Args:
        loop: event loop
        stop: stop condition
    """
    loop.stop()
    if not stop.done():
        # When exiting the thread that runs the event loop, raise
        # KeyboardInterrupt in the main thread to exit the program.
        os.kill(os.getpid(), signal.SIGINT)

def get_req_str(template: str, hub_id: str, seq_number: int, monitor_name: str) -> str:
    """
    Returns phoenix request string, built from the given template and hub_id.

    Args:
        template(str): template file
        hub_id(str): hub_id
        seq_number(int): message's sequence number starting from 1
        monitor_name(str): display name of this monitor program

    Returns:
        str: Phoenix request string after replacement
    """
    with open(template) as template_file:
        template_str = template_file.read()
        json_str = template_str.replace("{$hub_id}", hub_id)
        json_str = json_str.replace("{$seq_num}", str(seq_number))
        json_str = json_str.replace("{$monitor_name}", monitor_name)
        json_data = json.loads(json_str)
        return json.dumps(json_data)

def get_chat_str(hub_id: str, seq_number: int, message: str) -> str:
    """
    Returns phoenix chat request string.

    Args:
        hub_id(str): hub_id
        seq_number(int): message's sequence number starting from 1
        message(str): chat message

    Returns:
        str: Phoenix request string after replacement
    """
    template_str = CHAT_TEMPLATE
    json_str = template_str.replace("{$hub_id}", hub_id)
    json_str = json_str.replace("{$seq_num}", str(seq_number))
    json_str = json_str.replace("{$msg}", message)
    json_data = json.loads(json_str)
    return json.dumps(json_data)

def format_close(code: int, reason: str) -> str:
    """
    Display a human-readable version of the close code and reason.

    Args:
        code: close code
        reason: reason text
    """
    if 3000 <= code < 4000:
        explanation = "registered"
    elif 4000 <= code < 5000:
        explanation = "private use"
    else:
        explanation = CLOSE_CODES.get(code, "unknown")
    result = f"code = {code} ({explanation}), "

    if reason:
        result += f"reason = {reason}"
    else:
        result += "no reason"

    return result

def process_meta(hub_id: str, meta: dict, event_type: str) -> None:
    """
    Returns device type texts from the context.

    Args:
        meta: meta element

    Returns:
        list: a list of device type texts
    """

    dt_now = datetime.datetime.now()
    dt_now_str = dt_now.strftime('%Y-%m-%d %H:%M:%S')

    device_types = []
    is_hmd = False
    is_mobile = False
    if "hmd" in meta['context']:
        if meta['context']['hmd'] is True:
            is_hmd = True
            device_types.append('hmd')
    if "mobile" in meta['context']:
        if meta['context']['mobile'] is True:
            is_mobile = True
            device_types.append('mobile')

    print(dt_now_str,
          hub_id,
          meta['profile']['displayName'],
          device_types,
          event_type,
          meta['presence'])

    row = []
    row.append(dt_now_str)
    row.append(meta['profile']['displayName'])
    row.append(event_type)
    row.append(meta['presence'])
    row.append(is_hmd)
    row.append(is_mobile)
    with open(hub_id + '.csv', 'a') as csv_file:
        writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        writer.writerow(row)
        csv_file.flush()

def process_message(hub_id: str, message: str) -> bool:
    """
    Process a message sent from WebSocket server.

    Args:
        hub_id: hub ID.
        message: a message to be processed.
    """
    msg_as_json = json.loads(message)
    if msg_as_json[3] == 'presence_state':
        for key in msg_as_json[4]:
            for meta in msg_as_json[4][key]['metas']:
                process_meta(hub_id, meta, 'in')

    elif msg_as_json[3] == 'presence_diff':
        #print(json.dumps(msg_as_json[4], indent=2))
        for key in msg_as_json[4]['joins']:
            for meta in msg_as_json[4]['joins'][key]['metas']:
                process_meta(hub_id, meta, 'joins')

        for key in msg_as_json[4]['leaves']:
            for meta in msg_as_json[4]['leaves'][key]['metas']:
                process_meta(hub_id, meta, 'leaves')

    elif msg_as_json[3] == 'phx_reply':
        status = msg_as_json[4]['status']
        if status == 'error':
            print(json.dumps(msg_as_json[4]))
            return False

    return True

def init_csv(hubs_room: Room) -> None:
    """
    Creates new csv file with csv header if not exists.

    Args:
        hubs_room(Room): room obj
    """
    filename = hubs_room.get_hub_id() + '.csv'
    if os.path.exists(filename) is False:
        with open(filename, 'w') as csv_file:
            writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
            row = []
            row.append('Timestamp')
            row.append('Display name')
            row.append('Event type')
            row.append('Room or lobby')
            row.append('Access from HMD')
            row.append('Access from Mobile')
            writer.writerow(row)
            csv_file.flush()

async def run_client(hubs_room: Room,
                     loop: asyncio.AbstractEventLoop,
                     inputs: "asyncio.Queue[str]",
                     stop: "asyncio.Future[None]",
                     ) -> None:
    """
    WebSocket client thread

    Args:
        hub_id: hub ID
        loop: event loop
        inputs: queue for user input
        stop: stop condition
    """
    # initialize csv file if necessary
    init_csv(hubs_room)

    reticulum_io_url = "wss://" + hubs_room.get_reticulum_server() + "/socket/websocket?vsn=2.0.0"
    try:
        websocket = await websockets.connect(reticulum_io_url)
    except WebSocketException as ex:
        print(f"Failed to connect to {reticulum_io_url}: {ex}.")
        exit_from_event_loop_thread(loop, stop)
        return
    else:
        print(f"Connected to {reticulum_io_url}.")

    hub_id = hubs_room.get_hub_id()
    try:
        while True:
            incoming = asyncio.ensure_future(websocket.recv())
            outgoing = asyncio.ensure_future(inputs.get())
            done, pending = await asyncio.wait(
                [incoming, outgoing, stop], return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel pending tasks to avoid leaking them.
            if incoming in pending:
                incoming.cancel()
            if outgoing in pending:
                outgoing.cancel()

            if incoming in done:
                try:
                    message = incoming.result()
                except ConnectionClosed:
                    break
                else:
                    retval = process_message(hub_id, message)
                    if retval is False:
                        break

            if outgoing in done:
                message = outgoing.result()
                await websocket.send(message)

            if stop in done:
                break

    finally:
        await websocket.close()
        close_status = format_close(websocket.close_code, websocket.close_reason)
        print(f"Connection closed: {close_status}.")
        exit_from_event_loop_thread(loop, stop)

def main() -> None:
    """
    main thread of this program
    """

    # Parse command line arguments.
    parser = argparse.ArgumentParser(
        description="hubsmon - A tool to send chat messages to each Mozilla Hubs rooms."
    )
    parser.add_argument("rooms_file", help="a JSON file contains a list of room URLs.")
    parser.add_argument("-n", "--name", default='Presence Monitor', help="display name of monitor")
    args = parser.parse_args()

    rooms = []

    with open(args.rooms_file) as json_file:
        json_data = json.load(json_file)

        # setup stuffs for each room
        for room_url in json_data['rooms']:
            hubs_room = Room(room_url)

            room = {}
            rooms.append(room)

            # Create an event loop that will run in a background thread.
            loop = asyncio.new_event_loop()
            room['loop'] = loop

            # Create a queue of user inputs. There's no need to limit its size.
            inputs = asyncio.Queue(loop=loop)
            room['inputs'] = inputs
            hub_id = hubs_room.get_hub_id()
            room['hub_id'] = hub_id
            inputs.put_nowait(get_req_str('phx_join_1.template', hub_id, 1, args.name))
            inputs.put_nowait(get_req_str('phx_join_2.template', hub_id, 2, args.name))

            # Create a stop condition when receiving SIGINT or SIGTERM.
            stop = loop.create_future()
            room['stop'] = stop

            # Schedule the task that will manage the connection.
            asyncio.ensure_future(run_client(hubs_room, loop, inputs, stop), loop=loop)

            # Start the event loop in a background thread.
            thread = threading.Thread(target=loop.run_forever)
            room['thread'] = thread
            thread.start()

    if len(rooms) == 0:
        print('No valid room is specified. Exit monitoring.')
        return

    # Read from stdin in the main thread in order to receive signals.
    try:
        seq_num = 3
        while True:
            input_text = input()
            if len(input_text) == 0:
                print('bye.')
                raise KeyboardInterrupt

            for room in rooms:
                message = get_chat_str(room['hub_id'],
                                       seq_num,
                                       input_text)
                room['loop'].call_soon_threadsafe(room['inputs'].put_nowait, message)

            seq_num += 1

    except (KeyboardInterrupt, EOFError):  # ^C, ^D
        for room in rooms:
            room['loop'].call_soon_threadsafe(room['stop'].set_result, None)

    # Wait for the event loop to terminate.
    for room in rooms:
        room['thread'].join()

if __name__ == "__main__":
    main()
