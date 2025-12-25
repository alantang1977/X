const aggConfig = {
  headers: {
    default: { 'User-Agent': 'okhttp/3.12.11', 'content-type': 'application/json; charset=utf-8' },
    niuniu: { 'Cache-Control': 'no-cache', 'Content-Type': 'application/json;charset=UTF-8', 'User-Agent': 'okhttp/4.12.0' }
  },
  platform: {
    百度: { host: 'https://api.jkyai.top', url1: '/API/bddjss.php?name=fyclass&page=fypage', url2: '/API/bddjss.php?id=fyid', search: '/API/bddjss.php?name=**&page=fypage' },
    甜圈: { host: 'https://mov.cenguigui.cn', url1: '/duanju/api.php?classname', url2: '/duanju/api.php?book_id', search: '/duanju/api.php?name' },
    锦鲤: { host: 'https://api.jinlidj.com', search: '/api/search', url2: '/api/detail' },
    番茄: { host: 'https://reading.snssdk.com', url1: '/reading/bookapi/bookmall/cell/change/v', url2: 'https://fqgo.52dns.cc/catalog', search: 'https://fqgo.52dns.cc/search' },
    星芽: { host: 'https://app.whjzjx.cn', url1: '/cloud/v2/theater/home_page?theater_class_id', url2: '/v2/theater_parent/detail', search: '/v3/search', loginUrl: 'https://u.shytkjgs.com/user/v1/account/login' },
    西饭: { host: 'https://xifan-api-cn.youlishipin.com', url1: '/xifan/drama/portalPage', url2: '/xifan/drama/getDuanjuInfo', search: '/xifan/search/getSearchList' },
    围观: { host: 'https://api.drama.9ddm.com', url1: '/drama/home/shortVideoTags', url2: '/drama/home/shortVideoDetail', search: '/drama/home/search' },
    碎片: { host: 'https://free-api.bighotwind.cc', url1: '/papaya/papaya-api/theater/tags', url2: '/papaya/papaya-api/videos/info', search: '/papaya/papaya-api/videos/page' }
  },
  platformList: [
    { name: '甜圈短剧', id: '甜圈' }, { name: '锦鲤短剧', id: '锦鲤' }, { name: '番茄短剧', id: '番茄' },
    { name: '星芽短剧', id: '星芽' }, { name: '西饭短剧', id: '西饭' }, { name: '百度短剧', id: '百度' },
    { name: '围观短剧', id: '围观' }, { name: '碎片剧场', id: '碎片' }
  ],
  search: { limit: 30, timeout: 6000 }
};

const ruleFilterDef = {
  百度: { area: '逆袭' }, 甜圈: { area: '推荐榜' }, 锦鲤: { area: '' }, 番茄: { area: 'videoseries_hot' },
  星芽: { area: '1' }, 西饭: { area: '' }, 围观: { area: '' }, 碎片: { area: '' }
};

let xingyaToken = '';
let suipianToken = '';

function getRandomItem(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

function guid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

function base64Decode(str) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  let output = '';
  str = str.replace(/=+$/, '');
  for (let i = 0; i < str.length; i += 4) {
    const [e1, e2, e3, e4] = [str[i], str[i + 1], str[i + 2], str[i + 3]].map(c => chars.indexOf(c));
    const chr1 = (e1 << 2) | (e2 >> 4);
    const chr2 = ((e2 & 15) << 4) | (e3 >> 2);
    const chr3 = ((e3 & 3) << 6) | e4;
    output += String.fromCharCode(chr1);
    if (e3 !== -1) output += String.fromCharCode(chr2);
    if (e4 !== -1) output += String.fromCharCode(chr3);
  }
  return output;
}

function safeParse(res) {
  if (!res) return null;
  if (typeof res === 'string') return JSON.parse(res);
  if (typeof res === 'object') {
    const content = res.content || res.body || (typeof res.data === 'string' ? res.data : null);
    return content ? JSON.parse(content) : res;
  }
  return null;
}

function getHeaders(platId) {
  if (platId === '星芽' && xingyaToken) return { ...aggConfig.headers.default, authorization: xingyaToken };
  if (platId === '碎片' && suipianToken) return { ...aggConfig.headers.default, Authorization: suipianToken };
  return aggConfig.headers.default;
}

