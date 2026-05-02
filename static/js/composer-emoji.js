(() => {
    const pickers = document.querySelectorAll("[data-emoji-picker]");

    pickers.forEach((picker) => {
        const form = picker.closest("form");
        const textarea = form && form.querySelector("textarea");
        const toggle = picker.querySelector("[data-emoji-toggle]");
        const menu = picker.querySelector("[data-emoji-menu]");

        if (!textarea || !toggle || !menu) {
            return;
        }

        const closeMenu = () => menu.classList.add("d-none");

        toggle.addEventListener("click", () => {
            menu.classList.toggle("d-none");
        });

        menu.querySelectorAll("[data-emoji]").forEach((button) => {
            button.addEventListener("click", () => {
                const emoji = button.dataset.emoji || "";
                const start = textarea.selectionStart || 0;
                const end = textarea.selectionEnd || 0;
                const before = textarea.value.slice(0, start);
                const after = textarea.value.slice(end);

                textarea.value = `${before}${emoji}${after}`;
                textarea.focus({ preventScroll: true });
                textarea.selectionStart = start + emoji.length;
                textarea.selectionEnd = start + emoji.length;
                closeMenu();
            });
        });

        document.addEventListener("click", (event) => {
            if (!picker.contains(event.target)) {
                closeMenu();
            }
        });
    });
})();
