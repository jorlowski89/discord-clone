(() => {
    const messageList = document.querySelector(".message-list");

    if (messageList) {
        messageList.scrollTop = messageList.scrollHeight;
    }

    const messageForms = document.querySelectorAll(".message-form");
    const focusKey = "pycord-focus-composer";

    messageForms.forEach((form) => {
        const textarea = form.querySelector("textarea");

        if (!textarea) {
            return;
        }

        if (sessionStorage.getItem(focusKey) === window.location.pathname) {
            sessionStorage.removeItem(focusKey);
            textarea.focus({ preventScroll: true });
            if (messageList) {
                messageList.scrollTop = messageList.scrollHeight;
            }
        }

        textarea.addEventListener("keydown", (event) => {
            if (event.key !== "Enter" || event.shiftKey) {
                return;
            }

            event.preventDefault();
            sessionStorage.setItem(focusKey, window.location.pathname);
            if (form.requestSubmit) {
                form.requestSubmit();
            } else {
                form.submit();
            }
        });
    });

    const imagePickers = document.querySelectorAll("[data-image-picker]");

    imagePickers.forEach((picker) => {
        const input = picker.querySelector('input[type="file"]');
        const status = picker.querySelector("[data-image-status]");

        if (!input) {
            return;
        }

        input.addEventListener("change", () => {
            if (!status) {
                return;
            }

            const file = input.files && input.files[0];
            if (file) {
                status.textContent = file.name;
                status.classList.remove("d-none");
            } else {
                status.textContent = "";
                status.classList.add("d-none");
            }
        });
    });

    const recorderWidgets = document.querySelectorAll("[data-voice-recorder]");

    recorderWidgets.forEach((widget) => {
        const input = widget.querySelector('input[type="file"]');
        const startButton = widget.querySelector("[data-record-start]");
        const stopButton = widget.querySelector("[data-record-stop]");
        const clearButton = widget.querySelector("[data-record-clear]");
        const status = widget.querySelector("[data-record-status]");
        const preview = widget.querySelector("[data-record-preview]");
        const player = widget.querySelector("[data-record-player]");
        const playButton = widget.querySelector("[data-record-play]");
        const playIcon = widget.querySelector("[data-play-icon]");
        const pauseIcon = widget.querySelector("[data-pause-icon]");
        const timeLabel = widget.querySelector("[data-record-time]");
        const progress = widget.querySelector("[data-record-progress]");

        if (!input || !startButton || !stopButton || !clearButton || !preview) {
            return;
        }

        if (!navigator.mediaDevices || !window.MediaRecorder) {
            startButton.disabled = true;
            startButton.title = "Nagrywanie nie jest obsługiwane w tej przeglądarce.";
            return;
        }

        let recorder = null;
        let stream = null;
        let chunks = [];
        let previewUrl = null;

        const setButtonVisibility = (state) => {
            startButton.classList.toggle("d-none", state === "recording");
            stopButton.classList.toggle("d-none", state !== "recording");
            clearButton.classList.toggle("d-none", state !== "recorded");
        };

        const setRecordedFile = (blob) => {
            const extension = blob.type.includes("ogg") ? "ogg" : "webm";
            const file = new File([blob], `głosowka-${Date.now()}.${extension}`, {
                type: blob.type || "audio/webm",
            });
            const transfer = new DataTransfer();
            transfer.items.add(file);
            input.files = transfer.files;
        };

        const clearPreviewUrl = () => {
            if (previewUrl) {
                URL.revokeObjectURL(previewUrl);
                previewUrl = null;
            }
        };

        const stopStream = () => {
            if (stream) {
                stream.getTracks().forEach((track) => track.stop());
                stream = null;
            }
        };

        const formatTime = (seconds) => {
            if (!Number.isFinite(seconds)) {
                return "0:00";
            }

            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = Math.floor(seconds % 60).toString().padStart(2, "0");
            return `${minutes}:${remainingSeconds}`;
        };

        const setPlayingState = (isPlaying) => {
            if (playIcon) {
                playIcon.classList.toggle("d-none", isPlaying);
            }
            if (pauseIcon) {
                pauseIcon.classList.toggle("d-none", !isPlaying);
            }
        };

        const resetPlayer = () => {
            preview.pause();
            preview.currentTime = 0;
            setPlayingState(false);
            if (progress) {
                progress.value = 0;
            }
            if (timeLabel) {
                timeLabel.textContent = "0:00";
            }
        };

        if (playButton) {
            playButton.addEventListener("click", () => {
                if (preview.paused) {
                    preview.play();
                } else {
                    preview.pause();
                }
            });
        }

        preview.addEventListener("play", () => setPlayingState(true));
        preview.addEventListener("pause", () => setPlayingState(false));
        preview.addEventListener("ended", resetPlayer);
        preview.addEventListener("timeupdate", () => {
            if (timeLabel) {
                timeLabel.textContent = formatTime(preview.currentTime);
            }

            if (progress && Number.isFinite(preview.duration) && preview.duration > 0) {
                progress.value = Math.round((preview.currentTime / preview.duration) * 100);
            }
        });

        if (progress) {
            progress.addEventListener("input", () => {
                if (Number.isFinite(preview.duration) && preview.duration > 0) {
                    preview.currentTime = (Number(progress.value) / 100) * preview.duration;
                }
            });
        }

        startButton.addEventListener("click", async () => {
            try {
                clearPreviewUrl();
                chunks = [];
                resetPlayer();
                stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                recorder = new MediaRecorder(stream);

                recorder.addEventListener("dataavailable", (event) => {
                    if (event.data.size > 0) {
                        chunks.push(event.data);
                    }
                });

                recorder.addEventListener("stop", () => {
                    const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
                    setRecordedFile(blob);
                    clearPreviewUrl();
                    previewUrl = URL.createObjectURL(blob);
                    preview.src = previewUrl;
                    if (player) {
                        player.classList.remove("d-none");
                    }
                    if (status) {
                        status.textContent = "Głosówka gotowa";
                        status.classList.remove("d-none");
                    }
                    startButton.disabled = false;
                    stopButton.disabled = true;
                    clearButton.disabled = false;
                    setButtonVisibility("recorded");
                    stopStream();
                });

                recorder.start();
                startButton.disabled = true;
                stopButton.disabled = false;
                clearButton.disabled = true;
                setButtonVisibility("recording");
            } catch (error) {
                startButton.title = "Nie udało się włączyć mikrofonu.";
                startButton.disabled = false;
                stopButton.disabled = true;
                clearButton.disabled = true;
                setButtonVisibility("idle");
                stopStream();
            }
        });

        stopButton.addEventListener("click", () => {
            if (recorder && recorder.state === "recording") {
                recorder.stop();
            }
        });

        clearButton.addEventListener("click", () => {
            input.value = "";
            clearPreviewUrl();
            preview.removeAttribute("src");
            if (player) {
                player.classList.add("d-none");
            }
            resetPlayer();
            if (status) {
                status.textContent = "";
                status.classList.add("d-none");
            }
            clearButton.disabled = true;
            setButtonVisibility("idle");
        });

        setButtonVisibility("idle");
    });
})();
