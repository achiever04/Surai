import React, { useState, useEffect, useCallback } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

/**
 * Toast notification component.
 * Usage:
 *   <Toast message="Saved!" type="success" onClose={() => {}} />
 *
 * Or use the useToast hook for imperative control:
 *   const { toast, ToastContainer } = useToast();
 *   toast.success("Saved!");
 *   <ToastContainer />
 */

const ICONS = {
    success: CheckCircle,
    error: XCircle,
    warning: AlertTriangle,
    info: Info,
};

const COLORS = {
    success: 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800 text-green-800 dark:text-green-300',
    error: 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800 text-red-800 dark:text-red-300',
    warning: 'bg-yellow-50 dark:bg-yellow-900/30 border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-300',
    info: 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-300',
};

const ICON_COLORS = {
    success: 'text-green-500',
    error: 'text-red-500',
    warning: 'text-yellow-500',
    info: 'text-blue-500',
};


// ── Single Toast ──────────────────────────────────────────────────
export const Toast = ({ message, type = 'info', duration = 4000, onClose }) => {
    useEffect(() => {
        if (duration > 0) {
            const timer = setTimeout(onClose, duration);
            return () => clearTimeout(timer);
        }
    }, [duration, onClose]);

    const Icon = ICONS[type] || ICONS.info;

    return (
        <div
            className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg animate-slide-in ${COLORS[type] || COLORS.info}`}
            role="alert"
        >
            <Icon className={`h-5 w-5 flex-shrink-0 ${ICON_COLORS[type]}`} />
            <span className="text-sm font-medium flex-1">{message}</span>
            <button
                onClick={onClose}
                className="p-1 rounded hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
            >
                <X className="h-4 w-4" />
            </button>
        </div>
    );
};


// ── Toast Container + Hook ────────────────────────────────────────
export const useToast = () => {
    const [toasts, setToasts] = useState([]);

    const addToast = useCallback((message, type = 'info', duration = 4000) => {
        const id = Date.now() + Math.random();
        setToasts(prev => [...prev, { id, message, type, duration }]);
    }, []);

    const removeToast = useCallback((id) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    }, []);

    const toast = {
        success: (msg, dur) => addToast(msg, 'success', dur),
        error: (msg, dur) => addToast(msg, 'error', dur),
        warning: (msg, dur) => addToast(msg, 'warning', dur),
        info: (msg, dur) => addToast(msg, 'info', dur),
    };

    const ToastContainer = () => (
        <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 max-w-sm w-full pointer-events-auto">
            {toasts.map(t => (
                <Toast
                    key={t.id}
                    message={t.message}
                    type={t.type}
                    duration={t.duration}
                    onClose={() => removeToast(t.id)}
                />
            ))}
        </div>
    );

    return { toast, ToastContainer };
};

export default Toast;
