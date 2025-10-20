<?php
// 告诉服务器不要显示任何错误信息，防止网站出现错误时泄露敏感信息
error_reporting(0);

// 设置网页返回的内容类型为纯文本，使用UTF-8编码（支持中文显示）
header('Content-Type: text/plain; charset=utf-8');

// 从网址参数中获取id值，比如 http://127.0.0.1:35455/zgst.php?id=btv4k 中的btv4k
// 如果网址中没有id参数，就设置为空字符串
$id = isset($_GET['id']) ? $_GET['id'] : '';

// 建立一个对照表：把简单的频道代号（如btv4k）转换成网站内部使用的复杂数字编号
$channelMap = [
    'btv4k' => 91417,  // 北京卫视4K在网站内部的编号是91417
    'sh4k' => 96050,   // 上海卫视4K在网站内部的编号是96050
    'js4k' => 95925,   // 江苏卫视4K在网站内部的编号是95925
    'zj4k' => 96039,   // 浙江卫视4K在网站内部的编号是96039
    'sd4k' => 95975,   // 山东卫视4K在网站内部的编号是95975
    'hn4k' => 96038,   // 湖南卫视4K在网站内部的编号是96038
    'gd4k' => 93733,   // 广东卫视4K在网站内部的编号是93733
    'sc4k' => 95965,   // 四川卫视4K在网站内部的编号是95965
    'sz4k' => 93735,   // 深圳卫视4K在网站内部的编号是93735
];

// 建立另一个对照表：把频道代号转换成中文名称，用于显示给用户看
$channelNameMap = [
    'btv4k' => '北京卫视4K',
    'sh4k' => '上海卫视4K', 
    'js4k' => '江苏卫视4K',
    'zj4k' => '浙江卫视4K',
    'sd4k' => '山东卫视4K',
    'hn4k' => '湖南卫视4K',
    'gd4k' => '广东卫视4K',
    'sc4k' => '四川卫视4K',
    'sz4k' => '深圳卫视4K',
];

// 定义缓存文件夹的路径，缓存就是临时存储数据的地方，避免重复请求
define('CACHE_DIR', __DIR__ . '/zgstcache');

// 检查缓存文件夹是否存在，如果不存在就创建一个
if (!is_dir(CACHE_DIR)) {
    // 创建文件夹，0755是文件夹权限（所有者可读可写可执行，其他人可读可执行）
    mkdir(CACHE_DIR, 0755, true);
}

/**
 * 生成网站要求的加密签名（就像盖章一样，证明这个请求是合法的）
 * 网站用这种方式来验证请求是否来自官方APP
 * 
 * @param string $url 要请求的网址
 * @param string $params 请求参数
 * @param int $timeMillis 当前时间戳（精确到毫秒）
 * @param string $key 加密密码
 * @return string 返回加密后的签名字符串
 */
function makeSign($url, $params, $timeMillis, $key) {
    // 把网址、参数、时间戳打包成一个数组（就像把文件装进信封）
    $payload = [
        'url' => $url,          // 要访问的网址
        'params' => $params,    // 要传递的参数
        'time' => $timeMillis   // 当前时间
    ];
    
    // 把数组转换成JSON字符串格式（就像把中文翻译成英语，让机器能理解）
    $json = json_encode($payload);
    
    // 使用AES-256加密算法对JSON字符串进行加密（就像用密码锁锁上信封）
    // OPENSSL_RAW_DATA表示不要对加密结果做额外处理
    $encrypted = openssl_encrypt($json, 'AES-256-ECB', $key, OPENSSL_RAW_DATA);
    
    // 把加密后的二进制数据转换成Base64编码（就像把二进制数据转换成纯文本，方便传输）
    // 同时移除所有换行符，确保签名是一行完整的文本
    return str_replace(["\r\n", "\r", "\n"], '', base64_encode($encrypted));
}

/**
 * 从缓存中读取数据
 * 缓存就像临时记忆，避免每次都重新问网站要数据，提高速度
 * 
 * @param string $key 缓存键（就像记忆的名称）
 * @param int $ttl 缓存有效期（秒）（就像记忆的有效期）
 * @return mixed 返回缓存的数据，如果不存在或过期就返回null
 */
