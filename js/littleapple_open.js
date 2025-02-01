import { Crypto, Uri, _ } from 'assets://js/lib/cat.js';

let key = 'littleapple';
let HOST = ''
let siteKey = '';
let siteType = 0;

const APP_VER = '1.3.3';
const FULL_VER = 'XPGBOX com.phoenix.tv' + APP_VER;
const UA = 'okhttp/3.12.11';
let SIGN;
let TOKEN;
let TOKEN2;

async function request(reqUrl, method, data) {
    const res = await req(reqUrl, {
        method: method || 'get',
        headers: getHeaders(),
        data: data,
        postType: method === 'post' ? 'form' : '',
    });
    return res.content;
}

function getHeaders() {
    if (!SIGN || !TOKEN || !TOKEN2) {
        SIGN = generateSignContent();
        TOKEN = generateToken(SIGN);
        TOKEN2 = generateToken('eT/G/wE7YQpBbk02LN1uGw8s2cOPPAj9jVVkjWjY6BQ=');
    }
    const timestamp = Math.floor(new Date().getTime() / 1000).toString();
    const hash = getHash(SIGN, timestamp);
    const headers = {
        'token': TOKEN,
        'token2': TOKEN2,
        'user_id': 'XPGBOX',
        'version': FULL_VER,
        'timestamp': timestamp,
        'hash': hash,
        'screenx': 2331,
        'screeny': 1121,
        'User-Agent': UA,
    };
    return headers;
}

function getHash(signContent, timestamp) {
    const signStr = signContent + FULL_VER + timestamp;
    const md5 = Crypto.MD5(signStr).toString();
    return md5.substring(8, 12);
}

function generateSignContent() {
    const separator = '||';
    const serial = 'unknown';
    const fingerprint = 'HUAWEI/INE-LX2/HWINE:9/HUAWEIINE-LX2/9.1.0.318C636:user/release-keys';
  
    const strArr = [];
    strArr.push(randStr(16));
    strArr.push(randStr(16));

    const intCount = 6;
    const int8Arr = new Int8Array(intCount);
    for (let i = 0; i < intCount; i++) {
        const random = _.random(0, 127);
        int8Arr[i] = random;
    }
    const byte = int8Arr[0];
    int8Arr[0] = (byte & (byte ^ 1));
    const byteStr = _.map(int8Arr, (value) => value.toString(16).padStart(2, '0')).join('').toUpperCase();
    strArr.push(byteStr);

    strArr.push(randStr(16));
    strArr.push(serial);
    strArr.push(fingerprint);
    return strArr.join(separator);
}

const charStr = 'abacdefghjklmnopqrstuvwxyzABCDEFGHJKLMNOPQRSTUVWXYZ0123456789';
function randStr(len, withNum) {
    var _str = '';
    let containsNum = withNum === undefined ? true : withNum;
    for (var i = 0; i < len; i++) {
        let idx = _.random(0, containsNum ? charStr.length - 1 : charStr.length - 11);
        _str += charStr[idx];
    }
    return _str;
}

function generateToken(text) {
    const data = Crypto.enc.Utf8.parse(text);
    const uint8Array = wordArrayToUint8Array(data);
    const encoded = encodeBytes(uint8Array);
    const words = uint8ArrayToWordArray(encoded);
    return Crypto.enc.Base64.stringify(words);
}

function wordArrayToUint8Array(wordArray) {
    let words = wordArray.words;
    let sigBytes = wordArray.sigBytes;
    let uint8Array = new Uint8Array(sigBytes);
    for (let i = 0; i < sigBytes; i++) {
        let byte = (words[i >>> 2] >>> (24 - (i % 4) * 8)) & 0xff;
        uint8Array[i] = byte;
    }
    return uint8Array;
}

function uint8ArrayToWordArray(uint8Array) {
    let len = uint8Array.length;
    let words = [];
    for (let i = 0; i < len; i++) {
        words[i >>> 2] |= (uint8Array[i] & 0xff) << (24 - (i % 4) * 8);
    }
    return Crypto.lib.WordArray.create(words, len);
}

