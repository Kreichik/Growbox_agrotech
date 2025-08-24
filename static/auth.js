// auth.js

(function requireAuth() {
  const token = localStorage.getItem('jwtToken');
  if (!token) {
    // нет токена — сразу к логину
    return window.location.replace('login');
  }

  // опционально: проверка expiration (exp в JWT- payload)
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    // payload.exp — время в секундах с 1970
    if (payload.exp && Date.now() / 1000 > payload.exp) {
      // токен протух
      localStorage.removeItem('jwtToken');
      return window.location.replace('login');
    }
  } catch (e) {
    // невалидный токен
    localStorage.removeItem('jwtToken');
    return window.location.replace('login');
  }
})();
