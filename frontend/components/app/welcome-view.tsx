import React, { useState, useCallback } from 'react';

// --- Placeholder for Button Component (Using standard HTML + Tailwind) ---
const Button = ({ children, onClick, className = "", disabled = false }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className={`px-6 py-3 rounded-xl font-bold transition-all duration-200 shadow-lg 
                bg-purple-600 hover:bg-purple-700 text-white 
                disabled:bg-gray-400 disabled:shadow-none ${className}`}
  >
    {children}
  </button>
);

// --- Thematic Icon: Stage Spotlight/Microphone SVG ---
function StageIcon() {
  return (
    <svg 
      width="64" 
      height="64" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      className="text-yellow-400 mb-6 size-16 drop-shadow-md"
    >
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
      <line x1="12" x2="12" y1="19" y2="22"/>
    </svg>
  );
}

// --- Welcome View Component (Now an export const) ---
// Removed unused 'ref' prop for cleaner component definition.
export const WelcomeView = ({ onStartCall }) => {
  const [playerName, setPlayerName] = useState('');
  const [isConnecting, setIsConnecting] = useState(false);

  const handleStart = useCallback(() => {
    setIsConnecting(true);
    // Pass name to the handler (simulated connection)
    onStartCall(playerName.trim() || "Contestant");
  }, [playerName, onStartCall]);

  const buttonText = isConnecting ? "Connecting to Host..." : "Start Improv Battle!";
  const isDisabled = isConnecting;
  
  return (
    <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center p-4">
      <section className="bg-gray-800 p-8 md:p-12 rounded-2xl shadow-2xl flex flex-col items-center justify-center text-center max-w-lg w-full border border-purple-700/50">
        
        <StageIcon />

        <h1 className="text-4xl font-extrabold text-purple-400 mb-4">
          IMPROV BATTLE
        </h1>
        
        <p className="text-gray-300 max-w-prose leading-6 mb-8 text-lg">
          Get ready for action! You are the star contestant of this voice improv game. The host will give you the scenario, you improvise.
        </p>
        
        <div className="w-full mb-6">
          <label htmlFor="name-input" className="block text-sm font-medium text-gray-400 mb-2 text-left">
            Your Contestant Name:
          </label>
          <input
            id="name-input"
            type="text"
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
            placeholder="Ex: The Comedy Genius, The Drama Queen"
            maxLength={30}
            className="w-full px-4 py-3 bg-gray-700 border border-purple-500 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-400 text-base"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !isDisabled) {
                handleStart();
              }
            }}
          />
        </div>

        <Button 
          onClick={handleStart} 
          className="mt-4 w-full text-xl py-4" 
          disabled={isDisabled}
        >
          {buttonText}
        </Button>
        
        {isConnecting && (
          <p className="mt-4 text-purple-300 animate-pulse">
            The host is adjusting the spotlights...
          </p>
        )}
      </section>

      {/* Footer Info */}
      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-gray-500 max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm">
          Make sure your microphone is ready. The host will greet you and give you the first scene.
        </p>
      </div>
    </div>
  );
};


// --- Main Application Component ---
// This is the exported component that the environment renders.
const CONNECTION_STATE = {
    DISCONNECTED: 'DISCONNECTED',
    CONNECTING: 'CONNECTING',
    CONNECTED: 'CONNECTED',
};

export default function App() {
    const [connectionState, setConnectionState] = useState(CONNECTION_STATE.DISCONNECTED);
    const [contestantName, setContestantName] = useState('');
    const [chatHistory, setChatHistory] = useState([]);

    // Simulates the start of the call/session with the agent.
    const startCall = (name) => {
        setContestantName(name);
        setConnectionState(CONNECTION_STATE.CONNECTING);
        // In a real LiveKit environment, this would trigger the actual connection.
        // For this demo, we'll simulate a quick connection and jump to a 'game' view.
        setTimeout(() => {
            setConnectionState(CONNECTION_STATE.CONNECTED);
            setChatHistory([{ sender: 'Host', message: `Welcome, ${name}! I am your host and we are ready for the first challenge. (This is the game view, the real connection starts now.)` }]);
        }, 1500);
    };

    if (connectionState === CONNECTION_STATE.DISCONNECTED || connectionState === CONNECTION_STATE.CONNECTING) {
        return (
            <WelcomeView 
                onStartCall={startCall} 
            />
        );
    }

    // --- Simulated In-Game View ---
    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-900 p-4">
            <div className="bg-gray-800 p-8 rounded-2xl shadow-2xl max-w-xl w-full border border-purple-700/50">
                <h2 className="text-3xl font-bold text-yellow-400 mb-6">
                    IMPROV BATTLE - LIVE
                </h2>
                <h3 className="text-xl font-medium text-purple-300 mb-4">
                    Contestant: {contestantName}
                </h3>
                
                <div className="h-64 overflow-y-auto bg-gray-700 p-4 rounded-xl mb-6 space-y-3">
                    {chatHistory.map((item, index) => (
                        <p key={index} className={`text-sm ${item.sender === 'Host' ? 'text-green-300' : 'text-blue-300'}`}>
                            <span className="font-bold">{item.sender}:</span> {item.message}
                        </p>
                    ))}
                </div>
                
                <p className="text-gray-400 text-sm italic">
                    (In this phase, the real conversation with the voice agent would begin through your microphone.)
                </p>
                <Button onClick={() => setConnectionState(CONNECTION_STATE.DISCONNECTED)} className="mt-6">
                    End Show
                </Button>
            </div>
        </div>
    );
}
