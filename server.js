const express = require('express');
const app = express();
const http = require('http').Server(app);
const path = require('path');
const os = require('os'); // Added to find your IP automatically
const io = require("socket.io")(http, {
    cors: { origin: "*" },
    maxHttpBufferSize: 1e8, 
    pingTimeout: 5000,
    pingInterval: 10000
});

// --- HELPER: GET LOCAL IP ADDRESS ---
function getLocalIP() {
    const interfaces = os.networkInterfaces();
    for (const name of Object.keys(interfaces)) {
        for (const iface of interfaces[name]) {
            if (iface.family === 'IPv4' && !iface.internal) {
                return iface.address;
            }
        }
    }
    return 'localhost';
}

// --- ROUTES ---

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// Download the compiled agent.exe
app.get('/download-agent', (req, res) => {
    const filePath = path.join(__dirname, 'agent.exe');
    res.download(filePath, 'agent.exe', (err) => {
        if (err) {
            console.error("❌ ERROR: agent.exe NOT FOUND! Ensure you compiled it and put it in this folder.");
            res.status(404).send("Agent file not found on server.");
        }
    });
});

// --- SOCKET LOGIC ---

io.on("connection", (socket) => {
    console.log(`📡 Device Connected: ${socket.id}`);

    socket.on("agent-ready", () => {
        socket.join("agents");
        console.log(`🖥️  Remote Agent is Ready (Socket: ${socket.id})`);
    });

    socket.on("create-meeting", () => {
        const room = Math.floor(100000 + Math.random() * 900000).toString();
        socket.join(room);
        socket.emit("meeting-created", room);
        
        // Signal the agent to start capturing for this specific room
        io.to("agents").emit("start-streaming", { room });
        console.log(`✨ Meeting Session Created: ${room}`);
    });

    socket.on("join-meeting", (room) => {
        if (room) {
            socket.join(room);
            console.log(`👤 Viewer/Agent joined room: ${room}`);
        }
    });

    // Screen relay (volatile drops old frames if network is slow)
    socket.on("screen-data", (data) => {
        socket.to(data.room).volatile.emit("screen-data", data);
    });

    // Input relays
    socket.on("mouse-event", (data) => {
        socket.to(data.room).emit("mouse-event", data);
    });

    socket.on("keyboard-event", (data) => {
        socket.to(data.room).emit("keyboard-event", data);
    });

    socket.on("disconnect", (reason) => {
        console.log(`🔌 Device Disconnected: ${socket.id}`);
    });
});

// --- START SERVER ---

const PORT = 3000;
const MY_IP = getLocalIP();

http.listen(PORT, '0.0.0.0', () => {
    console.log("\n" + "=".repeat(40));
    console.log(`🚀 SUDHANSHU REMOTE CONTROL SERVER`);
    console.log(`✅ STATUS: ACTIVE`);
    console.log(`🌐 SHARE THIS URL: http://${MY_IP}:${PORT}`);
    console.log("=".repeat(40) + "\n");
    console.log("Press Ctrl+C to stop the server.");
});