function getCache($key, $ttl) {
    // 根据键名生成缓存文件路径，md5是为了避免特殊字符导致文件名问题
    $file = CACHE_DIR . '/' . md5($key) . '.cache';
    
    // 如果缓存文件不存在，直接返回空
    if (!file_exists($file)) return null;
    
    // 检查缓存是否过期：文件修改时间 + 有效期 < 当前时间 说明已过期
    if (filemtime($file) + $ttl < time()) {
        // 删除过期的缓存文件
        unlink($file);
        return null;
    }
    
    // 读取缓存文件内容并解析成PHP数组
    $cacheData = json_decode(file_get_contents($file), true);
    
    // 返回缓存数据，如果解析失败返回null
    return $cacheData ? $cacheData['data'] : null;
}

/**
 * 把数据保存到缓存中
 * 
 * @param string $key 缓存键
 * @param mixed $data 要缓存的数据
 * @param int $ttl 缓存有效期（毫秒）
 */
function setCache($key, $data, $ttl) {
    // 根据键名生成缓存文件路径
    $file = CACHE_DIR . '/' . md5($key) . '.cache';
    
    // 组织缓存数据结构，包括数据和过期时间
    $cacheData = [
        'data' => $data,                        // 要缓存的数据
        'expire' => time() + $ttl / 1000        // 过期时间戳（把毫秒转换成秒）
    ];
    
    // 把缓存数据转换成JSON格式并写入文件
    file_put_contents($file, json_encode($cacheData));
}

// 这是从官方APP中提取的加密密钥，用于生成签名（就像开锁的密码）
$key = '01234567890123450123456789012345';

// 定义两个API接口网址：
// 第一个用于获取访问令牌（就像获取门票）
$url1 = 'https://api.chinaaudiovisual.cn/web/user/getVisitor';
// 第二个用于获取频道列表（就像获取节目单）
$url2 = 'https://api.chinaaudiovisual.cn/column/getColumnAllList';

// 尝试从缓存中读取访问令牌，有效期24小时（86400秒）
$token = getCache('visitor_token', 86400);

// 如果缓存中没有令牌，就需要从网站API获取
if (!$token) {
    // 获取当前时间戳（精确到毫秒），比如 1640995200000
    $time1 = round(microtime(true) * 1000);
    
    // 生成加密签名（就像在申请书上盖章）
    $sign1 = makeSign($url1, '', $time1, $key);
    
    // 设置HTTP请求头，告诉服务器我们是谁，要做什么
    $headers = [
        'Content-Type: application/json',  // 内容类型是JSON格式
        'headers: 1.1.3',                  // 客户端版本号
        'sign: ' . $sign1                  // 加密签名
    ];
    
    // 初始化cURL会话（就像拿起电话准备打电话）
    $ch = curl_init($url1);
    
    // 设置cURL选项（就像设置打电话的参数）
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,    // 让curl_exec返回内容而不是直接输出
        CURLOPT_POST => true,              // 使用POST方法发送请求
        CURLOPT_HTTPHEADER => $headers,    // 设置请求头
        CURLOPT_SSL_VERIFYPEER => false,   // 不验证SSL证书（简化操作）
        CURLOPT_SSL_VERIFYHOST => false    // 不验证主机名（简化操作）
    ]);
    
    // 执行请求并获取响应（就像拨打电话并听取回复）
    $resp = curl_exec($ch);
    
    // 关闭cURL会话（就像挂断电话）
    curl_close($ch);
    
    // 把返回的JSON字符串解析成PHP数组
    $data = json_decode($resp, true);
    
    // 检查请求是否成功：success为true且有token数据
    if (empty($data['success']) || empty($data['data']['token'])) {
        // 返回404错误给浏览器
        header('HTTP/1.1 404 Not Found');
        echo '获取Token失败';  // 显示错误信息
        exit;  // 停止执行后续代码
    }
    
    // 从返回数据中提取访问令牌
    $token = $data['data']['token'];
    
    // 把令牌保存到缓存中，有效期24小时（86400000毫秒）
    setCache('visitor_token', $token, 86400000);
}

