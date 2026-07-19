// 3pseat Soundboard — vanilla JS (no jQuery / Materialize).
//
// Handles: mobile nav toggle, Discord playback with feedback, in-browser
// preview, search/sort/filter, entrance-sound toggle, localized dates, and the
// add-sound modal (tabs + upload).

(function () {
  "use strict";

  // ---------- Toasts ----------

  function toast(message, kind, emoji) {
    let stack = document.querySelector(".toast-stack");
    if (!stack) {
      stack = document.createElement("div");
      stack.className = "toast-stack";
      stack.setAttribute("role", "status");
      stack.setAttribute("aria-live", "polite");
      document.body.appendChild(stack);
    }
    const el = document.createElement("div");
    el.className = "toast" + (kind ? " " + kind : "");

    const text = document.createElement("span");
    text.className = "toast-text";
    text.textContent = message;
    el.appendChild(text);

    if (emoji) {
      const em = document.createElement("span");
      em.className = "toast-emoji";
      em.textContent = emoji;
      el.appendChild(em);
    }

    stack.appendChild(el);
    // Remove after the CSS out-animation finishes (3s delay + 0.25s).
    setTimeout(function () {
      el.remove();
    }, 3400);
  }

  // ---------- Playback ----------

  async function play(button) {
    const url = button.dataset.url;
    const name = button.dataset.name || "sound";
    if (!url || button.disabled) return;

    button.classList.remove("playing");
    // Force reflow so the animation can retrigger on rapid clicks.
    void button.offsetWidth;
    button.classList.add("playing");
    button.disabled = true;

    try {
      const response = await fetch(url, { method: "POST" });
      if (response.ok) {
        toast("Playing " + name, "success", "🔊");
      } else {
        const text = await response.text();
        toast(text || "Could not play that sound.", "error");
      }
    } catch (err) {
      toast("Network error while playing the sound.", "error");
    } finally {
      button.disabled = false;
    }
  }

  // ---------- Search, sort & filter ----------

  function initView() {
    const grid = document.getElementById("sound-grid");
    if (!grid) return;

    const input = document.getElementById("sound-search");
    const sortSelect = document.getElementById("sound-sort");
    const chips = Array.from(document.querySelectorAll(".chip[data-filter]"));
    const empty = document.getElementById("empty-state");
    const cards = Array.from(grid.querySelectorAll("[data-search]"));

    function activeFilters() {
      return chips
        .filter(function (c) {
          return c.classList.contains("active");
        })
        .map(function (c) {
          return c.dataset.filter;
        });
    }

    function sortCards() {
      const mode = sortSelect ? sortSelect.value : "name";
      const sorted = cards.slice().sort(function (a, b) {
        if (mode === "newest") {
          return (
            parseFloat(b.dataset.created) - parseFloat(a.dataset.created)
          );
        }
        if (mode === "author") {
          return (
            a.dataset.author.localeCompare(b.dataset.author) ||
            a.dataset.name.localeCompare(b.dataset.name)
          );
        }
        return a.dataset.name.localeCompare(b.dataset.name);
      });
      // Re-append in sorted order (moves existing nodes, no re-create).
      sorted.forEach(function (card) {
        grid.appendChild(card);
      });
    }

    function applyView() {
      const q = input ? input.value.trim().toLowerCase() : "";
      const filters = activeFilters();
      let visible = 0;
      cards.forEach(function (card) {
        let match = card.dataset.search.indexOf(q) !== -1;
        if (match && filters.indexOf("youtube") !== -1) {
          match = card.dataset.youtube === "1";
        }
        if (match && filters.indexOf("entrance") !== -1) {
          match = card.dataset.entrance === "1";
        }
        card.style.display = match ? "" : "none";
        if (match) visible += 1;
      });
      if (empty) empty.style.display = visible === 0 ? "block" : "none";
    }

    if (input) input.addEventListener("input", applyView);
    if (sortSelect) {
      sortSelect.addEventListener("change", function () {
        sortCards();
        applyView();
      });
    }
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        const on = chip.classList.toggle("active");
        chip.setAttribute("aria-pressed", on ? "true" : "false");
        applyView();
      });
    });

    sortCards();
    applyView();
  }

  // ---------- Entrance sound toggle ----------

  function initEntrance() {
    const buttons = Array.from(document.querySelectorAll(".entrance-btn"));
    if (buttons.length === 0) return;

    buttons.forEach(function (btn) {
      btn.addEventListener("click", async function () {
        try {
          const response = await fetch(btn.dataset.url, { method: "POST" });
          if (!response.ok) {
            const text = await response.text();
            toast(text || "Could not update your entrance sound.", "error");
            return;
          }
          const data = await response.json();
          // Only one entrance sound per guild: clear the others.
          buttons.forEach(function (b) {
            b.classList.remove("active");
            b.setAttribute("aria-pressed", "false");
          });
          if (data.active) {
            btn.classList.add("active");
            btn.setAttribute("aria-pressed", "true");
            toast("Entrance sound set to " + data.name, "success", "⭐");
          } else {
            toast("Entrance sound cleared.", "success");
          }
        } catch (err) {
          toast("Network error updating your entrance sound.", "error");
        }
      });
    });
  }

  // ---------- In-browser preview ----------

  function initPreview() {
    const buttons = Array.from(document.querySelectorAll(".preview-btn"));
    if (buttons.length === 0) return;

    const audio = new Audio();
    let currentBtn = null;

    function stop() {
      audio.pause();
      audio.removeAttribute("src");
      if (currentBtn) currentBtn.classList.remove("playing");
      currentBtn = null;
    }

    audio.addEventListener("ended", stop);
    audio.addEventListener("error", function () {
      if (currentBtn) {
        toast("Could not preview that sound.", "error");
        stop();
      }
    });

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        // Clicking the one that's playing stops it.
        if (currentBtn === btn) {
          stop();
          return;
        }
        stop();
        audio.src = btn.dataset.url;
        const started = audio.play();
        if (started && typeof started.catch === "function") {
          started.catch(function () {
            /* handled by the error listener */
          });
        }
        currentBtn = btn;
        btn.classList.add("playing");
      });
    });
  }

  // ---------- Localized dates ----------

  function initDates() {
    const els = document.querySelectorAll(".js-date[data-ts]");
    els.forEach(function (el) {
      const ts = parseFloat(el.dataset.ts);
      if (!isFinite(ts)) return;
      const date = new Date(ts * 1000);
      if (isNaN(date.getTime())) return;
      el.textContent = date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
      el.setAttribute("datetime", date.toISOString());
    });
  }

  // ---------- Navbar (mobile) ----------

  function initNav() {
    const toggle = document.querySelector(".nav-toggle");
    const links = document.querySelector(".nav-links");
    if (!toggle || !links) return;
    toggle.addEventListener("click", function () {
      links.classList.toggle("open");
    });
  }

  // ---------- Add-sound modal ----------

  function initModal() {
    const overlay = document.getElementById("add-sound-modal");
    if (!overlay) return;

    function open() {
      overlay.classList.add("open");
    }
    function close() {
      overlay.classList.remove("open");
    }

    document.querySelectorAll("[data-open-modal]").forEach(function (el) {
      el.addEventListener("click", open);
    });
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) close();
    });
    overlay.querySelectorAll("[data-close]").forEach(function (el) {
      el.addEventListener("click", close);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") close();
    });

    // Tabs
    let activeTab = "youtube";
    const tabs = overlay.querySelectorAll(".tab");
    const panels = overlay.querySelectorAll(".tab-panel");
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        activeTab = tab.dataset.tab;
        tabs.forEach(function (t) {
          t.classList.toggle("active", t === tab);
        });
        panels.forEach(function (p) {
          p.classList.toggle("active", p.dataset.tab === activeTab);
        });
      });
    });

    // Reflect chosen file names.
    overlay.querySelectorAll('input[type="file"]').forEach(function (input) {
      input.addEventListener("change", function () {
        const label = input
          .closest(".file-drop")
          .querySelector(".file-name");
        if (label) {
          label.textContent = input.files.length
            ? input.files[0].name
            : label.dataset.placeholder || "";
        }
      });
    });

    // Submit
    const form = document.getElementById("add-sound-form");
    const submit = document.getElementById("add-sound-submit");
    const progress = document.getElementById("upload-progress");

    async function upload() {
      const name = document.getElementById("sound-name").value.trim();
      const description = document
        .getElementById("sound-description")
        .value.trim();

      const data = new FormData();
      data.append("name", name);
      data.append("description", description);

      if (activeTab === "mp3") {
        const file = document.getElementById("sound-file").files[0];
        if (!file) return toast("Please choose an MP3 file.", "error");
        data.append("file", file);
      } else if (activeTab === "video") {
        const file = document.getElementById("sound-file-video").files[0];
        if (!file) return toast("Please choose a video file.", "error");
        data.append("file", file);
      } else {
        const link = document.getElementById("sound-link").value.trim();
        if (!link) return toast("Please enter a YouTube link.", "error");
        data.append("link", link);
      }

      submit.disabled = true;
      if (progress) progress.classList.add("show");

      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: data,
        });
        if (response.ok) {
          toast("Sound added!", "success", "🎉");
          setTimeout(function () {
            location.reload();
          }, 600);
        } else {
          const text = await response.text();
          submit.disabled = false;
          if (progress) progress.classList.remove("show");
          toast(text || "Failed to upload the sound.", "error");
        }
      } catch (err) {
        submit.disabled = false;
        if (progress) progress.classList.remove("show");
        toast("Network error during upload.", "error");
      }
    }

    if (submit) submit.addEventListener("click", upload);
  }

  // ---------- Wire up ----------

  document.addEventListener("DOMContentLoaded", function () {
    initNav();
    initView();
    initModal();
    initDates();
    initEntrance();
    initPreview();

    document.querySelectorAll(".play-btn").forEach(function (button) {
      button.addEventListener("click", function () {
        play(button);
      });
    });
  });
})();
