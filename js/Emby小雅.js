const config = {
  host: 'http://139.9.106.196:2345',
  userId: '623ba3ccaae348f9a3ce90adafb05bc1',
  token: '61450f3dc3e34bea80e5cbe4ae34fc05',
  deviceId: 'ea27caf7-9a51-4209-b1a5-374bf30c2ffd',
  clientVersion: '4.9.0.31',
};

const COMMON_FIELDS =
  'BasicSyncInfo,CanDelete,Container,PrimaryImageAspectRatio,ProductionYear,CommunityRating,Status,CriticRating,EndDate,Path,Overview,Genres,People,Taglines,Studios,IsFolder';
const IMAGE_TYPES = 'Primary,Backdrop,Thumb,Banner';

const deviceProfile = {
  DeviceProfile: {
    MaxStaticBitrate: 140000000,
    MaxStreamingBitrate: 140000000,
    DirectPlayProfiles: [
      { Container: 'mp4,mkv,webm', Type: 'Video', VideoCodec: 'h264,h265,av1,vp9', AudioCodec: 'aac,mp3,opus,flac' },
      { Container: 'mp3,aac,flac,opus', Type: 'Audio' },
    ],
    TranscodingProfiles: [
      { Container: 'mp4', Type: 'Video', VideoCodec: 'h264', AudioCodec: 'aac', Context: 'Streaming', Protocol: 'http' },
      { Container: 'aac', Type: 'Audio', Context: 'Streaming', Protocol: 'http' },
    ],
    SubtitleProfiles: [{ Format: 'srt,ass,vtt', Method: 'External' }],
    CodecProfiles: [{ Type: 'Video', Codec: 'h264', ApplyConditions: [{ Condition: 'LessThanEqual', Property: 'VideoLevel', Value: '62' }] }],
    BreakOnNonKeyFrames: true,
  },
};

const getHeaders = (extra = {}) => ({
  'X-Emby-Client': 'Emby Web',
  'X-Emby-Device-Name': 'Android WebView Android',
  'X-Emby-Device-Id': config.deviceId,
  'X-Emby-Client-Version': config.clientVersion,
  'X-Emby-Token': config.token,
  ...extra,
});

const buildUrl = (endpoint, params = {}) => {
  const qs = Object.entries(params)
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join('&');
  return `${config.host}${endpoint}${qs ? (endpoint.includes('?') ? '&' : '?') + qs : ''}`;
};

const getImageUrl = (itemId, imageTag) =>
  imageTag ? `${config.host}/emby/Items/${itemId}/Images/Primary?maxWidth=400&tag=${imageTag}&quality=90` : '';

const extractVideos = (jsonData) =>
  (jsonData?.Items || []).map((it) => ({
    vod_id: it.Id,
    vod_name: it.Name || '',
    vod_pic: getImageUrl(it.Id, it.ImageTags?.Primary),
    vod_remarks: it.ProductionYear?.toString() || '',
    Type: it.Type || '',
    vod_tag: it.Type === 'Folder' || it.Type === 'BoxSet' ? 'folder' : 'video',
  }));

const fetchApi = async (url, options = {}) => {
  const resp = await req(url, {
    ...options,
    headers: getHeaders(options.headers || {}),
  });
  return resp?.content ? JSON.parse(resp.content) : null;
};

const home = async () => {
  const json = await fetchApi(buildUrl(`/emby/Users/${config.userId}/Views`));
  const classList = (json?.Items || [])
    .filter((it) => !/播放列表|相机/.test(it.Name))
    .map((it) => ({ type_id: it.Id, type_name: it.Name }));
  return JSON.stringify({ class: classList, filters: {}, list: [] });
};

const homeVod = async () => {
  const url = buildUrl(`/emby/Users/${config.userId}/Items`, {
    SortBy: 'DateCreated',
    SortOrder: 'Descending',
    IncludeItemTypes: 'Movie,Series',
    Recursive: 'true',
    Limit: 40,
    Fields: COMMON_FIELDS,
    EnableImageTypes: IMAGE_TYPES,
    ImageTypeLimit: 1,
  });
  const json = await fetchApi(url);
  return JSON.stringify({ list: json ? extractVideos(json) : [] });
};

const category = async (tid, pg = 1) => {
  const startIndex = (pg - 1) * 30;
  const url = buildUrl(`/emby/Users/${config.userId}/Items`, {
    SortBy: 'DateLastContentAdded,SortName',
    SortOrder: 'Descending',
    IncludeItemTypes: 'Movie,Series',
    Recursive: 'true',
    Fields: COMMON_FIELDS,
    StartIndex: startIndex,
    ParentId: tid,
    EnableImageTypes: IMAGE_TYPES,
    ImageTypeLimit: 1,
    Limit: 30,
    EnableUserData: 'true',
  });
  const json = await fetchApi(url);
  if (!json) return JSON.stringify({ list: [], page: +pg, pagecount: 1, limit: 30, total: 0 });
  const list = extractVideos(json);
  const total = json.TotalRecordCount || 0;
  const pagecount = Math.ceil(total / 30) || 1;
  return JSON.stringify({ list, page: +pg, pagecount, limit: 30, total });
};

