import React from 'react';

// --- UTILIDADES MOCK ---
const cn = (...classes) => classes.filter(Boolean).join(' ');

/**
 * Componente Button Mock: Adaptado con colores de bienestar (Teal/Esmeralda)
 */
const Button = ({ children, onClick, className, variant = 'default', size = 'default' }) => {
  const baseClasses = 'inline-flex items-center justify-center whitespace-nowrap rounded-2xl text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50';

  const sizeClasses = {
    default: 'h-11 px-5 py-2',
    sm: 'h-9 px-3',
    lg: 'h-14 px-10 text-lg',
  }[size];

  const variantClasses = {
    default: 'bg-emerald-100 text-emerald-900 hover:bg-emerald-200',
    primary: 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/20 hover:bg-emerald-500 hover:-translate-y-0.5 active:translate-y-0',
  }[variant];

  return (
    <button
      onClick={onClick}
      className={cn(baseClasses, sizeClasses, variantClasses, className)}
    >
      {children}
    </button>
  );
};

/**
 * Icono Aura (Loto/Naturaleza) para un ambiente de paz.
 */
function AuraIcon() {
  return (
    <div className="relative mb-8">
      {/* Efecto de aura pulsante en el fondo */}
      <div className="absolute inset-0 bg-emerald-500/20 rounded-full blur-3xl animate-pulse"></div>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="80"
        height="80"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-emerald-400 relative z-10 drop-shadow-sm"
      >
        <path d="M12 3c-1.2 0-2.4.6-3 1.7A5 5 0 0 0 2 9c0 2.8 2.2 5 5 5h10c2.8 0 5-2.2 5-5a5 5 0 0 0-7-4.3c-.6-1.1-1.8-1.7-3-1.7z"></path>
        <path d="M12 21v-7"></path>
        <path d="m9 18 3 3 3-3"></path>
      </svg>
    </div>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

/**
 * Vista de Bienvenida de Aura: Wellness Companion
 */
export const WelcomeView = React.forwardRef<HTMLDivElement, WelcomeViewProps>(
  ({ startButtonText, onStartCall }, ref) => {
    return (
      <div 
        ref={ref} 
        className="min-h-screen w-full flex items-center justify-center p-6 bg-slate-950 text-slate-100 font-sans selection:bg-emerald-500/30"
      >
        <section className="
          bg-slate-900/60 backdrop-blur-xl p-10 md:p-14 
          rounded-[2.5rem] shadow-2xl border border-slate-800
          flex flex-col items-center justify-center text-center max-w-xl w-full
        ">
          
          <AuraIcon />

          <h1 className="text-4xl sm:text-5xl font-light text-white mb-3 tracking-tight">
            I'm <span className="font-semibold text-emerald-400">Aura</span>
          </h1>
          
          <p className="text-emerald-100/60 text-lg mb-8 font-light">
            Your gentle companion for mindfulness, <br />growth, and daily reflection.
          </p>

          <div className="space-y-4 w-full max-w-sm mb-10">
            {/* Tarjeta informativa sobre la memoria de sesión */}
            <div className="bg-emerald-950/30 border border-emerald-500/20 p-4 rounded-2xl text-left">
              <div className="flex items-start gap-3">
                <div className="mt-1 text-emerald-400 italic">
                   <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 8v4l3 3m6-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0z"/></svg>
                </div>
                <p className="text-sm text-emerald-100/80 leading-relaxed">
                  <strong>Session Memory Active:</strong> I remember our previous talks to help you track your mood and wellness goals over time.
                </p>
              </div>
            </div>
          </div>

          <Button 
            variant="primary" 
            size="lg" 
            onClick={onStartCall} 
            className="w-full max-w-xs shadow-emerald-500/10"
          >
            {startButtonText || "Start Session"}
          </Button>
          
          <p className="mt-6 text-slate-500 text-xs uppercase tracking-[0.2em]">
            Take a deep breath and begin
          </p>
        </section>
        
        {/* Footer con estado */}
        <div className="fixed bottom-6 left-0 w-full flex justify-center">
          <div className="bg-slate-900/80 px-4 py-2 rounded-full border border-slate-800 flex items-center gap-3">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-slate-400 text-[10px] font-bold tracking-widest uppercase">
              Aura is Online & Ready
            </span>
          </div>
        </div>
      </div>
    );
  }
);

export { WelcomeView as default };
