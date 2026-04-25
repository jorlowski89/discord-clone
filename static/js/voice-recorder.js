(() => {
    const recorderWidgets = document.querySelectorAll("[data-voice-recorder]");

    recorderWidgets.forEach((widget) => {
        const input = widget.querySelector('input[type="file"]');
        const startButton = widget.querySelector("[data-record-start]");
        const stopButton = widget.querySelector("[data-record-stop]");
        const clearButton = widget.querySelector("[data-record-clear]");
        const status = widget.querySelector("[data-record-status]");
        const preview = widget.querySelector("[data-record-preview]");

        if (!input || !startButton || !stopButton || !clearButton || !status || !preview) {
            return;
        }

        if (!navigator.mediaDevices || !window.MediaRecorder) {
            startButton.disabled = true;
            status.textContent = "Nagrywanie nie jest obslugiwane w tej przegladarce.";
            return;
        }

        let recorder = null;
        let stream = null;
        let chunks = [];
        let previewUrl = null;

        const setRecordedFile = (blob) => {
            const extension = blob.type.includes("ogg") ? "ogg" : "webm";
            const file = new File([blob], `glosowka-${Date.now()}.${extension}`, {
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

        startButton.addEventListener("click", async () => {
            try {
                clearPreviewUrl();
                chunks = [];
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
                    preview.classList.remove("d-none");
                    status.textContent = "Nagranie gotowe do wyslania.";
                    startButton.disabled = false;
                    stopButton.disabled = true;
                    clearButton.disabled = false;
                    stopStream();
                });

                recorder.start();
                status.textContent = "Nagrywanie...";
                startButton.disabled = true;
                stopButton.disabled = false;
                clearButton.disabled = true;
            } catch (error) {
                status.textContent = "Nie udalo sie wlaczyc mikrofonu.";
                startButton.disabled = false;
                stopButton.disabled = true;
                clearButton.disabled = true;
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
            preview.classList.add("d-none");
            status.textContent = "Brak nagrania";
            clearButton.disabled = true;
        });
    });
})();
