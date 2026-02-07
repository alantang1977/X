/**
 * ============================================================================
 * 3Q影视 - TVBox T4 接口插件
 * ============================================================================
 * 
 * 功能说明：
 * - 提供3Q影视视频源的 TVBox T4 格式接口
 * - 支持分类浏览、搜索、详情、播放等完整功能
 * - 智能线路管理系统，支持主站+聚合双数据源
 * - 多模式播放解析：直连/Web嗅探/自动解析器调用
 * 
 * 主要特性：
 * 1. 分类支持：电影、剧集、动漫、综艺
 * 2. 筛选功能：支持类型、地区、年份、排序等多维度筛选
 * 3. 线路管理：
 *    - 官源线路：腾讯、爱奇艺、芒果、优酷、bilibili（自动解析）
 *    - 蓝光线路：SE蓝光、JD蓝光、3Q蓝光、NB蓝光、YY蓝光、BB蓝光（Web嗅探）
 *    - 站外资源：直接播放
 * 4. 智能解析：
 *    - direct：直接播放，parse:0
 *    - 360parse：聚合数据Web嗅探，sid=site_key
 *    - qqqparse：主站数据Web嗅探，sid=线路标识
 *    - auto：自动调用解析器，失败自动回退
 *    - auto$解析器名：指定解析器，失败自动回退
 * 5. 线路优化：
 *    - 自动屏蔽失效/禁用线路
 *    - 支持线路排序、重命名、优先级配置
 *    - 播放失败自动切换备用线路
 * 
 * 播放URL格式：
 * 线路名称@@siteId@@mode@@影片ID@@第几集@@URL
 * 
 * 接口路径：/video/qqqys
 * 
 * 作者：Your Name
 * 日期：2026-02-07
 * ============================================================================
 */
const axios = require("axios");
const CryptoJS = require("crypto-js");

// ==========================================
// 1. 统一配置中心
// ==========================================

const sourceConfig = {
  // 全局开关：是否显示手动指定解析器的线路
  showManualLines: false,

  // 线路配置：以线路名称作为key
  // mode可选：direct/360parse/qqqparse/auto
  lines: {
    '腾讯': { displayName: '腾讯官源', order: 1, enabled: true, mode: 'auto', parserPriority: ['岁岁解析', '空城解析'] },
    '爱奇艺': { displayName: '爱奇艺官源', order: 2, enabled: true, mode: 'auto', parserPriority: ['岁岁解析', '空城解析'] },
    '芒果': { displayName: '芒果官源', order: 3, enabled: true, mode: 'auto', parserPriority: ['芒果解析'] },
    '优酷': { displayName: '优酷官源', order: 4, enabled: true, mode: '360parse', parserPriority: [''] },
    'bilibili': { displayName: 'B站官源', order: 5, enabled: true, mode: '360parse', parserPriority: [''] },
    'SE蓝光': { displayName: 'SE蓝光', order: 6, enabled: true, mode: 'qqqparse' },
    'JD蓝光': { displayName: 'JD蓝光', order: 7, enabled: true, mode: 'qqqparse' },
    '3Q蓝光': { displayName: '3Q蓝光', order: 8, enabled: true, mode: 'qqqparse' },
    'NB蓝光': { displayName: 'NB蓝光', order: 9, enabled: true, mode: 'qqqparse' },
    'YY蓝光': { displayName: 'YY蓝光', order: 10, enabled: true, mode: 'qqqparse' },
    'BB蓝光': { displayName: 'BB蓝光', order: 11, enabled: true, mode: 'qqqparse' },
    '站外': { displayName: '站外资源', order: 12, enabled: true, mode: 'direct' }
  },

  parsers: {
    '岁岁解析': 'parse_ss',
    '空城解析': 'parse_kc',
    '芒果解析': 'parse_mg'
  },

  api: {
    host: 'https://qqqys.com',
    timeout: 15000
  }
};

// ==========================================
// 2. 日志与网络工具
// ==========================================

let log = {
  info: (msg, ...args) => console.log(`[3Q影视][INFO] ${msg}`, ...args),
  error: (msg, err) => console.error(`[3Q影视][ERROR] ${msg}`, err?.message || err),
  debug: (msg, ...args) => console.log(`[3Q影视][DEBUG] ${msg}`, ...args)
};

