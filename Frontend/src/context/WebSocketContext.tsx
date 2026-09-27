import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { Alert } from '../types';

interface WebSocketContextType {
  isConnected: boolean;
  isConnecting: boolean;
  liveAlerts: Alert[];
  unreadCount: number;
  clearUnread: () => void;
  reconnect: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token, isAuthenticated } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [liveAlerts, setLiveAlerts] = useState<Alert[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectDelayRef = useRef<number>(2000);

  const connect = useCallback(() => {
    if (!isAuthenticated || !token) return;

    if (socketRef.current && (socketRef.current.readyState === WebSocket.OPEN || socketRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    setIsConnecting(true);

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Use host and port matching current environment or backend proxy
    const wsUrl = `${protocol}//${window.location.host}/api/v1/alerts/ws?token=${token}`;

    try {
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setIsConnecting(false);
        reconnectDelayRef.current = 2000; // Reset backoff
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          // Check if payload is an alert notification or ping
          if (payload && payload.alert_id) {
            const newAlert: Alert = {
              id: payload.alert_id,
              elderly_id: payload.elderly_id,
              device_id: payload.device_id,
              alert_type: payload.alert_type,
              severity: payload.severity,
              status: payload.status || 'OPEN',
              title: payload.title || `Alerte ${payload.alert_type}`,
              description: payload.description || 'Alerte temps réel',
              source: payload.source || 'RULE_ENGINE',
              occurred_at: payload.occurred_at || new Date().toISOString(),
              occurrence_count: 1,
              acknowledged_at: null,
              acknowledged_by: null,
              resolved_at: null,
              has_ai_analysis: !!payload.ai_summary,
              ai_summary: payload.ai_summary,
            };

            setLiveAlerts((prev) => [newAlert, ...prev.slice(0, 49)]);
            setUnreadCount((c) => c + 1);
          }
        } catch {
          // Ignored non-json heartbeat
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        setIsConnecting(false);
        // Exponential backoff reconnect
        if (isAuthenticated) {
          const delay = Math.min(reconnectDelayRef.current * 1.5, 30000);
          reconnectDelayRef.current = delay;
          reconnectTimeoutRef.current = window.setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        setIsConnected(false);
      };
    } catch {
      setIsConnecting(false);
      setIsConnected(false);
    }
  }, [isAuthenticated, token]);

  const reconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    connect();
  }, [connect]);

  useEffect(() => {
    if (isAuthenticated) {
      connect();
    } else {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      setIsConnected(false);
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [isAuthenticated, connect]);

  const clearUnread = useCallback(() => {
    setUnreadCount(0);
  }, []);

  return (
    <WebSocketContext.Provider
      value={{
        isConnected,
        isConnecting,
        liveAlerts,
        unreadCount,
        clearUnread,
        reconnect,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};
