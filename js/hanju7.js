/**
 * 新韩剧网 (hanju7.com) 爬虫
 * 适配原生 JS 提取逻辑与 WebView 模式
 */

function wvSpider() {
    const baseUrl = 'https://www.hanju7.com';

    // 补全 URL 工具函数
    const fixUrl = (url) => {
        if (!url) return '';
        if (url.startsWith('//')) return 'https:' + url;
        if (url.startsWith('/')) return baseUrl + url;
        return url;
    };

    return {
        /* 初始化配置 */
        async init(cfg) {
            return {
                webview: {
                    showWebView: false,
                    returnType: 'dom', // 使用 DOM 模式，方便直接操作 document
                    timeout: 30,
                    blockImages: true,
                    header: {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                }
            };
        },

        /* 分类列表 */
        async homeContent(filter) {
            return {
                class: [
                    { type_id: "1", type_name: "韩剧" },
                    { type_id: "3", type_name: "韩国电影" },
                    { type_id: "4", type_name: "韩国综艺" }
                ]
            };
        },

        /* 首页最近更新 */
        async homeVideoContent() {
            const document = await Java.wvOpen(baseUrl + '/');
            const items = document.querySelectorAll('.box_r .list li');
            const videos = Array.from(items).map(li => {
                const a = li.querySelector('a.tu');
                return {
                    vod_name: a?.getAttribute('title') || '',
                    vod_pic: fixUrl(a?.getAttribute('data-original')),
                    vod_remarks: li.querySelector('.tip')?.textContent || '',
                    vod_id: fixUrl(a?.getAttribute('href'))
                };
            });
            return { list: videos };
        },

        /* 分类页数据 */
        async categoryContent(tid, pg, filter, extend) {
            const url = `${baseUrl}/list/${tid}---${pg}.html`;
            const document = await Java.wvOpen(url);
            const items = document.querySelectorAll('.list ul li');
            const videos = Array.from(items).map(li => {
                const a = li.querySelector('a.tu');
                if (!a) return null;
                return {
                    vod_name: a.getAttribute('title'),
                    vod_pic: fixUrl(a.getAttribute('data-original')),
                    vod_remarks: li.querySelector('.tip')?.textContent || '',
                    vod_id: fixUrl(a.getAttribute('href'))
                };
            }).filter(Boolean);

            return { 
                list: videos, 
                page: pg, 
                pagecount: 99 // 简单处理分页
            };
        },

        /* 详情页数据提取（重点针对你发送的 HTML） */
        async detailContent(ids) {
            const detailUrl = ids[0];
            const document = await Java.wvOpen(detailUrl);

            // 1. 提取元数据（通过辅助函数查找 dt/dd）
            const getVal = (label) => {
                const dts = Array.from(document.querySelectorAll('.info dl dt'));
                const dt = dts.find(it => it.textContent.includes(label));
                return dt ? dt.nextElementSibling.textContent.trim() : '';
            };

            const vod = {
                vod_id: detailUrl,
                vod_name: document.querySelector('.info dl dd')?.textContent.trim() || '',
                vod_pic: fixUrl(document.querySelector('.pic img')?.getAttribute('data-original')),
                vod_actor: getVal('主演'),
                vod_area: getVal('电视'),
                vod_year: getVal('上映'),
                vod_remarks: getVal('状态'),
                vod_content: document.querySelector('.juqing')?.textContent.trim() || ''
            };

            // 2. 提取播放列表：解析 onclick="bb_a('3499_1_1',...)"
            const playLinks = document.querySelectorAll('.play ul li a');
            const playlist = [];

            playLinks.forEach(a => {
                const name = a.textContent.trim();
                const onclick = a.getAttribute('onclick') || '';
                // 正则匹配 bb_a 中的第一个参数作为 ID
                const match = onclick.match(/bb_a\('([^']+)'/);
                if (match) {
                    const playId = match[1];
                    // 构造播放页地址：/play/3499_1_1.html
                    const playUrl = `${baseUrl}/play/${playId}.html`;
                    playlist.push(`${name}$${playUrl}`);
                }
            });

            vod.vod_play_from = '在线云播';
            vod.vod_play_url = playlist.join('#');

            return { list: [vod] };
        },

        /* 搜索功能 */
        async searchContent(key, quick, pg) {
            // 该站搜索使用 POST 或特定 URL 拼接
            const searchUrl = `${baseUrl}/search/index.php?keyboard=${encodeURIComponent(key)}`;
            const document = await Java.wvOpen(searchUrl);
            const items = document.querySelectorAll('.list ul li');
            const videos = Array.from(items).map(li => {
                const a = li.querySelector('a.tu');
                if (!a) return null;
                return {
                    vod_name: a.getAttribute('title'),
                    vod_pic: fixUrl(a.getAttribute('data-original')),
                    vod_remarks: li.querySelector('.tip')?.textContent || '',
                    vod_id: fixUrl(a.getAttribute('href'))
                };
            }).filter(Boolean);
            return { list: videos };
        },

        /* 播放解析 */
        async playerContent(flag, id, vipFlags) {
            // id 是详情页拼出的 /play/xxxx.html
            // 在 WebView 模式下，直接返回这个 URL，WebView 会自动加载并触发嗅探
            return {
                url: id,
                parse: 1, // 设为 1 启用自动嗅探视频流
                header: {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
                    'Referer': baseUrl
                }
            };
        }
    };
}

// 导出爬虫实例
const spider = wvSpider();
spider;
