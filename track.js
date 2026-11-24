// Counts page views and referral link clicks/copies. No cookies, nothing personal:
// just event, page and where the visitor came from (search engine, Facebook, direct...).
(function () {
  var ENDPOINT = 'https://apirelay.sitetest.org.uk/evtariff/track.php';

  function source() {
    try {
      var saved = sessionStorage.getItem('evt_src');
      if (saved) return saved;
    } catch (e) {}
    var src = 'direct';
    var m = location.search.match(/[?&](?:src|utm_source)=([^&#]+)/);
    if (m) {
      src = decodeURIComponent(m[1]);
    } else if (document.referrer) {
      try {
        var host = new URL(document.referrer).hostname.replace(/^www\./, '');
        if (!/(^|\.)evtariffguide\.co\.uk$/.test(host)) src = host;
      } catch (e) {}
    }
    try { sessionStorage.setItem('evt_src', src); } catch (e) {}
    return src;
  }

  var src = source();
  var page = location.pathname.replace(/\.html$/, '').replace(/\/$/, '') || '/';

  function send(event) {
    var body = JSON.stringify({ e: event, p: page, s: src });
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon(ENDPOINT, new Blob([body], { type: 'text/plain' }));
      } else {
        fetch(ENDPOINT, { method: 'POST', body: body, keepalive: true, mode: 'no-cors' });
      }
    } catch (e) {}
  }

  send('view');

  document.addEventListener('click', function (ev) {
    var a = ev.target.closest && ev.target.closest('a[href]');
    if (a) {
      var href = a.getAttribute('href');
      if (/refer-a-friend/.test(href)) send('edf_click');
      else if (/fuseenergy\.com/.test(href)) send('fuse_click');
      else if (/share\.octopus\.energy/.test(href)) send('octopus_click');
      return;
    }
    var b = ev.target.closest && ev.target.closest('button[onclick]');
    if (b) {
      var fn = b.getAttribute('onclick');
      if (/copyCode/.test(fn)) send('fuse_copy');
      else if (/copyLink/.test(fn)) send('edf_copy');
    }
  }, true);

  // Copying the code or link by hand, without the button
  document.addEventListener('copy', function () {
    var sel = String(window.getSelection ? window.getSelection() : '');
    if (/STEVE25217/i.test(sel)) send('fuse_copy');
    else if (/refer-a-friend/.test(sel)) send('edf_copy');
  });
})();
