import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

const ThemeToggle = () => {
    const { theme, toggleTheme } = useTheme();
    const isDark = theme === 'dark';

    return (
        <button
            onClick={toggleTheme}
            className={`
        fixed bottom-5 right-5 z-[9999]
        w-10 h-10 rounded-full
        flex items-center justify-center
        shadow-lg border
        transition-all duration-300 ease-in-out
        hover:scale-110 active:scale-95
        ${isDark
                    ? 'bg-gray-800 border-gray-600 text-amber-400 hover:bg-gray-700 shadow-gray-900/50'
                    : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50 shadow-gray-300/50'
                }
      `}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label="Toggle theme"
        >
            <div className="relative w-5 h-5">
                {/* Sun icon */}
                <Sun
                    className={`absolute inset-0 w-5 h-5 transition-all duration-300 ${isDark ? 'opacity-0 rotate-90 scale-0' : 'opacity-100 rotate-0 scale-100'
                        }`}
                />
                {/* Moon icon */}
                <Moon
                    className={`absolute inset-0 w-5 h-5 transition-all duration-300 ${isDark ? 'opacity-100 rotate-0 scale-100' : 'opacity-0 -rotate-90 scale-0'
                        }`}
                />
            </div>
        </button>
    );
};

export default ThemeToggle;
