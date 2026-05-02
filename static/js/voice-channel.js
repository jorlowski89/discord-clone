(() => {
    const panel = document.querySelector("[data-voice-channel]");

    if (!panel || !window.WebSocket) {
        return;
    }

    const slug = panel.dataset.channelSlug;
    const currentUserId = Number(panel.dataset.currentUserId);
    const joinButton = panel.querySelector("[data-voice-join]");
    const leaveButton = panel.querySelector("[data-voice-leave]");
    const status = panel.querySelector("[data-voice-status]");
    const participantCount = panel.querySelector("[data-voice-count]");
    const participants = panel.querySelector("[data-voice-participants]");
    const remoteAudio = panel.querySelector("[data-voice-remote-audio]");
    const peers = new Map();

    let socket = null;
    let localStream = null;
    let isInVoice = false;

    const setStatus = (message) => {
        if (status) {
            status.textContent = message;
        }
    };

    const setActive = (isActive) => {
        if (!joinButton || !leaveButton) {
            return;
        }

        joinButton.classList.toggle("d-none", isActive);
        leaveButton.classList.toggle("d-none", !isActive);
        leaveButton.disabled = !isActive;
    };

    const participantId = (userId) => `voice-user-${userId}`;

    const updateParticipantCount = () => {
        if (!participantCount || !participants) {
            return;
        }

        const count = participants.querySelectorAll(".voice-participant").length;
        participantCount.textContent = `W rozmówie: ${count}`;
    };

    const displayName = (userId, username) => (
        Number(userId) === currentUserId ? "Ty" : username
    );

    const addParticipant = (userId, username) => {
        if (!participants || participants.querySelector(`#${participantId(userId)}`)) {
            return;
        }

        const item = document.createElement("span");
        item.id = participantId(userId);
        item.className = "voice-participant";
        item.textContent = displayName(userId, username);
        participants.append(item);
        updateParticipantCount();
    };

    const replaceParticipants = (items) => {
        if (!participants) {
            return;
        }

        participants.textContent = "";
        items.forEach((item) => addParticipant(item.user_id, item.username));
        updateParticipantCount();
    };

    const removeParticipant = (userId) => {
        const item = participants && participants.querySelector(`#${participantId(userId)}`);
        if (item) {
            item.remove();
            updateParticipantCount();
        }
    };

    const sendSignal = (payload) => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify(payload));
        }
    };

    const createPeer = (userId, username) => {
        if (peers.has(userId)) {
            return peers.get(userId);
        }

        addParticipant(userId, username);

        const peer = new RTCPeerConnection({
            iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
        });

        if (localStream) {
            localStream.getTracks().forEach((track) => {
                peer.addTrack(track, localStream);
            });
        }

        peer.addEventListener("icecandidate", (event) => {
            if (event.candidate) {
                sendSignal({
                    type: "ice_candidate",
                    target_user_id: userId,
                    candidate: event.candidate,
                });
            }
        });

        peer.addEventListener("track", (event) => {
            if (!remoteAudio) {
                return;
            }

            let audio = remoteAudio.querySelector(`[data-peer-id="${userId}"]`);
            if (!audio) {
                audio = document.createElement("audio");
                audio.dataset.peerId = userId;
                audio.autoplay = true;
                audio.controls = false;
                remoteAudio.append(audio);
            }
            audio.srcObject = event.streams[0];
        });

        peer.addEventListener("connectionstatechange", () => {
            if (["closed", "disconnected", "failed"].includes(peer.connectionState)) {
                closePeer(userId);
            }
        });

        peers.set(userId, peer);
        return peer;
    };

    const closePeer = (userId) => {
        const peer = peers.get(userId);
        if (peer) {
            peer.close();
            peers.delete(userId);
        }

        const audio = remoteAudio && remoteAudio.querySelector(`[data-peer-id="${userId}"]`);
        if (audio) {
            audio.remove();
        }
    };

    const closeAllPeers = () => {
        Array.from(peers.keys()).forEach(closePeer);
    };

    const handleSignal = async (payload) => {
        if (payload.type === "voice_presence") {
            replaceParticipants(payload.participants || []);
            return;
        }

        const senderId = Number(payload.sender_user_id || payload.user_id);
        const targetId = Number(payload.target_user_id || 0);

        if (!senderId || senderId === currentUserId) {
            return;
        }

        if (targetId && targetId !== currentUserId) {
            return;
        }

        if (payload.type === "user_joined") {
            addParticipant(senderId, payload.username);
            if (!isInVoice) {
                return;
            }

            const peer = createPeer(senderId, payload.username);
            const offer = await peer.createOffer();
            await peer.setLocalDescription(offer);
            sendSignal({
                type: "offer",
                target_user_id: senderId,
                description: peer.localDescription,
            });
            return;
        }

        if (payload.type === "user_left" || payload.type === "leave") {
            closePeer(senderId);
            removeParticipant(senderId);
            return;
        }

        if (!isInVoice) {
            return;
        }

        if (payload.type === "offer") {
            const peer = createPeer(senderId, payload.sender_username);
            await peer.setRemoteDescription(payload.description);
            const answer = await peer.createAnswer();
            await peer.setLocalDescription(answer);
            sendSignal({
                type: "answer",
                target_user_id: senderId,
                description: peer.localDescription,
            });
            return;
        }

        if (payload.type === "answer") {
            const peer = peers.get(senderId);
            if (peer && !peer.currentRemoteDescription) {
                await peer.setRemoteDescription(payload.description);
            }
            return;
        }

        if (payload.type === "ice_candidate") {
            const peer = peers.get(senderId);
            if (peer && payload.candidate) {
                await peer.addIceCandidate(payload.candidate);
            }
        }
    };

    const connectSocket = () => {
        if (socket && socket.readyState !== WebSocket.CLOSED) {
            return;
        }

        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        socket = new WebSocket(`${protocol}://${window.location.host}/ws/voice/${slug}/`);

        socket.addEventListener("open", () => {
            if (!isInVoice) {
                setStatus("Gotowy do rozmówy audio.");
            }
        });

        socket.addEventListener("message", async (event) => {
            const payload = JSON.parse(event.data);
            try {
                await handleSignal(payload);
            } catch (error) {
                setStatus("Nie udało się zestawić połączenia audio");
            }
        });

        socket.addEventListener("close", () => {
            if (localStream) {
                localStream.getTracks().forEach((track) => track.stop());
                localStream = null;
            }

            isInVoice = false;
            closeAllPeers();
            setActive(false);
            socket = null;
        });
    };

    const waitForOpenSocket = () => new Promise((resolve, reject) => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            resolve();
            return;
        }

        connectSocket();

        if (!socket) {
            reject();
            return;
        }

        socket.addEventListener("open", resolve, { once: true });
        socket.addEventListener("error", reject, { once: true });
    });

    const leaveVoice = () => {
        sendSignal({ type: "leave" });

        if (localStream) {
            localStream.getTracks().forEach((track) => track.stop());
            localStream = null;
        }

        closeAllPeers();
        isInVoice = false;
        setActive(false);
        setStatus("Rozłączono");
    };

    const joinVoice = async () => {
        if (!joinButton) {
            return;
        }

        joinButton.disabled = true;
        setStatus("Łączenie z mikrofonem...");

        try {
            await waitForOpenSocket();
            localStream = await navigator.mediaDevices.getUserMedia({
                audio: true,
                video: false,
            });

            isInVoice = true;
            sendSignal({ type: "join_voice" });
            setActive(true);
            setStatus("Połączono z kanałum głosowym");
            joinButton.disabled = false;
        } catch (error) {
            setStatus("Nie udało się włączyć mikrofonu");
            joinButton.disabled = false;
            setActive(false);
        }
    };

    connectSocket();

    if (!joinButton || !leaveButton) {
        return;
    }

    if (
        !window.RTCPeerConnection
        || !navigator.mediaDevices
        || !navigator.mediaDevices.getUserMedia
    ) {
        joinButton.disabled = true;
        setStatus("Ta przeglądarka nie obsługuje rozmów głosowych");
        return;
    }

    joinButton.addEventListener("click", joinVoice);
    leaveButton.addEventListener("click", leaveVoice);
    window.addEventListener("beforeunload", leaveVoice);
})();
