/**
 * ============================================================================
 * 新韩剧网 - 不夜版 (网盘版)
 * ============================================================================
 * 
 * 【功能说明】
 * 本插件整合了韩剧网原始功能与网盘聚合搜索功能，支持以下特性：
 * 
 * 1. 韩剧网原生功能
 *    - 分类浏览：韩剧、韩国电影、韩国综艺、排行榜、最新更新
 *    - 筛选功能：按年份筛选、按热度/最新排序
 *    - 搜索功能：支持韩剧网站内搜索
 *    - 播放解析：自动解密韩剧网真实播放地址
 * 
 * 2. 网盘聚合功能
 *    - 自动搜索：进入详情页时自动搜索夸克、天翼、移动、115、百度网盘资源
 *    - 线路分离：每种网盘独立线路，线路名称为网盘标识（quark/a189/a139/a115/baidu）
 *    - 推送播放：网盘资源使用 push:// 协议调起外部网盘APP或浏览器
 * 
 * 【技术架构】
 * - 基于 T4 协议规范
 * - 使用 CryptoJS 解密韩剧网播放地址
 * - 调用聚合盘搜 API 搜索网盘资源
 * - 使用 push:// 协议实现网盘推送播放
 * 
 * 【配置说明】
 * - HOST: 韩剧网主站地址
 * - PANSOU_HOST: 聚合盘搜API地址
 * - panTypes: 支持的网盘类型映射
 * 
 * 【更新日志】
 * 2025-06: 初始版本，整合韩剧网与网盘搜索功能
 * 
 * ============================================================================
 */

const CryptoJS = require('crypto-js');
const axios  = require('axios');
const cheerio = require('cheerio');

/* ----------  基础配置  ---------- */
const HOST = 'https://www.hanju7.com';
const UA   = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/135.0.0.0 Mobile';
const _http = axios.create({
  timeout: 15000,
  headers: {
    'User-Agent': UA,
    Referer: HOST + '/'
  }
});

/* ----------  盘搜配置  ---------- */
const PANSOU_HOST = ' ';
const panTypes = {
  quark: 'quark',
  a189: 'tianyi',
  a139: 'mobile',
  a115: '115',
  baidu: 'baidu'
};
const reversePanTypes = {
  quark: 'quark',
  tianyi: 'a189',
  mobile: 'a139',
  '115': 'a115',
  baidu: 'baidu'
};

// 缓存韩剧详情信息
const dramaInfoCache = new Map();

/* ----------  筛选配置  ---------- */
const yearOptions = [
  { n: '全部', v: '' },
  { n: '2025', v: '2025' },
  { n: '2024', v: '2024' },
  { n: '2023', v: '2023' },
  { n: '2022', v: '2022' },
  { n: '2021', v: '2021' },
  { n: '2020', v: '2020' },
  { n: '10后', v: '2010__2019' },
  { n: '00后', v: '2000__2009' },
  { n: '90后', v: '1990__1999' }
];
const sortOptions = [
  { n: '最新', v: 'newstime' },
  { n: '热门', v: 'onclick' }
];

/* ----------  工具  ---------- */
const wrapPic = (src) =>
  (src && !src.startsWith('http') ? 'https:' + src : src) ||
  'https://youke2.picui.cn/s1/2025/12/21/694796745c0c6.png';

// 并发池
const pMap = async (list, fn, c = 6) => {
  const ret = [];
  const exec = async () => {
    while (list.length) {
      const item = list.shift();
      ret.push(await fn(item));
    }
  };
  await Promise.all(Array.from({ length: c }, exec));
  return ret;
};

/* ----------  盘搜功能  ---------- */
const searchPanSou = async (wd) => {
  try {
    const res = await _http.post(`${PANSOU_HOST}/api/search`, {
      kw: wd,
      cloud_types: Object.values(panTypes),
    }, {
      headers: {
        'User-Agent': UA,
        'Content-Type': 'application/json'
      },
      timeout: 30000
    });

    if (res.data.code !== 0) return {};

    const results = {};
    for (const [typeKey, items] of Object.entries(res.data.data.merged_by_type || {})) {
      const panKey = reversePanTypes[typeKey];
      if (panKey && items.length > 0) {
        results[panKey] = items.map(item => ({
          url: item.url,
          name: item.note,
          panType: typeKey
        }));
      }
    }
    return results;
  } catch (e) {
    return {};
  }
};