// 尝试从缓存中获取频道列表数据，有效期10分钟（600秒）
$dataArr = getCache('column_all_list_33', 600);

// 如果缓存中没有频道列表数据，就从API获取
if (empty($dataArr)) {
    // 设置请求参数（就像填写申请表）
    $columnId = 350;        // 栏目ID
    $cityId = 0;            // 城市ID（0表示全国）
    $provinceId = 0;        // 省份ID（0表示全国）
    $version = "1.1.4";     // 客户端版本号
    
    // 拼接请求参数（就像把申请表的内容写成一行）
    $params = "cityId={$cityId}&columnId={$columnId}&provinceId={$provinceId}&token=" . rawurlencode($token) . "&version={$version}";
    
    // 获取当前时间戳（毫秒）
    $time2 = round(microtime(true) * 1000);
    
    // 生成加密签名
    $sign2 = makeSign($url2, $params, $time2, $key);
    
    // 设置请求头
    $headers = [
        'Content-Type: application/x-www-form-urlencoded',  // 内容类型是表单格式
        'User-Agent: okhttp/3.11.0',                        // 模拟Android APP
        'sign: ' . $sign2                                   // 加密签名
    ];
    
    // 初始化cURL会话
    $ch = curl_init($url2);
    
    // 设置cURL选项
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,    // 返回响应内容
        CURLOPT_POST => true,              // 使用POST方法
        CURLOPT_POSTFIELDS => $params,     // 设置POST数据
        CURLOPT_HTTPHEADER => $headers,    // 设置请求头
        CURLOPT_SSL_VERIFYPEER => false,   // 不验证SSL证书
        CURLOPT_SSL_VERIFYHOST => false    // 不验证主机名
    ]);
    
    // 执行请求
    $resp = curl_exec($ch);
    curl_close($ch);
    
    // 解析返回的JSON数据
    $dataArr = json_decode($resp, true);
    
    // 检查请求是否成功
    if (empty($dataArr['success'])) {
        header('HTTP/1.1 404 Not Found');
        echo '获取频道列表失败';
        exit;
    }
    
    // 把频道列表数据保存到缓存，有效期10分钟（600000毫秒）
    setCache('column_all_list_33', $dataArr, 600000);
}

// ==================== 处理频道列表请求 ====================
// 如果用户请求的是频道列表（id=list），比如 http://127.0.0.1:35455/zgst.php?id=list
if ($id == "list") {
    // 生成当前网页的完整网址（协议+域名+脚本路径）
    $baseUrl = sprintf(
        '%s://%s%s',
        isset($_SERVER['HTTPS']) ? 'https' : 'http',  // 判断是http还是https
        $_SERVER['HTTP_HOST'],                         // 域名
        $_SERVER['SCRIPT_NAME']                        // 脚本文件名
    );
    
    // 输出M3U格式的频道列表头
    // #genre# 是M3U格式的分类标记
    echo "4K频道列表,#genre#\n";
    
    // 遍历所有频道，生成频道列表
    foreach ($channelMap as $cid => $cidNum) {
        // 输出格式：频道名称,播放地址
        // 比如：北京卫视4K,http://127.0.0.1:35455/zgst.php?id=btv4k
        echo "{$channelNameMap[$cid]},{$baseUrl}?id={$cid}\n";
    }
    exit;  // 输出完列表就结束程序
}

// ==================== 查找播放地址 ====================
// 根据频道代号找到对应的内部数字编号
// 比如 btv4k 对应 91417
$targetId = $channelMap[$id];

// 初始化播放地址变量
$playUrl = null;

// 在频道列表数据中搜索目标频道的播放地址
if (!empty($dataArr['data']) && is_array($dataArr['data'])) {
    // 遍历所有频道数据
    foreach ($dataArr['data'] as $item) {
        // 检查当前频道的ID是否匹配目标ID
        if (isset($item['mediaAsset']['id']) && $item['mediaAsset']['id'] === $targetId) {
            // 找到播放地址，保存到变量中
            $playUrl = $item['mediaAsset']['url'];
            break;  // 找到后就跳出循环，不再继续查找
        }
    }
}

