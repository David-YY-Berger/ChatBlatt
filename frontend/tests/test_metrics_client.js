"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const script = fs.readFileSync(
  path.join(__dirname, "..", "components", "metrics_client", "metrics.js"), "utf8"
);

function client(initialUrl, storedAdmin) {
  const values = new Map(storedAdmin ? [["eitz_metrics_admin", storedAdmin]] : []);
  const listeners = {};
  const host = {
    location: new URL(initialUrl),
    sessionStorage: {
      getItem: key => values.has(key) ? values.get(key) : null,
      setItem: (key, value) => values.set(key, value),
      removeItem: key => values.delete(key),
    },
    document: {
      referrer: "https://referrer.example/private@example.com?secret=1",
      addEventListener: (name, callback) => { listeners[name] = callback; },
      removeEventListener() {},
    },
    addEventListener() {},
    removeEventListener() {},
    postMessage() {},
    Element: class {},
    MutationObserver: class {
      observe() {}
      disconnect() {}
    },
  };
  host.history = {
    state: null,
    pushState(data, unused, url) { host.location = new URL(url, host.location.href); },
    replaceState(data, unused, url) { host.location = new URL(url, host.location.href); },
  };
  const tags = [];
  const document = {
    createElement: () => ({}),
    head: {appendChild: tag => tags.push(tag)},
  };
  let onMessage;
  const window = {
    parent: host,
    addEventListener: (name, callback) => { if (name === "message") onMessage = callback; },
  };
  vm.runInNewContext(script, {window, document, URL, console, Set, Date, JSON, encodeURIComponent});
  const render = (events = [], originHint = "") => onMessage({
    source: host,
    origin: host.location.origin,
    data: {type: "streamlit:render", args: {
      measurement_id: "G-9ZHLKD65GM",
      base_url: "https://app.example/",
      paths: ["", "source_search", "number_search"],
      language: "he",
      origin_hint: originHint,
      events,
    }},
  });
  const calls = () => Array.from(window.dataLayer || [], call => Array.from(call));
  return {host, window, tags, render, calls, listeners};
}

test("admin persists through navigation and only false enables tracking", () => {
  const app = client("https://app.example/?admin=true");
  app.render([{id: "1", name: "app_search"}]);
  assert.equal(app.tags.length, 0);
  app.host.history.pushState(null, "", "/source_search");
  assert.equal(app.host.location.searchParams.get("admin"), "true");
  app.render([{id: "2", name: "app_search"}]);
  assert.equal(app.tags.length, 0);
  app.host.history.pushState(null, "", "/?admin=false");
  assert.equal(app.tags.length, 1);
  assert.equal(app.calls().filter(call => call[1] === "page_view").length, 1);
});

test("stored and conflicting admin values fail closed", () => {
  const stored = client("https://app.example/source_search", "true");
  stored.render();
  assert.equal(stored.host.location.searchParams.get("admin"), "true");
  assert.equal(stored.tags.length, 0);
  const conflicting = client("https://app.example/?admin=true&admin=false");
  conflicting.render();
  assert.equal(conflicting.host.location.searchParams.get("admin"), "true");
  assert.equal(conflicting.tags.length, 0);
});

test("internal links inherit admin before they are clicked or copied", () => {
  const app = client("https://app.example/?admin=true");
  const link = {
    href: "https://app.example/source_search?admin=false",
    getAttribute: () => "/source_search?admin=false",
    matches: () => true,
  };
  app.host.document.querySelectorAll = () => [link];
  app.render();
  assert.equal(new URL(link.href).searchParams.get("admin"), "true");
  assert.equal(app.host.sessionStorage.getItem("eitz_metrics_admin"), "true");
  app.host.history.pushState(null, "", "/?admin=false");
  assert.equal(new URL(link.href).searchParams.get("admin"), "false");
});

test("events redact free text and carry app language and navigation origin", () => {
  const app = client("https://app.example/source_search?q=private%40example.com&other=secret");
  app.render([{id: "1", name: "app_search", app_language: "he",
               search_type: "source", text_similarity_used: 1}], "entity_relationship_sources");
  const calls = app.calls();
  const view = calls.find(call => call[0] === "event" && call[1] === "page_view")[2];
  assert.equal(view.page_location, "https://app.example/source_search");
  assert.equal(view.page_referrer, "https://referrer.example/");
  assert.equal(view.app_language, "he");
  assert.equal(view.came_from, "entity_relationship_sources");
  assert.ok(!JSON.stringify(calls).includes("private"));
  assert.ok(!JSON.stringify(calls).includes("secret"));
  app.render([{id: "1", name: "app_search", search_type: "source"}]);
  assert.equal(app.calls().filter(call => call[1] === "app_search").length, 1);
});
