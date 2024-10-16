import asyncio
import websockets
import json

async def get_sensor_paths(host="localhost"):
    uri = f"ws://{host}/websocket"
    async with websockets.connect(uri) as websocket:
        # Request list of all objects
        request = {
            "jsonrpc": "2.0",
            "method": "printer.objects.list",
            "id": 1
        }
        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        data = json.loads(response)
        print("Available objects:", data)
        
        # Filter temperature sensors from available objects
        if 'result' in data:
            sensors = [obj for obj in data['result']['objects'] if 'temperature_sensor' in obj]
            print("Temperature sensors found:", sensors)
        else:
            print("No temperature sensors found.")

asyncio.run(get_sensor_paths(host="ratos.local"))