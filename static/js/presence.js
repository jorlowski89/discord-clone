(() => {
    const rows = Array.from(document.querySelectorAll("[data-presence-user]"));

    if (!rows.length) {
        return;
    }

    const userIds = Array.from(
        new Set(rows.map((row) => row.dataset.userId).filter(Boolean))
    );

    if (!userIds.length) {
        return;
    }

    const setPresence = (userId, isOnline) => {
        rows
            .filter((row) => row.dataset.userId === String(userId))
            .forEach((row) => {
                const dot = row.querySelector("[data-presence-dot]");
                const label = row.querySelector("[data-presence-label]");

                if (dot) {
                    dot.classList.toggle("online", isOnline);
                }
                if (label) {
                    label.textContent = isOnline ? "online" : "offline";
                }
            });
    };

    const refreshPresence = async () => {
        try {
            const response = await fetch(`/accounts/presence/?ids=${userIds.join(",")}`, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            if (!response.ok) {
                return;
            }

            const payload = await response.json();
            payload.users.forEach((user) => setPresence(user.id, user.online));
        } catch (error) {
            return;
        }
    };

    refreshPresence();
    setInterval(refreshPresence, 5000);
    document.addEventListener("visibilitychange", () => {
        if (!document.hidden) {
            refreshPresence();
        }
    });
})();
