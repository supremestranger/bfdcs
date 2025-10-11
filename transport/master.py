import aiohttp
import fastapi
from pydantic import BaseModel
import time

class WorkerData:
    def __init__(self, worker_id: int, status: str, last_time_updated: float, current_task: str):
        self.id = worker_id
        self.status = "idle"
        self.last_time_updated = last_time_updated
        self.current_task = current_task

workers: dict[str, WorkerData] = {}
app = fastapi.FastAPI(title="Master Node")

class TaskReq(BaseModel):
    code: str
    worker: int

class StatusReq(BaseModel):
    worker: int
    status: str

class ResReq(BaseModel):
    res: str

@app.post("/task")
async def send_task(task: TaskReq):
    code = task.code
    worker = task.worker
    print(f"Task with code: {code} for worker: {worker}.")

    async with aiohttp.ClientSession() as s:
        try:
            # compact plaintext JSON message ("c")
            async with s.post("http://localhost:"+str(worker)+"/", json={"c": code}) as resp: 
                print(resp)
        except Exception as e:
            print(e)

@app.post("/status")
async def get_status(status_req: StatusReq):
    worker = status_req.worker

    status = status_req.status
    if worker not in workers.keys():
        workers[worker] = WorkerData(worker, status, time.time(), "")

    data = workers[worker]
    data.status = status
    data.last_time_updated = time.time()
    workers[worker] = data

@app.post("/results")
async def get_results(res: ResReq):
    print("Res", res.res)
    # TODO send to web

@app.get("/dead_workers")
async def get_dead_workers():
    return dict(filter(lambda kv: time.time() - kv[1].last_time_updated > 10, workers.items()))

@app.get("/ready_workers")
async def get_ready_workers():
    return dict(filter(lambda kv: time.time() - kv[1].last_time_updated <= 10, workers.items()))
