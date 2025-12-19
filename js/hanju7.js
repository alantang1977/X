/**
 * 新韩剧网(hanju7.com)爬虫
 * 作者：deepseek
 * 版本：1.0
 * 最后更新：2025-12-17
 * 专注于韩国影视作品的爬虫
 * 发布页 https://www.hanju7.com/
 */

function wvSpider() {
    const baseUrl = 'https://www.hanju7.com';
    // 延时函数
    const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
    
    /**
     * 提取视频列表数据（私有方法）
     * @param {Document} document - DOM文档对象
     * @param {string} selector - 选择器，可选，默认为'.list li'
     * @returns {Array} 视频数据数组
     */
    const extractVideos = (document, selector = '.list li') => {
        return Array.from(document.querySelectorAll(selector)).map(li => {
            const titleEl = li.querySelector('p a');
            const thumbEl = li.querySelector('.tu');
            const remarksEl = li.querySelector('.tip');
            const actorEl = li.querySelectorAll('p')[1];
            
            let vodId = titleEl?.getAttribute('href') || '';
            if (vodId && !vodId.startsWith('http')) {
                vodId = baseUrl + (vodId.startsWith('/') ? '' : '/') + vodId;
            }
            
            return {
                vod_name: titleEl?.title || titleEl?.textContent || '',
                vod_pic: thumbEl?.getAttribute('data-original') || '',
                vod_remarks: remarksEl?.textContent || '',
                vod_id: vodId,
                vod_actor: actorEl?.textContent || ''
            };
        });
    };

    /**
     * 提取分类筛选器（私有方法）
     * @param {Document} document - DOM文档对象
     * @returns {Object} 筛选器对象
     */
    const extractFilters = (document) => {
        const filters = {
            hanju: [], // 韩剧筛选器
            hanmovie: [], // 韩国电影筛选器
            hanzongyi: [] // 韩国综艺筛选器
        };
        
        // 提取年份筛选
        const yearItems = Array.from(document.querySelectorAll('.category_box .category:nth-child(2) dd a'))
            .map(a => ({
                n: a.textContent.trim(),
                v: a.getAttribute('href').match(/list\/\d+-(.*?)--\.html/)?.[1] || ''
            }));
        
        // 提取排序筛选
        const sortItems = Array.from(document.querySelectorAll('.category_box .category:nth-child(3) dd a'))
            .map(a => ({
                n: a.textContent.trim(),
                v: a.getAttribute('href').match(/list\/\d+--(.*?)-\.html/)?.[1] || ''
            }));
        
        // 为各类别添加相同的筛选条件（年份和排序）
        ['hanju', 'hanmovie', 'hanzongyi'].forEach(type => {
            filters[type].push(
                {
                    key: 'year',
                    name: '年份',
                    value: yearItems
                },
                {
                    key: 'sort',
                    name: '排序',
                    value: sortItems
                }
            );
        });
        
        return filters;
    };

    return {
        async init(cfg) {
            return {
                webview: {
                    debug: true,                // 是否开启调试模式
                    showWebView: false,         // 默认不显示
                    widthPercent: 80,           // 窗口宽度百分比
                    heightPercent: 60,          // 窗口高度百分比
                    keyword: '',                // 页面关键字检测
                    returnType: 'dom',          // 返回类型: 'html'或'dom'
                    timeout: 30,                // 超时时间（秒）
                    blockImages: true,          // 禁止加载图片
                    enableJavaScript: true,     // 是否启用JavaScript
                    header: {                   // 全局请求头
                        'Referer': baseUrl
                    }
                }
            };
        },
        
        async homeContent(filter) {
            console.log("homeContent 开始执行, filter:", filter);
            
            // 获取分类页面以提取完整筛选器
            const document = await Java.wvOpen(baseUrl + '/list/1---.html');
            const filters = extractFilters(document);
            
            return {
                class: [
                    { type_id: "hanju", type_name: "韩剧" },
                    { type_id: "hanmovie", type_name: "韩国电影" },
                    { type_id: "hanzongyi", type_name: "韩国综艺" },
                    { type_id: "hanyu", type_name: "韩娱" }
                ],
                filters: filters
            };
        },
        
        async homeVideoContent() {
            console.log("homeVideoContent 开始执行");
            
            const document = await Java.wvOpen(baseUrl + '/');
            const videos = extractVideos(document);
            
            console.log("取到的首页列表", videos);
            return { list: videos };
        },
        
        async categoryContent(tid, pg, filter, extend) {
            console.log("categoryContent 开始执行, 参数:", { tid, pg, filter, extend });
            
            // 映射类型ID到网站分类ID
            const typeMap = {
                'hanju': 1,
                'hanmovie': 3,
                'hanzongyi': 4,
                'hanyu': 'hanyu'
            };
            
            const siteTypeId = typeMap[tid] || 1;
            
            // 构建筛选参数
            let yearParam = '';
            let sortParam = 'newstime'; // 默认按最新排序
            
            if (filter) {
                if (filter.year) yearParam = filter.year;
                if (filter.sort) sortParam = filter.sort;
            }
            
            // 构建URL
            let url = '';
            if (tid === 'hanyu') {
                // 韩娱页面URL格式不同
                url = `${baseUrl}/${siteTypeId}.html`;
                if (pg > 1) {
                    url = `${baseUrl}/${siteTypeId}-${pg}.html`;
                }
            } else {
                // 其他分类的URL格式
                url = `${baseUrl}/list/${siteTypeId}-${yearParam}--${sortParam}-${pg > 1 ? pg - 1 : ''}.html`;
            }
            
            console.log("请求的分类URL:", url);
            const document = await Java.wvOpen(url);
            
            // 提取视频列表
            const videos = extractVideos(document);
            
            // 提取分页信息
            let page = 1;
            let pagecount = 1;
            
            const pageEls = document.querySelectorAll('.page a, .page .current');
            if (pageEls.length > 0) {
                // 当前页
                const currentEl = document.querySelector('.page .current');
                if (currentEl) {
                    page = parseInt(currentEl.textContent) || 1;
                }
                
                // 总页数 - 从最后一个页码链接获取
                const lastPageEl = pageEls[pageEls.length - 2]; // 倒数第二个是最后一页
                if (lastPageEl) {
                    const lastPageMatch = lastPageEl.getAttribute('href').match(/-(\d+)\.html$/);
                    if (lastPageMatch) {
                        pagecount = parseInt(lastPageMatch[1]) + 1 || 1; // 页码是从0开始的
                    }
                }
            }
            
            const result = {
                code: 1,
                msg: "数据列表",
                list: videos,
                page: page,
                pagecount: pagecount,
                limit: videos.length,
                total: pagecount * videos.length
            };
            
            console.log("分类数据结果:", result);
            return result;
        },
        
        async detailContent(ids) {
            console.log("detailContent 开始执行, ids:", ids[0]);
            const document = await Java.wvOpen(ids[0]);
            
            // 提取基本信息
            const titleEl = document.querySelector('title');
            const title = titleEl ? titleEl.textContent.replace(' - 新韩剧网', '') : '';
            
            const imgEl = document.querySelector('.tu.lazyload');
            const vod_pic = imgEl?.getAttribute('data-original') || '';
            
            // 提取详细数据（这里需要根据实际详情页结构调整选择器）
            let vod_area = '韩国', vod_year = '', vod_actor = '', vod_director = '', type_name = '', vod_remarks = '';
            
            // 提取演员信息（从列表页带过来的简略信息）
            const actorText = document.querySelector('.list li p:nth-child(2)')?.textContent || '';
            if (actorText) {
                vod_actor = actorText;
            }
            
            // 提取更新状态
            const tipEl = document.querySelector('.tip');
            if (tipEl) {
                vod_remarks = tipEl.textContent || '';
            }
            
            // 提取简介（这里需要根据实际详情页结构调整）
            const vod_content = document.querySelector('.intro')?.textContent?.trim() || '暂无简介';
            
            // 提取播放列表（这里需要根据实际详情页结构调整）
            const playlists = [];
            // 假设播放列表在class为play-list的元素中
            const playListEl = document.querySelector('.play-list');
            if (playListEl) {
                const episodes = Array.from(playListEl.querySelectorAll('a')).map(a => 
                    `${a.textContent.trim()}$${baseUrl + (a.getAttribute('href').startsWith('/') ? '' : '/') + a.getAttribute('href')}`
                );
                
                if (episodes.length > 0) {
                    playlists.push({
                        title: '在线播放',
                        episodes: episodes
                    });
                }
            }
            
            // 构建结果
            const vod = {
                code: 1,
                msg: "数据列表",
                page: 1,
                pagecount: 1,
                limit: 1,
                total: 1,
                list: [{
                    vod_id: ids[0],
                    vod_name: title,
                    vod_pic: vod_pic,
                    vod_remarks: vod_remarks,
                    vod_year: vod_year,
                    vod_actor: vod_actor,
                    vod_director: vod_director,
                    vod_area: vod_area,
                    vod_lang: '韩语',
                    vod_content: vod_content,
                    vod_play_from: playlists.map(p => p.title).join('$$$'),
                    vod_play_url: playlists.map(p => p.episodes.join('#')).join('$$$'),
                    type_name: type_name
                }]
            };
            
            console.log("详情页数据:", vod);
            return vod;
        },
        
        async searchContent(key, quick, pg) {
            console.log("searchContent 开始执行, 参数:", { key, quick, pg });
            
            const searchUrl = `${baseUrl}/search/?show=searchkey&keyboard=${encodeURIComponent(key)}${pg > 1 ? `&page=${pg}` : ''}`;
            const document = await Java.wvOpen(searchUrl);
            
            const videos = extractVideos(document);
            
            // 提取分页信息
            let page = pg || 1;
            let pagecount = 1;
            
            const pageEls = document.querySelectorAll('.page a');
            if (pageEls.length > 0) {
                // 总页数
                const lastPageEl = pageEls[pageEls.length - 1];
                if (lastPageEl && lastPageEl.textContent.includes('下一页')) {
                    const prevPageEl = pageEls[pageEls.length - 2];
                    if (prevPageEl) {
                        pagecount = parseInt(prevPageEl.textContent) || 1;
                    }
                }
            }
            
            return {
                code: 1,
                msg: "搜索结果",
                list: videos,
                page: page,
                pagecount: pagecount,
                limit: videos.length,
                total: pagecount * videos.length
            };
        },
        
        async playerContent(flag, id, vipFlags) {
            console.log("playerContent 开始执行, 参数:", { flag, id, vipFlags });
            
            // 获取播放页面内容
            const document = await Java.wvOpen(id);
            
            // 提取实际播放地址（这里需要根据实际播放页结构调整）
            let playUrl = '';
            const iframeEl = document.querySelector('iframe');
            if (iframeEl) {
                playUrl = iframeEl.getAttribute('src') || '';
                if (playUrl && !playUrl.startsWith('http')) {
                    playUrl = baseUrl + (playUrl.startsWith('/') ? '' : '/') + playUrl;
                }
            }
            
            // 如果没找到iframe，尝试查找视频源
            if (!playUrl) {
                const videoEl = document.querySelector('video');
                if (videoEl) {
                    playUrl = videoEl.getAttribute('src') || '';
                }
            }
            
            return { url: playUrl || id, parse: 1 };
        },
        
        async action(actionStr) {
            console.log("action 开始执行, actionStr:", actionStr);
            try {
                const params = JSON.parse(actionStr);
                console.log("action 参数解析:", params);
                // 可以根据需要处理自定义动作
            } catch (e) {
                console.log("action 不是JSON格式，作为字符串处理");
            }
            return { list: [] };
        }
    };
}

const spider = wvSpider();
spider;