import { useState, useEffect } from 'react';
import { detectionAPI } from '../services/api';

export const useDetections = (filters = {}) => {
  const [detections, setDetections] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadDetections();
  }, [JSON.stringify(filters)]);

  const loadDetections = async () => {
    try {
      setIsLoading(true);
      const response = await detectionAPI.getAll(filters);
      setDetections(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const refresh = () => {
    loadDetections();
  };

  return { detections, isLoading, error, refresh };
};