/* ----------  抓取真实封面  ---------- */
const getPicFromDetail = async (id, log) => {
  try {
    const { data } = await _http.get(HOST + id);
    const $ = cheerio.load(data);
    return wrapPic($('div.detail div.pic img').attr('data-original'));
  } catch (e) {
    return wrapPic('');
  }
};

/* ----------  分类/筛选  ---------- */
const getClasses = () => [
  { type_id: '1', type_name: '韩剧'}, 
  { type_id: '3', type_name: '韩国电影'},
  { type_id: '4', type_name: '韩国综艺'},
  { type_id: 'hot', type_name: '排行榜'},
  { type_id: 'new', type_name: '最新更新'}
];


const getFilters = () => {
  const f = {};
  ['1', '3', '4'].forEach(tid => {
    f[tid] = [
      { key: 'year', name: '年份', value: yearOptions },
      { key: 'sort', name: '排序', value: sortOptions }
    ];
  });
  return f;
};

/* ----------  列表 + 分页  ---------- */
const getCategoryList = async (tid, page = 1, year = '', sort = 'newstime', ext, log) => {
  const pg = Math.max(1, +page);
  const pageSize = 20;

  /* 排行榜 / 最新更新  一次性拉全  内存分页 */
  if (['hot', 'new'].includes(tid)) {
    const { data } = await _http.get(`${HOST}/${tid}.html`);
    const $ = cheerio.load(data);
    const all = $('div.txt ul li')
      .get()
      .map(el => {
        const a = $(el).find('a');
        return {
          vod_id: a.attr('href'),
          vod_name: a.text().trim(),
          vod_remarks: $(el).find('#actor').text().trim()
        };
      })
      .filter(v => v.vod_id);

    const total = all.length;
    const pageCount = Math.ceil(total / pageSize);
    const slice = all.slice((pg - 1) * pageSize, pg * pageSize);

    // 并发补封面
    await pMap([...slice], async v => (v.vod_pic = await getPicFromDetail(v.vod_id, log)));

    return {
      list: slice,
      page: pg,
      pagecount: pageCount,
      limit: pageSize,
      total
    };
  }

  /* 常规分类  直接走远端分页 */
  const yearParam = year ? `-${year}` : '-';
  const url = `${HOST}/list/${tid}${yearParam}-${sort}-${pg - 1}.html`;
  const { data } = await _http.get(url);
  const $ = cheerio.load(data);

  const list = $('div.list ul li')
    .get()
    .map(el => {
      const a = $(el).find('a');
      return {
        vod_id: a.attr('href'),
        vod_name: a.attr('title') || a.text(),
        vod_pic: wrapPic(a.attr('data-original')),
        vod_remarks: $(el).find('span.tip').text().trim()
      };
    });

  // 从底部页码条提取总页数
  let pageCount = 100;
  const last = $('div.pages a[href*="-(\\d+)\\.html"]').last();
  if (last.length) {
    const m = last.attr('href').match(/-(\d+)\.html$/);
    if (m) pageCount = +m[1] + 1;
  }

  return { list, page: pg, pagecount: pageCount, limit: pageSize, total: pageCount * pageSize };
};

/* ----------  搜索  ---------- */
const getSearch = async (wd, log) => {
  const body = `show=searchkey&keyboard=${encodeURIComponent(wd)}`;
  const { data } = await _http.post(`${HOST}/search/`, body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  });
  const $ = cheerio.load(data);
  const items = $('div.txt ul li')
    .get()
    .map(el => {
      const a = $(el).find('a');
      return {
        vod_id: a.attr('href'),
        vod_name: a.text().trim(),
        vod_remarks: $(el).find('#actor').text().trim()
      };
    })
    .filter(v => v.vod_id);

  await pMap([...items], async v => (v.vod_pic = await getPicFromDetail(v.vod_id, log)));
  return { list: items };
};

