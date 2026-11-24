<?php
// evtariffguide.co.uk counter: page views and referral clicks/copies, counted per page and source.
// No cookies, no IP addresses, nothing per visitor. Totals per UTC hour, keyed event|page|source|HH.
// Lives on the relay server; the site posts to it with navigator.sendBeacon.

$dataDir = __DIR__ . '/data';

header('Access-Control-Allow-Origin: https://www.evtariffguide.co.uk');
header('Cache-Control: no-store');

// Reading the counts: GET ?action=stats&days=7 with header X-Token: <contents of data/token.txt>
if (($_GET['action'] ?? '') === 'stats') {
    $token = is_file("$dataDir/token.txt") ? trim(file_get_contents("$dataDir/token.txt")) : '';
    if ($token === '' || !hash_equals($token, $_SERVER['HTTP_X_TOKEN'] ?? '')) {
        http_response_code(403);
        exit;
    }
    $days = max(1, min(400, (int)($_GET['days'] ?? 7)));
    $out = [];
    for ($i = $days - 1; $i >= 0; $i--) {
        $day = gmdate('Y-m-d', time() - 86400 * $i);
        $file = "$dataDir/$day.json";
        $out[$day] = is_file($file) ? json_decode(file_get_contents($file), true) : new stdClass();
    }
    header('Content-Type: application/json');
    echo json_encode($out, JSON_PRETTY_PRINT);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    exit;
}

$in = json_decode((string)file_get_contents('php://input', false, null, 0, 1024), true);
$events = ['view', 'edf_click', 'edf_copy', 'fuse_click', 'fuse_copy', 'octopus_click'];
if (!is_array($in) || !in_array($in['e'] ?? '', $events, true)) {
    http_response_code(204);
    exit;
}
$page = preg_replace('~[^a-z0-9/_-]~', '', strtolower(substr((string)($in['p'] ?? ''), 0, 60))) ?: '/';
$src  = preg_replace('~[^a-z0-9._-]~', '', strtolower(substr((string)($in['s'] ?? ''), 0, 40))) ?: 'direct';
$key  = $in['e'] . '|' . $page . '|' . $src . '|' . gmdate('H');

if (!is_dir($dataDir)) {
    mkdir($dataDir, 0750, true);
    // Keep the raw count files private on Apache; on nginx, deny /evtariff/data/ in the site config.
    file_put_contents("$dataDir/.htaccess", "Require all denied\n");
}
$fh = fopen("$dataDir/" . gmdate('Y-m-d') . '.json', 'c+');
if ($fh && flock($fh, LOCK_EX)) {
    $data = json_decode(stream_get_contents($fh) ?: '{}', true) ?: [];
    if (isset($data[$key]) || count($data) < 20000) {
        $data[$key] = ($data[$key] ?? 0) + 1;
    }
    ftruncate($fh, 0);
    rewind($fh);
    fwrite($fh, json_encode($data));
    fflush($fh);
    flock($fh, LOCK_UN);
}
if ($fh) {
    fclose($fh);
}
http_response_code(204);
