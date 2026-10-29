"""FastAPI model server with two ways to get predictions.

POST /predict          synchronous online: one image in, its label out, right away
POST /batch            asynchronous batch: images are queued, a job_id comes back at once
GET  /jobs/{job_id}    job status and labels (?wait=N waits up to N seconds for the job to finish)
GET  /health           model and batching settings

One model and one lock: the model runs one forward pass at a time, for both endpoints.
"""
import asyncio
import time
import uuid
from contextlib import asynccontextmanager

import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.model import load_model, predict_labels

BATCH_WINDOW_S = 0.02  # after the first queued job, wait up to 20 ms to collect more
MAX_BATCH = 128        # stop collecting once this many images are waiting


class PredictRequest(BaseModel):
    pixels: list[float] = Field(min_length=64, max_length=64)


class BatchRequest(BaseModel):
    items: list[list[float]] = Field(min_length=1)


async def batch_worker(app):
    queue, jobs = app.state.queue, app.state.jobs
    loop = asyncio.get_running_loop()
    while True:
        ids = [await queue.get()]
        n = len(jobs[ids[0]]["items"])
        deadline = loop.time() + BATCH_WINDOW_S
        while n < MAX_BATCH:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                job_id = await asyncio.wait_for(queue.get(), remaining)
            except asyncio.TimeoutError:
                break
            ids.append(job_id)
            n += len(jobs[job_id]["items"])

        x = np.concatenate([jobs[j]["items"] for j in ids])
        async with app.state.lock:
            labels = await asyncio.to_thread(predict_labels, app.state.model, x)
        pos = 0
        for j in ids:
            job = jobs[j]
            k = len(job["items"])
            job.update(labels=labels[pos:pos + k].tolist(), batch_size=len(x), status="done")
            job["done"].set()
            pos += k


@asynccontextmanager
async def lifespan(app):
    app.state.model = load_model()
    app.state.lock = asyncio.Lock()
    app.state.queue = asyncio.Queue()
    app.state.jobs = {}
    worker = asyncio.create_task(batch_worker(app))
    yield
    worker.cancel()


app = FastAPI(title="digit-inference", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "model_threads": torch.get_num_threads(),
            "batch_window_ms": BATCH_WINDOW_S * 1000, "max_batch": MAX_BATCH}


@app.post("/predict")
async def predict(req: PredictRequest):
    x = np.asarray(req.pixels, dtype=np.float32).reshape(1, 64)
    async with app.state.lock:
        start = time.perf_counter()
        labels = await asyncio.to_thread(predict_labels, app.state.model, x)
        model_ms = (time.perf_counter() - start) * 1000
    return {"label": int(labels[0]), "model_ms": round(model_ms, 3)}


@app.post("/batch", status_code=202)
async def submit_batch(req: BatchRequest):
    if any(len(item) != 64 for item in req.items):
        raise HTTPException(status_code=422, detail="each item needs 64 pixel values")
    job_id = uuid.uuid4().hex[:12]
    app.state.jobs[job_id] = {"status": "queued", "items": np.asarray(req.items, dtype=np.float32),
                              "labels": None, "batch_size": None, "done": asyncio.Event()}
    await app.state.queue.put(job_id)
    return {"job_id": job_id, "status": "queued", "items": len(req.items)}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str, wait: float = 0.0):
    job = app.state.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job_id")
    if wait > 0 and job["status"] != "done":
        try:
            await asyncio.wait_for(job["done"].wait(), timeout=min(wait, 60))
        except asyncio.TimeoutError:
            pass
    out = {"job_id": job_id, "status": job["status"]}
    if job["status"] == "done":
        out.update(labels=job["labels"], batch_size=job["batch_size"])
    return out