async function req(url, options = {}) {
  try {
    const response = await axios({
      url,
      method: options.method || 'GET',
      headers: options.headers || { 'User-Agent': 'Mozilla/5.0' },
      timeout: options.timeout || sourceConfig.api.timeout
    });
    return { 
      content: typeof response.data === 'object' 
        ? JSON.stringify(response.data) 
        : response.data 
    };
  } catch (error) {
    log.error(`请求失败: ${url}`, error.message);
    return { content: "{}" };
  }
}

function json2vods(arr) {
  if (!arr) return [];
  return arr.map(i => ({
    'vod_id': i.vod_id.toString(),
    'vod_name': i.vod_name,
    'vod_pic': i.vod_pic,
    'vod_remarks': i.vod_remarks,
    'type_name': (i.type_name || '') + (i.vod_class ? ',' + i.vod_class : ''),
    'vod_year': i.vod_year
  }));
}

// ==========================================
// 3. 线路管理器
// ==========================================

const LineManager = {
  /**
   * 获取线路配置
   * @param {string} lineName - 线路名称
   * @returns {object|null} 配置对象
   */
  getConfig(lineName) {
    if (!lineName) return null;
    return sourceConfig.lines[lineName] || null;
  },

  /**
   * 判断是否屏蔽
   * @param {string} lineName - 线路名称
   */
  isBlocked(lineName) {
    const cfg = this.getConfig(lineName);
    return cfg && cfg.enabled === false;
  },

  /**
   * 获取mode
   * @param {string} lineName - 线路名称
   * @returns {string} mode，未配置默认为'direct'
   */
  getMode(lineName) {
    const cfg = this.getConfig(lineName);
    return cfg?.mode || 'direct';
  },

  /**
   * 获取显示名称
   * @param {string} lineName - 线路名称
   */
  getDisplayName(lineName) {
    const cfg = this.getConfig(lineName);
    return cfg?.displayName || lineName;
  },

  /**
   * 获取排序权重
   * @param {string} lineName - 线路名称
   */
  getOrder(lineName) {
    const cfg = this.getConfig(lineName);
    return cfg?.order ?? 999;
  },

  /**
   * 获取解析器列表（用于auto模式）
   * @param {string} lineName - 线路名称
   * @param {object} app - Fastify应用实例
   */
  getParsers(lineName, app) {
    const cfg = this.getConfig(lineName);
    if (!cfg || cfg.mode !== 'auto' || !cfg.parserPriority) return [];
    
    const result = [];
    for (const pName of cfg.parserPriority) {
      const funcName = sourceConfig.parsers[pName];
      if (funcName && app && app[funcName]) {
        result.push({ name: funcName, label: pName, func: app[funcName] });
      }
    }
    return result;
  },

  /**
   * 处理线路列表：排序、过滤、重命名
   * @param {Array} lines - 原始线路数组
   */
  processLines(lines) {
    if (!Array.isArray(lines)) return [];

    const processed = lines.map(line => {
      const lineName = line.lineName;  // 线路名称
      const cfg = this.getConfig(lineName);
      
      return {
        ...line,
        displayName: cfg?.displayName || lineName,
        order: cfg?.order ?? 999,
        mode: cfg?.mode || 'direct',
        parserPriority: cfg?.parserPriority || []
      };
    }).filter(line => !this.isBlocked(line.lineName));

    processed.sort((a, b) => a.order - b.order);
    return processed;
  }
};

// ==========================================
// 4. 筛选配置
// ==========================================

