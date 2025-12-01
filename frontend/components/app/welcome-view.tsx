<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Heaven Coffee Barista</title>
    <!-- Carga de Tailwind CSS para el estilizado rápido y responsivo -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Configuración de fuente y colores personalizados -->
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap');
        
        body {
            font-family: 'Inter', sans-serif;
            /* Color de fondo oscuro basado en la imagen */
            background-color: #3f305c; 
        }

        /* Estilo para el botón START CALL */
        .start-call-button {
            transition: all 0.2s;
            background-color: #8B5CF6; /* Violet-500 */
        }
        .start-call-button:hover {
            background-color: #7C3AED; /* Violet-600 */
            transform: scale(1.02);
            box-shadow: 0 10px 15px -3px rgba(139, 92, 246, 0.5), 0 4px 6px -2px rgba(139, 92, 246, 0.2);
        }

    </style>
</head>
<body class="h-screen w-screen flex flex-col justify-center items-center text-white">

    <!-- Contenedor Principal Centrado para simular la vista del navegador en la imagen -->
    <div class="flex flex-col items-center justify-center p-8 text-center w-full max-w-lg">
        
        <!-- Etiqueta CAFE (más pequeña) -->
        <p class="text-sm tracking-widest uppercase text-gray-400 mb-2">
            CAFE
        </p>

        <!-- Título Principal -->
        <h1 class="text-6xl md:text-8xl font-light tracking-tight mb-4">
            Heaven Coffee
        </h1>

        <!-- Subtítulo / Tagline -->
        <p class="text-lg md:text-xl text-gray-300 mb-12">
            Order in minutes with our AI barista
        </p>

        <!-- Botón START CALL -->
        <button id="start-call" class="start-call-button text-white font-semibold py-4 px-12 rounded-full shadow-lg">
            START CALL
        </button>

    </div>

    <!-- Texto del Footer -->
    <footer class="absolute bottom-4 text-xs text-gray-500">
        Built with LiveKit Agents
    </footer>

    <!-- Espacio para la lógica de JavaScript para iniciar la llamada (simulado) -->
    <script>
        document.getElementById('start-call').addEventListener('click', () => {
    
            console.log("Starting call to Heaven Coffee Barista Agent...");
            // En un entorno LiveKit real, aquí se iniciaría la conexión a la sala.
            
            // Para fines de la simulación de la UI:
            const button = document.getElementById('start-call');
            button.textContent = 'CONNECTING...';
            button.disabled = true;
            
            setTimeout(() => {
                button.textContent = 'CALL STARTED';
                // Aquí se integraría la lógica de la llamada de voz real.
            }, 1500);
        });
    </script>

</body>
</html>
