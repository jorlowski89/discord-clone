(() => {
    const form = document.querySelector("[data-channel-composer]");
    const messageList = document.querySelector("[data-message-list]");

    if (!form || !messageList || !window.WebSocket) {
        return;
    }

    const slug = form.dataset.channelSlug;
    const textarea = form.querySelector("textarea");
    const imageInput = form.querySelector('input[name="image"]');
    const audioInput = form.querySelector('input[name="audio"]');

    if (!slug || !textarea) {
        return;
    }

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws/channels/${slug}/`);

    const scrollToBottom = () => {
        messageList.scrollTop = messageList.scrollHeight;
    };

    const hasFile = (input) => input && input.files && input.files.length > 0;

    const appendMessage = (message) => {
        const emptyState = messageList.querySelector(".empty-chat");
        if (emptyState) {
            emptyState.remove();
        }

        const article = document.createElement("article");
        article.className = "chat-message";

        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        if (message.avatar_url) {
            const avatarImage = document.createElement("img");
            avatarImage.src = message.avatar_url;
            avatarImage.alt = "";
            avatar.append(avatarImage);
        } else {
            avatar.textContent = (message.author || "?").slice(0, 1).toUpperCase();
        }

        const body = document.createElement("div");
        body.className = "message-body";

        const meta = document.createElement("div");
        meta.className = "d-flex flex-wrap align-items-baseline gap-2 mb-1";

        const author = document.createElement("strong");
        author.textContent = message.author;

        const createdAt = document.createElement("span");
        createdAt.className = "text-secondary small";
        createdAt.textContent = message.created_at;

        meta.append(author, createdAt);
        body.append(meta);

        if (message.content) {
            const content = document.createElement("p");
            content.className = "mb-2";
            content.style.whiteSpace = "pre-wrap";
            content.textContent = message.content;
            body.append(content);
        }

        if (message.image_url) {
            const image = document.createElement("img");
            image.className = "message-image";
            image.src = message.image_url;
            image.alt = "Obraz z wiadomosci";
            body.append(image);
        }

        if (message.audio_url) {
            const audio = document.createElement("audio");
            audio.className = "message-audio";
            audio.controls = true;

            const source = document.createElement("source");
            source.src = message.audio_url;
            audio.append(source);
            body.append(audio);
        }

        article.append(avatar, body);
        messageList.append(article);
        scrollToBottom();
    };

    socket.addEventListener("message", (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type === "message") {
            appendMessage(payload.message);
        }
    });

    form.addEventListener("submit", (event) => {
        const content = textarea.value.trim();

        if (hasFile(imageInput) || hasFile(audioInput)) {
            return;
        }

        if (!content) {
            event.preventDefault();
            return;
        }

        if (socket.readyState !== WebSocket.OPEN) {
            return;
        }

        event.preventDefault();
        sessionStorage.removeItem("pycord-focus-composer");
        socket.send(JSON.stringify({ content }));
        textarea.value = "";
        textarea.focus({ preventScroll: true });
    });
})();