const filterConfig = {
  "电影": [
    { key: "class", name: "类型", value: [{ n: "全部", v: "" }, { n: "动作", v: "动作" }, { n: "喜剧", v: "喜剧" }, { n: "爱情", v: "爱情" }, { n: "科幻", v: "科幻" }, { n: "恐怖", v: "恐怖" }, { n: "悬疑", v: "悬疑" }, { n: "犯罪", v: "犯罪" }, { n: "战争", v: "战争" }, { n: "动画", v: "动画" }, { n: "冒险", v: "冒险" }, { n: "历史", v: "历史" }, { n: "灾难", v: "灾难" }, { n: "纪录", v: "纪录" }, { n: "剧情", v: "剧情" }] },
    { key: "area", name: "地区", value: [{ n: "全部", v: "" }, { n: "大陆", v: "大陆" }, { n: "香港", v: "香港" }, { n: "台湾", v: "台湾" }, { n: "美国", v: "美国" }, { n: "日本", v: "日本" }, { n: "韩国", v: "韩国" }, { n: "泰国", v: "泰国" }, { n: "印度", v: "印度" }, { n: "英国", v: "英国" }, { n: "法国", v: "法国" }, { n: "德国", v: "德国" }, { n: "加拿大", v: "加拿大" }, { n: "西班牙", v: "西班牙" }, { n: "意大利", v: "意大利" }, { n: "澳大利亚", v: "澳大利亚" }] },
    { key: "year", name: "年份", value: [{ n: "全部", v: "" }, { n: "2026", v: "2026" }, { n: "2025", v: "2025" }, { n: "2024", v: "2024" }, { n: "2023", v: "2023" }, { n: "2022", v: "2022" }, { n: "2021", v: "2021" }, { n: "2020", v: "2020" }, { n: "2019", v: "2019" }, { n: "2018", v: "2018" }, { n: "2017", v: "2017" }, { n: "2016", v: "2016" }, { n: "2015-2011", v: "2015-2011" }, { n: "2010-2000", v: "2010-2000" }, { n: "90年代", v: "90年代" }, { n: "80年代", v: "80年代" }, { n: "更早", v: "更早" }] },
    { key: "sort", name: "排序", value: [{ n: "人气", v: "hits" }, { n: "最新", v: "time" }, { n: "评分", v: "score" }, { n: "年份", v: "year" }] }
  ],
  "剧集": [
    { key: "class", name: "类型", value: [{ n: "全部", v: "" }, { n: "爱情", v: "爱情" }, { n: "古装", v: "古装" }, { n: "武侠", v: "武侠" }, { n: "历史", v: "历史" }, { n: "家庭", v: "家庭" }, { n: "喜剧", v: "喜剧" }, { n: "悬疑", v: "悬疑" }, { n: "犯罪", v: "犯罪" }, { n: "战争", v: "战争" }, { n: "奇幻", v: "奇幻" }, { n: "科幻", v: "科幻" }, { n: "恐怖", v: "恐怖" }] },
    { key: "area", name: "地区", value: [{ n: "全部", v: "" }, { n: "大陆", v: "大陆" }, { n: "香港", v: "香港" }, { n: "台湾", v: "台湾" }, { n: "美国", v: "美国" }, { n: "日本", v: "日本" }, { n: "韩国", v: "韩国" }, { n: "泰国", v: "泰国" }, { n: "英国", v: "英国" }] },
    { key: "year", name: "年份", value: [{ n: "全部", v: "" }, { n: "2026", v: "2026" }, { n: "2025", v: "2025" }, { n: "2024", v: "2024" }, { n: "2023", v: "2023" }, { n: "2022", v: "2022" }, { n: "2021", v: "2021" }, { n: "2020-2016", v: "2020-2016" }, { n: "2015-2011", v: "2015-2011" }, { n: "2010-2000", v: "2010-2000" }, { n: "更早", v: "更早" }] },
    { key: "sort", name: "排序", value: [{ n: "人气", v: "hits" }, { n: "最新", v: "time" }, { n: "评分", v: "score" }, { n: "年份", v: "year" }] }
  ],
  "动漫": [
    { key: "class", name: "类型", value: [{ n: "全部", v: "" }, { n: "冒险", v: "冒险" }, { n: "奇幻", v: "奇幻" }, { n: "科幻", v: "科幻" }, { n: "武侠", v: "武侠" }, { n: "悬疑", v: "悬疑" }] },
    { key: "area", name: "地区", value: [{ n: "全部", v: "" }, { n: "大陆", v: "大陆" }, { n: "日本", v: "日本" }, { n: "欧美", v: "欧美" }] },
    { key: "year", name: "年份", value: [{ n: "全部", v: "" }, { n: "2026", v: "2026" }, { n: "2025", v: "2025" }, { n: "2024", v: "2024" }, { n: "2023", v: "2023" }, { n: "2022", v: "2022" }, { n: "2021", v: "2021" }, { n: "2020", v: "2020" }, { n: "2019", v: "2019" }, { n: "2018", v: "2018" }, { n: "2017", v: "2017" }, { n: "2016", v: "2016" }, { n: "2015", v: "2015" }, { n: "2014", v: "2014" }, { n: "2013", v: "2013" }, { n: "2012", v: "2012" }, { n: "2011", v: "2011" }, { n: "更早", v: "更早" }] },
    { key: "sort", name: "排序", value: [{ n: "人气", v: "hits" }, { n: "最新", v: "time" }, { n: "评分", v: "score" }, { n: "年份", v: "year" }] }
  ],
  "综艺": [
    { key: "class", name: "类型", value: [{ n: "全部", v: "" }, { n: "真人秀", v: "真人秀" }, { n: "音乐", v: "音乐" }, { n: "脱口秀", v: "脱口秀" }, { n: "歌舞", v: "歌舞" }, { n: "爱情", v: "爱情" }] },
    { key: "area", name: "地区", value: [{ n: "全部", v: "" }, { n: "大陆", v: "大陆" }, { n: "香港", v: "香港" }, { n: "台湾", v: "台湾" }, { n: "美国", v: "美国" }, { n: "日本", v: "日本" }, { n: "韩国", v: "韩国" }] },
    { key: "year", name: "年份", value: [{ n: "全部", v: "" }, { n: "2026", v: "2026" }, { n: "2025", v: "2025" }, { n: "2024", v: "2024" }, { n: "2023", v: "2023" }, { n: "2022", v: "2022" }, { n: "2021", v: "2021" }, { n: "2020", v: "2020" }, { n: "2019", v: "2019" }, { n: "2018", v: "2018" }, { n: "2017", v: "2017" }, { n: "2016", v: "2016" }, { n: "2015", v: "2015" }, { n: "2014", v: "2014" }, { n: "2013", v: "2013" }, { n: "2012", v: "2012" }, { n: "2011", v: "2011" }, { n: "更早", v: "更早" }] },
    { key: "sort", name: "排序", value: [{ n: "人气", v: "hits" }, { n: "最新", v: "time" }, { n: "评分", v: "score" }, { n: "年份", v: "year" }] }
  ]
};

