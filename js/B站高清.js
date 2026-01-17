/**
 * 哔哩哔哩 - 猫影视/TVBox JS爬虫格式
 * 调用壳子超级解析功能
 */

class Spider extends BaseSpider {
    
    constructor() {
        super();
        this.host = 'https://www.bilibili.com';
        
        this.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.com',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cookie': 'bili_jct=; DedeUserID=; SESSDATA=;'
        };
        
        // 分类配置
        this.classes = [
            { type_id: '1', type_name: '番剧' },
            { type_id: '4', type_name: '国创' },
            { type_id: '2', type_name: '电影' },
            { type_id: '5', type_name: '电视剧' },
            { type_id: '3', type_name: '纪录片' },
            { type_id: '7', type_name: '综艺' },
            { type_id: '全部', type_name: '全部' },
            { type_id: '追番', type_name: '追番' },
            { type_id: '追剧', type_name: '追剧' },
            { type_id: '时间表', type_name: '时间表' }
        ];
        
        // 筛选配置
        this.filters = {
            '全部': [
                {
                    key: 'tid',
                    name: '分类',
                    value: [
                        { n: '番剧', v: '1' },
                        { n: '国创', v: '4' },
                        { n: '电影', v: '2' },
                        { n: '电视剧', v: '5' },
                        { n: '记录片', v: '3' },
                        { n: '综艺', v: '7' }
                    ]
                },
                {
                    key: 'order',
                    name: '排序',
                    value: [
                        { n: '播放数量', v: '2' },
                        { n: '更新时间', v: '0' },
                        { n: '最高评分', v: '4' },
                        { n: '弹幕数量', v: '1' },
                        { n: '追看人数', v: '3' },
                        { n: '开播时间', v: '5' },
                        { n: '上映时间', v: '6' }
                    ]
                },
                {
                    key: 'season_status',
                    name: '付费',
                    value: [
                        { n: '全部', v: '-1' },
                        { n: '免费', v: '1' },
                        { n: '付费', v: '2%2C6' },
                        { n: '大会员', v: '4%2C6' }
                    ]
                }
            ],
            '时间表': [
                {
                    key: 'tid',
                    name: '分类',
                    value: [
                        { n: '番剧', v: '1' },
                        { n: '国创', v: '4' }
                    ]
                }
            ]
        };
    }
    
    init(extend = '') {
        return '';
    }
    
    getName() {
        return '哔哩哔哩';
    }
    
    isVideoFormat(url) {
        return true;
    }
    
    manualVideoCheck() {
        return false;
    }
    
    destroy() {
        // 清理资源
    }
    
    homeContent(filter) {
        const result = {
            class: this.classes,
            filters: this.filters
        };
        
        return result;
    }
    
    async homeVideoContent() {
        try {
            const videos = [];
            
            // 获取番剧排行榜
            const bangumiList = await this.getRankList(1, 1);
            videos.push(...bangumiList.slice(0, 5));
            
            // 获取其他分类排行榜
            const categories = [4, 2, 5, 3, 7];
            for (const cat of categories) {
                const list = await this.getRankList(cat, 1);
                videos.push(...list.slice(0, 3));
            }
            
            // 过滤预告片
            const filteredVideos = videos.filter(item => 
                !item.vod_name?.includes("预告") && 
                !item.vod_remarks?.includes("预告")
            );
            
            return { list: filteredVideos };
            
        } catch (error) {
            console.error(`homeVideoContent error: ${error.message}`);
            return { list: [] };
        }
    }
    
    async categoryContent(tid, pg, filter, extend) {
        try {
            const page = parseInt(pg) || 1;
            let videos = [];
            
            // 解析筛选参数
            let filterObj = {};
            if (extend) {
                if (typeof extend === 'string') {
                    try {
                        filterObj = JSON.parse(extend);
                    } catch (e) {
                        // 如果不是JSON，尝试解析为key=value格式
                        extend.split('&').forEach(item => {
                            const [key, value] = item.split('=');
                            if (key && value) {
                                filterObj[key] = value;
                            }
                        });
                    }
                } else if (typeof extend === 'object') {
                    filterObj = extend;
                }
            }
            
            if (tid === '1') { // 番剧
                videos = await this.getRankList(1, page);
            } else if (['2', '3', '4', '5', '7'].includes(tid)) {
                videos = await this.getRankList(parseInt(tid), page);
            } else if (tid === '全部') {
                const seasonType = filterObj.tid || '1';
                const order = filterObj.order || '2';
                const seasonStatus = filterObj.season_status || '-1';
                videos = await this.getAllList(seasonType, page, order, seasonStatus);
            } else if (tid === '时间表') {
                const seasonType = filterObj.tid || '1';
                videos = await this.getTimeline(seasonType);
            }
            
            // 过滤预告片
            const filteredVideos = videos.filter(item => 
                !item.vod_name?.includes("预告") && 
                !item.vod_remarks?.includes("预告")
            );
            
            return {
                list: filteredVideos,
                page: page,
                pagecount: 9999,
                limit: 20,
                total: 999999
            };
            
        } catch (error) {
            console.error(`categoryContent error: ${error.message}`);
            return {
                list: [],
                page: pg,
                pagecount: 0,
                limit: 20,
                total: 0
            };
        }
    }
    
    async detailContent(ids) {
        try {
            const id = ids[0];
            const url = "https://api.bilibili.com/pgc/view/web/season";
            
            const response = await fetch(`${url}?season_id=${id}`, { 
                headers: this.headers 
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.code !== 0 || !data.result) {
                console.log('详情接口返回错误:', data.message);
                return { list: [] };
            }
            
            const jo = data.result;
            const stat = jo.stat || {};
            const rating = jo.rating || {};
            
            // 格式化数字
            const formatNumber = (num) => {
                if (!num) return '0';
                if (num > 1e8) return (num / 1e8).toFixed(2) + "亿";
                if (num > 1e4) return (num / 1e4).toFixed(2) + "万";
                return num.toString();
            };
            
            // 清理HTML标签
            const cleanHtml = (text) => {
                if (!text) return "";
                return text.replace(/<[^>]+>/g, "").replace(/&quot;/g, '"').replace(/&amp;/g, "&");
            };
            
            const vod = {
                vod_id: id,
                vod_name: jo.title || '',
                vod_pic: jo.cover || '',
                type_name: jo.share_sub_title || '',
                vod_year: jo.publish?.pub_time?.substr(0, 4) || '',
                vod_area: jo.areas?.[0]?.name || '',
                vod_remarks: jo.new_ep?.desc || '',
                vod_actor: `弹幕: ${formatNumber(stat.danmakus)}　点赞: ${formatNumber(stat.likes)}　投币: ${formatNumber(stat.coins)}`,
                vod_director: rating.score ? `评分: ${rating.score}　${jo.subtitle || ''}` : `暂无评分　${jo.subtitle || ''}`,
                vod_content: cleanHtml(jo.evaluate || ''),
                vod_play_from: '',
                vod_play_url: ''
            };

            // 处理剧集
            const episodes = jo.episodes || [];
            const filteredEpisodes = episodes.filter(ep => 
                !ep.title?.includes("预告") && 
                !(ep.badge && ep.badge.includes("预告"))
            );

            if (filteredEpisodes.length > 0) {
                const playItems = [];

                filteredEpisodes.forEach(ep => {
                    // 使用分享链接作为播放ID
                    const shareUrl = ep.share_url || `https://www.bilibili.com/bangumi/play/ep${ep.id}`;
                    let part = `${ep.title || ''} ${ep.long_title || ''}`.trim();
                    
                    // 清理标题
                    part = part
                        .replace(/#/g, "-")
                        .replace(/\[预告\]/g, "")
                        .replace(/预告/g, "")
                        .replace(/\s+/g, " ")
                        .trim();
                    
                    if (!part) {
                        part = `第${ep.order || '?'}集`;
                    }
                    
                    playItems.push(`${part}$${shareUrl}`);
                });

                if (playItems.length > 0) {
                    vod.vod_play_from = '哔哩哔哩';
                    vod.vod_play_url = playItems.join('#');
                }
            }

            return { list: [vod] };
            
        } catch (error) {
            console.error(`detailContent error: ${error.message}`);
            return { list: [] };
        }
    }
    
    async searchContent(key, quick, pg = '1') {
        try {
            const page = parseInt(pg) || 1;
            const encodedKeyword = encodeURIComponent(key);
            
            // 搜索番剧
            const url1 = `https://api.bilibili.com/x/web-interface/search/type?search_type=media_bangumi&keyword=${encodedKeyword}&page=${page}`;
            const url2 = `https://api.bilibili.com/x/web-interface/search/type?search_type=media_ft&keyword=${encodedKeyword}&page=${page}`;
            
            const videos = [];
            
            // 搜索番剧
            try {
                const response1 = await fetch(url1, { headers: this.headers });
                if (response1.ok) {
                    const data1 = await response1.json();
                    if (data1.code === 0 && data1.data?.result) {
                        data1.data.result.forEach(vod => {
                            if (!vod.title?.includes("预告") && !vod.index_show?.includes("预告")) {
                                videos.push({
                                    vod_id: String(vod.season_id || '').trim(),
                                    vod_name: this.cleanHtml(vod.title || '').trim(),
                                    vod_pic: vod.cover?.trim() || '',
                                    vod_remarks: this.cleanHtml(vod.index_show || '').trim()
                                });
                            }
                        });
                    }
                }
            } catch (e) {
                console.error('番剧搜索失败:', e.message);
            }
            
            // 搜索影视
            try {
                const response2 = await fetch(url2, { headers: this.headers });
                if (response2.ok) {
                    const data2 = await response2.json();
                    if (data2.code === 0 && data2.data?.result) {
                        data2.data.result.forEach(vod => {
                            if (!vod.title?.includes("预告") && !vod.index_show?.includes("预告")) {
                                videos.push({
                                    vod_id: String(vod.season_id || '').trim(),
                                    vod_name: this.cleanHtml(vod.title || '').trim(),
                                    vod_pic: vod.cover?.trim() || '',
                                    vod_remarks: this.cleanHtml(vod.index_show || '').trim()
                                });
                            }
                        });
                    }
                }
            } catch (e) {
                console.error('影视搜索失败:', e.message);
            }
            
            return {
                list: videos,
                page: page,
                pagecount: 10,
                limit: 20,
                total: videos.length
            };
            
        } catch (error) {
            console.error(`searchContent error: ${error.message}`);
            return {
                list: [],
                page: pg,
                pagecount: 0,
                limit: 20,
                total: 0
            };
        }
    }
    
    async playerContent(flag, id, vipFlags) {
        try {
            // 调用壳子超级解析
            return {
                parse: 1,           // 必须为1，表示需要解析
                jx: 1,              // 必须为1，启用解析
                play_parse: true,   // 启用播放解析
                parse_type: '壳子超级解析',
                parse_source: '哔哩哔哩',
                url: id,            // B站分享链接
                header: JSON.stringify({
                    'User-Agent': this.headers['User-Agent'],
                    'Referer': 'https://www.bilibili.com',
                    'Origin': 'https://www.bilibili.com'
                })
            };
            
        } catch (error) {
            console.error(`playerContent error: ${error.message}`);
            // 即使出错也返回超级解析参数，让壳子处理
            return {
                parse: 1,
                jx: 1,
                play_parse: true,
                parse_type: '壳子超级解析',
                parse_source: '哔哩哔哩',
                url: id,
                header: JSON.stringify(this.headers)
            };
        }
    }
    
    localProxy(param) {
        return null;
    }
    
    // ============ 辅助方法 ============
    
    // 清理HTML标签
    cleanHtml(text) {
        if (!text) return "";
        return text.replace(/<[^>]+>/g, "").replace(/&quot;/g, '"').replace(/&amp;/g, "&");
    }
    
    // 获取排行榜数据
    async getRankList(seasonType, page = 1) {
        try {
            const url = `https://api.bilibili.com/pgc/web/rank/list?season_type=${seasonType}&pagesize=20&page=${page}&day=3`;
            const response = await fetch(url, { headers: this.headers });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.code === 0) {
                const items = data.result?.list || data.data?.list || [];
                return items.map(item => ({
                    vod_id: String(item.season_id || '').trim(),
                    vod_name: item.title?.trim() || '',
                    vod_pic: item.cover?.trim() || '',
                    vod_remarks: item.new_ep?.index_show || item.index_show || ''
                }));
            }
            
            return [];
            
        } catch (error) {
            console.error(`getRankList error: ${error.message}`);
            return [];
        }
    }
    
    // 获取全部分类数据
    async getAllList(tid, page = 1, order = "2", seasonStatus = "-1") {
        try {
            const url = `https://api.bilibili.com/pgc/season/index/result?order=${order}&pagesize=20&type=1&season_type=${tid}&page=${page}&season_status=${seasonStatus}`;
            const response = await fetch(url, { headers: this.headers });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.code === 0) {
                const items = data.data?.list || [];
                return items.map(item => ({
                    vod_id: String(item.season_id || '').trim(),
                    vod_name: item.title?.trim() || '',
                    vod_pic: item.cover?.trim() || '',
                    vod_remarks: item.index_show || ''
                }));
            }
            
            return [];
            
        } catch (error) {
            console.error(`getAllList error: ${error.message}`);
            return [];
        }
    }
    
    // 获取时间表数据
    async getTimeline(tid) {
        try {
            const url = `https://api.bilibili.com/pgc/web/timeline/v2?season_type=${tid}&day_before=2&day_after=4`;
            const response = await fetch(url, { headers: this.headers });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            const videos = [];
            
            if (data.code === 0 && data.result) {
                const result = data.result;
                
                // 最新更新
                const latestList = result.latest || [];
                latestList.forEach(vod => {
                    if (!vod.title?.includes("预告")) {
                        videos.push({
                            vod_id: String(vod.season_id || '').trim(),
                            vod_name: vod.title?.trim() || '',
                            vod_pic: vod.cover?.trim() || '',
                            vod_remarks: (vod.pub_index || '') + '　' + (vod.follows || '').replace('系列', '')
                        });
                    }
                });
                
                // 时间表
                for (let i = 0; i < 7; i++) {
                    const dayList = result.timeline?.[i]?.episodes || [];
                    dayList.forEach(vod => {
                        if (String(vod.published) === '0' && !vod.title?.includes('预告')) {
                            videos.push({
                                vod_id: String(vod.season_id || '').trim(),
                                vod_name: vod.title?.trim() || '',
                                vod_pic: vod.cover?.trim() || '',
                                vod_remarks: (vod.pub_ts || '') + '   ' + (vod.pub_index || '')
                            });
                        }
                    });
                }
            }
            
            return videos;
            
        } catch (error) {
            console.error(`getTimeline error: ${error.message}`);
            return [];
        }
    }
}

// 导出 Spider 类
module.exports = Spider;