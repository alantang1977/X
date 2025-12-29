const config = {
    host: 'http://139.9.106.196:2345',/*Emby服务器URL (例如 http://localhost:8096)*/
    userId: "623ba3ccaae348f9a3ce90adafb05bc1",/*Emby_userId (通过账号密码获取)*/
    token: "61450f3dc3e34bea80e5cbe4ae34fc05",/*Emby_token (通过账号密码获取)*/
    deviceId: "ea27caf7-9a51-4209-b1a5-374bf30c2ffd",
    clientVersion: "4.9.0.31"
};

const deviceProfile = { DeviceProfile: { MaxStaticBitrate: 140000000, MaxStreamingBitrate: 140000000, MusicStreamingTranscodingBitrate: 192000, DirectPlayProfiles: [{ Container: "mp4,m4v", Type: "Video", VideoCodec: "h264,h265,hevc,av1,vp8,vp9", AudioCodec: "ac3,eac3,mp3,aac,opus,flac,vorbis" }, { Container: "mkv", Type: "Video", VideoCodec: "h264,h265,hevc,av1,vp8,vp9", AudioCodec: "ac3,eac3,mp3,aac,opus,flac,vorbis" }, { Container: "flv", Type: "Video", VideoCodec: "h264", AudioCodec: "aac,mp3" }, { Container: "mov", Type: "Video", VideoCodec: "h264", AudioCodec: "ac3,eac3,mp3,aac,opus,flac,vorbis" }, { Container: "opus", Type: "Audio" }, { Container: "mp3", Type: "Audio", AudioCodec: "mp3" }, { Container: "mp2,mp3", Type: "Audio", AudioCodec: "mp2" }, { Container: "aac", Type: "Audio", AudioCodec: "aac" }, { Container: "m4a", AudioCodec: "aac", Type: "Audio" }, { Container: "mp4", AudioCodec: "aac", Type: "Audio" }, { Container: "flac", Type: "Audio" }, { Container: "webma,webm", Type: "Audio" }, { Container: "wav", Type: "Audio", AudioCodec: "PCM_S16LE,PCM_S24LE" }, { Container: "ogg", Type: "Audio" }, { Container: "webm", Type: "Video", AudioCodec: "vorbis,opus", VideoCodec: "av1,VP8,VP9" }], TranscodingProfiles: [{ Container: "aac", Type: "Audio", AudioCodec: "aac", Context: "Streaming", Protocol: "hls", MaxAudioChannels: "2", MinSegments: "1", BreakOnNonKeyFrames: true }, { Container: "aac", Type: "Audio", AudioCodec: "aac", Context: "Streaming", Protocol: "http", MaxAudioChannels: "2" }, { Container: "mp3", Type: "Audio", AudioCodec: "mp3", Context: "Streaming", Protocol: "http", MaxAudioChannels: "2" }, { Container: "opus", Type: "Audio", AudioCodec: "opus", Context: "Streaming", Protocol: "http", MaxAudioChannels: "2" }, { Container: "wav", Type: "Audio", AudioCodec: "wav", Context: "Streaming", Protocol: "http", MaxAudioChannels: "2" }, { Container: "opus", Type: "Audio", AudioCodec: "opus", Context: "Static", Protocol: "http", MaxAudioChannels: "2" }, { Container: "mp3", Type: "Audio", AudioCodec: "mp3", Context: "Static", Protocol: "http", MaxAudioChannels: "2" }, { Container: "aac", Type: "Audio", AudioCodec: "aac", Context: "Static", Protocol: "http", MaxAudioChannels: "2" }, { Container: "wav", Type: "Audio", AudioCodec: "wav", Context: "Static", Protocol: "http", MaxAudioChannels: "2" }, { Container: "ts", Type: "Video", VideoCodec: "h264", AudioCodec: "aac,mp3", Protocol: "hls", MaxAudioChannels: "2", MinSegments: "1", BreakOnNonKeyFrames: true, Context: "Streaming" }, { Container: "mp4", Type: "Video", VideoCodec: "h264", AudioCodec: "aac,mp3", Protocol: "http", MaxAudioChannels: "2", Context: "Static" }, { Container: "webm", Type: "Video", VideoCodec: "vp8", AudioCodec: "vorbis", Protocol: "http", MaxAudioChannels: "2", Context: "Static" }, { Container: "webm", Type: "Video", VideoCodec: "vp8", AudioCodec: "vorbis", Protocol: "http", MaxAudioChannels: "2", Context: "Streaming" }], SubtitleProfiles: [{ Format: "ass", Method: "External" }, { Format: "ssa", Method: "External" }, { Format: "srt", Method: "External" }, { Format: "subrip", Method: "External" }, { Format: "vtt", Method: "External" }, { Format: "pgssub", Method: "Embed" }, { Format: "pgs", Method: "Embed" }, { Format: "dvdsub", Method: "Embed" }, { Format: "vobsub", Method: "Embed" }, { Format: "subrip", Method: "Embed" }, { Format: "ass", Method: "Embed" }, { Format: "ssa", Method: "Embed" }], CodecProfiles: [{ Type: "Video", Codec: "h264", ApplyConditions: [{ Condition: "LessThanEqual", Property: "VideoLevel", Value: "62", IsRequired: false }] }, { Type: "Video", Codec: "h265", ApplyConditions: [{ Condition: "LessThanEqual", Property: "VideoLevel", Value: "153", IsRequired: false }] }], ResponseProfiles: [{ Container: "m4v", Type: "Video", MimeType: "video/mp4" }], ContainerProfiles: [], LiveStreamProfiles: ["m3u8"], SupportedCommands: ["Play", "Pause", "Stop", "Seek", "SetAudioStreamIndex", "SetSubtitleStreamIndex"], IgnoreDts: true, IgnoreIndex: false, MinSegments: 0, BreakOnNonKeyFrames: true, TranscodeReasons: ["ContainerNotSupported", "VideoCodecNotSupported", "AudioCodecNotSupported"] } };