// ==================== 处理TS片段请求 ====================
// 检查是否是TS文件请求（ts=1表示请求视频碎片文件）
$isTsRequest = isset($_GET['ts']) && $_GET['ts'] === '1';

// 如果是TS请求并且有播放地址
if ($isTsRequest && $playUrl) {
    // 获取TS文件路径参数（path参数指定要请求哪个TS文件）
    $tsPath = $_GET['path'] ?? '';
    
    // 如果没有提供路径参数，返回错误
    if (empty($tsPath)) {
        header('HTTP/1.1 400 Bad Request');
        echo '缺少TS路径参数';
        exit;
    }
    
    // 解析原始播放URL，提取协议和域名（比如 https://example.com）
    $parsed = parse_url($playUrl);
    $baseUrl = "{$parsed['scheme']}://{$parsed['host']}";
    
    // 获取其他查询参数（除了ts、path、id之外的所有参数）
    $queryParams = $_GET;
    unset($queryParams['ts'], $queryParams['path'], $queryParams['id']);
    $queryString = http_build_query($queryParams);
    
    // 构建完整的TS文件URL（基础URL + TS文件路径 + 查询参数）
    $tsUrl = "{$baseUrl}/{$tsPath}" . ($queryString ? "?{$queryString}" : "");
    
    // 根据不同的频道设置不同的请求头（模拟官方APP）
    if ($id === 'gd4k') {
        // 广东卫视4K的特殊请求头
        $forwardHeaders = [
            'User-Agent: aliplayer',       // 模拟阿里播放器
            'Accept: */*',                 // 接受所有类型内容
            'Accept-Encoding: deflate, gzip', // 支持压缩
            'Referer: https://api.chinaaudiovisual.cn', // 来源页面
            'version: 1.1.4'               // 版本号
        ];
    } else {
        // 其他频道的通用请求头
        $forwardHeaders = [
            'User-Agent: aliplayer',       // 模拟阿里播放器
            'Referer: https://api.chinaaudiovisual.cn/', // 来源页面
            'Accept: */*',                 // 接受所有类型内容
            'Connection: keep-alive'       // 保持连接
        ];
    }
    
    // 如果客户端请求了部分内容（比如断点续传），传递Range头
    if (!empty($_SERVER['HTTP_RANGE'])) {
        $forwardHeaders[] = 'Range: ' . $_SERVER['HTTP_RANGE'];
    }
    
    // ==================== 设置流式传输 ====================
    // 禁用输出缓冲，让视频数据能够实时传输（就像打开水龙头）
    @ini_set('output_buffering', 'off');   // 关闭输出缓冲
    @ini_set('zlib.output_compression', '0'); // 关闭压缩
    @ini_set('implicit_flush', '1');       // 启用隐式刷新
    
    // 清空所有输出缓冲区
    while (ob_get_level() > 0) {
        @ob_end_flush();
    }
    ob_implicit_flush(true);               // 自动刷新输出缓冲区
    
    // 告诉Nginx不要缓冲输出（直接传输给客户端）
    header('X-Accel-Buffering: no');
    
    // 设置响应头（告诉浏览器这是视频文件）
    if (!headers_sent()) {
        header('Content-Type: video/MP2T');  // TS视频文件类型
        header('Cache-Control: no-cache, no-store, must-revalidate'); // 禁用缓存
        header('Pragma: no-cache');          // 兼容旧浏览器
    }
    
    // 初始化cURL会话，用于获取TS文件
    $ch = curl_init($tsUrl);
    $httpCode = 0;
    
    // 设置响应头处理函数（处理服务器返回的头信息）
    curl_setopt($ch, CURLOPT_HEADERFUNCTION, function($ch, $headerLine) {
        $len = strlen($headerLine);  // 头信息长度
        
        // 检查是否是HTTP状态行（比如 HTTP/1.1 200 OK）
        if (preg_match('#^HTTP/\d\.\d\s+(\d+)#', $headerLine, $m)) {
            // 设置HTTP状态码
            if (!headers_sent()) {
                http_response_code((int)$m[1]);
            }
            return $len;
        }
        
        // 转发重要的响应头给浏览器
        if (stripos($headerLine, 'Content-Length:') === 0 ||    // 内容长度
            stripos($headerLine, 'Content-Range:') === 0 ||     // 内容范围
            stripos($headerLine, 'Accept-Ranges:') === 0 ||     // 接受范围
            stripos($headerLine, 'Content-Type:') === 0) {      // 内容类型
            if (!headers_sent()) {
                $trimmed = trim($headerLine);
                if ($trimmed !== '') header($trimmed, true);
            }
        }
        return $len;
    });
    
    // 设置数据写入函数（实时传输视频数据）
    curl_setopt($ch, CURLOPT_WRITEFUNCTION, function($ch, $data) {
        // 检查客户端是否已经断开连接
        if (connection_aborted()) {
            return 0;  // 返回0表示停止传输
        }
        
        // 输出数据到浏览器
        echo $data;
        
        // 立即刷新输出缓冲区（确保数据实时传输）
        @flush();
        @ob_flush();
        
        // 返回处理的数据长度
        return strlen($data);
    });
    
    // 设置cURL选项
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => false,     // 不返回内容，直接输出
        CURLOPT_FOLLOWLOCATION => true,      // 跟随重定向
        CURLOPT_SSL_VERIFYPEER => false,     // 不验证SSL证书
        CURLOPT_SSL_VERIFYHOST => false,     // 不验证主机名
        CURLOPT_HTTPHEADER => $forwardHeaders, // 设置请求头
        CURLOPT_BUFFERSIZE => 128 * 1024,    // 缓冲区大小128KB
        CURLOPT_CONNECTTIMEOUT => 10,        // 连接超时10秒
        CURLOPT_TIMEOUT => 0,                // 总超时无限制（长视频）
        CURLOPT_NOSIGNAL => true,            // 忽略cURL信号
    ]);
    
    // 执行请求（开始传输视频数据）
    $ok = curl_exec($ch);
    
    // 获取HTTP状态码和错误信息
    $httpCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err = curl_error($ch);
    
    // 关闭cURL会话
    curl_close($ch);
    
    // 如果请求失败，返回错误信息
    if (!$ok && $httpCode === 0) {
        if (!headers_sent()) {
            header('HTTP/1.1 502 Bad Gateway');  // 网关错误
            header('Content-Type: text/plain; charset=utf-8');
        }
        echo "TS获取失败: {$err}";
    }
    exit;  // TS请求处理完毕
}

