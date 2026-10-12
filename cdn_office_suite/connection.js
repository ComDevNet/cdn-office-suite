(() => {
  const config = window.OFFICE_CONFIG;
  const keys = ['port', 'oc4dPort', 'mailPort'];
  const valid = config && keys.every(key => Number.isInteger(config[key]) && config[key] >= 1024 && config[key] <= 65535) && new Set(keys.map(key => config[key])).size === 3;
  if (!valid) {
    window.OFFICE_CONNECTION = Object.freeze({error:'The server port settings are missing or invalid. Ask your administrator to repair the installation.'});
    return;
  }
  const saved = Object.freeze(Object.fromEntries(keys.map(key => [key, config[key]])));
  function address(port) {
    const url = new URL(location.origin);
    url.port = port;
    url.pathname = '/';
    url.search = '';
    url.hash = '';
    return url.href;
  }
  window.OFFICE_CONNECTION = Object.freeze({ports:saved, service:address(saved.port), mail:address(saved.mailPort)});
})();
