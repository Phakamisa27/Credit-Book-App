// api.js — the single place the frontend talks to the backend.
//
// Every page uses these functions. No page builds a fetch() of its own, so
// auth headers, error shapes and the base URL are defined once.

const API = (() => {
  // Which port the backend listens on. Override before this script loads if
  // you changed PORT in backend/.env:
  //   <script>window.CREDIT_BOOK_API_PORT = '5050';</script>
  const BACKEND_PORT = String(window.CREDIT_BOOK_API_PORT || '5000');

  // Where to send API calls.
  //
  // Normally Express serves these pages itself, so a relative "/api" is right.
  // But the pages are plain static files, so they can also be opened by
  // VS Code Live Server, Live Preview, or straight off disk — and those cannot
  // handle a POST. They answer "405 Method Not Allowed", which looks like a
  // login failure but is really the request never reaching the backend.
  //
  // So: use the current origin ONLY when it is actually the backend.
  function resolveBaseUrl() {
    // An explicit override always wins.
    if (window.CREDIT_BOOK_API_URL) return window.CREDIT_BOOK_API_URL;

    const { protocol, hostname, port } = window.location;

    // Opened from disk — there is no origin to talk to.
    if (protocol === 'file:') return `http://localhost:${BACKEND_PORT}/api`;

    // Served by the backend itself: the normal case.
    if (port === BACKEND_PORT) return '/api';

    // Served by something else on another port (any static dev server,
    // whichever port it happened to pick). Talk to the backend directly.
    if (port) return `${protocol}//${hostname}:${BACKEND_PORT}/api`;

    // No port at all — port 80/443 behind a proxy. Assume same origin.
    return '/api';
  }

  const BASE_URL = resolveBaseUrl();

  const TOKEN_KEY = 'creditbook_token';
  const USER_KEY = 'creditbook_user';
  const OFFLINE_MSG = 'Cannot reach the server. Is it running?';

  class ApiError extends Error {
    constructor(message, status) {
      super(message);
      this.name = 'ApiError';
      this.status = status;
    }
  }

  // ---------------------------------------------------------------- token --
  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || '';
  }

  function setSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user || {}));
  }

  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  // The cached user is for instant rendering only (business name in the
  // sidebar). Anything that matters is re-fetched from the server.
  function getCachedUser() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || 'null');
    } catch (_) {
      return null;
    }
  }

  function isLoggedIn() {
    return Boolean(getToken());
  }

  // -------------------------------------------------------------- request --
  async function request(path, { method = 'GET', body, auth = true } = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (auth && getToken()) {
      headers.Authorization = `Bearer ${getToken()}`;
    }

    let res;
    try {
      res = await fetch(`${BASE_URL}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (_) {
      throw new ApiError(OFFLINE_MSG, 0);
    }

    let payload = null;
    const text = await res.text();
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch (_) {
        payload = null;
      }
    }

    if (!res.ok) {
      // An expired or missing token means the session is over. Drop it and
      // send the owner to the login page rather than showing a broken screen.
      if (res.status === 401 && auth) {
        clearSession();
        if (!/login\.html|register\.html|index\.html$|\/$/.test(window.location.pathname)) {
          window.location.href = 'login.html';
        }
      }
      // A reply with no JSON body did not come from this API. Almost always
      // it is a static file server answering instead of the backend, so say
      // that rather than showing a bare status code.
      if (!payload) {
        if (res.status === 405 || res.status === 501) {
          throw new ApiError(
            `Reached a web server that cannot run the ThathaCash API (${res.status}). ` +
              `Make sure the backend is running, then open http://localhost:${BACKEND_PORT}`,
            res.status
          );
        }
        if (res.status === 404) {
          throw new ApiError(
            `The ThathaCash API was not found at ${BASE_URL}. ` +
              `Make sure the backend is running, then open http://localhost:${BACKEND_PORT}`,
            res.status
          );
        }
      }

      throw new ApiError(
        (payload && payload.message) || `Request failed (${res.status})`,
        res.status
      );
    }

    return payload ? payload.data : null;
  }

  const get = (path) => request(path);
  const post = (path, body, opts) => request(path, { method: 'POST', body, ...opts });
  const patch = (path, body) => request(path, { method: 'PATCH', body });
  const del = (path) => request(path, { method: 'DELETE' });

  // Turns an object into a query string, skipping empty values.
  function qs(params) {
    const search = new URLSearchParams();
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        search.set(key, value);
      }
    });
    const str = search.toString();
    return str ? `?${str}` : '';
  }

  // ----------------------------------------------------------------- auth --
  const auth = {
    async status() {
      return request('/auth/status', { auth: false });
    },
    async register(data) {
      const result = await post('/auth/register', data, { auth: false });
      setSession(result.token, result.user);
      return result.user;
    },
    async login(email, password) {
      const result = await post('/auth/login', { email, password }, { auth: false });
      setSession(result.token, result.user);
      return result.user;
    },
    async logout() {
      try {
        await post('/auth/logout');
      } catch (_) {
        // Logging out must work even with no connection — the token is ours
        // to discard.
      }
      clearSession();
    },
    me: () => get('/auth/me'),
    updateMe: (data) => patch('/auth/me', data),
    changePassword: (data) => post('/auth/change-password', data),
  };

  // ------------------------------------------------------------ customers --
  const customers = {
    list: (params) => get(`/customers${qs(params)}`),
    getById: (id) => get(`/customers/${id}`),
    create: (data) => post('/customers', data),
    update: (id, data) => patch(`/customers/${id}`, data),
    remove: (id) => del(`/customers/${id}`),
    transactions: (id) => get(`/customers/${id}/transactions`),
    addTransaction: (id, data) => post(`/customers/${id}/transactions`, data),
  };

  // --------------------------------------------------------- transactions --
  const transactions = {
    list: (params) => get(`/transactions${qs(params)}`),
    getById: (id) => get(`/transactions/${id}`),
    remove: (id) => del(`/transactions/${id}`),
  };

  // ------------------------------------------------------------ reminders --
  const reminders = {
    list: (params) => get(`/reminders${qs(params)}`),
    create: (data) => post('/reminders', data),
    update: (id, data) => patch(`/reminders/${id}`, data),
    remove: (id) => del(`/reminders/${id}`),
  };

  // -------------------------------------------------------------- reports --
  const reports = {
    summary: () => get('/reports/summary'),
    dashboard: () => get('/reports/dashboard'),
    full: (days) => get(`/reports${qs({ days })}`),
  };

  // ---------------------------------------------------------------- items --
  // Products. Credit Book quick items, and ThathaCash stock.
  const items = {
    list: () => get('/items'),
    create: (data) => post('/items', data),
    update: (id, data) => patch(`/items/${id}`, data),
    remove: (id) => del(`/items/${id}`),
  };

  // ============================================================ ThathaCash ==
  // ----------------------------------------------------------------- cash --
  // type: OPENING (starting cash) | INCOME | EXPENSE | STOCK | DRAW
  // (RECOUNT_IN / RECOUNT_OUT are written only by count())
  const cash = {
    list: (params) => get(`/cash${qs(params)}`), // { entries, totals }
    summary: () => get('/cash/summary'),
    create: (data) => post('/cash', data),
    remove: (id) => del(`/cash/${id}`),
    // The cash the owner counted in the till -> { difference, cash }
    count: (amount) => post('/cash/count', { amount }),
  };

  // Everything the Home screen shows, in one request.
  const home = {
    get: () => get('/home'),
  };

  // The suggested next order from the wholesaler.
  const order = {
    get: () => get('/order'),
  };

  return {
    ApiError,
    OFFLINE_MSG,
    BASE_URL,
    getToken,
    setSession,
    clearSession,
    getCachedUser,
    isLoggedIn,
    auth,
    customers,
    transactions,
    reminders,
    reports,
    items,
    cash,
    home,
    order,
  };
})();
