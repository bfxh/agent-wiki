/* agent-wiki 站点交互：搜索 + 传输层抽屉。零依赖，纯本地数据。 */
(function () {
  "use strict";

  function $(selector) {
    return document.querySelector(selector);
  }

  // ---------------------------------------------------------------- 搜索
  var searchInput = $("#wiki-search");
  var searchResults = $("#search-results");
  var searchIndex = Array.isArray(window.SEARCH_INDEX) ? window.SEARCH_INDEX : [];

  function renderSearch(query) {
    if (!searchResults) return;
    var q = String(query || "").trim().toLowerCase();
    searchResults.textContent = "";

    if (!q) {
      searchResults.hidden = true;
      return;
    }

    var hits = searchIndex
      .filter(function (page) {
        var haystack = [
          page.title,
          page.summary,
          (page.tags || []).join(" "),
          page.text,
        ]
          .join(" ")
          .toLowerCase();
        return haystack.indexOf(q) !== -1;
      })
      .slice(0, 8);

    if (!hits.length) {
      var empty = document.createElement("div");
      empty.className = "search-empty";
      empty.textContent = "没有匹配";
      searchResults.appendChild(empty);
    } else {
      hits.forEach(function (page) {
        var link = document.createElement("a");
        link.href = String(page.slug) + ".html";

        var title = document.createElement("strong");
        title.textContent = String(page.title == null ? "" : page.title);
        link.appendChild(title);

        var snippet = document.createElement("span");
        snippet.className = "snippet";
        snippet.textContent = String(page.summary == null ? "" : page.summary);
        link.appendChild(snippet);

        searchResults.appendChild(link);
      });
    }
    searchResults.hidden = false;
  }

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      renderSearch(searchInput.value);
    });
    searchInput.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        searchInput.value = "";
        renderSearch("");
        searchInput.blur();
      }
      if (event.key === "Enter") {
        var first = searchResults && searchResults.querySelector("a");
        if (first) first.click();
      }
    });
  }

  document.addEventListener("click", function (event) {
    if (!searchResults || !searchInput) return;
    if (event.target !== searchInput && !searchResults.contains(event.target)) {
      searchResults.hidden = true;
    }
  });

  // ---------------------------------------------------------------- 传输层
  var events = Array.isArray(window.TRANSPORT_EVENTS) ? window.TRANSPORT_EVENTS : [];
  var badge = $("#tx-badge");
  var count = $("#tx-count");
  var drawer = $("#tx-drawer");
  var overlay = $("#tx-overlay");
  var closeButton = $("#tx-close");
  var filter = $("#tx-filter");
  var list = $("#tx-list");
  var isOpen = false;

  if (count) count.textContent = String(events.length);

  if (filter) {
    var statuses = [];
    events.forEach(function (event) {
      if (event && event.status && statuses.indexOf(event.status) === -1) {
        statuses.push(event.status);
      }
    });
    statuses.sort();
    statuses.forEach(function (status) {
      var option = document.createElement("option");
      option.value = String(status);
      option.textContent = String(status);
      filter.appendChild(option);
    });
  }

  function eventText(event, key, fallback) {
    var value = event && event[key];
    return String(value == null ? fallback : value);
  }

  function renderEvents(status) {
    if (!list) return;
    var rows = events.filter(function (event) {
      return !status || (event && event.status === status);
    });

    list.textContent = "";
    if (!rows.length) {
      var empty = document.createElement("div");
      empty.className = "tx-empty";
      empty.textContent = "没有记录";
      list.appendChild(empty);
      return;
    }

    rows.forEach(function (event) {
      var item = document.createElement("button");
      item.className = "tx-item";
      item.type = "button";

      var head = document.createElement("div");
      var kind = document.createElement("strong");
      kind.textContent = eventText(event, "kind", "event");
      head.appendChild(kind);
      head.appendChild(document.createTextNode(" · " + eventText(event, "summary", "")));
      item.appendChild(head);

      var meta = document.createElement("div");
      meta.className = "tx-meta";
      meta.textContent =
        eventText(event, "time", "") +
        " · " +
        eventText(event, "from", "?") +
        " → " +
        eventText(event, "to", "?") +
        " · round " +
        eventText(event, "round", "-") +
        " · " +
        eventText(event, "bytes", "-") +
        " B · " +
        eventText(event, "status", "?");
      item.appendChild(meta);

      if (event && event.payload) {
        var payload = document.createElement("pre");
        payload.className = "tx-payload";
        payload.textContent = String(event.payload);
        item.appendChild(payload);
      }

      item.addEventListener("click", function () {
        item.classList.toggle("open");
      });
      list.appendChild(item);
    });
  }

  function setOpen(next) {
    if (!drawer || !overlay || !badge) return;
    isOpen = next;
    if (next) {
      drawer.hidden = false;
      overlay.hidden = false;
      window.requestAnimationFrame(function () {
        drawer.classList.add("open");
      });
      badge.setAttribute("aria-expanded", "true");
      if (closeButton) closeButton.focus();
    } else {
      drawer.classList.remove("open");
      badge.setAttribute("aria-expanded", "false");
      window.setTimeout(function () {
        if (!isOpen) {
          drawer.hidden = true;
          overlay.hidden = true;
        }
      }, 180);
    }
  }

  if (badge) {
    badge.addEventListener("click", function () {
      setOpen(!isOpen);
    });
  }
  if (closeButton) {
    closeButton.addEventListener("click", function () {
      setOpen(false);
    });
  }
  if (overlay) {
    overlay.addEventListener("click", function () {
      setOpen(false);
    });
  }
  if (filter) {
    filter.addEventListener("change", function () {
      renderEvents(filter.value);
    });
  }
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && isOpen) setOpen(false);
  });

  renderEvents("");
})();
