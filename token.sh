#!/bin/bash

#获取工作路径
CURRENT_DIR=$(
	cd $(dirname $0)
	pwd
)
#读取token
token=$(cat $CURRENT_DIR/token.txt)
#设置默认Headers参数
Header="User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36"
Rererer=https://www.aliyundrive.com/
#刷新token并获取drive_id、access_token
response=$(curl https://auth.aliyundrive.com/v2/account/token -X POST -H "User-Agent:$Header" -H "Content-Type:application/json" -H "Rererer:$Rererer" -d '{"refresh_token":"'$token'", "grant_type": "refresh_token"}')
drive_id=$(echo "$response" | sed -n 's/.*"default_drive_id":"\([^"]*\).*/\1/p')
new_token=$(echo "$response" | sed -n 's/.*"refresh_token":"\([^"]*\).*/\1/p')
access_token=$(echo "$response" | sed -n 's/.*"access_token":"\([^"]*\).*/\1/p')
if [ -z "$new_token" ]; then
	echo "刷新Token失败"
	exit 1
fi
echo -n ${new_token} >$CURRENT_DIR/token.txt

#签到
response=$(curl "https://member.aliyundrive.com/v1/activity/sign_in_list" -X POST -H "User-Agent:$Header" -H "Content-Type:application/json" -H "Authorization:Bearer $access_token" -d '{"grant_type":"refresh_token", "refresh_token":"'$new_token'"}')
success=$(echo $response | cut -f1 -d, | cut -f2 -d:)
if [ $success = "true" ]; then
	echo "阿里签到成功"
fi
signday=$(echo "$response" | grep -o '"day":[0-9]\+' | cut -d':' -f2-)
status=$(echo "$response" | grep -o "\"status\":\"[^\"]*\"" | cut -d':' -f2- | tr -d '"')
isReward=$(echo "$response" | grep -o '"isReward":[^,}]\+' | cut -d':' -f2- | sed '1d')
col=1
for day in $signday; do
	stat=$(echo $status | awk -v col="$col" '{print $col}')
	reward=$(echo $isReward | awk -v col="$col" '{print $col}')
	if [ $stat = "normal" ] && [ "$reward" = "false" ]; then
		echo "正在领取第$day天奖励"
		curl -s -H "User-Agent:$Header" -H "Authorization:Bearer $access_token" -H "Content-Type: application/json" -X POST -d '{"refresh_token":"'$token'", "grant_type": "refresh_token", "signInDay": "'$day'"}' "https://member.aliyundrive.com/v1/activity/sign_in_reward"
	fi
	col=$((col + 1))
done

#获取opentoken
response=$(curl "https://open.aliyundrive.com/oauth/users/authorize?client_id=76917ccccd4441c39457a04f6084fb2f&redirect_uri=https://alist.nn.ci/tool/aliyundrive/callback&scope=user:base,file:all:read,file:all:write&state=" -X POST -H "User-Agent:$Header" -H "Content-Type:application/json" -H "Rererer:$Rererer" -H "Authorization:Bearer $access_token" -d '{"authorize":"1", "scope": "user:base,file:all:read,file:all:write"}')
code=$(echo $response | sed -n 's/.*code=\([^"]*\).*/\1/p')
response=$(curl "https://api.nn.ci/alist/ali_open/code" -X POST -H "User-Agent:$Header" -H "Content-Type:application/json" -H "Rererer:$Rererer" -H "Authorization:Bearer $access_token" -d '{"code":"'$code'", "grant_type":"authorization_code"}')
opentoken=$(echo $response | sed -n 's/.*"refresh_token":"\([^"]*\).*/\1/p')
echo -n ${opentoken} >$CURRENT_DIR/open.txt
echo -n "${new_token};${opentoken}" >$CURRENT_DIR/alltok.txt

#删除文件
delete_File() {
	response=$(curl -s -H "User-Agent:$Header" -H "Authorization:Bearer $access_token" -H "Content-Type: application/json" -X POST -d '{"drive_id": "'$drive_id'","parent_file_id": "root"}' "https://api.aliyundrive.com/adrive/v3/file/list")
	if [ -z "$(echo "$response" | grep "items")" ]; then
		echo "获取文件列表失败"
		exit 1
	fi
	file_lines=$(echo "$response" | grep -o "\"file_id\":\"[^\"]*\"" | cut -d':' -f2- | tr -d '"')
	type_lines=$(echo "$response" | grep -o "\"type\":\"[^\"]*\"" | cut -d':' -f2- | tr -d '"')
	col=1
	for file_id in $file_lines; do
		type=$(echo $type_lines | awk -v col="$col" '{print $col}')
		if [ $type = "file" ]; then
			curl -s -H "User-Agent:$Header" -H "Authorization:Bearer $access_token" -H "Content-Type: application/json" -X POST -d '{"requests": [{"body": {"drive_id": "'$drive_id'", "file_id": "'$file_id'"}, "headers": {"Content-Type": "application/json"}, "id": "'$file_id'", "method": "POST", "url": "/file/delete"}], "resource": "file"}' "https://api.aliyundrive.com/v3/batch"
		fi
		col=$((col + 1))
	done
}

INPUT=$1
case $INPUT in
delete_File) delete_File ;;
esac