async function init() {
  try {
    const res = await req(aggConfig.platform.星芽.loginUrl, {
      method: 'POST',
      headers: { 'User-Agent': 'okhttp/4.10.0', platform: '1', 'Content-Type': 'application/json' },
      body: JSON.stringify({ device: '24250683a3bdb3f118dff25ba4b1cba1a' })
    });
    const data = safeParse(res);
    xingyaToken = data?.data?.token || data?.token || '';
  } catch (e) { /* ignore */ }
  return true;
}

async function ensureSuipianToken() {
  if (suipianToken) return;
  try {
    const openId = guid();
    const res = await req('https://free-api.bighotwind.cc/papaya/papaya-api/oauth2/uuid', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ openId })
    });
    const data = safeParse(res);
    suipianToken = data?.data?.token || '';
  } catch (e) { suipianToken = ''; }
}

async function home() {
  return JSON.stringify({ class: aggConfig.platformList.map(p => ({ type_name: p.name, type_id: p.id })) });
}
async function homeVod() { return await recommend(); }

async function recommend() {
  const randomPlat = getRandomItem(aggConfig.platformList);
  const platId = randomPlat.id;
  const area = ruleFilterDef[platId]?.area || '';
  const videos = await fetchList(platId, area, 1, 10);
  return JSON.stringify({ list: videos.slice(0, 10) });
}

// Category & Search common fetch
async function fetchList(platId, area, page, pageSize = 24) {
  const plat = aggConfig.platform[platId];
  if (!plat) return [];

  if (platId === '星芽' && !xingyaToken) await init();
  if (platId === '碎片') await ensureSuipianToken();

  try {
    let data = [];
    const headers = getHeaders(platId);
    const host = plat.host;

    switch (platId) {
      case '百度': {
        const res = await req(`${host}${plat.url1.replace('fyclass', area).replace('fypage', page)}`, { headers });
        const d = safeParse(res)?.data || [];
        data = d.map(i => ({ vod_id: `百度@${i.id}`, vod_name: i.title, vod_pic: i.cover, vod_remarks: `更新至${i.totalChapterNum}集` }));
        break;
      }
      case '甜圈': {
        const res = await req(`${host}${plat.url1}=${area}&offset=${page}`, { headers });
        const d = safeParse(res)?.data || [];
        data = d.map(i => ({ vod_id: `甜圈@${i.book_id}`, vod_name: i.title, vod_pic: i.cover, vod_remarks: i.copyright || '' }));
        break;
      }
      case '锦鲤': {
        const res = await req(`${host}${plat.search}`, { method: 'POST', body: JSON.stringify({ page, limit: pageSize, type_id: area, keyword: '' }) });
        const d = safeParse(res)?.data?.list || [];
        data = d.map(i => ({ vod_id: `锦鲤@${i.vod_id}`, vod_name: i.vod_name, vod_pic: i.vod_pic, vod_remarks: `${i.vod_total}集` }));
        break;
      }
      case '番茄': {
        const sessionId = new Date().toISOString().slice(0, 16).replace(/-|T:/g, '');
        const url = `${host}${plat.url1}?change_type=0&selected_items=${area}&tab_type=8&cell_id=6952850996422770718&version_tag=video_feed_refactor&device_id=1423244030195267&aid=1967&app_name=novelapp&ssmix=a&session_id=${sessionId}${page > 1 ? `&offset=${(page - 1) * 12}` : ''}`;
        const res = await req(url, { headers });
        const d = safeParse(res);
        const items = d?.data?.cell_view?.cell_data || (Array.isArray(d?.data) ? d.data : []);
        data = items.map(i => {
          const v = i.video_data?.[0] || i;
          return { vod_id: `番茄@${v.series_id || v.book_id || ''}`, vod_name: v.title, vod_pic: v.cover || v.horiz_cover, vod_remarks: v.sub_title || '' };
        });
        break;
      }
      case '星芽': {
        const res = await req(`${host}${plat.url1}=${area}&type=1&class2_ids=0&page_num=${page}&page_size=${pageSize}`, { headers });
        const d = safeParse(res)?.data?.list || [];
        data = d.map(i => ({ vod_id: `星芽@${host}${plat.url2}?theater_parent_id=${i.theater.id}`, vod_name: i.theater.title, vod_pic: i.theater.cover_url, vod_remarks: `${i.theater.total}集` }));
        break;
      }
      case '西饭': {
        const [typeId] = area.split('@');
        const url = `${host}${plat.url1}?reqType=aggregationPage&offset=${(page - 1) * 30}&categoryId=${typeId}`;
        const res = await req(url, { headers });
        const elements = safeParse(res)?.result?.elements || [];
        elements.forEach(s => (s.contents || []).forEach(v => {
          const d = v.duanjuVo;
          data.push({ vod_id: `西饭@${d.duanjuId}#${d.source}`, vod_name: d.title, vod_pic: d.coverImageUrl, vod_remarks: `${d.total}集` });
        }));
        break;
      }
      case '围观': {
        const res = await req(`${host}${plat.search}`, {
          method: 'POST', headers,
          body: JSON.stringify({ audience: "全部受众", page, pageSize, searchWord: "", subject: "全部主题" })
        });
        const d = safeParse(res)?.data || [];
        data = d.map(i => ({ vod_id: `围观@${i.oneId}`, vod_name: i.title, vod_pic: i.vertPoster, vod_remarks: `集数:${i.episodeCount} 播放:${i.viewCount}` }));
        break;
      }
      case '碎片': {
        const res = await req(`${host}${plat.search}?type=5&tagId=&pageNum=${page}&pageSize=${pageSize}`, { headers });
        const d = safeParse(res)?.list || [];
        data = d.map(i => {
          const id = `${i.itemId}@${i.videoCode}`;
          const pic = `https://speed.hiknz.com/papaya/papaya-file/files/download/${i.imageKey}/${i.imageName}`;
          return { vod_id: `碎片@${id}`, vod_name: i.title, vod_pic: pic, vod_remarks: `集数:${i.episodesMax} 播放:${i.hitShowNum}` };
        });
        break;
      }
    }
    return data;
  } catch { return []; }
}

