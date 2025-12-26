import 'assets://js/lib/crypto-js.js';
const { HOSTS, KEY, USER_AGENT } = {
  HOSTS: ["https://hnytxj.com","https://www.hkybqufgh.com","https://www.sizhengxt.com","https://www.sdzhgt.com","https://www.jiabaide.cn","https://m.9zhoukj.com","https://m.cqzuoer.com","https://www.hellosht52bwb.com"],
  KEY: "cb808529bae6b6be45ecfab29a4889bc",
  USER_AGENT: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.6478.61 Safari/537.36"
};
let currentHost = '';
const guid = () => 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
  const r = Math.random() * 16 | 0;
  return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
});
const md5 = s => CryptoJS.MD5(s).toString();
const sha1 = s => CryptoJS.SHA1(s).toString();
const toQueryString = obj => Object.keys(obj).filter(k => obj[k] != null && obj[k] !== '').map(k => `${k}=${obj[k]}`).join('&');
const getHeaders = (params = {}) => {
  const t = Date.now().toString();
  const sign = sha1(md5(toQueryString({ ...params, key: KEY, t })));
  return {
    'User-Agent': USER_AGENT,
    'Accept': 'application/json, text/plain, */*',
    'sign': sign,
    't': t,
    'deviceid': guid()
  };
};

const normalizeFieldName = k => {
  const l = k.toLowerCase();
  if (l.startsWith('vod') && l.length > 3) return 'vod_' + l.slice(3);
  if (l.startsWith('type') && l.length > 4) return 'type_' + l.slice(4);
  return l;
};

const normalizeVodList = list => (list || []).map(item => {
  const res = {};
  for (const [k, v] of Object.entries(item || {})) if (v != null) res[normalizeFieldName(k)] = v;
  return res;
});

async function reqSafe(url, options = {}) {
  try {
    const res = await req(url, options);
    return JSON.parse(res.content);
  } catch (e) {
    return {};
  }
}

async function init() {
  currentHost = HOSTS[Math.floor(Math.random() * HOSTS.length)];
  return true;
}

async function home() {
  const [cRes, fRes] = await Promise.all([
    reqSafe(`${currentHost}/api/mw-movie/anonymous/get/filer/type`, { headers: getHeaders() }),
    reqSafe(`${currentHost}/api/mw-movie/anonymous/v1/get/filer/list`, { headers: getHeaders() })
  ]);

  const classes = (cRes.data || []).map(k => ({ type_name: k.typeName, type_id: k.typeId.toString() }));
  const fData = fRes.data || {};
  const baseSort = [{ n: "最近更新", v: "2" }, { n: "人气高低", v: "3" }, { n: "评分高低", v: "4" }];
  const filters = {};
  for (const [tid, d] of Object.entries(fData)) {
    const sortValues = tid === '1' ? baseSort.slice(1) : baseSort;
    const arr = [
      { key: "type", name: "类型", value: (d.typeList || []).map(i => ({ n: i.itemText, v: i.itemValue })) },
      { key: "area", name: "地区", value: (d.districtList || []).map(i => ({ n: i.itemText, v: i.itemText })) },
      { key: "year", name: "年份", value: (d.yearList || []).map(i => ({ n: i.itemText, v: i.itemText })) },
      { key: "lang", name: "语言", value: (d.languageList || []).map(i => ({ n: i.itemText, v: i.itemText })) },
      { key: "sort", name: "排序", value: sortValues }
    ];
    if (d.plotList?.length) arr.splice(1, 0, { key: "v_class", name: "剧情", value: d.plotList.map(i => ({ n: i.itemText, v: i.itemText })) });
    filters[tid] = arr;
  }
  return JSON.stringify({ class: classes, filters });
}

async function homeVod() {
  const [r1, r2] = await Promise.all([
    reqSafe(`${currentHost}/api/mw-movie/anonymous/v1/home/all/list`, { headers: getHeaders() }),
    reqSafe(`${currentHost}/api/mw-movie/anonymous/home/hotSearch`, { headers: getHeaders() })
  ]);
  let list = [];
  const data1 = r1.data || {};
  for (const k in data1) if (data1[k]?.list) list.push(...data1[k].list);
  if (Array.isArray(r2.data)) list.push(...r2.data);
  return JSON.stringify({ list: normalizeVodList(list) });
}

async function category(tid, pg, _, ext = {}) {
  const params = {
    area: ext.area || '',
    filterStatus: "1",
    lang: ext.lang || '',
    pageNum: pg,
    pageSize: "30",
    sort: ext.sort || '1',
    sortBy: "1",
    type: ext.type || '',
    type1: tid,
    v_class: ext.v_class || '',
    year: ext.year || ''
  };

  const url = `${currentHost}/api/mw-movie/anonymous/video/list?${toQueryString(params)}`;
  const res = await reqSafe(url, { headers: getHeaders(params) });
  const vodList = normalizeVodList(res.data?.list || []);
  return JSON.stringify({
    list: vodList,
    page: +pg,
    pagecount: 9999,
    limit: 90,
    total: 999999
  });
}

async function detail(id) {
  const res = await reqSafe(`${currentHost}/api/mw-movie/anonymous/video/detail?id=${id}`, {
    headers: getHeaders({ id })
  });
  const vod = normalizeVodList([res.data])[0];
  if (!vod) {
    return JSON.stringify({ list: [{ vod_id: id, vod_name: '加载失败', vod_play_url: '' }] });
  }

  vod.vod_play_from = '金牌影院';
  if (vod.episodelist?.length) {
    const name = vod.episodelist.length > 1 ? vod.episodelist[0].name : vod.vod_name;
    vod.vod_play_url = vod.episodelist.map(ep => `${name}$${id}@@${ep.nid}`).join('#');
    delete vod.episodelist;
  }
  return JSON.stringify({ list: [vod] });
}

async function play(_, id) {
  const [vid, nid] = id.split('@@');
  const url = `${currentHost}/api/mw-movie/anonymous/v2/video/episode/url?clientType=1&id=${vid}&nid=${nid}`;
  const res = await reqSafe(url, { headers: getHeaders({ clientType: '1', id: vid, nid: nid }) });
  const urls = [];
  for (const item of res.data?.list || []) {
    urls.push(item.resolutionName, item.url);
  }
  return JSON.stringify({
    parse: 0,
    url: urls,
    header: {
      'User-Agent': USER_AGENT,
      'sec-ch-ua-platform': '"Windows"',
      'DNT': '1',
      'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
      'sec-ch-ua-mobile': '?0',
      'Origin': currentHost,
      'Referer': currentHost + '/'
    }
  });
}

async function search(wd, _, pg = "1") {
  const params = { keyword: wd, pageNum: pg, pageSize: "8", sourceCode: "1" };
  const url = `${currentHost}/api/mw-movie/anonymous/video/searchByWord?${toQueryString(params)}`;
  const res = await reqSafe(url, { headers: getHeaders(params) });
  const list = normalizeVodList(res.data?.result?.list || []);
  return JSON.stringify({ list, page: +pg });
}

export function __jsEvalReturn() {
  return { init, home, homeVod, category, detail, play, proxy: null, search };
}
