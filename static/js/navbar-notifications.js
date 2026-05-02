(() => {
    if (!window.WebSocket) {
        return;
    }

    const storageKey = "pycord-navbar-notifications";
    const defaultCounts = { channel: 0, direct: 0 };

    const readCounts = () => {
        try {
            return { ...defaultCounts, ...JSON.parse(localStorage.getItem(storageKey)) };
        } catch (error) {
            return { ...defaultCounts };
        }
    };

    const writeCounts = (counts) => {
        localStorage.setItem(storageKey, JSON.stringify(counts));
    };

    const renderCounts = (counts) => {
        Object.entries(counts).forEach(([kind, count]) => {
            const badge = document.querySelector(`[data-notification-badge="${kind}"]`);
            if (!badge) {
                return;
            }

            badge.textContent = count > 99 ? "99+" : String(count);
            badge.classList.toggle("d-none", count <= 0);
        });
    };

    const clearKind = (kind) => {
        const counts = readCounts();
        counts[kind] = 0;
        writeCounts(counts);
        renderCounts(counts);
    };

    const clearForCurrentPath = () => {
        const path = window.location.pathname;
        if (path.startsWith("/channels/dm/")) {
            clearKind("direct");
            return;
        }
        if (path.startsWith("/channels/")) {
            clearKind("channel");
        }
    };

    const increment = (kind) => {
        const counts = readCounts();
        counts[kind] = (counts[kind] || 0) + 1;
        writeCounts(counts);
        renderCounts(counts);
    };

    document.querySelectorAll("[data-notification-link]").forEach((link) => {
        link.addEventListener("click", () => clearKind(link.dataset.notificationLink));
    });

    renderCounts(readCounts());
    clearForCurrentPath();

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws/notifications/`);

    socket.addEventListener("message", (event) => {
        const payload = JSON.parse(event.data);
        const kind = payload.kind;

        if (!["channel", "direct"].includes(kind)) {
            return;
        }

        if (payload.url && window.location.pathname === payload.url) {
            return;
        }

        increment(kind);
    });
})();