const detail = async (id) => {
  const info = await fetchApi(buildUrl(`/emby/Users/${config.userId}/Items/${id}`, { Fields: COMMON_FIELDS }));
  if (!info) return JSON.stringify({ list: [] });
  if (info.Type === 'Folder' || info.Type === 'BoxSet') {
    const folderItems = await fetchApi(
      buildUrl(`/emby/Users/${config.userId}/Items`, {
        ParentId: id,
        SortBy: 'DateLastContentAdded,SortName',
        SortOrder: 'Descending',
        IncludeItemTypes: 'Movie,Series,Folder',
        Recursive: 'false',
        Fields: COMMON_FIELDS.replace(',Overview,Genres,People,Taglines,Studios,IsFolder', ''),
        EnableImageTypes: IMAGE_TYPES,
        ImageTypeLimit: 1,
        Limit: 100,
        EnableUserData: 'true',
      })
    );
    const list = extractVideos(folderItems);
    return JSON.stringify({ list, page: 1, pagecount: 1, limit: 100, total: list.length });
  }
  const rating = info.CommunityRating || info.CriticRating;
  const formattedRating = rating ? rating.toFixed(1) : '';
  const year = info.ProductionYear?.toString() || '';
  let remarks = year;
  if (formattedRating) remarks = remarks ? `${remarks} / ${formattedRating}分` : `${formattedRating}分`;
  const directors = (info.People || [])
    .filter(p => p.Type === 'Director' || p.Role === 'Director')
    .map(p => p.Name);
  const actors = (info.People || [])
    .filter(p => p.Type === 'Actor' || p.Role === 'Actor')
    .map(p => p.Name);
  const studios = (info.Studios || []).map(s => s.Name);

  const VOD = {
    vod_id: id,
    vod_name: info.Name || '',
    vod_pic: getImageUrl(id, info.ImageTags?.Primary),
    vod_content: (info.Overview || '暂无简介').replace(/\xa0/g, ' ').replace(/\n\n/g, '\n').trim(),
    vod_year: year,
    vod_director: directors.join(' / '),
    vod_actor: actors.join(' / '),
    vod_area: studios.join(' / '),
    vod_remarks: remarks,
    vod_score: formattedRating,
    vod_type: (info.Genres || []).join(' / '),
    vod_play_from: '',
    vod_play_url: '',
  };

  if (info.Type === 'Series') {
    const seasons = await fetchApi(buildUrl(`/emby/Shows/${id}/Seasons`, {
      UserId: config.userId,
      Fields: COMMON_FIELDS,
      EnableTotalRecordCount: 'false',
    }));
    const from = [];
    const urls = [];
    for (const season of seasons?.Items || []) {
      from.push(season.Name);
      const episodes = await fetchApi(buildUrl(`/emby/Shows/${id}/Episodes`, {
        SeasonId: season.Id,
        UserId: config.userId,
        Fields: 'Overview,PrimaryImageAspectRatio',
        ImageTypeLimit: 1,
        Limit: 1000,
      }));
      const playlist = (episodes?.Items || []).map(e => `${e.Name}$${e.Id}`);
      urls.push(playlist.join('#'));
    }
    VOD.vod_play_from = from.join('$$$');
    VOD.vod_play_url = urls.join('$$$');
  } else {
    VOD.vod_play_from = 'EMBY';
    VOD.vod_play_url = `${info.Name || '播放'}$${id}`;
  }

  return JSON.stringify({ list: [VOD] });
};

const search = async (wd, quick, pg = 1) => {
  const url = buildUrl(`/emby/Users/${config.userId}/Items`, {
    SearchTerm: wd,
    SortBy: 'SortName',
    SortOrder: 'Ascending',
    Fields: 'BasicSyncInfo,CanDelete,Container,PrimaryImageAspectRatio,ProductionYear,Status,EndDate',
    StartIndex: (pg - 1) * 50,
    EnableImageTypes: 'Primary,Backdrop,Thumb',
    ImageTypeLimit: 1,
    Recursive: 'true',
    GroupProgramsBySeries: 'true',
    Limit: 50,
  });
  const json = await fetchApi(url);
  return JSON.stringify({ list: json ? extractVideos(json) : [] });
};

const play = async (_, id) => {
  const url = buildUrl(`/Items/${id}/PlaybackInfo`, {
    UserId: config.userId,
    IsPlayback: 'true',
    AutoOpenLiveStream: 'false',
    StartTimeTicks: 0,
    MaxStreamingBitrate: 140000000,
  });
  const resp = await req(url, {
    method: 'POST',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(deviceProfile),
  });
  const json = JSON.parse(resp.content);
  const mediaSource = json.MediaSources?.[0];
  if (!mediaSource) return JSON.stringify({ parse: 1, msg: '无可用媒体源' });
  let playUrl = mediaSource.DirectStreamUrl || mediaSource.DirectPlayUrl;
  if (!playUrl) return JSON.stringify({ parse: 1, msg: '无直通播放链接' });
  if (playUrl.startsWith('/')) {
    playUrl = config.host + playUrl;
  }
  return JSON.stringify({
    parse: 0,
    url: playUrl,
    header: getHeaders(),
  });
};

export default { home, homeVod, category, detail, search, play };
