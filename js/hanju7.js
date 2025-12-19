/**
 * 韩剧网(hanju7.com)爬虫
 * 作者：基于ddys爬虫模板适配
 * 版本：1.0
 * 最后更新：2025-12-17
 */

function hanju7Spider() {
    const baseUrl = 'https://www.hanju7.com';
    
    // 延时函数
    const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
    
    /**
     * 提取视频列表数据（私有方法）
     * @param {Document} document - DOM文档对象
     * @param {string} selector - 选择器，默认为'.list li'
     * @returns {Array} 视频数据数组
     */
    const extractVideos = (document, selector = '.list li') => {
        return Array.from(document.querySelectorAll(selector)).map(li => {
            const linkEl = li.querySelector('a.tu');
            const titleEl = li.querySelector('p a');
            const tipEl = li.querySelector('.tip');
            const actorEl = li.querySelector('p:nth-child(3)');
            
            // 提取图片URL
            let vod_pic = '';
            if (linkEl) {
                vod_pic = linkEl.getAttribute('data-original') || 
                          linkEl.style.backgroundImage?.match(/url\(["']?([^"')]+)["']?\)/)?.[1] || '';
            }
            
            // 提取详情页链接
            let vod_id = '';
            if (linkEl && linkEl.href) {
                vod_id = linkEl.href.startsWith('http') ? linkEl.href : baseUrl + (linkEl.href.startsWith('/') ? '' : '/') + linkEl.href;
            } else if (titleEl && titleEl.href) {
                vod_id = titleEl.href.startsWith('http') ? titleEl.href : baseUrl + (titleEl.href.startsWith('/') ? '' : '/') + titleEl.href;
            }
            
            // 提取标题
            let vod_name = '';
            if (titleEl) {
                vod_name = titleEl.title || titleEl.textContent || '';
            } else if (linkEl) {
                vod_name = linkEl.title || '';
            }
            
            // 生成视频ID（用于详情页）
            let videoId = '';
            if (vod_id) {
                const match = vod_id.match(/\/detail\/(\d+)\.html/);
                if (match) {
                    videoId = match[1];
                }
            }
            
            return {
                vod_id: videoId || vod_name.replace(/[^\w]/g, '_'),
                vod_name: vod_name,
                vod_pic: vod_pic,
                vod_remarks: tipEl?.textContent?.trim() || '',
                vod_actor: actorEl?.textContent?.trim() || '',
                vod_href: vod_id // 保存完整链接用于详情页
            };
        }).filter(video => video.vod_name && video.vod_pic); // 过滤无效数据
    };
    
    /**
     * 提取排行榜数据
     * @param {Document} document - DOM文档对象
     * @returns {Array} 排行榜视频数据
     */
    const extractRankVideos = (document) => {
        const rankVideos = [];
        
        // 提取韩剧榜
        const kdramaRankList = document.querySelectorAll('.box:nth-child(1) .list_txt li');
        kdramaRankList.forEach(li => {
            const spanEl = li.querySelector('span');
            const aEl = li.querySelector('a');
            const iEl = li.querySelector('i');
            
            if (aEl && aEl.href) {
                const vod_id = aEl.href.match(/\/detail\/(\d+)\.html/)?.[1] || '';
                rankVideos.push({
                    vod_id: vod_id,
                    vod_name: aEl.textContent.replace(/^\d+\s*/, '').trim(),
                    vod_remarks: spanEl?.textContent?.trim() || '',
                    vod_pic: `//pics.hanju7.com/pics/${vod_id}.jpg`,
                    vod_href: baseUrl + (aEl.href.startsWith('/') ? '' : '/') + aEl.href,
                    vod_type: '韩剧',
                    vod_rank: iEl?.textContent?.trim() || ''
                });
            }
        });
        
        // 提取韩影榜
        const movieRankList = document.querySelectorAll('.box:nth-child(2) .list_txt li');
        movieRankList.forEach(li => {
            const spanEl = li.querySelector('span');
            const aEl = li.querySelector('a');
            const iEl = li.querySelector('i');
            
            if (aEl && aEl.href) {
                const vod_id = aEl.href.match(/\/detail\/(\d+)\.html/)?.[1] || '';
                rankVideos.push({
                    vod_id: vod_id,
                    vod_name: aEl.textContent.replace(/^\d+\s*/, '').trim(),
                    vod_remarks: spanEl?.textContent?.trim() || '',
                    vod_pic: `//pics.hanju7.com/pics/${vod_id}.jpg`,
                    vod_href: baseUrl + (aEl.href.startsWith('/') ? '' : '/') + aEl.href,
                    vod_type: '韩影',
                    vod_rank: iEl?.textContent?.trim() || ''
                });
            }
        });
        
        // 提取韩综榜
        const varietyRankList = document.querySelectorAll('.box:nth-child(3) .list_txt li');
        varietyRankList.forEach(li => {
            const spanEl = li.querySelector('span');
            const aEl = li.querySelector('a');
            const iEl = li.querySelector('i');
            
            if (aEl && aEl.href) {
                const vod_id = aEl.href.match(/\/detail\/(\d+)\.html/)?.[1] || '';
                rankVideos.push({
                    vod_id: vod_id,
                    vod_name: aEl.textContent.replace(/^\d+\s*/, '').trim(),
                    vod_remarks: spanEl?.textContent?.trim() || '',
                    vod_pic: `//pics.hanju7.com/pics/${vod_id}.jpg`,
                    vod_href: baseUrl + (aEl.href.startsWith('/') ? '' : '/') + aEl.href,
                    vod_type: '韩综',
                    vod_rank: iEl?.textContent?.trim() || ''
                });
            }
        });
        
        return rankVideos;
    };

    return {
        async init(cfg) {
            return {
                webview: {
                    debug: true,
                    showWebView: false,
                    widthPercent: 80,
                    heightPercent: 60,
                    keyword: '',
                    returnType: 'dom',
                    timeout: 30,
                    blockImages: true,
                    enableJavaScript: true,
                    header: {
                        'Referer': baseUrl,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                }
            };
        },
        
        async homeContent(filter) {
            console.log("homeContent 开始执行, filter:", filter);

            return {
                class: [
                    { type_id: "1", type_name: "韩剧" },
                    { type_id: "3", type_name: "韩国电影" },
                    { type_id: "4", type_name: "韩国综艺" },
                    { type_id: "hot", type_name: "排行榜" },
                    { type_id: "new", type_name: "最近更新" }
                ]
            };
        },
        
        async homeVideoContent() {
            console.log("homeVideoContent 开始执行");

            try {
                const document = await Java.wvOpen(baseUrl + '/');
                
                // 提取首页的三个板块
                const allVideos = [];
                
                // 韩剧板块
                const kdramaSection = document.querySelector('.box:nth-child(1) .list');
                if (kdramaSection) {
                    const kdramaVideos = extractVideos(kdramaSection);
                    allVideos.push(...kdramaVideos.map(v => ({...v, vod_type: '韩剧'})));
                }
                
                // 韩影板块
                const movieSection = document.querySelector('.box:nth-child(2) .list');
                if (movieSection) {
                    const movieVideos = extractVideos(movieSection);
                    allVideos.push(...movieVideos.map(v => ({...v, vod_type: '韩影'})));
                }
                
                // 韩综板块
                const varietySection = document.querySelector('.box:nth-child(3) .list');
                if (varietySection) {
                    const varietyVideos = extractVideos(varietySection);
                    allVideos.push(...varietyVideos.map(v => ({...v, vod_type: '韩综'})));
                }
                
                // 提取排行榜数据
                const rankVideos = extractRankVideos(document);
                allVideos.push(...rankVideos);
                
                console.log("首页取到的视频列表，共", allVideos.length, "条");
                return { list: allVideos };
            } catch (error) {
                console.error("homeVideoContent 出错:", error);
                return { list: [] };
            }
        },
        
        async categoryContent(tid, pg, filter, extend) {
            console.log(`categoryContent - tid:${tid}, pg:${pg}`);
            
            try {
                let url = '';
                if (tid === 'hot') {
                    url = `${baseUrl}/hot.html`;
                } else if (tid === 'new') {
                    url = `${baseUrl}/new.html`;
                } else {
                    url = `${baseUrl}/list/${tid}---${pg}---.html`;
                }
                
                const document = await Java.wvOpen(url);
                
                // 提取列表数据
                const videos = extractVideos(document);
                
                // 提取分页信息
                let page = pg || 1;
                let pagecount = 1;
                let total = videos.length;
                
                // 尝试获取分页信息
                const pageElement = document.querySelector('.pages a:last-child');
                if (pageElement) {
                    const pageText = pageElement.textContent;
                    const pageMatch = pageText.match(/\d+/);
                    if (pageMatch) {
                        pagecount = parseInt(pageMatch[0]);
                    }
                }
                
                console.log(`categoryContent - 获取到 ${videos.length} 条数据`);
                
                return {
                    code: 1,
                    msg: "数据列表",
                    list: videos,
                    page: parseInt(page),
                    pagecount: pagecount,
                    limit: 20,
                    total: total
                };
            } catch (error) {
                console.error("categoryContent 出错:", error);
                return { code: 0, msg: "获取数据失败", list: [] };
            }
        },
        
        async detailContent(ids) {
            console.log("detailContent - ids:", ids);
            
            try {
                const id = ids[0];
                let url = '';
                
                // 判断是完整URL还是ID
                if (id.startsWith('http')) {
                    url = id;
                } else if (id.match(/^\d+$/)) {
                    url = `${baseUrl}/detail/${id}.html`;
                } else {
                    // 尝试从vod_href中获取
                    url = id;
                }
                
                const document = await Java.wvOpen(url);
                
                // 提取基本信息
                const title = document.querySelector('.detail h1')?.textContent?.trim() || 
                             document.querySelector('.detail .title')?.textContent?.trim() || '';
                
                // 提取图片
                const imgEl = document.querySelector('.pic img, .detail-pic img');
                let vod_pic = '';
                if (imgEl) {
                    vod_pic = imgEl.getAttribute('src') || 
                             imgEl.getAttribute('data-src') || 
                             imgEl.getAttribute('data-original') || '';
                }
                
                if (!vod_pic && id.match(/^\d+$/)) {
                    vod_pic = `//pics.hanju7.com/pics/${id}.jpg`;
                }
                
                // 提取详细信息
                let vod_area = '', vod_year = '', vod_actor = '', vod_director = '', 
                    vod_remarks = '', vod_lang = '', vod_content = '';
                
                const infoElements = document.querySelectorAll('.info p, .detail-info p, .info li');
                infoElements.forEach(el => {
                    const text = el.textContent.trim();
                    if (text.includes('地区：')) vod_area = text.replace('地区：', '').trim();
                    else if (text.includes('年份：')) vod_year = text.replace('年份：', '').trim();
                    else if (text.includes('主演：')) vod_actor = text.replace('主演：', '').trim();
                    else if (text.includes('导演：')) vod_director = text.replace('导演：', '').trim();
                    else if (text.includes('语言：')) vod_lang = text.replace('语言：', '').trim();
                    else if (text.includes('状态：')) vod_remarks = text.replace('状态：', '').trim();
                    else if (text.includes('更新：')) vod_remarks = text.replace('更新：', '').trim();
                });
                
                // 提取简介
                const contentEl = document.querySelector('.content, .intro, .detail-content');
                if (contentEl) {
                    vod_content = contentEl.textContent.trim();
                }
                
                // 提取播放列表
                const playlists = [];
                const playElements = document.querySelectorAll('.playlist, .play-list, .downlist');
                
                playElements.forEach((playlist, index) => {
                    const episodes = [];
                    const links = playlist.querySelectorAll('a');
                    
                    links.forEach(a => {
                        const episodeName = a.textContent.trim();
                        let episodeUrl = a.getAttribute('href') || '';
                        
                        if (episodeUrl && !episodeUrl.startsWith('http')) {
                            episodeUrl = baseUrl + (episodeUrl.startsWith('/') ? '' : '/') + episodeUrl;
                        }
                        
                        if (episodeName && episodeUrl) {
                            episodes.push(`${episodeName}$${episodeUrl}`);
                        }
                    });
                    
                    if (episodes.length > 0) {
                        playlists.push({
                            title: `线路${index + 1}`,
                            episodes: episodes
                        });
                    }
                });
                
                // 如果没有找到播放列表，尝试其他选择器
                if (playlists.length === 0) {
                    const allLinks = document.querySelectorAll('a[href*="play"]');
                    allLinks.forEach(a => {
                        if (a.textContent.includes('播放') || a.href.includes('play')) {
                            playlists.push({
                                title: '在线播放',
                                episodes: [`播放$${a.href}`]
                            });
                        }
                    });
                }
                
                // 构建视频对象
                const vod = {
                    vod_id: id.match(/^\d+$/) ? id : id.replace(/[^\w]/g, '_'),
                    vod_name: title,
                    vod_pic: vod_pic,
                    vod_remarks: vod_remarks,
                    vod_year: vod_year,
                    vod_actor: vod_actor,
                    vod_director: vod_director,
                    vod_area: vod_area,
                    vod_lang: vod_lang || '韩语',
                    vod_content: vod_content,
                    vod_play_from: playlists.map(p => p.title).join('$$$'),
                    vod_play_url: playlists.map(p => p.episodes.join('#')).join('$$$'),
                    type_name: '' // 将在下面判断
                };
                
                // 判断类型
                if (url.includes('/detail/')) {
                    const typeMatch = url.match(/\/list\/(\d+)---/);
                    if (typeMatch) {
                        const typeId = typeMatch[1];
                        if (typeId === '1') vod.type_name = '韩剧';
                        else if (typeId === '3') vod.type_name = '韩国电影';
                        else if (typeId === '4') vod.type_name = '韩国综艺';
                    }
                }
                
                return {
                    code: 1,
                    msg: "数据列表",
                    page: 1,
                    pagecount: 1,
                    limit: 1,
                    total: 1,
                    list: [vod]
                };
                
            } catch (error) {
                console.error("detailContent 出错:", error);
                return {
                    code: 0,
                    msg: "获取详情失败",
                    list: []
                };
            }
        },
        
        async searchContent(key, quick, pg) {
            console.log("searchContent - key:", key, "pg:", pg);
            
            try {
                const encodedKey = encodeURIComponent(key);
                const url = `${baseUrl}/search/?wd=${encodedKey}&page=${pg || 1}`;
                
                const document = await Java.wvOpen(url);
                
                // 提取搜索结果
                const videos = extractVideos(document, '.search-list li');
                
                // 如果没有找到，尝试其他选择器
                if (videos.length === 0) {
                    const fallbackVideos = extractVideos(document, '.list li');
                    return {
                        code: 1,
                        msg: "搜索结果",
                        list: fallbackVideos,
                        page: pg || 1,
                        pagecount: 1,
                        limit: 20,
                        total: fallbackVideos.length
                    };
                }
                
                return {
                    code: 1,
                    msg: "搜索结果",
                    list: videos,
                    page: pg || 1,
                    pagecount: 1,
                    limit: 20,
                    total: videos.length
                };
            } catch (error) {
                console.error("searchContent 出错:", error);
                return { code: 0, msg: "搜索失败", list: [] };
            }
        },
        
        async playerContent(flag, id, vipFlags) {
            console.log("playerContent - flag:", flag, "id:", id);
            
            // 韩剧网直接返回原始播放链接
            return { 
                url: id, 
                parse: 1,  // 表示需要解析
                header: {
                    'Referer': baseUrl,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            };
        },
        
        async action(actionStr) {
            console.log("action - actionStr:", actionStr);
            try {
                const params = JSON.parse(actionStr);
                console.log("action params:", params);
                // 这里可以根据action参数执行特定操作
                return { code: 1, msg: "操作成功", list: [] };
            } catch (e) {
                console.log("action is not JSON, treat as string");
                return { code: 0, msg: "操作失败", list: [] };
            }
        }
    };
}

const spider = hanju7Spider();
spider;