const getHeaders = (extra = {}) => ({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": config.host + "/",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "X-Emby-Client": "Emby Web",
    "X-Emby-Device-Name": "Android WebView Android",
    "X-Emby-Device-Id": config.deviceId,
    "X-Emby-Client-Version": config.clientVersion,
    "X-Emby-Token": config.token,
    ...extra
});
const buildUrl = (endpoint, params = {}) => {
    const baseParams = {
        'X-Emby-Client': 'Emby Web',
        'X-Emby-Device-Name': 'Android WebView Android',
        'X-Emby-Device-Id': config.deviceId,
        'X-Emby-Client-Version': config.clientVersion,
        'X-Emby-Token': config.token,
        'X-Emby-Language': 'zh-cn'
    };
    const allParams = { ...baseParams, ...params };
    const queryString = Object.entries(allParams)
        .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
        .join('&');
    return `${config.host}${endpoint}${endpoint.includes('?') ? '&' : '?'}${queryString}`;
};
const getImageUrl = (itemId, imageTag) => 
    imageTag ? `${config.host}/emby/Items/${itemId}/Images/Primary?maxWidth=400&tag=${imageTag}&quality=90` : "";
const init = async () => {};
const extractVideos = (jsonData) => {
    if (!jsonData?.Items) return [];
    return jsonData.Items.map(it => ({
        vod_id: it.Id,
        vod_name: it.Name || "",
        vod_pic: getImageUrl(it.Id, it.ImageTags?.Primary),
        vod_remarks: it.ProductionYear?.toString() || ""
    }));
};
const getViews = async () => {
    const url = buildUrl(`/emby/Users/${config.userId}/Views`);
    const resp = await req(url, { headers: getHeaders() });
    if (!resp?.content) return null;
    return JSON.parse(resp.content);
};
const homeVod = async () => {
    const json = await getViews();
    return JSON.stringify({ 
        list: json ? extractVideos(json) : [] 
    });
};
const home = async () => {
    const json = await getViews();
    if (!json) return JSON.stringify({ class: [], filters: {}, list: [] });
    const classList = json.Items
        .filter(it => !it.Name.includes("播放列表") && !it.Name.includes("相机"))
        .map(it => ({
            type_id: it.Id,
            type_name: it.Name
        }));
    return JSON.stringify({
        class: classList,
        filters: {},
        list: []
    });
};
const category = async (tid, pg, _, extend) => {
    const startIndex = (pg - 1) * 30;
    const url = buildUrl(`/emby/Users/${config.userId}/Items`, {
        SortBy: 'DateLastContentAdded,SortName',
        SortOrder: 'Descending',
        IncludeItemTypes: 'Movie,Series',
        Recursive: 'true',
        Fields: 'BasicSyncInfo,CanDelete,Container,PrimaryImageAspectRatio,ProductionYear,CommunityRating,Status,CriticRating,EndDate,Path',
        StartIndex: startIndex,
        ParentId: tid,
        EnableImageTypes: 'Primary,Backdrop,Thumb,Banner',
        ImageTypeLimit: 1,
        Limit: 30,
        EnableUserData: 'true'
    });
    const resp = await req(url, { headers: getHeaders() });
    if (!resp?.content) return JSON.stringify({ 
        list: [], 
        page: +pg, 
        pagecount: 1, 
        limit: 30 
    });
    const json = JSON.parse(resp.content);
    const list = extractVideos(json);
    const total = json.TotalRecordCount || 0;
    const pagecount = pg * 30 < total ? +pg + 1 : +pg;
    return JSON.stringify({ 
        list, 
        page: +pg, 
        pagecount, 
        limit: 30, 
        total 
    });
};
const getPlayUrlForFolder = async (id, info) => {
    let playUrl = "";
    if (info.Type === "Series") {
        const seasonsUrl = buildUrl(`/emby/Shows/${id}/Seasons`, {
            UserId: config.userId,
            Fields: 'BasicSyncInfo,CanDelete,Container,PrimaryImageAspectRatio,ProductionYear,CommunityRating',
            EnableImages: 'true',
            EnableUserData: 'true'
        });
        const seasonsResp = await req(seasonsUrl, { headers: getHeaders() });
        if (!seasonsResp?.content) return "";
        const seasons = JSON.parse(seasonsResp.content);
        for (const season of seasons.Items) {
            const episodesUrl = buildUrl(`/emby/Shows/${id}/Episodes`, {
            SeasonId: season.Id,
            Fields: 'BasicSyncInfo,CanDelete,CommunityRating,PrimaryImageAspectRatio,ProductionYear,Overview',
            UserId: config.userId,
            Limit: 1000
        });
        const episodesResp = await req(episodesUrl, { headers: getHeaders() });
        if (!episodesResp?.content) continue;
        const episodes = JSON.parse(episodesResp.content);
            for (const episode of episodes.Items) {
                const seasonName = season.Name.replace(/#/g, '-').replace(/\$/g, '|').trim();
                const episodeName = episode.Name.trim();
                playUrl += `${seasonName}|${episodeName}$${episode.Id}#`;
            }
        }
    } else {
        const itemsUrl = buildUrl(`/emby/Users/${config.userId}/Items`, {
            ParentId: id,
            Fields: 'BasicSyncInfo,CanDelete,Container,PrimaryImageAspectRatio,ProductionYear,CommunityRating,CriticRating',
            ImageTypeLimit: 1,
            StartIndex: 0,
            EnableUserData: 'true'
        });
        const itemsResp = await req(itemsUrl, { headers: getHeaders() });
        if (!itemsResp?.content) return "";
        const items = JSON.parse(itemsResp.content);
        for (const item of items.Items) {
            playUrl += `${item.Name.replace(/#/g, '-').replace(/\$/g, '|').trim()}$${item.Id}#`;
        }
    }
    return playUrl.slice(0, -1);
};
const detail = async (id) => {
    const url = buildUrl(`/emby/Users/${config.userId}/Items/${id}`);
    const resp = await req(url, { headers: getHeaders() });
    if (!resp?.content) return JSON.stringify({ list: [] });
    const info = JSON.parse(resp.content);
    let playUrl = "";
    if (!info.IsFolder) {
        playUrl = `${info.Name.trim()}$${info.Id}`;
    } else {
        playUrl = await getPlayUrlForFolder(id, info);
    }
    return JSON.stringify({
        list: [{
            vod_id: id,
            vod_name: info.Name || "",
            vod_pic: getImageUrl(id, info.ImageTags?.Primary),
            vod_content: info.Overview?.replace(/\xa0/g, ' ').replace(/\n\n/g, '\n').trim() || "暂无简介",
            vod_year: info.ProductionYear?.toString() || "",
            vod_director: "",
            vod_actor: "",
            vod_type: info.Genres?.join(" / ") || "",
            vod_play_from: "EMBY",
            vod_play_url: playUrl
        }]
    });
};
const search = async (wd, _, pg = 1) => {
    const url = buildUrl(`/emby/Users/${config.userId}/Items`, {
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
    const resp = await req(url, { headers: getHeaders() });
    if (!resp?.content) return JSON.stringify({ list: [] });
    const json = JSON.parse(resp.content);
    return JSON.stringify({ list: extractVideos(json) });
};
const play = async (_, id) => {
    const url = buildUrl(`/emby/Items/${id}/PlaybackInfo`, {
        UserId: config.userId,
        IsPlayback: 'false',
        AutoOpenLiveStream: 'false',
        StartTimeTicks: 0,
        MaxStreamingBitrate: 2147483647
    });
    const reqHeaders = getHeaders({
        "Content-Type": "application/json"
    });
    const resp = await req(url, {
        method: "POST",
        headers: reqHeaders,
        body: JSON.stringify(deviceProfile)
    });
    if (!resp?.content) {
        return JSON.stringify({ 
            parse: 1, 
            url, 
            header: reqHeaders, 
            msg: "无法获取播放URL" 
        });
    }
    const json = JSON.parse(resp.content);
    const mediaSources = json.MediaSources;
    if (!mediaSources || mediaSources.length === 0) {
        return JSON.stringify({ parse: 1, url, header: reqHeaders });
    }
    const mediaSource = mediaSources[0];
    let playUrl = "";
    if (mediaSource.DirectStreamUrl) {
        playUrl = config.host + mediaSource.DirectStreamUrl;
    } else if (mediaSource.DirectPlayUrl) {
        playUrl = config.host + mediaSource.DirectPlayUrl;
    } else {
        return JSON.stringify({ 
            parse: 1, 
            url, 
            header: reqHeaders, 
            msg: "无法获取播放URL" 
        });
    }
    return JSON.stringify({
        parse: 0,
        url: playUrl,
        header: {
            "X-Emby-Client": "Emby Web",
            "X-Emby-Device-Name": "Android WebView Android",
            "X-Emby-Device-Id": config.deviceId,
            "X-Emby-Client-Version": config.clientVersion,
            "X-Emby-Token": config.token
        }
    });
};
export default { init, home, homeVod, category, detail, search, play };
