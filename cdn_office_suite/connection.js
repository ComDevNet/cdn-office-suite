(() => {
  const config = window.OFFICE_CONFIG;
  const keys = ['port', 'oc4dPort', 'mailPort'];
  const valid = config && keys.every(key => Number.isInteger(config[key]) && config[key] >= 1024 && config[key] <= 65535) && new Set(keys.map(key => config[key])).size === 3;
  if (!valid) {
    window.OFFICE_CONNECTION = Object.freeze({error:'The server port settings are missing or invalid. Ask your administrator to repair the installation.'});
    return;
  }
  const saved = Object.freeze(Object.fromEntries(keys.map(key => [key, config[key]])));
  const gatewayRoute = /^((?:\d{1,3}x){3}\d{1,3})(?:-\d{1,5})?(\.[a-z0-9.-]+\.nip\.io)$/i.exec(location.hostname || '');
  const gateway = Boolean(gatewayRoute && gatewayRoute[1].split('x').every(n => Number(n) <= 255));
  function address(port) {
    const url = new URL(location.origin);
    if (gateway) url.hostname = gatewayRoute[1] + '-' + port + gatewayRoute[2];
    else url.port = port;
    url.pathname = '/';
    url.search = '';
    url.hash = '';
    return url.href;
  }
  window.OFFICE_CONNECTION = Object.freeze({ports:saved, gateway, service:address(saved.port), mail:address(saved.mailPort)});
})();
