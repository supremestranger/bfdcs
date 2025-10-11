import aiohttp
import asyncio
import fastapi
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    asyncio.create_task(send_status())
    yield

app = fastapi.FastAPI(title="Worker Node", lifespan=lifespan)
status = "idle"
port: int = 8004

async def send_status(period: float = 5):
    while True:
        async with aiohttp.ClientSession() as s:
            try:
                async with s.post("http://localhost:8080/status", json={"status": status, "worker": port}) as resp:
                    print(resp)
            except Exception as e:
                print(e)
        await asyncio.sleep(period)

async def run_code(code: str):
    global status
    await asyncio.to_thread(exec, code)
    status = "idle"

@app.post("/")
async def get_task(task: dict):
    global status
    print(task["c"])
    status = "busy"
    asyncio.create_task(run_code(task["c"]))
    return {"ok"}