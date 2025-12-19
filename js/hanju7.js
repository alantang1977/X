/**
 * 新韩剧网(hanju7.com)爬虫 - 极简解决方案版
 * 作者：助手
 * 版本：2.1
 * 最后更新：2025-12-19
 * 发布页 https://www.hanju7.com/
 */

function hanjuSpider() {
    const baseUrl = 'https://www.hanju7.com';
    
    /**
     * 提取视频列表数据（私有方法）
     */
    const extractVideos = (document, selector = '.list li') => {
        return Array.from(document.querySelectorAll(selector)).map(item => {
            const linkEl = item.querySelector('a.tu');
            const titleEl = item.querySelector('p a');
            const tipEl = item.querySelector('.tip');
            const actorsEl = item.querySelector('p:nth-child(3)');
            
            let vodId = linkEl?.getAttribute('href') || '';
            if (vodId && !vodId.startsWith('http')) {
                vodId = baseUrl + (vodId.startsWith('/') ? '' : '/') + vodId;
            }
            
            // 提取图片
            let vodPic = '';
            const imgEl = linkEl?.querySelector('img');
            if (imgEl) {
                vodPic = imgEl.getAttribute('data-original') || imgEl.src || '';
            } else if (linkEl) {
                vodPic = linkEl.getAttribute('data-original') || '';
            }
            
            // 确保图片地址是完整的URL
            if (vodPic && !vodPic.startsWith('http')) {
                vodPic = vodPic.startsWith('//') ? 'https:' + vodPic : (vodPic.startsWith('/') ? baseUrl + vodPic : baseUrl + '/' + vodPic);
            }
            
            return {
                vod_name: titleEl?.textContent?.trim() || '',
                vod_pic: vodPic,
                vod_remarks: tipEl?.textContent?.trim() || '',
                vod_id: vodId,
                vod_actor: actorsEl?.textContent?.replace(/…$/, '')?.trim() || ''
            };
        }).filter(vod => vod.vod_name);
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
                    { type_id: "4", type_name: "韩国综艺" }
                ]
            };
        },
        
        async homeVideoContent() {
            console.log("homeVideoContent 开始执行");

            const document = await Java.wvOpen(baseUrl + '/');
            
            // 提取首页三个榜单的视频
            const videos = [];
            
            // 获取所有.box元素
            const boxes = document.querySelectorAll('.box');
            
            // 第一个box是韩剧榜
            if (boxes[0]) {
                const hanjuVideos = extractVideos(boxes[0]);
                videos.push(...hanjuVideos);
            }
            
            // 第二个box是韩影榜
            if (boxes[1]) {
                const hanyingVideos = extractVideos(boxes[1]);
                videos.push(...hanyingVideos);
            }
            
            // 第三个box是韩综榜
            if (boxes[2]) {
                const hanzongVideos = extractVideos(boxes[2]);
                videos.push(...hanzongVideos);
            }

            console.log("首页取到的视频列表", videos);
            return { list: videos };
        },
        
        async categoryContent(tid, pg, filter, extend) {
            console.log("categoryContent - tid:", tid, "pg:", pg);
            
            // 构建分类页URL
            let url = `${baseUrl}/list/${tid}---.html`;
            if (pg > 1) {
                url = `${baseUrl}/list/${tid}---${pg-1}.html`;
            }
            
            const document = await Java.wvOpen(url);
            const videos = extractVideos(document);
            
            // 提取分页信息
            let currentPage = pg || 1;
            let totalPages = 1;
            
            const pageEl = document.querySelector('.page');
            if (pageEl) {
                const currentSpan = pageEl.querySelector('.current');
                if (currentSpan) {
                    currentPage = parseInt(currentSpan.textContent) || pg || 1;
                }
                
                const links = pageEl.querySelectorAll('a');
                if (links.length > 0) {
                    totalPages = currentPage + 10;
                }
            }

            console.log("categoryContent 返回数据");
            
            return {
                code: 1,
                msg: "数据列表",
                list: videos,
                page: currentPage,
                pagecount: totalPages,
                limit: 16,
                total: totalPages * 16
            };
        },
        
        async detailContent(ids) {
            console.log("detailContent - ids:", ids[0]);
            const document = await Java.wvOpen(ids[0]);

            // 提取基本信息
            const title = document.querySelector('#wp1ay .name dd')?.textContent?.trim() || 
                         document.querySelector('.box .name dd')?.textContent?.trim() || '';
            
            // 提取封面图片
            const imgEl = document.querySelector('.detail .pic img');
            let vodPic = imgEl?.getAttribute('data-original') || imgEl?.src || '';
            
            // 处理图片地址
            if (vodPic) {
                if (vodPic.startsWith('//')) {
                    vodPic = 'https:' + vodPic;
                } else if (!vodPic.startsWith('http')) {
                    vodPic = vodPic.startsWith('/') ? baseUrl + vodPic : baseUrl + '/' + vodPic;
                }
            }
            
            // 提取详细数据
            let vod_actor = '', vod_year = '', vod_remarks = '', vod_area = '韩国', type_name = '';
            const infoDl = document.querySelectorAll('.info dl');
            
            infoDl.forEach(dl => {
                const dt = dl.querySelector('dt')?.textContent?.trim();
                const dd = dl.querySelector('dd')?.textContent?.trim();
                
                if (!dt || !dd) return;
                
                switch (dt) {
                    case '主演：':
                        vod_actor = dd;
                        break;
                    case '上映：':
                        vod_year = dd.split('-')[0] || '';
                        break;
                    case '状态：':
                        vod_remarks = dd;
                        break;
                }
            });
            
            // 提取剧情介绍
            const vod_content = document.querySelector('.juqing p')?.textContent?.trim() || 
                              document.querySelector('.juqing')?.textContent?.trim() || '';
            
            // 提取播放列表
            const playlists = [];
            const playEl = document.querySelector('.play ul');
            
            if (playEl) {
                const episodes = [];
                const links = playEl.querySelectorAll('a');
                
                links.forEach((link, index) => {
                    const title = link.textContent?.trim() || `播放源${index + 1}`;
                    const onclick = link.getAttribute('onclick');
                    
                    if (onclick) {
                        // 解析 onclick 中的参数
                        // 格式: bb_a('1365_1_1','HD',event)
                        const match = onclick.match(/bb_a\('([^']+)'[\s,]*'([^']*)'/);
                        if (match) {
                            const playId = match[1];
                            episodes.push(`${title}$${playId}`);
                        }
                    }
                });
                
                if (episodes.length > 0) {
                    playlists.push({
                        title: '在线云播',
                        episodes: episodes
                    });
                }
            }
            
            // 从script中提取类型信息
            const scripts = document.querySelectorAll('script');
            scripts.forEach(script => {
                const content = script.textContent;
                if (content.includes('korcms')) {
                    const typeMatch = content.match(/"type":"(\d+)"/);
                    if (typeMatch) {
                        const typeId = typeMatch[1];
                        const typeMap = {
                            '1': '韩剧',
                            '3': '韩国电影',
                            '4': '韩国综艺'
                        };
                        type_name = typeMap[typeId] || '';
                    }
                }
            });
            
            // 构建视频详情
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
                    vod_pic: vodPic,
                    vod_remarks: vod_remarks,
                    vod_year: vod_year,
                    vod_actor: vod_actor,
                    vod_director: '',
                    vod_area: vod_area,
                    vod_lang: '韩语',
                    vod_content: vod_content,
                    vod_play_from: playlists.map(p => p.title).join('$$$') || '在线云播',
                    vod_play_url: playlists.map(p => p.episodes.join('#')).join('$$$') || '',
                    type_name: type_name
                }]
            };
            
            console.log("detailContent 返回数据:", vod);
            return vod;
        },
        
        async searchContent(key, quick, pg) {
            console.log("searchContent - key:", key, "quick:", quick, "pg:", pg);
            
            const searchUrl = `${baseUrl}/search/?show=searchkey&keyboard=${encodeURIComponent(key)}`;
            
            try {
                const document = await Java.wvOpen(searchUrl);
                const videos = extractVideos(document);
                
                return {
                    list: videos,
                    page: 1,
                    pagecount: 1,
                    limit: 20,
                    total: videos.length
                };
            } catch (error) {
                console.log("搜索失败:", error);
                return { list: [] };
            }
        },
        
        async playerContent(flag, id, vipFlags) {
            console.log("playerContent - flag:", flag, "id:", id, "vipFlags:", vipFlags);
            
            if (!id || id.trim() === '') {
                console.error("播放ID为空");
                return {
                    url: `https://jx.bozrc.com:4433/player/?url=${baseUrl}`,
                    parse: 1,
                    header: {
                        'Referer': baseUrl,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                };
            }
            
            try {
                // 解析播放ID
                const parts = id.split('_');
                if (parts.length < 3) {
                    throw new Error(`无效的播放ID格式: ${id}`);
                }
                
                const videoId = parts[0];
                console.log("视频ID:", videoId, "播放ID:", id);
                
                // 方案1：尝试直接构造播放地址（根据我们之前分析的逻辑）
                // 根据网站JavaScript，播放地址是通过 /u/u1.php?ud={id} 获取并解密的
                // 但由于CORS限制，我们无法直接获取
                
                // 方案2：尝试直接访问播放页
                try {
                    const playPageUrl = `${baseUrl}/play/${videoId}_${parts[2] || '1'}.html`;
                    console.log("尝试访问播放页:", playPageUrl);
                    
                    // 注意：这里我们只是记录URL，不实际访问
                    // 因为Java.wvOpen可能无法正确处理播放页
                    
                    // 尝试一些可能的直接视频地址格式
                    const possibleUrls = [
                        // 可能是直接的视频地址
                        `https://vod.hanju7.com/${videoId}/index.m3u8`,
                        `https://play.hanju7.com/vod/${videoId}.m3u8`,
                        `https://cdn.hanju7.com/${videoId}/playlist.m3u8`,
                        `https://v.hanju7.com/${videoId}/video.m3u8`,
                        
                        // 可能是通过API获取的地址
                        `${baseUrl}/api/play/${videoId}`,
                        `${baseUrl}/play_api.php?id=${videoId}`,
                        `${baseUrl}/vod_api.php?vid=${videoId}`,
                        
                        // 可能是播放页
                        playPageUrl,
                        `${baseUrl}/player/${videoId}.html`,
                        `${baseUrl}/vod/${videoId}.html`
                    ];
                    
                    console.log("可能的播放地址:", possibleUrls);
                    
                    // 由于我们无法直接测试这些地址，我们选择最有可能的一个
                    // 根据之前的分析，真实的播放地址格式可能是：
                    // /m3/edit-down.php?url={解密后的视频地址}
                    
                    // 我们无法解密，所以直接返回播放页让播放器尝试解析
                    return {
                        url: playPageUrl,
                        parse: 1, // 需要解析
                        header: {
                            'Referer': baseUrl,
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Origin': baseUrl
                        }
                    };
                    
                } catch (error) {
                    console.log("构造播放地址失败:", error);
                    throw error;
                }
                
            } catch (error) {
                console.error("获取播放地址失败:", error);
                
                // 备用方案：回退到通用解析
                const videoId = id.split('_')[0] || '';
                const detailUrl = videoId ? `${baseUrl}/detail/${videoId}.html` : baseUrl;
                console.log("回退到通用解析:", detailUrl);
                
                return {
                    url: `https://jx.bozrc.com:4433/player/?url=${encodeURIComponent(detailUrl)}`,
                    parse: 1, // 需要解析
                    header: {
                        'Referer': baseUrl,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                };
            }
        },
        
        async action(actionStr) {
            console.log("action - actionStr:", actionStr);
            try {
                const params = JSON.parse(actionStr);
                console.log("action params:", params);
                
                if (params.action === 'getPossibleUrls') {
                    const { videoId, episode = 1 } = params;
                    const playId = `${videoId}_1_${episode}`;
                    
                    // 返回所有可能的播放地址
                    const possibleUrls = [
                        `${baseUrl}/play/${videoId}_${episode}.html`,
                        `${baseUrl}/player/${videoId}.html`,
                        `${baseUrl}/vod/${videoId}.html`,
                        `${baseUrl}/api/play/${videoId}`,
                        `${baseUrl}/play_api.php?id=${videoId}`,
                        `${baseUrl}/vod_api.php?vid=${videoId}`,
                        `${baseUrl}/player_api.php?vid=${videoId}&episode=${episode}`,
                        `https://vod.hanju7.com/${videoId}/index.m3u8`,
                        `https://play.hanju7.com/vod/${videoId}.m3u8`,
                        `https://cdn.hanju7.com/${videoId}/playlist.m3u8`,
                        `${baseUrl}/u/u1.php?ud=${playId}`,
                        `${baseUrl}/m3/edit-down.php?url=`
                    ];
                    
                    return {
                        videoId: videoId,
                        playId: playId,
                        possibleUrls: possibleUrls,
                        message: "所有可能的播放地址（需要手动测试哪个可用）"
                    };
                }
                
            } catch (e) {
                console.log("action is not JSON, treat as string");
            }
            return { list: [] };
        }
    };
}

const spider = hanjuSpider();
spider;