// ==================== 处理子M3U8请求 ====================
// 检查是否是子M3U8请求（嵌套的播放列表）
$isSubRequest = isset($_GET['sub']) && $_GET['sub'] === '1' && !empty($_GET['url']);

if ($isSubRequest) {
    // 获取子M3U8文件的URL
    $subUrl = $_GET['url'];
    
    // 获取子M3U8文件内容
    $ch = curl_init($subUrl);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,    // 返回响应内容
        CURLOPT_SSL_VERIFYPEER => false,   // 不验证SSL证书
        CURLOPT_SSL_VERIFYHOST => false,   // 不验证主机名
        CURLOPT_HTTPHEADER => [            // 设置请求头
            'User-Agent: aliplayer',
            'Referer: https://api.chinaaudiovisual.cn/',
            'Accept: */*',
            'Connection: keep-alive'
        ],
        CURLOPT_HEADER => false            // 不包含响应头
    ]);
    
    $m3u8Content = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    // 检查请求是否成功
    if ($httpCode != 200 || empty($m3u8Content)) {
        header('HTTP/1.1 502 Bad Gateway');
        echo "子M3U8获取失败: HTTP {$httpCode}";
        exit;
    }
    
    // 解析子M3U8 URL，提取基础路径（用于构建完整URL）
    $parsed = parse_url($subUrl);
    $baseUrlForM3u8 = "{$parsed['scheme']}://{$parsed['host']}";
    if (isset($parsed['path'])) {
        $m3u8Path = dirname($parsed['path']);  // 获取目录路径
        $baseUrlForM3u8 .= rtrim($m3u8Path, '/') . '/';  // 构建基础URL
    }
    
    // 按行处理M3U8内容
    $lines = explode("\n", $m3u8Content);
    $newLines = [];
    
    foreach ($lines as $line) {
        $trimmed = trim($line);
        
        // 处理空行和注释行（以#开头的行）
        if ($trimmed === '' || $trimmed[0] === '#') {
            // 特殊处理EXT-X-MAP标签（视频初始化片段）
            if (strpos($trimmed, '#EXT-X-MAP:URI=') === 0) {
                // 提取初始化片段的URL
                if (preg_match('/#EXT-X-MAP:URI="([^"]+)"/', $trimmed, $m)) {
                    $uri = $m[1];
                    
                    // 构建绝对URL（如果是相对路径就加上基础URL）
                    $abs = (strpos($uri, '://') === false) ? $baseUrlForM3u8 . ltrim($uri, '/') : $uri;
                    
                    // 解析URL获取路径和查询参数
                    $u = parse_url($abs);
                    $path = $u['path'] ?? '';
                    $query = isset($u['query']) ? $u['query'] : '';
                    
                    // 生成代理URL（通过本脚本访问）
                    $proxy = $_SERVER['SCRIPT_NAME'] . "?id={$id}&ts=1&path=" . urlencode(ltrim($path, '/'));
                    if ($query) $proxy .= "&{$query}";
                    
                    // 替换为代理URL
                    $newLines[] = '#EXT-X-MAP:URI="' . $proxy . '"';
                } else {
                    $newLines[] = $trimmed;
                }
            } else {
                // 其他注释行直接保留
                $newLines[] = $trimmed;
            }
            continue;
        }
        
        // 处理TS文件行：把相对路径转换成绝对URL，再转换成代理URL
        $abs = (strpos($trimmed, '://') === false) ? $baseUrlForM3u8 . ltrim($trimmed, '/') : $trimmed;
        $u = parse_url($abs);
        $path = $u['path'] ?? '';
        $query = isset($u['query']) ? $u['query'] : '';
        
        // 生成TS文件代理URL
        $proxy = $_SERVER['SCRIPT_NAME'] . "?id={$id}&ts=1&path=" . urlencode(ltrim($path, '/'));
        if ($query) $proxy .= "&{$query}";
        $newLines[] = $proxy;
    }
    
    // 输出重写后的M3U8内容
    header('Content-Type: application/vnd.apple.mpegurl');
    echo implode("\n", $newLines);
    exit;
}

