var rule={
    title:'高光影视',
    host:'https://ggys.me',
    url:'/fyclass/page/fypage',
    filterable:0,//是否启用分类筛选,
    searchUrl:'/xssearch?q=**',
    searchable:1,
    filterable:1,
    headers:{
        'User-Agent': 'MOBILE_UA',
    },
    class_name:'欧美电影&华语电影&日韩电影&欧美剧&国产剧&日韩剧',
    class_url:'movie-tag/欧美电影&movie-tag/华语电影&movie-tag/日韩电影&tv-show-tag/欧美剧&tv-show-tag/国产剧&tv-show-tag/日韩剧',
	play_parse:true,
    lazy:'',
	推荐: `js:
		pdfh=jsp.pdfh;pdfa=jsp.pdfa;pd=jsp.pd;
		var d = [];
		var html = request(input);
		var list = pdfa(html, '.has-post-thumbnail');
		list.forEach(it => {
			d.push({
				title: pdfh(it, 'h3&&Text'),
				desc: pdfh(it, '.movie__meta&&span:eq(1)&&Text')||pdfh(it, '.tv-show__meta&&span:eq(1)&&Text'),
				pic_url: pdfh(it, '.movie__poster&&img&&data-lazy-src')||pdfh(it, '.tv-show__poster&&img&&data-lazy-src'),
				url: pd(it, 'a&&href')
			});
		})
		setResult(d);
	`,
    double:true,
    //一级:'.has-post-thumbnail;h3&&Text;.movie__poster&&img&&data-lazy-src;.movie__meta&&span:eq(1)&&Text;a&&href',
    一级: `js:
		pdfh=jsp.pdfh;pdfa=jsp.pdfa;pd=jsp.pd;
		var d = [];
		var html = request(input);
		var list = pdfa(html, '.has-post-thumbnail');
		list.forEach(it => {
			d.push({
				title: pdfh(it, 'h3&&Text'),
				desc: pdfh(it, '.movie__meta&&span:eq(1)&&Text')||pdfh(it, '.tv-show__meta&&span:eq(1)&&Text'),
				pic_url: pdfh(it, '.movie__poster&&img&&data-lazy-src')||pdfh(it, '.tv-show__poster&&img&&data-lazy-src'),
				url: pd(it, 'a&&href')
			});
		})
		setResult(d);
	`,
    二级:{
        title: "h1&&Text;.movie__meta&&span:eq(2)&&Text",
        img: "div.dyimg img&&src",
        desc: ".movie__meta&&span:eq(1)&&Text;.moviedteail_list li:eq(2) a&&Text;.moviedteail_list li:eq(1) a&&Text;.moviedteail_list li:eq(7)&&Text;.moviedteail_list li:eq(5)&&Text",
        content: ".movie__description&&Text",
        //"tabs": "h1&&Text",
        tabs:'js:TABS = ["在线播放"]',
        lists: ".ggys-video-player:eq(#id)"
    },
    搜索:'.search_list&&ul&&li;*;*;*;*',
}