async function category(tid, pg, filter, extend) {
  const page = parseInt(pg) || 1;
  const area = filter?.area || ruleFilterDef[tid]?.area || '';
  const videos = await fetchList(tid, area, page);
  return JSON.stringify({
    list: videos,
    page,
    pagecount: page + 1,
    limit: videos.length,
    total: videos.length * (page + 1)
  });
}

async function detail(id) {
  const [platId, ...rest] = id.split('@');
  const did = rest.join('@');
  const plat = aggConfig.platform[platId];
  if (!plat) return JSON.stringify({ list: [{ vod_id: id, vod_name: '平台不支持', vod_play_url: '' }] });

  if (platId === '星芽' && !xingyaToken) await init();
  if (platId === '碎片') await ensureSuipianToken();

  try {
    let vod = { vod_id: id, vod_name: '未知', vod_pic: '', vod_remarks: '', vod_content: '', vod_play_from: '', vod_play_url: '' };
    const headers = getHeaders(platId);

    switch (platId) {
      case '百度': {
        const res = safeParse(await req(`${plat.host}${plat.url2.replace('fyid', did)}`, { headers }));
        if (res) vod = { ...vod, vod_name: res.title, vod_pic: res.data?.[0]?.cover, vod_remarks: `更新至:${res.total || 0}集`, vod_play_from: '百度短剧', vod_play_url: (res.data || []).map(i => `${i.title}$${i.video_id}`).join('#') };
        break;
      }
      case '甜圈': {
        const res = safeParse(await req(`${plat.host}${plat.url2}=${did}`, { headers }));
        if (res) vod = { ...vod, vod_name: res.book_name || res.title, vod_pic: res.book_pic || res.cover, vod_remarks: `更新时间:${res.time}`, vod_content: res.desc, vod_play_from: '甜圈短剧', vod_play_url: (res.data || []).map(i => `${i.title || '第1集'}$${i.video_id || i.id}`).join('#') };
        break;
      }
      case '锦鲤': {
        const res = safeParse(await req(`${plat.host}${plat.url2}/${did}`, { headers }));
        if (res?.data) {
          const list = res.data;
          const urls = list.player ? Object.keys(list.player).map(k => `${k}$${list.player[k]}`) : [];
          vod = { ...vod, vod_name: list.vod_name, vod_pic: list.vod_pic, vod_remarks: list.vod_remarks, vod_play_from: '锦鲤短剧', vod_play_url: urls.join('#') };
        }
        break;
      }
      case '番茄': {
        const res = safeParse(await req(`${plat.url2}?book_id=${did}`, { headers }));
        if (res?.data) {
          const b = res.data.book_info;
          const u = (res.data.item_data_list || []).map(i => `${i.title}$${i.item_id}`).join('#');
          vod = { ...vod, vod_name: b.book_name, vod_pic: b.thumb_url, vod_remarks: `更新至${res.data.item_data_list?.length}集`, vod_play_from: '番茄短剧', vod_play_url: u };
        }
        break;
      }
      case '星芽': {
        const res = safeParse(await req(did, { headers }));
        if (res?.data) {
          const d = res.data;
          const u = (d.theaters || []).map(i => `${i.num}$${i.son_video_url}`).join('#');
          vod = { ...vod, vod_name: d.title, vod_pic: d.cover_url, vod_remarks: d.desc_tags + '', vod_play_from: '星芽短剧', vod_play_url: u };
        }
        break;
      }
      case '西饭': {
        const [duanjuId, source] = did.split('#');
        const url = `${plat.host}${plat.url2}?duanjuId=${duanjuId}&source=${source}`;
        const res = safeParse(await req(url, { headers }));
        if (res?.result) {
          const d = res.result;
          const u = (d.episodeList || []).map(e => `${e.index}$${e.playUrl}`).join('#');
          vod = { ...vod, vod_name: d.title, vod_pic: d.coverImageUrl, vod_remarks: d.updateStatus === 'over' ? `${d.total}集 已完结` : `更新${d.total}集`, vod_play_from: '西饭短剧', vod_play_url: u };
        }
        break;
      }
      case '围观': {
        const res = safeParse(await req(`${plat.host}${plat.url2}?oneId=${did}&page=1&pageSize=1000`, { headers }));
        if (res?.data?.length) {
          const d = res.data;
          vod = { ...vod, vod_name: d[0].title, vod_pic: d[0].vertPoster, vod_remarks: `共${d.length}集`, vod_play_from: '围观短剧', vod_play_url: d.map(e => `${e.title}第${e.playOrder}集$${e.playSetting}`).join('#') };
        }
        break;
      }
      case '碎片': {
        const [itemId, videoCode] = did.split('@');
        const res = safeParse(await req(`${plat.host}${plat.url2}?videoCode=${videoCode}&itemId=${itemId}`, { headers }));
        if (res) {
          const d = res.data || res;
          const pic = `https://speed.hiknz.com/papaya/papaya-file/files/download/${d.imageKey}/${d.imageName}`;
          const u = (d.episodesList || []).map(e => {
            const best = e.resolutionList?.sort((a, b) => b.resolution - a.resolution)[0];
            return best ? `第${e.episodes}集$https://speed.hiknz.com/papaya/papaya-file/files/download/${best.fileKey}/${best.fileName}` : null;
          }).filter(Boolean).join('#');
          vod = { ...vod, vod_name: d.title, vod_pic: pic, vod_remarks: `共${d.episodesMax || 0}集`, vod_play_from: '碎片剧场', vod_play_url: u };
        }
        break;
      }
    }
    return JSON.stringify({ list: [vod] });
  } catch {
    return JSON.stringify({ list: [{ vod_id: id, vod_name: '加载失败', vod_play_url: '' }] });
  }
}

