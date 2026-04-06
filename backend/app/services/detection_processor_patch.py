# Blockchain anchoring code to add after line 375 in detection_processor.py
# Insert this block after: logger.info(f"Detection saved: {detection_type} (severity: {severity}, id: {detection_id})")
# And before: finally:

                # Anchor evidence to blockchain
                try:
                    from app.services.blockchain_service import BlockchainService
                    
                    # Create evidence receipt
                    evidence_receipt = {
                        "event_id": event_id,
                        "clip_hash": clip_hash,
                        "timestamp": timestamp.isoformat(),
                        "camera_id": camera_id,
                        "detection_type": detection_type,
                        "confidence": result.confidence,
                        "matched_person_id": result.matched_person_id,
                        "severity": severity
                    }
                    
                    # Use sync blockchain service
                    blockchain_service = BlockchainService(session)
                    tx_id = blockchain_service.register_evidence_sync(
                        event_id=event_id,
                        evidence_receipt=evidence_receipt
                    )
                    
                    # Update detection with blockchain TX ID
                    detection.blockchain_tx_id = tx_id
                    detection.anchored_at = datetime.utcnow()
                    session.commit()
                    
                    logger.info(f"Evidence anchored to blockchain: {tx_id}")
                    
                except Exception as e:
                    logger.warning(f"Blockchain anchoring failed (non-critical): {e}")
                    # Continue without blockchain - detection is still saved
