"""
Watchlist service for managing persons of interest
"""
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import shutil

from app.models.watchlist import WatchlistPerson
from app.utils.ipfs_client import IPFSClient
from ai_engine.model_manager import ai_model_manager
import cv2
import numpy as np

class WatchlistService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ipfs_client = IPFSClient()
        # Use shared singleton from model manager to avoid loading InsightFace twice
        self.face_recognizer = ai_model_manager.get_face_recognizer()
        self.storage_path = Path("data/watchlist")
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def enroll_person(
        self,
        person_data: Dict[str, Any],
        photos: List[UploadFile],
        enrolled_by: str
    ) -> WatchlistPerson:
        """
        Enroll new person with face photos.
        Also detects age from the first photo and warns if it doesn't match entered age.
        """
        person_id = person_data["person_id"]
        
        # Process photos and extract embeddings
        embeddings = []
        photo_hashes = []
        local_paths = []
        ipfs_cids = []
        photo_detected_age = None  # AI-detected age from enrollment photo
        
        for idx, photo in enumerate(photos):
            # Read photo
            contents = await photo.read()
            
            # Save locally
            person_folder = self.storage_path / person_id
            person_folder.mkdir(exist_ok=True)
            
            photo_filename = f"photo_{idx}.jpg"
            photo_path = person_folder / photo_filename
            
            with open(photo_path, "wb") as f:
                f.write(contents)
            
            local_paths.append(str(photo_path))
            
            # Compute hash
            photo_hash = hashlib.sha256(contents).hexdigest()
            photo_hashes.append(photo_hash)
            
            # Extract face embedding
            image = cv2.imdecode(
                np.frombuffer(contents, np.uint8),
                cv2.IMREAD_COLOR
            )
            
            embedding = self.face_recognizer.extract_embedding(image)
            
            if embedding is not None:
                embeddings.append(embedding.tolist())
                
                # AGE PROGRESSION: Detect age from the FIRST valid face photo
                if photo_detected_age is None:
                    try:
                        from ai_engine.models.age_estimator import AgeEstimator
                        age_estimator = AgeEstimator()
                        photo_detected_age = age_estimator.estimate(image)
                        if photo_detected_age is not None:
                            from loguru import logger
                            logger.info(f"📊 Enrollment age estimation: photo appears ~{photo_detected_age}yrs for person {person_id}")
                    except Exception as age_err:
                        from loguru import logger
                        logger.debug(f"Age estimation during enrollment failed: {age_err}")
            
            # Upload to IPFS (optional)
            try:
                cid = await self.ipfs_client.add_file(contents)
                ipfs_cids.append(cid)
            except Exception as e:
                print(f"IPFS upload failed: {e}")
                ipfs_cids.append(None)
        
        if not embeddings:
            raise ValueError("No valid faces detected in provided photos")
        
        # Convert age from string to integer (form data comes as string)
        age_value = person_data.get("age")
        if age_value and str(age_value).strip():
            try:
                age_value = int(age_value)
            except (ValueError, TypeError):
                age_value = None
        else:
            age_value = None
        
        # AGE PROGRESSION: Compute age warning if entered age mismatches photo
        age_warning = None
        if age_value is not None and photo_detected_age is not None:
            age_diff = abs(age_value - photo_detected_age)
            if age_diff > 5:
                age_warning = (
                    f"The entered age ({age_value}) differs significantly from the "
                    f"AI-detected age (~{photo_detected_age}) in the uploaded photo. "
                    f"Please verify that the age is correct for the person in the photo."
                )
        
        # Store detected age in metadata for future reference
        person_metadata = person_data.get("person_metadata") or {}
        if photo_detected_age is not None:
            person_metadata["photo_detected_age"] = photo_detected_age
        if age_warning:
            person_metadata["age_warning"] = age_warning
        
        # Create watchlist person
        person = WatchlistPerson(
            person_id=person_id,
            name=person_data["name"],
            category=person_data["category"],
            risk_level=person_data.get("risk_level", "low"),
            age=age_value,
            gender=person_data.get("gender") or None,
            description=person_data.get("description") or None,
            authorization_ref=person_data.get("authorization_ref"),
            face_embeddings=embeddings,
            photo_hashes=photo_hashes,
            num_photos=len(photos),
            photos_local_paths=local_paths,
            photos_ipfs_cids=ipfs_cids,
            enrolled_by=enrolled_by,
            alert_on_detection=person_data.get("alert_on_detection", True),
            person_metadata=person_metadata if person_metadata else None
        )
        
        self.db.add(person)
        await self.db.commit()
        await self.db.refresh(person)
        
        # Attach transient fields for response (not in DB)
        person._photo_detected_age = photo_detected_age
        person._age_warning = age_warning
        
        return person
    
    async def get_all_active(self) -> List[WatchlistPerson]:
        """
        Get all active watchlist persons
        
        Returns:
            List of active watchlist persons
        """
        result = await self.db.execute(
            select(WatchlistPerson).where(WatchlistPerson.is_active == True)
        )
        return result.scalars().all()
    
    async def get_all_active_embeddings(self) -> List[tuple]:
        """
        Get all active watchlist embeddings for matching
        Returns: List of (person_id, embedding) tuples
        """
        result = await self.db.execute(
            select(WatchlistPerson)
            .where(WatchlistPerson.is_active == True)
        )
        persons = result.scalars().all()
        
        embeddings_list = []
        for person in persons:
            for embedding in person.face_embeddings:
                embeddings_list.append((person.id, np.array(embedding)))
        
        return embeddings_list
    
    async def update_last_seen(
        self,
        person_id: int,
        camera_id: int,
        location: str
    ):
        """Update last seen information"""
        result = await self.db.execute(
            select(WatchlistPerson).where(WatchlistPerson.id == person_id)
        )
        person = result.scalar_one_or_none()
        
        if person:
            person.last_seen_at = datetime.utcnow()
            person.last_seen_location = location
            person.last_seen_camera_id = camera_id
            person.total_detections += 1
            
            await self.db.commit()
    
    async def search_by_embedding(
        self,
        query_embedding: np.ndarray,
        threshold: float = 0.4
    ) -> tuple:
        """
        Search for matching person by face embedding
        Returns: (person_id, similarity_score) or None
        """
        embeddings_list = await self.get_all_active_embeddings()
        
        if not embeddings_list:
            return None
        
        best_match = None
        best_similarity = threshold
        
        for person_id, embedding in embeddings_list:
            similarity = np.dot(query_embedding, embedding)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = person_id
        
        if best_match:
            return (best_match, float(best_similarity))
        
        return None