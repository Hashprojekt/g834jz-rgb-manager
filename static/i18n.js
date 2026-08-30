(() => {
    const EN = {
        "RGB, temperatury, wentylatory i profile ASUS": "RGB, temperatures, fans and ASUS profiles",
        "Profil ASUS": "ASUS profile",
        "Przełącz": "Switch",
        "Profile RGB": "RGB Profiles",
        "FINAL i CODZIENNY są chronione. Pozostałe możesz edytować lub kopiować.":
            "FINAL and CODZIENNY are protected. Other profiles can be edited or duplicated.",

        "+ Nowy profil": "+ New profile",
        "＋ Nowy profil": "＋ New profile",
        "NOWY PROFIL": "NEW PROFILE",
        "Utwórz profil RGB": "Create RGB profile",
        "Nazwa": "Name",
        "Profil bazowy": "Base profile",
        "Anuluj": "Cancel",
        "Utwórz": "Create",

        "chroniony": "protected",
        "aktywny": "active",
        "domyślny": "default",
        "Aktywuj": "Activate",
        "Aktywny ✓": "Active ✓",
        "Domyślny": "Default",
        "Domyślny ★": "Default ★",
        "Edytuj": "Edit",
        "🎨 Edytuj": "🎨 Edit",
        "Duplikuj": "Duplicate",
        "Usuń": "Delete",
        "Eksport": "Export",

        "Aktualny sprawdzony profil G834JZ": "Current verified G834JZ profile",
        "Spokojniejszy profil: klawisze 1–8 fioletowe":
            "Calmer profile: keys 1–8 are purple",

        "← Profile": "← Profiles",
        "EDYTOR RGB": "RGB EDITOR",
        "Cofnij": "Undo",
        "↶ Cofnij": "↶ Undo",
        "Ponów": "Redo",
        "↷ Ponów": "↷ Redo",
        "Eksportuj": "Export",

        "Wybrane klawisze": "Selected keys",
        "Kliknij klawisze poniżej": "Click the keys below",
        "Kolor": "Colour",
        "Zastosuj": "Apply",
        "Zaznacz:": "Select:",
        "Strzałki": "Arrows",
        "Modyfikatory": "Modifiers",
        "Numpad cały": "Full numpad",
        "Operatory numpada": "Numpad operators",
        "Wszystkie dostępne": "All available",
        "Wyczyść": "Clear",

        "edytowalny": "editable",
        "dynamiczny": "dynamic",
        "brak bezpiecznego mapowania": "no safe mapping",

        "ROG / F1–F12": "ROG / F1–F12",
        "Klawiatura główna + numpad": "Main keyboard + numpad",

        "PALETA PROFILU": "PROFILE PALETTE",
        "Kolory": "Colours",
        "Kliknij kolor, aby zaznaczyć klawisze używające go. Zmiana palety działa tylko na bezpiecznie zmapowanych klawiszach.":
            "Click a colour to select the keys using it. Palette changes affect only safely mapped keys.",

        "WARSTWA DYNAMICZNA": "DYNAMIC LAYER",
        "Chronione LED-y": "Protected LEDs",
        "RTX / temperatura": "RTX / temperature",
        "profil ASUS": "ASUS profile",
        "CPU / temperatura": "CPU / temperature",

        "CICHY": "SILENT",

        "Nieprawidłowy HEX.": "Invalid HEX value.",
        "Najpierw zaznacz klawisze.": "Select keys first.",
        "Nieprawidłowy kolor.": "Invalid colour.",
        "Kolor już był ustawiony.": "Colour was already set.",
        "Cofnięto zmianę.": "Change undone.",
        "Ponowiono zmianę.": "Change redone.",

        "Profil nie istnieje.": "Profile does not exist.",
        "Profil nie istnieje lub jest uszkodzony.":
            "Profile does not exist or is damaged.",
        "Profil chroniony nie może być edytowany.":
            "Protected profile cannot be edited.",
        "Profil chroniony nie może być usunięty.":
            "Protected profile cannot be deleted.",
        "Nie można usunąć aktywnego profilu.":
            "The active profile cannot be deleted.",
        "Nie można usunąć profilu domyślnego.":
            "The default profile cannot be deleted.",
        "Nie wybrano żadnych klawiszy.":
            "No keys selected.",
        "Nieprawidłowy kolor RGB.":
            "Invalid RGB colour."
    };

    const PL = Object.fromEntries(
        Object.entries(EN).map(([pl, en]) => [en, pl])
    );

    function getLang() {
        const saved = localStorage.getItem("g834jz-language");

        if (saved === "pl" || saved === "en")
            return saved;

        return navigator.language.toLowerCase().startsWith("pl")
            ? "pl"
            : "en";
    }

    let lang = getLang();

    function translateString(value) {
        if (!value)
            return value;

        let text = String(value);

        if (lang === "en") {
            if (EN[text])
                return EN[text];

            if (text.startsWith("Profil utworzony na podstawie: "))
                return text.replace(
                    "Profil utworzony na podstawie: ",
                    "Profile created from: "
                );

            if (/^\d+ kolorów$/.test(text))
                return text.replace(" kolorów", " colours");

            if (text.startsWith("monitor aktywny"))
                return text.replace("monitor aktywny", "monitor active");
        } else {
            if (PL[text])
                return PL[text];

            if (text.startsWith("Profile created from: "))
                return text.replace(
                    "Profile created from: ",
                    "Profil utworzony na podstawie: "
                );

            if (/^\d+ colours$/.test(text))
                return text.replace(" colours", " kolorów");
        }

        return text;
    }

    function translateNode(node) {
        if (node.nodeType !== Node.TEXT_NODE)
            return;

        const parent = node.parentElement;

        if (!parent ||
            ["SCRIPT", "STYLE", "TEXTAREA"].includes(parent.tagName))
            return;

        const old = node.nodeValue;
        const trimmed = old.trim();

        if (!trimmed)
            return;

        const translated = translateString(trimmed);

        if (translated !== trimmed) {
            node.nodeValue =
                old.slice(0, old.indexOf(trimmed)) +
                translated +
                old.slice(old.indexOf(trimmed) + trimmed.length);
        }
    }

    function translateElement(el) {
        if (!(el instanceof Element))
            return;

        if (el.placeholder)
            el.placeholder = translateString(el.placeholder);

        if (el.title)
            el.title = translateString(el.title);

        el.childNodes.forEach(translateNode);

        el.querySelectorAll("*").forEach(child => {
            if (child.placeholder)
                child.placeholder = translateString(child.placeholder);

            if (child.title)
                child.title = translateString(child.title);

            child.childNodes.forEach(translateNode);
        });

        // Kontekstowe przyciski tworzone przez dashboard.js.
        document.querySelectorAll('[data-action="rename"]').forEach(b => {
            b.textContent = lang === "en" ? "Rename" : "Nazwa";
        });

        document.querySelectorAll('[data-action="duplicate"]').forEach(b => {
            b.textContent = lang === "en" ? "Duplicate" : "Duplikuj";
        });

        document.querySelectorAll('[data-action="delete"]').forEach(b => {
            b.textContent = lang === "en" ? "Delete" : "Usuń";
        });

        document.documentElement.lang = lang;
    }

    function createSwitcher() {
        if (document.querySelector(".language-switch"))
            return;

        const container =
            document.querySelector(".top-actions") ||
            document.querySelector(".editor-header-actions");

        if (!container)
            return;

        const box = document.createElement("div");
        box.className = "language-switch";

        box.innerHTML = `
            <button type="button" data-lang="pl">PL</button>
            <span>/</span>
            <button type="button" data-lang="en">EN</button>
        `;

        container.prepend(box);

        box.querySelectorAll("button").forEach(button => {
            button.addEventListener("click", () => {
                lang = button.dataset.lang;
                localStorage.setItem("g834jz-language", lang);

                translateElement(document.body);
                updateSwitcher();
            });
        });

        updateSwitcher();
    }

    function updateSwitcher() {
        document.querySelectorAll(".language-switch button").forEach(b => {
            b.classList.toggle("active", b.dataset.lang === lang);
        });
    }

    const originalPrompt = window.prompt.bind(window);
    const originalConfirm = window.confirm.bind(window);

    window.prompt = (message, defaultValue) => {
        let m = translateString(message);

        if (lang === "en" && m === "Nazwa kopii:")
            m = "Copy name:";

        if (lang === "en" && m === "Nowa nazwa:")
            m = "New name:";

        return originalPrompt(m, defaultValue);
    };

    window.confirm = message => {
        let m = String(message);

        if (lang === "en" && m.startsWith("Usunąć profil"))
            m = m.replace("Usunąć profil", "Delete profile");

        return originalConfirm(m);
    };

    function init() {
        createSwitcher();
        translateElement(document.body);

        const observer = new MutationObserver(mutations => {
            for (const mutation of mutations) {
                for (const node of mutation.addedNodes) {
                    if (node.nodeType === Node.TEXT_NODE)
                        translateNode(node);
                    else if (node.nodeType === Node.ELEMENT_NODE)
                        translateElement(node);
                }
            }

            updateSwitcher();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    if (document.readyState === "loading")
        document.addEventListener("DOMContentLoaded", init);
    else
        init();
})();
