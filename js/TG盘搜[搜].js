/*
@header({
  searchable: 1,
  filterable: 0,
  quickSearch: 1,
  title: '盘搜',
  '类型': '搜索',
  lang: 'ds'
  by:EylinSir
})
*/

const NETDISK_PATTERNS = {
  quark: /pan\.quark\.cn/,
  uc: /drive\.uc\.cn/,
  ali: /www\.alipan\.com|www\.aliyundrive\.com/,
  cloud189: /cloud\.189\.cn/,
  yun139: /yun\.139\.com|caiyun\.139\.com/,
  pan123: /www\.123(?:684|865|912|pan\.com|pan\.cn|592)\.com/,
  baidu: /pan\.baidu\.com/
};

const UCDownloadingCache = {};

var rule = {
  类型: '搜索',
  title: '盘搜',
  alias: '盘搜引擎',
  desc: '支持网盘优先级与过滤的纯搜索源',
  DEFAULT_CONFIG: {
    cloud_types: 'baidu,quark,uc,a189,a139',// 限制网盘类型
    max_results_per_pan: 5, // 限制搜索结果数量
    pan_priority: 'baidu,quark,uc,a189,a139',// 网盘排序
    pan_order: 'desc'  // asc: 旧→新, desc: 新→旧
  },
  host: 'https://so.252035.xyz',
  url: '/api/search',
  searchUrl: '/api/search?kw=**',
  headers: {
    'User-Agent': 'MOBILE_UA',
    'Content-Type': 'application/json',
    'Referer': 'https://so.252035.xyz'
  },
  searchable: 1,
  quickSearch: 1,
  filterable: 0,
  double: true,
  play_parse: true,
  search_match: true,
  limit: 10,

  // 注意：api_type 使用简洁名称，与用户配置一致
  panConfig: {
    baidu: { api_type: 'baidu', name: '百度' },
    uc:    { api_type: 'uc',    name: 'UC' },
    quark: { api_type: 'quark', name: '夸克' },
    a189:  { api_type: '189',   name: '天翼' },
    ali:   { api_type: 'ali',   name: '阿里' },
    xunlei:{ api_type: 'xunlei',name: '迅雷' },
    a123:  { api_type: '123',   name: '123' },
    a139:  { api_type: '139',   name: '移动' },
    a115:  { api_type: '115',   name: '115' },
    pikpak:{ api_type: 'pikpak',name: 'PikPak' },
    magnet:{ api_type: 'magnet',name: '磁力' },
    ed2k:  { api_type: 'ed2k',  name: '电驴' }
  },

  action: async (action, value) => {
    if (action === 'only_search') return '此源为纯搜索源，直接搜索即可！';
    if (action === 'init') {
      this.init(value);
      return '配置已更新';
    }
    return `注意:${action}`;
  },

  init: function (extend) {
    try {
      const cfg = extend ? (typeof extend === 'string' ? JSON.parse(extend) : extend) : {};
      Object.assign(this, this.DEFAULT_CONFIG);
      // 仅应用有效字段
      if (cfg.cloud_types) this.cloud_types = String(cfg.cloud_types);
      if (cfg.max_results_per_pan) this.max_results_per_pan = Number(cfg.max_results_per_pan) || 5;
      if (cfg.pan_priority) this.pan_priority = String(cfg.pan_priority);
      if (cfg.pan_order) this.pan_order = ['asc', 'desc'].includes(cfg.pan_order) ? cfg.pan_order : 'desc';
      this.headers.Referer = `${this.host}/`;
    } catch {
      Object.assign(this, this.DEFAULT_CONFIG);
      this.headers.Referer = `${this.host}/`;
    }
  },

  推荐: async () => [{
    vod_id: '直接搜索即可！',
    vod_pic: 'https://images.gamedog.cn/gamedog/imgfile/20241205/05105843u5j9.png',
    vod_name: '纯搜索源哦！',
    vod_tag: 'action'
  }],

  二级: async function (ids) {
    const input = decodeURIComponent(this.orId);
    const vod = {
      vod_id: this.orId,
      vod_content: `盘搜分享资源\n链接: ${input}`,
      vod_name: '盘搜资源'
    };
    const playform = [], playurls = [], playPans = [];

    const processResult = (name, successUrls) => {
      playform.push(name);
      playurls.push(successUrls.length > 0 ? successUrls.join('#') : '资源已经失效');
    };

    try {
      if (NETDISK_PATTERNS.quark.test(input)) {
        playPans.push(input);
        const url = input.replace(/#\/list\/share.*/, '');
        const share = Quark.getShareData(url);
        if (share) {
          const files = await Quark.getFilesByShareUrl(share);
          const list = Array.isArray(files) ? files : Object.values(files).flat();
          processResult('夸克网盘', list.map(v =>
            `${v.file_name}$${share.shareId}*${v.stoken}*${v.fid}*${v.share_fid_token}*${v.subtitle?.fid || ''}*${v.subtitle?.share_fid_token || ''}`
          ));
        } else {
          processResult('夸克网盘', []);
        }
      } else if (NETDISK_PATTERNS.uc.test(input)) {
        playPans.push(input);
        const share = UC.getShareData(input);
        if (share) {
          const files = await UC.getFilesByShareUrl(share);
          processResult('UC网盘', files.map(v =>
            `${v.file_name}$${share.shareId}*${v.stoken}*${v.fid}*${v.share_fid_token}*${v.subtitle?.fid || ''}*${v.subtitle?.share_fid_token || ''}`
          ));
        } else {
          processResult('UC网盘', []);
        }
      } else if (NETDISK_PATTERNS.ali.test(input)) {
        playPans.push(input);
        const share = Ali.getShareData(input);
        if (share) {
          const files = await Ali.getFilesByShareUrl(share);
          processResult('阿里云盘', files.map(v =>
            `${misc.formatPlayUrl('', v.name)}$${v.share_id}*${v.file_id}*${v.subtitle?.file_id || ''}`
          ));
        } else {
          processResult('阿里云盘', []);
        }
      } else if (NETDISK_PATTERNS.cloud189.test(input)) {
        playPans.push(input);
        const data = await Cloud.getShareData(input);
        const files = Object.values(data || {}).flat();
        processResult('天翼云盘', files.map(item =>
          `${item.name}$${item.fileId}*${item.shareId}`
        ));
      } else if (NETDISK_PATTERNS.yun139.test(input)) {
        playPans.push(input);
        const data = await Yun.getShareData(input);
        const files = Object.values(data || {}).flat();
        processResult('移动云盘', files.map(item =>
          `${item.name}$${item.contentId}*${item.linkID}`
        ));
      } else if (NETDISK_PATTERNS.pan123.test(input)) {
        playPans.push(input);
        const share = await Pan.getShareData(input);
        const videos = await Pan.getFilesByShareUrl(share);
        const files = Object.values(videos || {}).flat();
        processResult('123盘', files.map(v =>
          `${v.FileName}$${share}*${v.FileId}*${v.S3KeyFlag}*${v.Size}*${v.Etag}`
        ));
      } else if (NETDISK_PATTERNS.baidu.test(input)) {
        playPans.push(input);
        const data = await Baidu2.getShareData(input);
        const vod_content_add = [vod.vod_content];
        const files = Object.entries(data || {}).flatMap(([dir, items]) => {
          vod_content_add.push(dir);
          return items;
        });
        vod.vod_content = vod_content_add.join('\n');
        processResult('百度网盘', files.map(item =>
          `${item.name}$${item.path}*${item.uk}*${item.shareid}*${item.fsid}`
        ));
      } else {
        playform.push('盘搜');
        playurls.push(`播放$${input}`);
      }
    } catch (e) {
      log(`[盘搜] 解析失败: ${e.message || e}`);
      playform.push('解析错误');
      playurls.push('解析发生异常');
    }

    vod.vod_play_from = playform.join('$$$');
    vod.vod_play_url = playurls.join('$$$');
    vod.vod_play_pan = playPans.join('$$$');
    return vod;
  },

  搜索: async function (wd, pg) {
    // === 1. 网盘类型白名单 ===
    const allowedTypes = this.cloud_types
      ? this.cloud_types.split(',').map(s => s.trim()).filter(Boolean)
      : Object.values(this.panConfig).map(c => c.api_type);

    // === 2. 构建优先级排序映射 ===
    const apiTypeToPanKey = {};
    for (const [key, cfg] of Object.entries(this.panConfig)) {
      apiTypeToPanKey[cfg.api_type] = key;
    }
    const priorityPanKeys = this.pan_priority
      ? this.pan_priority.split(',').map(t => apiTypeToPanKey[t.trim()]).filter(Boolean)
      : [];

    // === 3. 请求搜索数据 ===
    const apiUrl = `${this.host}/api/search?kw=${encodeURIComponent(wd)}`;
    let html;
    for (let i = 0; i <= 3; i++) {
      try {
        html = await request(apiUrl, {
          headers: { 'User-Agent': 'MOBILE_UA', 'Referer': this.headers.Referer }
        });
        if (html) break;
      } catch (e) {
        if (i === 3) throw e;
        await new Promise(r => setTimeout(r, Math.pow(2, i) * 1000));
      }
    }

    const data = JSON.parse(html);
    if (data.code !== 0) throw new Error(data.message || '请求失败');

    // === 4. 收集并过滤结果 ===
    const allImages = Object.values(data.data?.merged_by_type || {})
      .flatMap(group => group.flatMap(item => item.images || []))
      .filter(Boolean);

    const allItems = [];
    for (const [apiType, rows] of Object.entries(data.data?.merged_by_type || {})) {
      if (!allowedTypes.includes(apiType)) continue;

      const panKey = apiTypeToPanKey[apiType];
      if (!panKey) continue;

      const panName = this.panConfig[panKey]?.name || '网盘';
      const limitedRows = (rows || []).slice(0, this.max_results_per_pan);
      for (const row of limitedRows) {
        const dt = new Date(row.datetime);
        const timeStr = `${(dt.getMonth() + 1).toString().padStart(2, '0')}-${dt.getDate().toString().padStart(2, '0')}`;
        const vodPic = row.images?.[0] || (allImages.length ? allImages[Math.floor(Math.random() * allImages.length)] : '');
        allItems.push({
          title: row.note || '未知名称',
          img: vodPic,
          desc: timeStr,
          url: row.url,
          pan: panKey,
          panName,
          time: dt.getTime(),
          source: row.source || '盘搜'
        });
      }
    }

    // === 5. 排序：优先级 + 时间 ===
    allItems.sort((a, b) => {
      const aIdx = priorityPanKeys.indexOf(a.pan);
      const bIdx = priorityPanKeys.indexOf(b.pan);
      if (aIdx !== -1 || bIdx !== -1) {
        if (aIdx === -1) return 1;
        if (bIdx === -1) return -1;
        return aIdx - bIdx;
      }
      // 时间排序
      return this.pan_order === 'asc' ? a.time - b.time : b.time - a.time;
    });

    // === 6. 返回结果 ===
    return allItems
      .filter(item => !this.search_match || item.title.includes(wd))
      .map(item => ({
        vod_id: item.url,
        vod_name: item.title,
        vod_pic: item.img,
        vod_remarks: `${item.panName}:${item.desc}|${item.source}`
      }));
  },

  lazy: async function (flag, id, flags) {
    const { input, mediaProxyUrl } = this;
    const ids = input.split('*');

    if (flag === '盘搜') {
      if (tellIsJx(input)) return { parse: 1, jx: 1, url: input };
      if (/\.(m3u8|mp4|m3u)$/i.test(input)) return { url: input };
      return { parse: 1, url: input };
    }

    try {
      if (flag === '夸克网盘') {
        const down = await Quark.getDownload(ids[0], ids[1], ids[2], ids[3], true);
        const urls = [];
        down.forEach(t => {
          if (t.url) {
            urls.push(`猫${t.name}`, `http://127.0.0.1:5575/proxy?thread=${ENV.get('thread') || 6}&chunkSize=1024&url=${encodeURIComponent(t.url)}`);
            urls.push(t.name, `${t.url}#isVideo=true##fastPlayMode##threads=20#`);
          }
        });
        const transcoding = (await Quark.getLiveTranscoding(ids[0], ids[1], ids[2], ids[3])).filter(t => t.accessable);
        transcoding.forEach(t => {
          const label = t.resolution === 'low' ? '流畅' : t.resolution === 'high' ? '高清' : t.resolution === 'super' ? '超清' : t.resolution;
          urls.push(label, `${t.video_info.url}#isVideo=true##fastPlayMode##threads=20#`);
        });
        return { parse: 0, url: urls, header: { Cookie: ENV.get('quark_cookie') } };
      }

      if (flag === 'UC网盘') {
        if (!UCDownloadingCache[ids[1]]) {
          UCDownloadingCache[ids[1]] = await UC.getDownload(ids[0], ids[1], ids[2], ids[3], true);
        }
        return UC.getLazyResult(UCDownloadingCache[ids[1]], mediaProxyUrl);
      }

      if (flag === '阿里云盘') {
        const transcoding_flag = { UHD: "4K 超清", QHD: "2K 超清", FHD: "1080 全高清", HD: "720 高清", SD: "540 标清", LD: "360 流畅" };
        const down = await Ali.getDownload(ids[0], ids[1], flag === 'down');
        const urls = [
          "原画", `${down.url}#isVideo=true##ignoreMusic=true#`,
          "极速原画", `${down.url}#fastPlayMode##threads=10#`
        ];
        const transcoding = (await Ali.getLiveTranscoding(ids[0], ids[1]))
          .sort((a, b) => b.template_width - a.template_width);
        transcoding.forEach(t => {
          if (t.url) urls.push(transcoding_flag[t.template_id], t.url);
        });
        return {
          parse: 0,
          url: urls,
          header: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.aliyundrive.com/'
          }
        };
      }

      if (flag === '天翼云盘') {
        const url = await Cloud.getShareUrl(ids[0], ids[1]);
        return { url: `${url}#isVideo=true#` };
      }

      if (flag === '移动云盘') {
        const url = await Yun.getSharePlay(ids[0], ids[1]);
        return { url };
      }

      if (flag === '123盘') {
        const url = await Pan.getDownload(ids[0], ids[1], ids[2], ids[3], ids[4]);
        const urls = ["原画", url];
        const transcoding = await Pan.getLiveTranscoding(ids[0], ids[1], ids[2], ids[3], ids[4]);
        transcoding.forEach(item => urls.push(item.name, item.url));
        return { parse: 0, url: urls };
      }

      if (flag === '百度网盘') {
        const url = await Baidu2.getAppShareUrl(ids[0], ids[1], ids[2], ids[3]);
        return {
          parse: 0,
          url: `${url}#isVideo=true##fastPlayMode##threads=10#`,
          header: {
            "User-Agent": 'netdisk;P2SP;2.2.91.136;android-android;',
            "Cookie": ENV.get('baidu_cookie')
          }
        };
      }
    } catch (e) {
      log(`[盘搜] lazy解析异常: ${e.message}`);
    }

    return input;
  }
};

// 初始化默认配置
Object.assign(rule, rule.DEFAULT_CONFIG);