// ==========================================
// 5. 业务接口
// ==========================================

const _home = async () => {
  let resp = await req(sourceConfig.api.host + '/api.php/web/index/home');
  let json = JSON.parse(resp.content);
  let categories = json.data.categories;
  let classes = categories.map(i => ({ 'type_id': i.type_name, 'type_name': i.type_name }));
  let videos = [];
  for (const i of categories) videos.push(...json2vods(i.videos));
  return { class: classes, list: videos, filters: filterConfig };
};

const _category = async ({ id, page, filters }) => {
  let sort = filters.sort || 'hits';
  let url = `${sourceConfig.api.host}/api.php/web/filter/vod?type_name=${encodeURIComponent(id)}&page=${page}&sort=${sort}`;
  if (filters.class) url += `&class=${encodeURIComponent(filters.class)}`;
  if (filters.area) url += `&area=${encodeURIComponent(filters.area)}`;
  if (filters.year) url += `&year=${encodeURIComponent(filters.year)}`;
  let resp = await req(url);
  let json = JSON.parse(resp.content);
  return { list: json2vods(json.data), page: parseInt(page), pagecount: json.pageCount };
};

const _search = async ({ page, wd }) => {
  let url = `${sourceConfig.api.host}/api.php/web/search/index?wd=${encodeURIComponent(wd)}&page=${page}`;
  let resp = await req(url);
  let json = JSON.parse(resp.content);
  return { list: json2vods(json.data), page: parseInt(page), pagecount: json.pageCount };
};

// ==========================================
// 6. 全局缓存（供播放时使用）
// ==========================================

let detailCache = {};
let aggregateCache = {};

// ==========================================
// 7. 详情页（核心：生成新格式URL）
// ==========================================