function encodeBytes(byteArray) {
    let result = null;
    const key = Crypto.enc.Utf8.parse('XPINGGUO');
    const keyBytes = wordArrayToUint8Array(key);
    const table = new Int8Array(333);
    for (let i = 0; i < 333; i++) {
        table[i] = i;
    }
    let index1 = 0;
    let index2 = 0;
    const keyLength = keyBytes.length;
    for (let i = 0; i < 333; i++) {
        let keyByte = keyBytes[index2];
        let tableByte = table[i];
        index1 = ((index1 + (((((keyByte & (keyByte ^ (-256))) - 4) + (tableByte & (tableByte ^ (-256)))) + 4) + 17)) - 17) % 333;
        let temp = table[i];
        table[i] = table[index1];
        table[index1] = temp;
        index2 = (index2 + 1) % keyLength;
    }
    result = table;
    const encryptedData = new Int8Array(byteArray.length);
    index1 = 0;
    index2 = 0;
    for (let i = 0; i < byteArray.length; i++) {
        let pos = (index1 + 1) % 333;
        const tableByte = result[pos];
        index2 = ((tableByte & (tableByte ^ -256)) + index2) % 333;
        const temp = result[pos];
        result[pos] = result[index2];
        result[index2] = temp;
        const b6 = result[pos];
        const b7 = result[index2];
        const b8 = result[(-((-(b6 & (b6 ^ (-256)))) - (b7 & (b7 ^ (-256))))) % 333];
        const inputByte = byteArray[i];
        encryptedData[i] = (b8 & ~inputByte) | (~b8 & inputByte);
        index1 = pos;
    }
    return encryptedData;
}

// cfg = {skey: siteKey, ext: extend}
async function init(cfg) {
    siteKey = cfg.skey;
    siteType = cfg.stype;
    await requestAppHost();
}

async function requestAppHost() {
    const resp = await request('http://194.147.100.39/api.php/v3.user/tokenlogin?version=' + APP_VER + '&os=4', 'post', {});
    try {
        const encrypted = JSON.parse(resp).data;
        const key = Crypto.enc.Utf8.parse('XPINGGUOXPINGGUO');
        const decrypted = Crypto.AES.decrypt(encrypted, key, {
            mode: Crypto.mode.ECB,
            padding: Crypto.pad.Pkcs7
        });
        const json = Crypto.enc.Utf8.stringify(decrypted).substring(8);
        const data = JSON.parse(json);
        const uri = new Uri(data.apiurl);
        uri.setPath('/api.php');
        HOST = uri.toString();
    } catch(e) {
        HOST = 'http://tipu.xjqxz.top/api.php';
    }
}

async function home(filter) {
    const url = HOST + '/v2.vod/androidtypes';
    const homeResult = await request(url);
    const json = JSON.parse(homeResult);
    const filters = {};
    const classes = _.map(json.data, (item) => {
        const filter = getFilters(item);
        filters[item.type_id] = filter;
        return {
            type_id: item.type_id,
            type_name: item.type_name,
        };
    });
    return {
        class: classes,
        filters: filters,
    };
}

function getFilters(data) {
    const filterArray = [];
    const clazz = convertTypeData(data, 'classes', '类型');
    if (clazz) filterArray.push(clazz);
    const area = convertTypeData(data, 'areas', '地区');
    if (area) filterArray.push(area);
    const year = convertTypeData(data, 'years', '年份');
    if (year) filterArray.push(year);
    const by = {
        key: 'by',
        name: '排序',
        init: '',
        value: [
            {'n':'时间','v':'updatetime'},
            {'n':'人气','v':'hits'},
            {'n':'评分','v':'score'},
        ]
    };
    filterArray.push(by);
    return filterArray;
}

function convertTypeData(typeData, typeKey, typeName) {
    if (!typeData || !typeData[typeKey] || _.isEmpty(typeData[typeKey])) {
        return null;
    }
    let valueList = typeData[typeKey];
    const values = _.map(valueList, (item) => {
        return {
            n: item,
            v: item,
        };
    });
    values.unshift({
        n: '全部',
        v: '',
    });
    const typeClass = {
        key: typeKey,
        name: typeName,
        init: '',
        value: values,
    };
    return typeClass;
}

