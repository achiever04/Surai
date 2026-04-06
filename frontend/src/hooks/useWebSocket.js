import { useEffect, useRef } from 'react';
import websocketService from '../services/websocket';

export const useWebSocket = (event, callback) => {
  const callbackRef = useRef(callback);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    const handler = (data) => {
      callbackRef.current(data);
    };

    websocketService.on(event, handler);

    return () => {
      websocketService.off(event, handler);
    };
  }, [event]);
};