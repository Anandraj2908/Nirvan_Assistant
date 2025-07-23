// Nirvan AI Assistant - React Component
// Enhanced version with modern UI and improved functionality

const { useState, useEffect, useRef } = React;

// Mic Icon Component
const MicIcon = () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2a3 3 0 0 1 3 3v6a3 3 0 0 1-6 0V5a3 3 0 0 1 3-3z"/>
        <path d="M19 10v1a7 7 0 0 1-14 0v-1"/>
        <path d="M12 18v4"/>
        <path d="M8 22h8"/>
    </svg>
);

// Close Icon Component
const CloseIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M18 6L6 18"/>
        <path d="M6 6l12 12"/>
    </svg>
);

// Message Component
const Message = ({ type, content, timestamp }) => (
    <div className={`message ${type} fade-in`}>
        <div className="message-bubble">
            {content}
        </div>
    </div>
);

// Status Indicator Component
const StatusIndicator = ({ state, onMicClick }) => {
    const renderMicButton = () => (
        <button 
            className={`mic-button ${state}`}
            onClick={onMicClick}
        >
            {state === 'listening' && (
                <>
                    <div className="listening-rings"></div>
                    <div className="listening-rings"></div>
                    <div className="listening-rings"></div>
                </>
            )}
            {state === 'thinking' ? (
                <div className="spinner"></div>
            ) : (
                <MicIcon />
            )}
        </button>
    );

    const getStatusText = () => {
        switch (state) {
            case 'listening': return 'Listening...';
            case 'thinking': return 'Processing...';
            default: return 'Say "Hey Nirvan" to start';
        }
    };

    return (
        <div className="status-area">
            <div className="mic-container">
                {renderMicButton()}
            </div>
            <div className="status-text">
                {getStatusText()}
            </div>
        </div>
    );
};

// Welcome Screen Component
const WelcomeScreen = () => (
    <div className="welcome-screen fade-in">
        <div className="logo">
            N
        </div>
        <h1 className="welcome-title">Hi there!</h1>
        <p className="welcome-subtitle">
            I'm Nirvan, your AI assistant. Say "Hey Nirvan" to get started, or click the mic button below.
        </p>
    </div>
);

// Main App Component
const App = () => {
    const [isActive, setIsActive] = useState(false);
    const [messages, setMessages] = useState([]);
    const [uiState, setUiState] = useState('waiting'); // 'waiting', 'listening', 'thinking'
    const [isConnected, setIsConnected] = useState(false);
    const socketRef = useRef(null);
    const chatEndRef = useRef(null);

    // Auto-scroll to bottom when new messages arrive
    useEffect(() => {
        if (chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [messages]);

    // Socket.IO setup
    useEffect(() => {
        const setupSocket = () => {
            if (socketRef.current) return;
            
            try {
                socketRef.current = io.connect(`http://${document.domain}:${location.port}`);

                socketRef.current.on('connect', () => {
                    console.log('Connected to server');
                    setIsConnected(true);
                });

                socketRef.current.on('disconnect', () => {
                    console.log('Disconnected from server');
                    setIsConnected(false);
                });

                // Window control events
                socketRef.current.on('activate_window', () => {
                    setIsActive(true);
                    setMessages([]);
                    if (window.pywebview?.api?.show_window) {
                        window.pywebview.api.show_window();
                    }
                    if (window.pywebview?.api?.start_logic) {
                        window.pywebview.api.start_logic();
                    }
                });

                socketRef.current.on('deactivate_window', () => {
                    setIsActive(false);
                    setUiState('waiting');
                    setTimeout(() => {
                        if (window.pywebview?.api?.hide_window) {
                            window.pywebview.api.hide_window();
                        }
                    }, 500);
                });

                // Message and state events
                socketRef.current.on('display_message', (data) => {
                    setMessages(prev => [...prev, {
                        type: data.who,
                        content: data.message,
                        timestamp: new Date().getTime()
                    }]);
                });

                socketRef.current.on('start_listening', () => {
                    setUiState('listening');
                });

                socketRef.current.on('stop_listening', () => {
                    setUiState('thinking');
                });

                socketRef.current.on('thinking', () => {
                    setUiState('thinking');
                });

                socketRef.current.on('waiting_for_command', () => {
                    setUiState('waiting');
                });

            } catch (error) {
                console.error('Socket setup error:', error);
            }
        };

        // Setup socket when pywebview is ready or immediately if not using pywebview
        if (window.pywebview) {
            if (window.pywebview.api) {
                setupSocket();
            } else {
                window.addEventListener('pywebviewready', setupSocket);
            }
        } else {
            // For testing without pywebview
            setupSocket();
            setIsActive(true); // Show window for testing
        }

        return () => {
            if (socketRef.current) {
                socketRef.current.disconnect();
            }
            window.removeEventListener('pywebviewready', setupSocket);
        };
    }, []);

    // Handle manual mic button click
    const handleMicClick = () => {
        if (socketRef.current && isConnected) {
            if (uiState === 'waiting') {
                socketRef.current.emit('manual_start_listening');
                setUiState('listening');
            } else if (uiState === 'listening') {
                socketRef.current.emit('manual_stop_listening');
                setUiState('thinking');
            }
        }
    };

    // Handle close button
    const handleClose = () => {
        if (socketRef.current) {
            socketRef.current.emit('close_window');
        }
        setIsActive(false);
        setTimeout(() => {
            if (window.pywebview?.api?.hide_window) {
                window.pywebview.api.hide_window();
            }
        }, 300);
    };

    // Demo function for testing (remove in production)
    const addDemoMessage = (type, content) => {
        setMessages(prev => [...prev, {
            type,
            content,
            timestamp: new Date().getTime()
        }]);
    };

    // Test keyboard shortcuts (remove in production)
    useEffect(() => {
        const handleKeyPress = (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case '1':
                        e.preventDefault();
                        setIsActive(!isActive);
                        break;
                    case '2':
                        e.preventDefault();
                        addDemoMessage('user', 'Hello, can you help me with something?');
                        break;
                    case '3':
                        e.preventDefault();
                        addDemoMessage('assistant', 'Of course! I\'d be happy to help you. What do you need assistance with?');
                        break;
                    case '4':
                        e.preventDefault();
                        setUiState(uiState === 'listening' ? 'waiting' : 'listening');
                        break;
                }
            }
        };

        window.addEventListener('keydown', handleKeyPress);
        return () => window.removeEventListener('keydown', handleKeyPress);
    }, [isActive, uiState]);

    return (
        <div id="root-container" className={isActive ? 'active' : ''}>
            <div className="main-container">
                {/* Header */}
                <div className="header">
                    <div className="header-title">Nirvan</div>
                    <button className="close-btn" onClick={handleClose}>
                        <CloseIcon />
                    </button>
                </div>

                {/* Chat Area */}
                {messages.length === 0 ? (
                    <WelcomeScreen />
                ) : (
                    <div className="chat-area">
                        {messages.map((message, index) => (
                            <Message
                                key={`${message.timestamp}-${index}`}
                                type={message.type}
                                content={message.content}
                                timestamp={message.timestamp}
                            />
                        ))}
                        <div ref={chatEndRef} />
                    </div>
                )}

                {/* Status Area */}
                <StatusIndicator 
                    state={uiState} 
                    onMicClick={handleMicClick}
                />
            </div>
        </div>
    );
};

// Render the app
ReactDOM.render(<App />, document.getElementById('root'));