const _detail = async ({ id }) => {
  const vod_id = id[0];
  log.info(`========== 获取详情: ID[${vod_id}] ==========`);
  
  let [mainResp, aggResp] = await Promise.all([
    req(`${sourceConfig.api.host}/api.php/web/vod/get_detail?vod_id=${vod_id}`),
    req(`${sourceConfig.api.host}/api.php/web/internal/search_aggregate?vod_id=${vod_id}`)
  ]);

  // 缓存数据供播放时使用
  detailCache[vod_id] = JSON.parse(mainResp.content);
  aggregateCache[vod_id] = JSON.parse(aggResp.content);

  let data = detailCache[vod_id].data[0];
  let vodplayer = detailCache[vod_id].vodplayer;
  let aggJson = aggregateCache[vod_id];

  log.info(`[数据源] 主站线路数: ${data.vod_play_from.split('$$$').length}, 聚合线路数: ${aggJson.data ? aggJson.data.length : 0}`);

  const rawLines = [];

  // ========== 处理主站线路 ==========
  log.info('---------- 处理主站线路 ----------');
  let raw_shows = data.vod_play_from.split('$$$');
  let raw_urls_list = data.vod_play_url.split('$$$');

  for (let i = 0; i < raw_shows.length; i++) {
    let show_code = raw_shows[i];  // 原始线路标识，如"JD4K"
    let player = vodplayer.find(p => p.from === show_code);
    if (!player) continue;

    // 关键：使用player.show作为线路名称，如"腾讯"、"爱奇艺"
    let lineName = player.show || show_code;
    let mode = LineManager.getMode(lineName);
    
    log.info(`[主站线路${i}] show_code="${show_code}", lineName="${lineName}", mode="${mode}"`);

    let urls = [];
    let items = raw_urls_list[i].split('#');

    for (let j = 0; j < items.length; j++) {
      if (items[j].includes('$')) {
        let [name, url_val] = items[j].split('$');
        let nid = j + 1;
        
        // 新格式：线路名称@@siteId@@mode@@影片ID@@第几集@@URL
        // 主站线路：siteId=show_code（原始标识）
        urls.push(`${name}$${lineName}@@${show_code}@@${mode}@@${vod_id}@@${nid}@@${url_val}`);
      }
    }
    
    if (urls.length > 0) {
      rawLines.push({
        lineName: lineName,      // 线路名称，作为判断依据
        siteId: show_code,        // 原始线路标识
        name: player.show || show_code,
        urls: urls.join('#'),
        mode: mode
      });
    }
  }

  // ========== 处理聚合线路 ==========
  if (aggJson.data) {
    log.info('---------- 处理聚合线路 ----------');
    
    aggJson.data.forEach((item, idx) => {
      // 聚合线路：使用site_name作为lineName，site_key作为siteId
      let lineName = item.site_name;  // 如"腾讯"、"爱奇艺"
      let siteKey = item.site_key;     // 如"site_1769395953671_qq"
      
      // 关键修复：以lineName作为判断依据获取mode，而不是固定360parse
      let mode = LineManager.getMode(lineName);
      
      // 如果没找到配置（mode 为 direct），但又是聚合数据，则默认使用直连
      if (mode === 'direct' && !LineManager.getConfig(lineName)) {
        // 这里不再切换到 360parse，而是保持直连（direct）
        mode = 'direct';                     // 可选：显式写一次，增强可读性
        log.info(`[聚合线路${idx}] lineName="${lineName}" 未找到配置，默认使用直连 (direct)`);
      } else {
        log.info(`[聚合线路${idx}] lineName="${lineName}", siteKey="${siteKey}", mode="${mode}"`);
      }

      let urls = [];
      let items = item.vod_play_url.replace(/\t/g, '').split('#');

      for (let j = 0; j < items.length; j++) {
        if (items[j].includes('$')) {
          let [name, url_val] = items[j].split('$');
          
          // 新格式：线路名称@@siteId@@mode@@影片ID@@第几集@@URL
          urls.push(`${name}$${lineName}@@${siteKey}@@${mode}@@${vod_id}@@${j + 1}@@${url_val}`);
        }
      }
      
      if (urls.length > 0) {
        rawLines.push({
          lineName: lineName,
          siteId: siteKey,
          name: item.site_name,
          urls: urls.join('#'),
          mode: mode
        });
      }
    });
  }

  // ========== 处理线路 ==========
  const processed = LineManager.processLines(rawLines);
  if (processed.length === 0) return { list: [] };

  // ========== 构建最终线路 ==========
  const finalLines = [];
  
  processed.forEach(line => {
    const baseUrls = line.urls;
    const mode = line.mode;
    const lineName = line.lineName;

    // direct/360parse/qqqparse：直接输出
    if (mode === 'direct' || mode === '360parse' || mode === 'qqqparse') {
      finalLines.push({
        displayName: line.displayName,
        urls: baseUrls
      });
      return;
    }

    // auto模式：生成自动/默认/手动线路
    if (mode === 'auto') {
      // 1. 自动
      finalLines.push({
        displayName: `${line.displayName}·自动`,
        urls: baseUrls
      });

      // 2. 默认（转为qqqparse模式）
      finalLines.push({
        displayName: `${line.displayName}·默认`,
        urls: baseUrls.replace(/@@auto@@/g, '@@qqqparse@@')
      });

      // 3. 手动解析器
      if (sourceConfig.showManualLines && line.parserPriority.length > 0) {
        line.parserPriority.forEach(pName => {
          finalLines.push({
            displayName: `${line.displayName}·${pName}`,
            urls: baseUrls.replace(/@@auto@@/g, `@@auto@${pName}@@`)
          });
        });
      }
    }
  });

  log.info(`最终线路: ${finalLines.map(l => l.displayName).join(' > ')}`);

  return {
    list: [{
      ...data,
      vod_play_from: finalLines.map(l => l.displayName).join('$$$'),
      vod_play_url: finalLines.map(l => l.urls).join('$$$'),
      vod_content: data.vod_blurb
    }]
  };
};

