let host = 'https://emby.bangumi.ca';
let Token = "8b0b16aae7e8403cb3d19969b82c3902";
let Users = "80e861cbff1343bfa0bedcea78895b91";
let headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": host + "/",
    "Accept-Language": "zh-CN,zh;q=0.9"
};
const init = async () => {};
const extractVideos = jsonData => {
    if (!jsonData || !jsonData.Items) return [];
    return jsonData.Items.map(it => {
        if (!(it.Type === "Series" || it.Type === "Movie")) return null;
        return {
            vod_id: it.Id,
            vod_name: it.Name || "",
            vod_pic: `${host}/emby/Items/${it.Id}/Images/Primary?maxHeight=300&maxWidth=200&tag=${it.ImageTags.Primary}&quality=90`,
            vod_remarks: it.UserData?.UnplayedItemCount ? it.UserData.UnplayedItemCount.toString() : ""
        };
    }).filter(Boolean);
};
const generateFilters = () => {
    return {};
};
const homeVod = async () => {
    const url = `${host}/emby/Users/${Users}/Views?X-Emby-Client=Emby+Web&X-Emby-Device-Name=Android+WebView+Android&X-Emby-Device-Id=ea27caf7-9a51-4209-b1a5-374bf30c2ffd&X-Emby-Client-Version=4.9.0.31&X-Emby-Token=${Token}&X-Emby-Language=zh-cn`;
    const resp = await req(url, { headers });
    if (!resp?.content) return JSON.stringify({ list: [] });
    const json = JSON.parse(resp.content);
    return JSON.stringify({ list: extractVideos(json) });
};
const home = async () => {
    const url = `${host}/emby/Users/${Users}/Views?X-Emby-Client=Emby+Web&X-Emby-Device-Name=Android+WebView+Android&X-Emby-Device-Id=ea27caf7-9a51-4209-b1a5-374bf30c2ffd&X-Emby-Client-Version=4.9.0.31&X-Emby-Token=${Token}&X-Emby-Language=zh-cn`;
    const resp = await req(url, { headers });
    if (!resp?.content) return JSON.stringify({ class: [], filters: {}, list: [] });
    const json = JSON.parse(resp.content);
    
    const classList = json.Items
        .filter(it => it.CollectionType === "tvshows" || it.CollectionType === "movies")
        .map(it => ({
            type_id: it.Id,
            type_name: it.Name
        }));
    const list = [];
    return JSON.stringify({
        class: classList,
        filters: generateFilters(),
        list
    });
};
const category = async (tid, pg, _, extend) => {
    const startIndex = (pg - 1) * 50;
    const url = `${host}/emby/Users/${Users}/Items?SortBy=DateLastContentAdded%2CSortName&SortOrder=Descending&IncludeItemTypes=Series&Recursive=true&Fields=BasicSyncInfo%2CCanDelete%2CContainer%2CPrimaryImageAspectRatio%2CPrefix&StartIndex=${startIndex}&ParentId=${tid}&EnableImageTypes=Primary%2CBackdrop%2CThumb&ImageTypeLimit=1&Limit=50&X-Emby-Token=${Token}`;
    const resp = await req(url, { headers });
    if (!resp?.content) return JSON.stringify({ list: [], page: +pg, pagecount: 1, limit: 50 });
    const json = JSON.parse(resp.content);
    const list = extractVideos(json);
    return JSON.stringify({ list, page: +pg, pagecount: 999, limit: 50 });
};
const detail = async id => {
    const url = `${host}/emby/Users/${Users}/Items/${id}?X-Emby-Token=${Token}`;
    const resp = await req(url, { headers });
    if (!resp?.content) return JSON.stringify({ list: [] });
    const info = JSON.parse(resp.content);
    let playFrom = "在线播放";
    let playUrl = "";
    if (info.Type === "Series") {
        const seasonsUrl = `${host}/emby/Shows/${id}/Seasons?UserId=${Users}&Fields=BasicSyncInfo%2CCanDelete%2CContainer%2CPrimaryImageAspectRatio&EnableTotalRecordCount=false&X-Emby-Token=${Token}`;
        const seasonsResp = await req(seasonsUrl, { headers });
        if (seasonsResp?.content) {
            const seasons = JSON.parse(seasonsResp.content);
            const fromList = [];
            const urlList = [];
            for (const season of seasons.Items) {
                fromList.push(season.Name);
                const episodesUrl = `${host}/emby/Shows/${id}/Episodes?SeasonId=${season.Id}&ImageTypeLimit=1&UserId=${Users}&Fields=Overview%2CPrimaryImageAspectRatio&Limit=1000&X-Emby-Token=${Token}`;
                const episodesResp = await req(episodesUrl, { headers });
                if (episodesResp?.content) {
                    const episodes = JSON.parse(episodesResp.content);
                    const episodeUrls = episodes.Items.map(item => {
                        const title = item.Name;
                        const playUrl = `${host}/emby/Items/${item.Id}/PlaybackInfo?UserId=${Users}&StartTimeTicks=0&IsPlayback=false&AutoOpenLiveStream=false&MaxStreamingBitrate=7000000&X-Emby-Client=Emby+Web&X-Emby-Device-Name=Android+WebView+Android&X-Emby-Device-Id=09d93358-fdd6-4d0b-9e13-d988795e8742&X-Emby-Client-Version=4.8.0.62&X-Emby-Token=${Token}&X-Emby-Language=zh-cn&reqformat=json`;
                        return `${title}$${playUrl}`;
                    });
                    urlList.push(episodeUrls.join('#'));
                }
            }
            playFrom = fromList.join('$$$');
            playUrl = urlList.join('$$$');
        }
    } else if (info.Type === "Movie") {
        const arr = [];
        if (info.MediaSources) {
            for (const it of info.MediaSources) {
                arr.push(`${it.Name}$${host}/emby/Items/${id}/PlaybackInfo?UserId=${Users}&StartTimeTicks=0&IsPlayback=true&AutoOpenLiveStream=true&AudioStreamIndex=5&SubtitleStreamIndex=2&MediaSourceId=${it.Id}&MaxStreamingBitrate=7000000&X-Emby-Client=Emby+Web&X-Emby-Device-Name=Android+WebView+Android&X-Emby-Device-Id=09d93358-fdd6-4d0b-9e13-d988795e8742&X-Emby-Client-Version=4.8.0.62&X-Emby-Token=${Token}&reqformat=json`);
            }
        }
        playUrl = arr.join('$$$');
    }
    if (!playUrl) return JSON.stringify({ list: [] });
    return JSON.stringify({
        list: [{
            vod_id: id,
            vod_name: info.Name || "",
            vod_pic: info.ImageTags?.Primary ? `${host}/emby/Items/${id}/Images/Primary?maxHeight=300&maxWidth=200&tag=${info.ImageTags.Primary}&quality=90` : "",
            vod_content: info.Overview || "暂无简介",
            vod_year: info.ProductionYear ? info.ProductionYear.toString() : "",
            vod_director: "",
            vod_actor: "",
            vod_type: info.Genres ? info.Genres.join(" / ") : "",
            vod_play_from: playFrom,
            vod_play_url: playUrl
        }]
    });
};

