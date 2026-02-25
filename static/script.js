document.addEventListener("DOMContentLoaded", () => {
    const fileInput = document.getElementById("file-input");
    const uploadZone = document.getElementById("upload-zone");
    const uploadStatus = document.getElementById("upload-status");
    const uploadedFilename = document.getElementById("uploaded-filename");
    const refTextContainer = document.getElementById("ref-text-container");
    const refTextInput = document.getElementById("ref-text-input");

    const step2 = document.getElementById("step2");
    const textInput = document.getElementById("text-input");
    const generateBtn = document.getElementById("generate-btn");
    const loadingState = document.getElementById("loading");

    const historyBlock = document.getElementById("history-block");
    const historyList = document.getElementById("history-list");

    let currentRefAudioPath = null;

    // File Selection Handling
    fileInput.addEventListener("change", async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Visual feedback
        uploadZone.querySelector("p").innerText = "오디오 분석 및 기계학습 전사(STT) 진행 중...";

        try {
            const formData = new FormData();
            formData.append("file", file);

            const req = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });
            const res = await req.json();

            if (req.ok && res.ref_audio_path) {
                currentRefAudioPath = res.ref_audio_path;

                // Update UI: unlock Step 2
                uploadZone.classList.add("hidden");
                uploadStatus.classList.remove("hidden");
                uploadedFilename.innerText = `업로드 완료: ${file.name}`;
                refTextContainer.classList.remove("hidden");

                // Auto-fill transcription
                if (res.auto_transcription) {
                    refTextInput.value = res.auto_transcription;
                }

                step2.classList.remove("disabled");
                textInput.disabled = false;
                generateBtn.disabled = false;
                textInput.focus();
            } else {
                alert(`오류: ${res.detail}`);
                uploadZone.querySelector("p").innerText = "다시 시도해주세요.";
            }

        } catch (err) {
            console.error(err);
            alert("업로드 중 문제가 발생했습니다.");
            uploadZone.querySelector("p").innerText = "클릭하여 파일 업로드";
        }
    });

    // Generation Handling
    generateBtn.addEventListener("click", async () => {
        const text = textInput.value.trim();
        const refText = refTextInput.value.trim();
        if (!text) {
            alert("합성할 텍스트를 입력해주세요.");
            return;
        }
        if (!refText) {
            alert("업로드한 음성의 실제 대본을 1단계에 입력해주세요.");
            return;
        }

        // Lock UI
        generateBtn.disabled = true;
        textInput.disabled = true;
        loadingState.classList.remove("hidden");

        try {
            const formData = new FormData();
            formData.append("text", text);
            formData.append("ref_text", refText);
            formData.append("ref_audio_path", currentRefAudioPath);

            const req = await fetch("/api/generate", {
                method: "POST",
                body: formData
            });
            const res = await req.json();

            if (req.ok) {
                // Success: append to history
                appendHistoryItem(text, res.url, res.timestamp, res.time_taken);

                // Clear input for next run
                textInput.value = "";
            } else {
                alert(`오류: ${res.detail}`);
            }

        } catch (err) {
            console.error(err);
            alert("서버 연결에 실패했습니다.");
        } finally {
            // Unlock UI
            generateBtn.disabled = false;
            textInput.disabled = false;
            loadingState.classList.add("hidden");
            textInput.focus();
        }
    });

    // Enter Key to submit
    textInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (!generateBtn.disabled) generateBtn.click();
        }
    });

    function appendHistoryItem(text, audioUrl, timestamp, timeTaken) {
        historyBlock.classList.remove("hidden");

        const card = document.createElement("div");
        card.className = "history-card";

        card.innerHTML = `
            <div class="meta">${timestamp} (소요시간: ${timeTaken}초)</div>
            <p>${text}</p>
            <audio controls src="${audioUrl}"></audio>
        `;

        // Add to top of list
        historyList.prepend(card);
    }
});
