import { useEffect, useRef, useCallback } from 'react';
import { useApp } from '../context/AppContext';
import contextService from '../services/contextService';

const CONTEXT_GATHER_INTERVAL = 3 * 60 * 1000; // 3 minutes in milliseconds

export const usePeriodicContextGather = () => {
  const { state, actions } = useApp();
  const intervalRef = useRef(null);
  const isRunningRef = useRef(false);

  const gatherContext = useCallback(async () => {
    if (!state.codebasePath || isRunningRef.current) {
      return;
    }

    isRunningRef.current = true;
    
    try {
      console.log(`[${new Date().toISOString()}] Starting periodic context gathering...`);
      
      const response = await contextService.gatherContext(state.codebasePath);
      
      console.log(`[${new Date().toISOString()}] Context gathering completed:`, {
        statusCode: response.statuscode,
        timeTaken: response.time_taken_seconds,
        detail: response.detail
      });
      
      // Only update context gathered status if it was successful
      if (response.statuscode === 200) {
        actions.setContextGathered(true);
      }
      
    } catch (error) {
      console.error(`[${new Date().toISOString()}] Periodic context gathering failed:`, error);
      
      // Don't set error state for periodic failures to avoid disrupting user experience
      // Just log and continue
    } finally {
      isRunningRef.current = false;
    }
  }, [state.codebasePath, actions]);

  const startPeriodicGathering = useCallback(() => {
    if (intervalRef.current || !state.codebasePath) {
      return;
    }

    console.log(`[${new Date().toISOString()}] Starting periodic context gathering every ${CONTEXT_GATHER_INTERVAL / 1000 / 60} minutes`);
    
    intervalRef.current = setInterval(gatherContext, CONTEXT_GATHER_INTERVAL);
  }, [gatherContext, state.codebasePath]);

  const stopPeriodicGathering = useCallback(() => {
    if (intervalRef.current) {
      console.log(`[${new Date().toISOString()}] Stopping periodic context gathering`);
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Start periodic gathering when context is gathered and codebase path exists
  useEffect(() => {
    if (state.isContextGathered && state.codebasePath) {
      startPeriodicGathering();
    } else {
      stopPeriodicGathering();
    }

    // Cleanup on unmount
    return () => {
      stopPeriodicGathering();
    };
  }, [state.isContextGathered, state.codebasePath, startPeriodicGathering, stopPeriodicGathering]);

  // Cleanup on codebase path change
  useEffect(() => {
    return () => {
      stopPeriodicGathering();
    };
  }, [state.codebasePath, stopPeriodicGathering]);

  return {
    isPeriodicGatheringActive: !!intervalRef.current,
    startPeriodicGathering,
    stopPeriodicGathering,
    gatherContext
  };
}; 