const search = async (wd, _, pg = 1) => {
    const url = `${host}/emby/Users/${Users}/Items?SortBy=SortName&SortOrder=Ascending&Fields=BasicSyncInfo%2CCanDelete%2CContainer%2CPrimaryImageAspectRatio%2CProductionYear%2CStatus%2CEndDate&StartIndex=0&EnableImageTypes=Primary%2CBackdrop%2CThumb&ImageTypeLimit=1&Recursive=true&SearchTerm=${encodeURIComponent(wd)}&GroupProgramsBySeries=true&Limit=50&X-Emby-Token=${Token}`;
    const resp = await req(url, { headers });
    if (!resp?.content) return JSON.stringify({ list: [] });
    const json = JSON.parse(resp.content);
    return JSON.stringify({ list: extractVideos(json) });
};

const play = async (_, id) => {
    const bo = {
        "DeviceProfile": {
            "MaxStaticBitrate": 140000000,
            "MaxStreamingBitrate": 140000000,
            "MusicStreamingTranscodingBitrate": 192000,
            "DirectPlayProfiles": [{
                "Container": "mp4,m4v",
                "Type": "Video",
                "VideoCodec": "h264,h265,hevc,av1,vp8,vp9",
                "AudioCodec": "ac3,eac3,mp3,aac,opus,flac,vorbis"
            }, {
                "Container": "mkv",
                "Type": "Video",
                "VideoCodec": "h264,h265,hevc,av1,vp8,vp9",
                "AudioCodec": "ac3,eac3,mp3,aac,opus,flac,vorbis"
            }],
            "TranscodingProfiles": [{
                "Container": "m4s,ts",
                "Type": "Video",
                "AudioCodec": "ac3,mp3,aac",
                "VideoCodec": "h264,h265,hevc",
                "Context": "Streaming",
                "Protocol": "hls",
                "MaxAudioChannels": "2",
                "MinSegments": "1",
                "BreakOnNonKeyFrames": true,
                "ManifestSubtitles": "vtt"
            }],
            "SubtitleProfiles": [{
                "Format": "vtt",
                "Method": "Hls"
            }]
        }
    };
    
    const resp = await req(id, {
        method: "POST",
        headers: {
            ...headers,
            "Content-Type": "application/json"
        },
        body: JSON.stringify(bo)
    });
    if (!resp?.content) return JSON.stringify({ parse: 1, url: id, header: headers });
    const playlist = JSON.parse(resp.content).MediaSources;
    if (playlist && playlist.length > 0) {
        const url = host + playlist[0].DirectStreamUrl;
        return JSON.stringify({ parse: 0, url, header: headers });
    }
    return JSON.stringify({ parse: 1, url: id, header: headers });
};
export default { init, home, homeVod, category, detail, search, play };