async function play(flag, id) {
  const input = id;
  const defaultRes = () => JSON.stringify({ parse: 0, url: input });

  if (/百度/.test(flag)) {
    const res = safeParse(await req(`https://api.jkyai.top/API/bddjss.php?video_id=${input}`));
    if (res?.data?.qualities) {
      const order = ["1080p", "sc", "sd"];
      const qMap = { "1080p": "蓝光", "sc": "超清", "sd": "标清" };
      const urls = [];
      order.forEach(k => {
        const q = res.data.qualities.find(x => x.quality === k);
        if (q) urls.push(qMap[k], q.download_url);
      });
      return JSON.stringify({ parse: 0, url: urls });
    }
  }

  if (/甜圈/.test(flag)) {
    return JSON.stringify({ parse: 0, url: `https://mov.cenguigui.cn/duanju/api.php?video_id=${input}&type=mp4` });
  }

  if (/锦鲤/.test(flag)) {
    try {
      const html = await req(`${input}&auto=1`, { headers: { referer: 'https://www.jinlidj.com/' } });
      const str = typeof html === 'string' ? html : html.content || html.body || '{}';
      const match = str.match(/let data\s*=\s*({[^;]*});/);
      if (match) {
        const data = JSON.parse(match[1]);
        if (data.url) return JSON.stringify({ parse: 0, url: data.url });
      }
    } catch {}
  }

  if (/番茄/.test(flag)) {
    try {
      const res = safeParse(await req(`https://fqgo.52dns.cc/video?item_ids=${input}`));
      if (res?.data?.[input]?.video_model) {
        const model = JSON.parse(res.data[input].video_model);
        const mainUrl = model?.video_list?.video_1?.main_url;
        if (mainUrl) return JSON.stringify({ parse: 0, url: base64Decode(mainUrl) });
      }
    } catch { /* ignore */ }
  }

  if (/围观/.test(flag)) {
    try {
      const ps = typeof input === 'string' ? JSON.parse(input) : input;
      const urls = [];
      if (ps?.super) urls.push("超清", ps.super);
      if (ps?.high) urls.push("高清", ps.high);
      if (ps?.normal) urls.push("流畅", ps.normal);
      return JSON.stringify({ parse: 0, url: urls });
    } catch { return defaultRes(); }
  }

  return defaultRes();
}