/* ----------  详情（整合网盘）  ---------- */
const getDetail = async (id, log) => {
  const { data } = await _http.get(HOST + id);
  const $ = cheerio.load(data);
  
  // 原有播放列表
  const playUrls = [];
  $('div.play ul li a').each((_, el) => {
    const m = ($(el).attr('onclick') || '').match(/'(.*?)'/);
    if (m) playUrls.push(`${$(el).text()}$${m[1]}`);
  });

  // 韩剧信息
  const dramaInfo = {
    vod_id: id,
    vod_name: $('div.detail div.info dl').eq(0).find('dd').text().trim(),
    vod_pic: wrapPic($('div.detail div.pic img').attr('data-original')),
    type_name: $('div.detail div.info dl').eq(2).find('dd').text().trim(),
    vod_actor: $('div.detail div.info dl').eq(1).find('dd').text().trim(),
    vod_remarks: $('div.detail div.info dl').eq(4).find('dd').text().trim(),
    vod_year: $('div.detail div.info dl').eq(5).find('dd').text().trim(),
    vod_content: $('div.juqing').text().trim()
  };

  // 缓存信息用于网盘推送
  dramaInfoCache.set(id, dramaInfo);

  // 构建播放来源和地址
  const playFrom = [$('#playlist').text() || '新韩剧'];
  const allPlayUrls = [playUrls.join('#')];

  // 搜索网盘资源
  const panResults = await searchPanSou(dramaInfo.vod_name);

  // 整合网盘线路
  for (const [panKey, items] of Object.entries(panResults)) {
    if (items.length === 0) continue;
    
    playFrom.push(panKey);
    
    const panPlayUrls = items.map((item, index) => {
      const displayName = item.name || `资源${index + 1}`;
      // 格式: push://韩剧ID|网盘链接|剧集名称
      return `${displayName}$push://${id}|${item.url}|${displayName}`;
    });
    
    allPlayUrls.push(panPlayUrls.join('#'));
  }

  return {
    ...dramaInfo,
    vod_play_from: playFrom.join('$$$'),
    vod_play_url: allPlayUrls.join('$$$')
  };
};

/* ----------  播放（含网盘推送）  ---------- */
const getPlayUrl = async (pid, log) => {
  const { data } = await _http.get(`${HOST}/u/u1.php?ud=${pid}`);
  const key = CryptoJS.enc.Utf8.parse('my-to-newhan-2025\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0');
  const base64 = CryptoJS.enc.Base64.parse(data);
  const iv = CryptoJS.lib.WordArray.create(base64.words.slice(0, 4));
  const cipher = CryptoJS.lib.WordArray.create(base64.words.slice(4));
  const plain = CryptoJS.AES.decrypt({ ciphertext: cipher }, key, {
    iv,
    mode: CryptoJS.mode.CBC,
    padding: CryptoJS.pad.Pkcs7
  });
  return plain.toString(CryptoJS.enc.Utf8).trim();
};

/**
 * 网盘播放处理
 * 【关键】保留push://协议头，让客户端调用外部应用打开
 */
const _play = async ({ flag, flags, id }) => {
  if (id && id.startsWith('push://')) {
    const pushData = id.replace('push://', '');
    const parts = pushData.split('|');
    const dramaId = parts[0];
    const panUrl = parts[1];
    
    return {
      parse: 0,
      jx: 0,
      url: `push://${panUrl}`,
      header: {}
    };
  }
  
  return {
    parse: 0,
    jx: 0,
    url: id,
    header: {}
  };
};

/* ----------  T4 协议统一入口  ---------- */
const handleT4Request = async (req, reply) => {
  const log = req.log || (req.server && req.server.log) || console;
  const { t, ids, play, pg = 1, wd, ext, flag, flags } = req.query;
  let extObj = {};
  if (ext) {
    try {
      const raw = Buffer.from(ext, 'base64').toString('utf8');
      extObj = JSON.parse(raw);
    } catch {
      // ext 解析失败，已忽略
    }
  }
  const year = extObj.year || '';
  const sort = extObj.sort || 'newstime';

  try {
    // 网盘推送播放
    if (play && play.startsWith('push://')) {
      return await _play({ flag, flags, id: play });
    }
    // 原有韩剧播放
    if (play) return { parse: 0, url: await getPlayUrl(play, log) || 'error_url', header: _http.defaults.headers };
    if (ids) return { list: [await getDetail(ids, log)].filter(Boolean) };
    if (wd) return await getSearch(wd, log);
    if (t) return await getCategoryList(t, pg, year, sort, extObj, log);
    return { class: getClasses(), filters: getFilters() };
  } catch (e) {
    throw e;
  }
};

/* ----------  fastify 插件导出  ---------- */
module.exports = async (app, opt) => {
  const meta = {
    key: 'hanju7',
    name: '新韩剧网',
    type: 4,
    api: '/video/hanju7',
    searchable: 1,
    quickSearch: 1,
    filterable: 1
  };
  app.get(meta.api, handleT4Request);
  opt.sites.push(meta);
};