// ==========================================
// 8. 播放解析（核心：以lineName为判断依据）
// ==========================================

const _play = async ({ id, app }) => {
  log.info(`========== 播放处理 ==========`);
  log.info(`播放ID: ${id}`);

  // 格式：线路名称@@siteId@@mode@@影片ID@@第几集@@URL
  // mode可能是：direct/360parse/qqqparse/auto/auto@解析器名
  const parts = id.split('@@');
  if (parts.length < 6) {
    log.error(`格式错误，parts长度=${parts.length}，期望6`);
    return { parse: 0, url: parts[parts.length - 1] || '' };
  }

  const lineName = parts[0];
  const siteId = parts[1];
  const mode = parts[2];
  const mediaId = parts[3];
  const nid = parts[4];
  const rawUrl = parts[5];

  log.info(`解析 -> lineName="${lineName}", siteId="${siteId}", mode="${mode}"`);
  log.info(`       mediaId=${mediaId}, nid=${nid}`);

  // ========== direct：直接播放 ==========
  if (mode === 'direct') {
    log.info(`[处理] direct模式 -> 直接播放 parse:0,url:${rawUrl}`);
    return { parse: 0, url: rawUrl };
  }

  // ========== 360parse：聚合数据Web嗅探 ==========
  if (mode === '360parse') {
    const finalUrl = `https://qqqys.com/play/${mediaId}#sid=${siteId}&nid=${nid}`;
    log.info(`[处理] 360parse模式 -> Web嗅探 parse:1,url:${finalUrl}`);
    return { parse: 1, url: finalUrl, header: { 'User-Agent': 'Mozilla/5.0' } };
  }

  // ========== qqqparse：主站数据Web嗅探 ==========
  if (mode === 'qqqparse') {
    const finalUrl = `https://qqqys.com/play/${mediaId}#sid=${siteId}&nid=${nid}`;
    log.info(`[处理] qqqparse模式 -> Web嗅探 parse:1,url:${finalUrl}`);
    return { parse: 1, url: finalUrl, header: { 'User-Agent': 'Mozilla/5.0' } };
  }

  // ========== auto@解析器名：指定解析器（必须先于auto判断）==========
  if (mode.startsWith('auto@')) {
    const parserName = mode.substring(5);  // 去掉"auto@"
    log.info(`[处理] 指定解析器模式: ${parserName}`);
    
    const funcName = sourceConfig.parsers[parserName];
    log.info(`[指定] 查找: ${parserName} -> funcName=${funcName || '未找到'}`);
    
    if (funcName && app && app[funcName]) {
      try {
        log.info(`[指定] 调用 ${parserName}...`);
        const res = await app[funcName]({ flag: lineName, id: rawUrl });
        
        if (res?.url) {
          log.info(`[指定] ✅ 成功 [${parserName}],url:${res.url}`);
          return { parse: 0, url: res.url, header: { 'User-Agent': 'Mozilla/5.0' } };
        } else {
          log.info(`[指定] ❌ ${parserName} 返回无效URL`);
        }
      } catch (e) {
        log.error(`[指定] ${parserName} 异常: ${e.message}`);
      }
    } else {
      log.error(`[指定] 未找到解析器函数: ${funcName}`);
    }
    
    // 失败回退到qqqparse
    const finalUrl = `https://qqqys.com/play/${mediaId}#sid=${siteId}&nid=${nid}`;
    log.info(`[指定] 失败,回退到qqqparse,url:${finalUrl}`);
    return { parse: 1, url: finalUrl, header: { 'User-Agent': 'Mozilla/5.0' } };
  }

  // ========== auto：自动调用解析器 ==========
  if (mode === 'auto') {
    log.info(`[处理] auto模式 -> 以lineName="${lineName}"获取解析器`);
    
    const parsers = LineManager.getParsers(lineName, app);
    log.info(`[auto] 找到${parsers.length}个解析器: ${parsers.map(p => p.label).join(', ') || '无'}`);

    for (const parser of parsers) {
      try {
        log.info(`[auto] 尝试: ${parser.label}`);
        const res = await parser.func({ flag: lineName, id: rawUrl });
        
        if (res?.url) {
          log.info(`[auto] ✅ 成功 [${parser.label}],url:${res.url}`);
          return { parse: 0, url: res.url, header: { 'User-Agent': 'Mozilla/5.0' } };
        }
      } catch (e) {
        log.error(`[auto] ${parser.label} 异常: ${e.message}`);
      }
    }
    
    log.info('[auto] 所有解析器失败，回退到qqqparse');
    const finalUrl = `https://qqqys.com/play/${mediaId}#sid=${siteId}&nid=${nid}`;
    return { parse: 1, url: finalUrl, header: { 'User-Agent': 'Mozilla/5.0' } };
  }

  // 未知mode
  log.info(`[处理] 未知mode[${mode}]，默认direct,url:${finalUrl}`);
  return { parse: 0, url: rawUrl };
};
// ==========================================
// 9. 模块导出
// ==========================================