async function homeVod() {
    const url = HOST + '/v2.main/androidhome';
    const homeResult = await request(url);
    const json = JSON.parse(homeResult);
    const filters = {};
    const videos = [];
    videos.push({
        vod_id: json.data.top.id,
        vod_name: json.data.top.name,
        vod_pic: json.data.top.pic,
        vod_remarks: json.data.top.state,
    });
    for (const list of json.data.list) {
        for (const item of list.list) {
            videos.push({
                vod_id: item.id,
                vod_name: item.name,
                vod_pic: item.pic,
                vod_remarks: item.state,
            });
        }
    }
    return {
        list: videos,
    };
}

async function category(tid, pg, filter, extend) {
    const limit = 20;
    const areaPath = extend.areas ? ('&area=' + extend.areas) : '';
    const classPath = extend.classes ? ('&class=' + extend.classes) : '';
    const yearPath = extend.years ? ('&year=' + extend.years) : '';
    const byPath = extend.by ? ('&sortby=' + extend.by) : '';
    const url = HOST + '/v2.vod/androidfilter?page=' + pg + '&type=' + tid + areaPath + yearPath + byPath + classPath;
    const cateResult = await request(url);
    const json = JSON.parse(cateResult);
    const videos = _.map(json.data, (vObj) => {
        return {
            vod_id: vObj.id,
            vod_name: vObj.name,
            vod_pic: vObj.pic,
            vod_remarks: vObj.state,
        };
    });
    const hasMore = !_.isEmpty(videos);
    const page = parseInt(pg);
    const pageCount = hasMore ? page + 1 :page;
    return {
        page: page,
        pagecount: pageCount,
        limit: limit,
        total: pageCount * limit,
        list: videos,
    };
}


async function detail(id) {
    const url = HOST + '/v3.vod/androiddetail2?vod_id=' + id;
    const detailResult = await request(url);
    const content = JSON.parse(detailResult);
    const vObj = content.data;
    const vodAtom = {
        vod_id: id,
        vod_name: vObj.name,
        vod_pic: vObj.pic,
        type_name: vObj.className,
        vod_year: vObj.year,
        vod_area: vObj.area,
        vod_remarks: vObj.state,
        vod_actor: vObj.actor,
        vod_director: vObj.director,
        vod_content: vObj.content,
    }
    const playInfo = vObj.urls;
    const vodItems = _.map(playInfo, (epObj) => {
        const epName = epObj.key;
        const playUrl = epObj.url;
        return epName + '$' + playUrl;
    });
    vodAtom.vod_play_from = '主力源';
    vodAtom.vod_play_url = vodItems.join('#');
    return {
        list: [vodAtom],
    };
}

async function play(flag, id, flags) {
    let playUrl = id;
    if (!playUrl.startsWith('http')) {
        playUrl = 'http://c.xpgtv.net/m3u8/' + id + '.m3u8';
    }
    return {
        parse: 0,
        url: playUrl,
        header: getHeaders(),
    };
}

async function search(wd, quick, pg) {
    const limit = 20;
    const url = HOST + '/v2.vod/androidsearch10086?page=' + pg + '&wd=' + encodeURIComponent(wd);
    const searchResult = await request(url);
    const json = JSON.parse(searchResult);
    const videos = _.map(json.data, (vObj) => {
        return {
            vod_id: vObj.id,
            vod_name: vObj.name,
            vod_pic: vObj.pic,
            vod_remarks: vObj.state,
        };
    });
    const page = parseInt(pg);
    const hasMore = limit * page < json.totalcount;
    const pageCount = hasMore ? page + 1 :page;
    return {
        page: page,
        pagecount: pageCount,
        limit: limit,
        total: pageCount * limit,
        list: videos,
    };
}

export function __jsEvalReturn() {
    return {
        init: init,
        home: home,
        homeVod: homeVod,
        category: category,
        detail: detail,
        play: play,
        search: search,
    };
}