async function search(wd, quick, pg) {
  const page = parseInt(pg) || 1;
  const timeout = aggConfig.search.timeout;
  const limit = aggConfig.search.limit;

  const promises = aggConfig.platformList.map(async p => {
    const plat = aggConfig.platform[p.id];
    try {
      if (p.id === '星芽' && !xingyaToken) await init();
      if (p.id === '碎片') await ensureSuipianToken();

      let res, data;
      const headers = getHeaders(p.id);
      const host = plat.host;

      switch (p.id) {
        case '百度':
          res = await req(`${host}${plat.search.replace('**', encodeURIComponent(wd)).replace('fypage', page)}`, { headers, timeout });
          data = (safeParse(res)?.data || []).map(i => ({ vod_id: `百度@${i.id}`, vod_name: i.title, vod_pic: i.cover, vod_remarks: `百度短剧｜更新至${i.totalChapterNum}集` }));
          break;
        case '甜圈':
          res = await req(`${host}${plat.search}=${encodeURIComponent(wd)}&offset=${page}`, { headers, timeout });
          data = (safeParse(res)?.data || []).map(i => ({ vod_id: `甜圈@${i.book_id}`, vod_name: i.title, vod_pic: i.cover, vod_remarks: `甜圈短剧｜${i.copyright}` }));
          break;
        case '锦鲤':
          res = await req(host + plat.search, { method: 'POST', body: JSON.stringify({ page, limit, keyword: wd }), timeout });
          data = (safeParse(res)?.data?.list || []).map(i => ({ vod_id: `锦鲤@${i.vod_id}`, vod_name: i.vod_name, vod_pic: i.vod_pic, vod_remarks: `锦鲤短剧｜${i.vod_total}集` }));
          break;
        case '番茄':
          res = await req(`${plat.search}?keyword=${encodeURIComponent(wd)}&page=${page}`, { headers, timeout });
          data = (safeParse(res)?.data || []).map(i => ({ vod_id: `番茄@${i.series_id}`, vod_name: i.title, vod_pic: i.cover, vod_remarks: `番茄短剧｜${i.sub_title}` }));
          break;
        case '星芽':
          res = await req(host + plat.search, { method: 'POST', headers, body: JSON.stringify({ text: wd }), timeout });
          data = (safeParse(res)?.data?.theater?.search_data || []).map(i => ({ vod_id: `星芽@${host}${plat.url2}?theater_parent_id=${i.id}`, vod_name: i.title, vod_pic: i.cover_url, vod_remarks: `星芽短剧｜${i.total}集 播放:${i.play_amount_str}` }));
          break;
        case '碎片':
          res = await req(`${host}${plat.search}?type=5&tagId=&pageNum=${page}&pageSize=${limit}&title=${encodeURIComponent(wd)}`, { headers, timeout });
          data = (safeParse(res)?.list || []).map(i => {
            const id = `${i.itemId}@${i.videoCode}`;
            const pic = `https://speed.hiknz.com/papaya/papaya-file/files/download/${i.imageKey}/${i.imageName}`;
            return { vod_id: `碎片@${id}`, vod_name: i.title, vod_pic: pic, vod_remarks: `碎片剧场｜集数:${i.episodesMax} 播放:${i.hitShowNum}` };
          });
          break;
        default:
          return [];
      }
      return data.filter(v => v.vod_name?.toLowerCase().includes(wd.toLowerCase()));
    } catch { return []; }
  });

  const results = (await Promise.allSettled(promises))
    .filter(r => r.status === 'fulfilled')
    .flatMap(r => r.value || []);

  return JSON.stringify({
    list: results,
    page,
    pagecount: page + 1,
    limit: results.length,
    total: results.length * (page + 1)
  });
}

export function __jsEvalReturn() {
  return { init, home, homeVod, category, detail, play, proxy: null, search };
}