// ==================== 处理主M3U8请求 ====================
// 如果有播放地址，处理主M3U8文件
if ($playUrl) {
    // 获取主M3U8文件内容
    $ch = curl_init($playUrl);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,    // 返回响应内容
        CURLOPT_SSL_VERIFYPEER => false,   // 不验证SSL证书
        CURLOPT_SSL_VERIFYHOST => false,   // 不验证主机名
        CURLOPT_HTTPHEADER => [            // 设置请求头
            'User-Agent: aliplayer',
            'Referer: https://api.chinaaudiovisual.cn/',
            'Accept: */*',
            'Connection: keep-alive'
        ],
        CURLOPT_HEADER => false            // 不包含响应头
    ]);
    
    $m3u8Content = curl_exec($ch);
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    // 检查请求是否成功
    if ($httpCode != 200 || empty($m3u8Content)) {
        header('HTTP/1.1 502 Bad Gateway');
        echo "M3U8获取失败: HTTP {$httpCode}";
        exit;
    }
    
    // 解析播放URL，提取基础路径
    $parsed = parse_url($playUrl);
    $baseUrlForM3u8 = "{$parsed['scheme']}://{$parsed['host']}";
    if (isset($parsed['path'])) {
        $m3u8Path = dirname($parsed['path']);
        $baseUrlForM3u8 .= rtrim($m3u8Path, '/') . '/';
    }
    
    // 按行处理M3U8内容
    $lines = explode("\n", $m3u8Content);
    $newLines = [];
    
    foreach ($lines as $line) {
        $trimmed = trim($line);
        
        // 处理空行和注释行
        if (empty($trimmed) || $trimmed[0] === '#') {
            // 在M3U8文件开头添加VLC播放器选项
            if (strpos($trimmed, '#EXTM3U') === 0) {
                $newLines[] = $trimmed;
                $newLines[] = '#EXTVLCOPT:http-referrer=https://api.chinaaudiovisual.cn/';
            } else {
                $newLines[] = $trimmed;
            }
            continue;
        } 
        // 特殊处理四川卫视4K（多码率自适应流）
        elseif ($id === 'sc4k') {
            // 重新处理所有行（多码率流需要特殊处理）
            $newLines = [];
            $expectNextUriToRewrite = false;  // 标记下一行是否需要重写
            
            foreach ($lines as $rawLine) {
                $trimmed = trim($rawLine);
                if ($trimmed === '') {
                    $newLines[] = $trimmed;
                    continue;
                }
                
                // 处理注释行
                if ($trimmed[0] === '#') {
                    // 处理媒体播放列表引用（多码率选择）
                    if (stripos($trimmed, '#EXT-X-MEDIA:') === 0) {
                        // 提取媒体播放列表URL
                        if (preg_match('/URI="([^"]+)"/i', $trimmed, $m)) {
                            $uri = $m[1];
                            // 构建绝对URL
                            $abs = (strpos($uri, '://') === false) ? $baseUrlForM3u8 . ltrim($uri, '/') : $uri;
                            // 生成子M3U8代理URL
                            $proxyM3u8 = $_SERVER['SCRIPT_NAME'] . "?id={$id}&sub=1&url=" . urlencode($abs);
                            // 替换URI为代理URL
                            $rewritten = preg_replace('/URI="[^"]+"/i', 'URI="' . $proxyM3u8 . '"', $trimmed, 1);
                            $newLines[] = $rewritten;
                        } else {
                            $newLines[] = $trimmed;
                        }
                    } else {
                        // 如果是流信息行，标记下一行需要重写
                        if (stripos($trimmed, '#EXT-X-STREAM-INF:') === 0) {
                            $expectNextUriToRewrite = true;
                        }
                        $newLines[] = $trimmed;
                    }
                    continue;
                }
                
                // 重写流URL（多码率播放列表）
                if ($expectNextUriToRewrite) {
                    $expectNextUriToRewrite = false;
                    $abs = (strpos($trimmed, '://') === false) ? $baseUrlForM3u8 . ltrim($trimmed, '/') : $trimmed;
                    // 生成子M3U8代理URL
                    $proxyM3u8 = $_SERVER['SCRIPT_NAME'] . "?id={$id}&sub=1&url=" . urlencode($abs);
                    $newLines[] = $proxyM3u8;
                } else {
                    // 构建绝对URL
                    $newLines[] = (strpos($trimmed, '://') === false) ? $baseUrlForM3u8 . ltrim($trimmed, '/') : $trimmed;
                }
            }
        } 
        // 特殊处理北京卫视4K和广东卫视4K（直接代理TS文件）
        elseif ($id === 'btv4k' || $id === 'gd4k') {
            // 分离路径和查询参数
            $path = strpos($line, '?') ? explode('?', $line, 2)[0] : $line;
            $query = strpos($line, '?') ? explode('?', $line, 2)[1] : '';
            
            // 生成TS文件代理URL
            $proxyUrl = $_SERVER['SCRIPT_NAME'] . "?id={$id}&ts=1&path=" . urlencode($path);
            $proxyUrl .= $query ? "&{$query}" : "";
            $newLines[] = $proxyUrl;
        } 
        // 默认处理：构建绝对URL
        else {
            $newLines[] = (strpos($line, '://') === false) ? $baseUrlForM3u8 . ltrim($line, '/') : $line;
        }
    }
    
    // 输出重写后的M3U8内容
    header('Content-Type: application/vnd.apple.mpegurl');
    echo implode("\n", $newLines);
} else {
    // 未找到播放地址
    header('HTTP/1.1 404 Not Found');
    echo '未找到播放地址';
}
?>