const meta = {
  key: "qqqys",
  name: "3Q影视",
  type: 4,
  api: "/video/qqqys",
  searchable: 1,
  quickSearch: 1,
  changeable: 1,
  filterable: 1
};

module.exports = async (app, opt) => {
  log = {
    info: (msg, ...args) => app.log.info(`[3Q影视] ${msg}`, ...args),
    error: (msg, err) => app.log.error(`[3Q影视] ${msg} ${err?.message || err}`),
    debug: (msg, ...args) => app.log.debug(`[3Q影视] ${msg}`, ...args)
  };
  
  log.info('3Q影视初始化完成');
  log.info(`配置线路: ${Object.keys(sourceConfig.lines).join(', ')}`);
  
  app.get(meta.api, async (req_fastify, reply) => {
    const { ac, t, pg, wd, play, ids, ext } = req_fastify.query;
    
    let filters = {};
    if (ext) {
      try {
        filters = JSON.parse(CryptoJS.enc.Base64.parse(ext).toString(CryptoJS.enc.Utf8));
      } catch (e) {}
    }
    
    if (play) return await _play({ id: play, app });
    if (wd) return await _search({ wd, page: pg || "1" });
    if (ac === "detail") {
      if (t) return await _category({ id: t, page: pg || "1", filters });
      if (ids) return await _detail({ id: ids.split(",") });
    }
    return await _home();
  });
  
  opt.sites.push(meta);
};