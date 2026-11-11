"use strict";

(() => {
  const host = window.parent;
  const storageKey = "eitz_metrics_admin";
  const sharedKey = "__eitzMetrics";
  const pendingKey = "eitz_metrics_navigation";
  let args;
  let loadedId;

  function explicitAdmin(url) {
    if (!url.searchParams.has("admin")) return null;
    return url.searchParams.getAll("admin").every(value => value.toLowerCase() === "false")
      ? "false" : "true";
  }

  function readAdmin(url) {
    const explicit = explicitAdmin(url);
    if (explicit !== null) {
      host.sessionStorage.setItem(storageKey, explicit);
      return explicit;
    }
    return host.sessionStorage.getItem(storageKey);
  }

  function propagate(url) {
    const value = readAdmin(url);
    if (value !== null) url.searchParams.set("admin", value);
    return url;
  }

  function rewriteLink(anchor) {
    const raw = anchor.getAttribute("href");
    if (!args || !raw || raw.startsWith("#")) return;
    const url = new URL(anchor.href, host.location.href);
    if (url.origin !== host.location.origin || !args.paths.includes(url.pathname.slice(1))) return;
    const value = readAdmin(new URL(host.location.href));
    if (value !== null) url.searchParams.set("admin", value);
    if (anchor.href !== url.href) anchor.href = url.href;
  }

  function safeLocation() {
    const url = new URL(host.location.href);
    const paths = new Set(args.paths.map(path => "/" + path));
    const path = paths.has(url.pathname) ? url.pathname : "/";
    const clean = new URL(path, url.origin);
    if (path === "/number_search") {
      const type = url.searchParams.get("type");
      const value = url.searchParams.get("value") || "";
      if (type === "number" && /^\d{1,40}(\/\d{1,40})?$/.test(value)) {
        clean.searchParams.set("type", type);
        clean.searchParams.set("value", value);
      }
    }
    return clean.href;
  }

  function safeReferrer() {
    if (host.document.referrer) {
      const referrer = new URL(host.document.referrer);
      if (referrer.protocol === "http:" || referrer.protocol === "https:") {
        return referrer.origin + "/";
      }
    }
    return host.location.origin + "/";
  }

  function enabled() {
    if (!args) return false;
    if (!/^G-[A-Z0-9]+$/.test(args.measurement_id)) {
      console.error("Analytics disabled: invalid GA4 measurement ID.");
      return false;
    }
    if (readAdmin(new URL(host.location.href)) === "true") return false;
    return host.location.origin === new URL(args.base_url).origin;
  }

  function loadTag() {
    if (loadedId === args.measurement_id) return;
    loadedId = args.measurement_id;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", loadedId, {
      send_page_view: false,
      page_location: safeLocation(),
      page_referrer: safeReferrer(),
      app_language: args.language,
      allow_google_signals: false,
    });
    const script = document.createElement("script");
    script.async = true;
    script.referrerPolicy = "no-referrer";
    script.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(loadedId);
    script.onerror = () => console.error("Could not load Google Analytics.");
    document.head.appendChild(script);
  }

  function send(name, params) {
    if (!enabled()) return;
    window["ga-disable-" + args.measurement_id] = false;
    loadTag();
    window.gtag("set", {
      page_location: safeLocation(),
      page_referrer: safeReferrer(),
      app_language: args.language,
    });
    const eventParams = {
      page_location: safeLocation(),
      page_referrer: safeReferrer(),
      app_language: args.language,
    };
    for (const [key, value] of Object.entries(params || {})) {
      if (key !== "id" && key !== "name" && value !== "" && value != null) {
        eventParams[key] = typeof value === "string" ? value.slice(0, 100) : value;
      }
    }
    window.gtag("event", name, eventParams);
  }

  function controlName(element) {
    if (element.closest(".app-home-link")) return "header_home";
    const container = element.closest("[class*='st-key-']");
    if (!container) return "navigation";
    const cls = Array.from(container.classList).find(name => name.startsWith("st-key-")) || "";
    for (const prefix of ["st-key-home_tool_", "st-key-entity_landing_btn_",
                          "st-key-entity_type_btn_", "st-key-mobile_page_"]) {
      if (cls.startsWith(prefix)) return cls.slice(7, 100);
    }
    if (cls.startsWith("st-key-open_family_tree_")) return "open_family_tree";
    if (cls.startsWith("st-key-nav_")) return "view_related_entity";
    const relationship = /^st-key-relationship_sources_([a-zA-Z]+)_\d+$/.exec(cls);
    if (relationship) return "relationship_sources_" + relationship[1];
    return "navigation";
  }

  function inspectUrl() {
    const url = propagate(new URL(host.location.href));
    if (url.href !== host.location.href) {
      host.history.replaceState(host.history.state, "", url.href);
    }
    if (args && readAdmin(url) === "true") {
      window["ga-disable-" + args.measurement_id] = true;
    }
    const state = host[sharedKey];
    if (state.rewriteLinks) state.rewriteLinks();
    if (!args || url.href === state.lastUrl) return;
    const old = state.lastUrl && new URL(state.lastUrl);
    state.lastUrl = url.href;
    const knownPaths = new Set(args.paths.map(path => "/" + path));
    const origin = old && old.pathname !== url.pathname && knownPaths.has(old.pathname)
      ? old.pathname : "";
    let cameFrom = origin ? origin + ":" + (state.lastControl || "navigation") : "";
    const pending = host.sessionStorage.getItem(pendingKey);
    if (!cameFrom && pending) {
      const info = JSON.parse(pending);
      if (info.target === url.pathname && info.source !== url.pathname) {
        cameFrom = info.source + ":" + info.control;
      }
    }
    if (!old && !cameFrom && args.origin_hint === "entity_relationship_sources") {
      cameFrom = args.origin_hint;
    }
    host.sessionStorage.removeItem(pendingKey);
    state.lastControl = "";
    send("page_view", {came_from: cameFrom});
  }

  function install() {
    const previous = host[sharedKey];
    if (previous && previous.cleanup) previous.cleanup();
    const state = previous || {seen: new Set(), lastControl: ""};
    host[sharedKey] = state;
    const history = host.history;
    const push = history.pushState;
    const replace = history.replaceState;
    function wrap(original) {
      return function (data, unused, target) {
        if (target != null) {
          const next = new URL(target, host.location.href);
          if (next.origin === host.location.origin) target = propagate(next).href;
        }
        const result = original.call(this, data, unused, target);
        inspectUrl();
        if (loadedId && enabled()) {
          window.gtag("set", {
            page_location: safeLocation(),
            page_referrer: safeReferrer(),
            app_language: args.language,
          });
        }
        return result;
      };
    }
    const wrappedPush = wrap(push);
    const wrappedReplace = wrap(replace);
    history.pushState = wrappedPush;
    history.replaceState = wrappedReplace;
    const click = event => {
      const element = event.target instanceof host.Element ? event.target : event.target.parentElement;
      if (!element) return;
      const anchor = element.closest("a[href]");
      if (anchor) {
        rewriteLink(anchor);
        const url = new URL(anchor.href, host.location.href);
        if (url.origin === host.location.origin) {
          if (args && args.paths.includes(url.pathname.slice(1)) &&
              args.paths.includes(host.location.pathname.slice(1))) {
            host.sessionStorage.setItem(pendingKey, JSON.stringify({
              source: host.location.pathname,
              target: url.pathname,
              control: controlName(element),
            }));
          }
        }
      }
      if (element.closest(".st-key-pdf_download button")) {
        send("file_download", {file_type: "pdf", download_type: "source_results"});
      }
      if (element.closest("button, a")) state.lastControl = controlName(element);
    };
    host.document.addEventListener("click", click, true);
    host.addEventListener("popstate", inspectUrl);
    const rewriteAll = node => {
      if (node.matches && node.matches("a[href]")) rewriteLink(node);
      if (node.querySelectorAll) node.querySelectorAll("a[href]").forEach(rewriteLink);
    };
    state.rewriteLinks = () => rewriteAll(host.document);
    rewriteAll(host.document);
    const observer = new host.MutationObserver(mutations => {
      for (const mutation of mutations) {
        if (mutation.type === "attributes") rewriteLink(mutation.target);
        else mutation.addedNodes.forEach(rewriteAll);
      }
    });
    observer.observe(host.document, {subtree: true, childList: true, attributes: true,
                                     attributeFilter: ["href"]});
    state.cleanup = () => {
      observer.disconnect();
      host.document.removeEventListener("click", click, true);
      host.removeEventListener("popstate", inspectUrl);
      if (history.pushState === wrappedPush) history.pushState = push;
      if (history.replaceState === wrappedReplace) history.replaceState = replace;
    };
  }

  window.addEventListener("message", event => {
    if (event.source !== host || event.origin !== host.location.origin ||
        !event.data || event.data.type !== "streamlit:render") return;
    args = event.data.args;
    try {
      if (!host[sharedKey] || host[sharedKey].owner !== window) {
        install();
        host[sharedKey].owner = window;
      }
      inspectUrl();
      for (const item of args.events || []) {
        if (host[sharedKey].seen.has(item.id)) continue;
        host[sharedKey].seen.add(item.id);
        send(item.name, item);
      }
    } catch (error) {
      console.error("Analytics disabled: unable to enforce the admin opt-out.", error);
    }
  });
  window.parent.postMessage({isStreamlitMessage: true, type: "streamlit:componentReady", apiVersion: 1}, "*");
  window.parent.postMessage({isStreamlitMessage: true, type: "streamlit:setFrameHeight", height: 0}, "*");
})();
