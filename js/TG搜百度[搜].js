/*
@header({
  searchable: 1,
  filterable: 0,
  quickSearch: 1,
  title: 'Tg搜索',
  '类型': '搜索',
  lang: 'ds'
  by:EylinSir
})
*/

const DEFAULT_PAGE_SIZE = 10;
const API_URLS = [
    'https://tgsou.252035.xyz/api/search',
    'https://so.252035.xyz/api/search',
    'https://so.566987.xyz/api/search'
];
const DEFAULT_SOURCES = ['百度'];//定义搜索网盘类型

const domainMap = {
    'alipan': '阿里', 'aliyundrive': '阿里', 'quark': '夸克', '115cdn': '115',
    'baidu.com': '百度', 'uc': 'UC', '189.cn': '天翼', '139.com': '移动', '123': '123盘'
};

const disk_type_mapping = {
    "百度网盘": /pan\.baidu\.com/,
    "夸克网盘": /pan\.quark\.cn/,
    "移动云盘": /(?:yun\.139\.com|139\.com|caiyun\.139\.com)/,
    "阿里云盘": /(?:aliyundrive\.com|alipan\.com)/,
    "123云盘": /(?:www\.123pan\.com|www\.123684\.com|www\.123865\.com|www\.123912\.com|www\.123pan\.cn|www\.123592\.com)/,
    "115网盘": /115\.com/,
    "天翼云盘": /cloud\.189\.cn/
};

var rule = {
    类型: '搜索',
    title: 'Tg搜索',
    alias: 'Tg搜索',
    desc: '支持网盘搜索',
    host: 'https://tgsou.252035.xyz',
    url: '/',
    searchUrl: '/?keyword=**',
    headers: {
        'User-Agent': 'MOBILE_UA',
        'Content-Type': 'application/json',
        'Referer': 'https://tgsou.252035.xyz/'
    },
    searchable: 1,
    quickSearch: 1,
    filterable: 0,
    double: true,
    play_parse: true,
    search_match: true,
    limit: 10,

    init: function() {},

    action: async (action) => 
        action === 'only_search' ? '此源为纯搜索源，直接搜索即可！' : `注意:${action}`,

    推荐: async () => [{
        vod_id: '直接搜索即可！',
        vod_pic: 'https://images.gamedog.cn/gamedog/imgfile/20241205/05105843u5j9.png',
        vod_name: '纯搜索源哦！',
        vod_tag: 'action'
    }],

    搜索: async function(wd, pg) {
        const page = parseInt(pg) || 1;
        const channelUsername = 'alyp_1,clouddriveresources,dianyingshare,hdhhd21,jdjdn1111,leoziyuan,NewQuark,PanjClub,Quark_Movies,xiangxiunb,yunpanchat,yunpanqk,XiangxiuNB,alyp_4K_Movies,alyp_Animation,alyp_TV,alyp_JLP';

        for (const apiUrl of API_URLS) {
            if (!/^https?:\/\//.test(apiUrl)) continue;
            try {
                const fullUrl = `${apiUrl}?channelUsername=${channelUsername}&pic=true&keyword=${encodeURIComponent(wd)}&page=${page}&size=${this.limit}`;
                const html = await request(fullUrl, {
                    headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' }
                });
                if (!html) continue;

                const data = JSON.parse(html);
                let resultsList = [];

                if (data.results?.length) {
                    resultsList = data.results;
                } else if (data.code === 0 && data.data?.results?.length) {
                    resultsList = data.data.results;
                }

                const results = [];

                for (const element of resultsList) {
                    if (typeof element !== 'string') continue;
                    const parts = element.split('$$$');
                    if (parts.length < 2) continue;
                    for (const resource of parts[1].split('##')) {
                        const segs = resource.split('@');
                        if (segs.length < 2) continue;
                        const id = segs[0].trim();
                        const [pic, name] = segs[1].split('$$').map(s => s?.trim() || '');
                        if (!id || !name) continue;

                        const sourceName = this._mapSource(id);
                        if (sourceName && DEFAULT_SOURCES.includes(sourceName) && (!this.search_match || name.includes(wd))) {
                            results.push({
                                vod_id: id,
                                vod_name: name,
                                vod_pic: pic,
                                vod_remarks: `${sourceName}:${new Date().getMonth() + 1}-${new Date().getDate()}|TG搜`
                            });
                        }
                    }
                }

                if (data.code === 0 && data.data?.merged_by_type && typeof data.data.merged_by_type === 'object') {
                    for (const items of Object.values(data.data.merged_by_type)) {
                        if (!Array.isArray(items)) continue;
                        for (const item of items) {
                            if (!item?.url) continue;
                            const url = item.url.trim();
                            const title = item.note || '未命名资源';
                            const pic = item.images?.[0] || '';
                            if (!title) continue;

                            const sourceName = this._mapSource(url);
                            if (sourceName && DEFAULT_SOURCES.includes(sourceName) && (!this.search_match || title.includes(wd))) {
                                results.push({
                                    vod_id: url,
                                    vod_name: title,
                                    vod_pic: pic,
                                    vod_remarks: `${sourceName}:${new Date().getMonth() + 1}-${new Date().getDate()}|TG搜`
                                });
                            }
                        }
                    }
                }

                if (results.length) return results;
            } catch (e) {}
        }

        return [{
            vod_id: 'error',
            vod_name: '搜索失败',
            vod_remarks: '无匹配资源或API异常',
            vod_pic: ''
        }];
    },

    _mapSource(str) {
        if (!str) return null;
        for (const [domain, name] of Object.entries(domainMap)) {
            if (str.includes(domain)) return name;
        }
        return null;
    },

    _getDiskType(url) {
        for (const [type, pattern] of Object.entries(disk_type_mapping)) {
            if (pattern.test(url)) return type;
        }
        return "其他网盘";
    },

    二级() {
        let input = this.orId;
        if (input.startsWith('push://')) {
            input = decodeURIComponent(input.slice(7));
        }
        const clean = input.trim().replace(/&amp;/g, '&');
        const disk = this._getDiskType(clean);
        return {
            vod_pic: '',
            vod_id: this.orId,
            vod_content: `TG频道分享资源\n链接: ${clean}`,
            vod_play_from: disk,
            vod_play_url: `点我播放$push://${encodeURIComponent(clean)}`,
            vod_name: `${disk}资源`
        };
    },

    lazy(flag, id) {
        return {
            url: id.includes('$') ? id.split('$')[1] : id,
            header: JSON.stringify(this.headers)
        };
    }
};
