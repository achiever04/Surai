import asyncio
import numpy as np
from loguru import logger
from ai_engine.model_manager import ai_model_manager
from app.services.watchlist_service import WatchlistService
from ai_engine.pipelines.tracker_manager import TrackerManager

class AsyncWorkerPool:
    """
    Subscribes to tracking events and runs heavy face/emotion models 
    asynchronously so the main camera feed never drops frames.
    Implements Pub-Sub queuing.
    """
    def __init__(self, watchlist_service: WatchlistService, tracker_manager: TrackerManager, num_workers=4):
        self.queue = asyncio.Queue()
        self.workers = []
        self.watchlist_service = watchlist_service
        self.tracker_manager = tracker_manager
        self.num_workers = num_workers
        self.is_running = False

    async def start(self):
        self.is_running = True
        for i in range(self.num_workers):
            task = asyncio.create_task(self._worker_loop(i))
            self.workers.append(task)
            
    async def stop(self):
        self.is_running = False
        for _ in range(self.num_workers):
            await self.queue.put(None)
        await asyncio.gather(*self.workers)

    async def submit_job(self, track_id: int, frame: np.ndarray, crop_box: list):
        """Called by the main thread to push bounding box crops"""
        await self.queue.put((track_id, frame, crop_box))

    async def _worker_loop(self, worker_id: int):
        logger.info(f"Worker {worker_id} started")
        while self.is_running:
            job = await self.queue.get()
            if job is None:
                break
                
            track_id, frame, crop_box = job
            try:
                # Heavy Deep analysis executed here (Stage 2)
                x1, y1, x2, y2 = map(int, crop_box)
                h, w = frame.shape[:2]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                face_crop = frame[y1:y2, x1:x2]
                if face_crop.size == 0:
                    continue

                identity = "Unknown"
                emotion = "Neutral"

                # 1. Run InsightFace (Shared model instance)
                # Only accesses memory if the object is loaded via the ThreadLock
                face_rec = ai_model_manager.face_recognizer
                embedding = face_rec.extract_embedding(face_crop)
                
                if embedding is not None:
                    # 2. Search FAISS index natively (Near-Instant)
                    match = await self.watchlist_service.search_by_embedding(embedding)
                    if match:
                        person_id, score = match
                        identity = f"ID:{person_id}"

                # 3. Emotion Detection (DeepFace context)
                emotion_detector = ai_model_manager.emotion_detector
                emo_result = emotion_detector.detect_emotion(face_crop)
                if emo_result:
                    # Note: We will apply temporal smoothing to this in Phase 5
                    emotion = emo_result
                
                # 4. Push back to the Tracker State cache (Pub-Sub sync)
                self.tracker_manager.update_track_identity(track_id, identity, emotion)
                
            except Exception as e:
                logger.error(f"Async worker {worker_id} failed on ID {track_id}: {e}")
            finally:
                self.queue.task_done()
