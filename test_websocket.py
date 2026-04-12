import asyncio
import websockets
import json

async def test_websocket():
    
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc1OTM1MzY4LCJpYXQiOjE3NzU5MzE3NjgsImp0aSI6ImNiN2E0MzdjYjNlNTRhMTc4YWJjNzQ5ZDkxMzFkZmFmIiwidXNlcl9pZCI6MX0.C5SEteZZCgHHI5uoR58xwG-Mt25JkB919Nf5v6XPXYA"

    uri = f'ws://localhost:8000/ws/posts/post-1/comments/?token={token}'

    print(f'Connecting to {uri}...')

    async with websockets.connect(uri) as websocket:
        print('Connected to WebSocket server.')

        async for message in websocket:
            data = json.loads(message)
            print(f"\n ---- New comment ---")
            print(f"Comment: {data['content']}")

if __name__ == "__main__":
    asyncio.run(test_websocket())