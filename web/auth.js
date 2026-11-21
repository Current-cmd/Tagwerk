// API token for Tagwerk. Open any page once with ?token=<API_TOKEN> (or answer the prompt): the token is kept in
// localStorage, sent as a Bearer header on fetch() and as a SameSite cookie, so XHR uploads, <img>/<video> media,
// downloads and the websocket are authenticated too. Without API_TOKEN on the server (TAGWERK_DEV=1) nothing is asked.
(function () {
  const KEY = 'tagwerk_token';
  const store = {
    get() { try { return localStorage.getItem(KEY) || ''; } catch (e) { return ''; } },
    set(v) { try { localStorage.setItem(KEY, v); } catch (e) { /* private mode: cookie only */ } },
  };
  function setCookie(v) {
    document.cookie = `${KEY}=${encodeURIComponent(v)}; path=/; SameSite=Strict` +
      (location.protocol === 'https:' ? '; Secure' : '');
  }
  const url = new URL(location.href);
  const fromUrl = url.searchParams.get('token');
  if (fromUrl) {
    store.set(fromUrl);
    url.searchParams.delete('token');
    history.replaceState(null, '', url);  // keep the token out of the address bar and history
  }
  if (store.get()) setCookie(store.get());

  let asking = false;
  function ask() {
    if (asking) return;
    asking = true;
    const v = (prompt('Tagwerk: Zugangstoken eingeben') || '').trim();
    asking = false;
    if (v) { store.set(v); setCookie(v); location.reload(); }
  }

  const origFetch = window.fetch.bind(window);
  window.fetch = async (input, init = {}) => {
    const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
    const tok = store.get();
    if (tok && !headers.has('Authorization')) headers.set('Authorization', 'Bearer ' + tok);
    const r = await origFetch(input, { ...init, headers });
    if (r.status === 401) ask();
    return r;
  };
  window.tagwerkAuth = { token: () => store.get(), ask };
})();
