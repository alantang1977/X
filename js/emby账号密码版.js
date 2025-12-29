// ===================================================================
// 🔧 配置区（只需修改此处）
// ===================================================================
const CONFIG = {
    // Emby 服务器配置
    host: 'https://emby.hohai.eu.org:443',
    username: '你的账号',
    password: '你的密码',
    deviceId: 'ea27caf7-9a51-4209-b1a5-374bf30c2ffd',
    clientVersion: '4.9.0.31',

    // ⚙️ 高级选项
    isJellyfin: false,          // 设为 true 可兼容 Jellyfin
    maxRetries: 2,              // 请求失败重试次数
    retryDelay: 1000            // 重试间隔（毫秒）
};
// ===================================================================

let authCache = null;

// 安全 URL 编码（避免 # $ 等字符破坏播放）
const safeName = (name) => (name || '').replace(/#/g, '-').replace(/\$/g, '|').trim();

// 通用请求封装（带重试）
const request = async (url, options, retries = CONFIG.maxRetries) => {
    try {
        const resp = await req(url, options);
        if (resp?.content) return resp;
        throw new Error('Empty response');
    } catch (error) {
        if (retries > 0) {
            await new Promise(r => setTimeout(r, CONFIG.retryDelay));
            return request(url, options, retries - 1);
        }
        throw error;
    }
};

// 初始化：认证（带缓存）
const init = async () => {
    if (authCache) return;
    const authPath = CONFIG.isJellyfin ? '/Users/AuthenticateByName' : '/emby/Users/AuthenticateByName';
    const url = CONFIG.host + authPath;
    const headers = {
        'X-Emby-Client': 'Emby Web',
        'X-Emby-Device-Name': 'Android WebView Android',
        'X-Emby-Device-Id': CONFIG.deviceId,
        'X-Emby-Client-Version': CONFIG.clientVersion,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    };
    const body = JSON.stringify({ Username: CONFIG.username, Pw: CONFIG.password });
    const resp = await request(url, { method: 'POST', headers, body });
    const data = JSON.parse(resp.content);
    authCache = {
        userId: data.User.Id,
        token: data.AccessToken,
        serverType: CONFIG.isJellyfin ? 'jellyfin' : 'emby'
    };
};

// 获取带认证的请求头
const getHeaders = (extra = {}) => ({
    'X-Emby-Token': authCache.token,
    'X-Emby-Device-Id': CONFIG.deviceId,
    'X-Emby-Client': 'Emby Web',
    'X-Emby-Device-Name': 'Android WebView Android',
    'X-Emby-Client-Version': CONFIG.clientVersion,
    'User-Agent': 'Mozilla/5.0',
    'Referer': CONFIG.host + '/',
    ...extra
});

// 构建 API URL
const buildUrl = (path, params = {}) => {
    const prefix = CONFIG.isJellyfin ? '' : '/emby';
    const baseParams = {
        'X-Emby-Token': authCache.token,
        'X-Emby-Device-Id': CONFIG.deviceId,
        'X-Emby-Client-Version': CONFIG.clientVersion,
        'X-Emby-Language': 'zh-cn',
        ...params
    };
    const qs = Object.entries(baseParams)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&');
    return `${CONFIG.host}${prefix}${path}${path.includes('?') ? '&' : '?'}${qs}`;
};

// 获取图片 URL
const getImageUrl = (itemId, imageTag) =>
    imageTag ? `${CONFIG.host}/emby/Items/${itemId}/Images/Primary?maxWidth=400&tag=${imageTag}&quality=90` : '';

// 获取视图（媒体库）
const fetchViews = async () => {
    if (!authCache) await init();
    const url = buildUrl(`/Users/${authCache.userId}/Views`);
    const resp = await request(url, { headers: getHeaders() });
    return JSON.parse(resp.content);
};

// 首页分类（仅电影/剧集）
const home = async () => {
    try {
        const json = await fetchViews();
        const classes = json.Items
            .filter(i => i.CollectionType === 'movies' || i.CollectionType === 'tvshows')
            .map(i => ({ type_id: i.Id, type_name: i.Name }));
        return JSON.stringify({ class: classes, filters: {} });
    } catch (e) {
        return JSON.stringify({ class: [], filters: {}, msg: '加载分类失败' });
    }
};

// 首页推荐（禁用）
const homeVod = async () => JSON.stringify({ list: [] });

// 提取视频列表
const extractVideos = (data) => (data?.Items || []).map(i => ({
    vod_id: i.Id,
    vod_name: i.Name || '',
    vod_pic: getImageUrl(i.Id, i.ImageTags?.Primary),
    vod_remarks: i.ProductionYear?.toString() || ''
}));

// 分类列表
const category = async (tid, pg) => {
    if (!authCache) await init();
    const start = (pg - 1) * 30;
    const url = buildUrl(`/Users/${authCache.userId}/Items`, {
        SortBy: 'DateLastContentAdded,SortName',
        SortOrder: 'Descending',
        IncludeItemTypes: 'Movie,Series',
        Recursive: 'true',
        Fields: 'BasicSyncInfo,CanDelete,Container,PrimaryImageAspectRatio,ProductionYear,CommunityRating,Status,CriticRating,EndDate,Path',
        StartIndex: start,
        ParentId: tid,
        EnableImageTypes: 'Primary,Backdrop,Thumb,Banner',
        ImageTypeLimit: 1,
        Limit: 30,
        EnableUserData: 'true'
    });
    const resp = await request(url, { headers: getHeaders() });
    const json = JSON.parse(resp.content);
    const list = extractVideos(json);
    const total = json.TotalRecordCount || 0;
    const pagecount = Math.ceil(total / 30);
    return JSON.stringify({ list, page: pg, pagecount, limit: 30, total });
};

// 获取剧集播放列表
const getPlayUrlForFolder = async (id, info) => {
    let playUrl = '';
    if (info.Type === 'Series') {
        const seasonsUrl = buildUrl(`/Shows/${id}/Seasons`, { UserId: authCache.userId });
        const seasonsResp = await request(seasonsUrl, { headers: getHeaders() });
        const seasons = JSON.parse(seasonsResp.content);
        for (const season of seasons.Items) {
            const episodesUrl = buildUrl(`/Shows/${id}/Episodes`, {
                SeasonId: season.Id,
                UserId: authCache.userId,
                Limit: 1000
            });
            const episodesResp = await request(episodesUrl, { headers: getHeaders() });
            const episodes = JSON.parse(episodesResp.content);
            for (const episode of episodes.Items) {
                playUrl += `${safeName(season.Name)}|${safeName(episode.Name)}$${episode.Id}#`;
            }
        }
    } else {
        const itemsUrl = buildUrl(`/Users/${authCache.userId}/Items`, { ParentId: id });
        const itemsResp = await request(itemsUrl, { headers: getHeaders() });
        const items = JSON.parse(itemsResp.content);
        for (const item of items.Items) {
            playUrl += `${safeName(item.Name)}$${item.Id}#`;
        }
    }
    return playUrl ? playUrl.slice(0, -1) : '';
};

// 详情页
const detail = async (id) => {
    if (!authCache) await init();
    const url = buildUrl(`/Users/${authCache.userId}/Items/${id}`);
    const resp = await request(url, { headers: getHeaders() });
    const info = JSON.parse(resp.content);

    let playUrl = '', nextEpisodeId = '';
    if (!info.IsFolder) {
        playUrl = `${safeName(info.Name)}$${info.Id}`;
        if (info.Type === 'Episode' && info.SeriesId && info.SeasonId && info.IndexNumber) {
            const nextEpUrl = buildUrl(`/Shows/${info.SeriesId}/Episodes`, {
                UserId: authCache.userId,
                SeasonId: info.SeasonId,
                StartIndex: 0,
                Limit: 500
            });
            const nextResp = await request(nextEpUrl, { headers: getHeaders() });
            const episodes = JSON.parse(nextResp.content).Items || [];
            const nextEp = episodes
                .filter(e => e.IndexNumber > info.IndexNumber)
                .sort((a, b) => a.IndexNumber - b.IndexNumber)[0];
            if (nextEp) nextEpisodeId = nextEp.Id;
        }
    } else {
        playUrl = await getPlayUrlForFolder(id, info);
    }

    return JSON.stringify({
        list: [{
            vod_id: id,
            vod_name: info.Name || '',
            vod_pic: getImageUrl(id, info.ImageTags?.Primary),
            vod_content: (info.Overview || '').replace(/\xa0/g, ' ').replace(/\n\n/g, '\n').trim() || '暂无简介',
            vod_year: info.ProductionYear?.toString() || '',
            vod_type: (info.Genres || []).join(' / ') || '',
            vod_play_from: 'EMBY',
            vod_play_url: playUrl,
            vod_next_episode_id: nextEpisodeId
        }]
    });
};

// 搜索
const search = async (wd, _, pg = 1) => {
    if (!authCache) await init();
    const url = buildUrl(`/Users/${authCache.userId}/Items`, {
        SortBy: 'SortName',
        SortOrder: 'Ascending',
        Fields: 'BasicSyncInfo,CanDelete,Container,PrimaryImageAspectRatio,ProductionYear,Status,EndDate',
        StartIndex: (pg - 1) * 50,
        EnableImageTypes: 'Primary,Backdrop,Thumb',
        ImageTypeLimit: 1,
        Recursive: 'true',
        SearchTerm: wd,
        GroupProgramsBySeries: 'true',
        Limit: 50
    });
    const resp = await request(url, { headers: getHeaders() });
    const json = JSON.parse(resp.content);
    return JSON.stringify({ list: extractVideos(json) });
};

// 播放
const play = async (_, id) => {
    if (!authCache) await init();
    const url = buildUrl(`/Items/${id}/PlaybackInfo`, {
        UserId: authCache.userId,
        IsPlayback: 'true',
        AutoOpenLiveStream: 'false',
        StartTimeTicks: 0,
        MaxStreamingBitrate: 140000000
    });
    const headers = getHeaders({ 'Content-Type': 'application/json' });
    const resp = await request(url, { method: 'POST', headers, body: JSON.stringify(deviceProfile) });
    const json = JSON.parse(resp.content);
    const mediaSource = json.MediaSources?.[0];
    if (!mediaSource) {
        return JSON.stringify({ parse: 1, msg: '无可用媒体源' });
    }

    // 强制使用公网 host，防止内网链接
    const getPublicUrl = (originalUrl) => {
        if (!originalUrl) return '';
        const cleanPath = originalUrl.replace(/^https?:\/\/[^\/]+/i, '');
        return CONFIG.host + cleanPath;
    };

    let playUrl = '';
    if (mediaSource.DirectStreamUrl) {
        playUrl = getPublicUrl(mediaSource.DirectStreamUrl);
    } else if (mediaSource.DirectPlayUrl) {
        playUrl = getPublicUrl(mediaSource.DirectPlayUrl);
    } else {
        return JSON.stringify({ parse: 1, msg: '无直通播放链接' });
    }

    return JSON.stringify({
        parse: 0,
        url: playUrl,
        header: {
            'X-Emby-Client': 'Emby Web',
            'X-Emby-Device-Name': 'Android WebView Android',
            'X-Emby-Device-Id': CONFIG.deviceId,
            'X-Emby-Client-Version': CONFIG.clientVersion,
            'X-Emby-Token': authCache.token
        }
    });
};

// 精简但高效的 DeviceProfile
const deviceProfile = {
    DeviceProfile: {
        MaxStaticBitrate: 140000000,
        MaxStreamingBitrate: 140000000,
        DirectPlayProfiles: [
            { Container: "mp4,mkv,webm", Type: "Video", VideoCodec: "h264,h265,av1,vp9", AudioCodec: "aac,mp3,opus,flac" },
            { Container: "mp3,aac,flac,opus", Type: "Audio" }
        ],
        TranscodingProfiles: [
            { Container: "mp4", Type: "Video", VideoCodec: "h264", AudioCodec: "aac", Context: "Streaming", Protocol: "http" },
            { Container: "aac", Type: "Audio", Context: "Streaming", Protocol: "http" }
        ],
        SubtitleProfiles: [{ Format: "srt,ass,vtt", Method: "External" }],
        CodecProfiles: [
            { Type: "Video", Codec: "h264", ApplyConditions: [{ Condition: "LessThanEqual", Property: "VideoLevel", Value: "62" }] }
        ],
        BreakOnNonKeyFrames: true
    }
};

export default { init, home, homeVod, category, detail, search, play };