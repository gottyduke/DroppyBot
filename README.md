# Droppy Bot 自用DC机器人
![version](https://img.shields.io/badge/DroppyBot-0.6.10-R.svg)


---
于开黑嬉闹中写就, 待夜深人静时完工. 在远程服务器运行, 供好友娱乐间使用😅
---

---
## module
+ gpt
  + 使用`chatGPT`进行文字补全
  + 可附加有上限的上下文(context)
  + 可回复机器人消息以模拟对话(包含此对话上下文)
  + 可使用`gpt-3.5-turbo`或`gpt-4`模型
+ gpti
  + 使用`DALL-E`进行图片生成
  + 提供`256`, `512`, 以及`1024`像素
  + 多张生成
+ tts
  + 使用`azure-cognitive-service`进行文字转语音
  + 转播用户的文字消息
  + 分辨消息类型(图片, 链接, mention, 表情/符号, 回复)
  + 附加nlp语义处理


---
## package
+ [Python 3+](https://www.python.org/downloads/)
+ 此项目依赖库
```
git clone https://github.com/gottyduke/DroppyBot
cd DroppyBot
pip install -r requirements.txt
```
+ [FFmpeg解码库](https://ffmpeg.org/download.html)


---
## environments
|env|detail|
|-|-|
|`BOT_TOKEN`|discord机器人密钥|
|`DEV_CHANNEL`|维护频道id|
|`DEV_ID`|管理员id|
|`OPENAI_KEY`|openAI API密钥|
|`ACS_KEY`|azure认知服务 API密钥|


---
## commands
|cmd|arg|detail|
|-|-|-|
|`gpt`|`[prompt]`|向`chatGPT`文字补全提供prompt|
|`gpt4`|`[prompt]`|向`chatGPT`文字补全提供prompt, 此处指定使用`gpt-4`模型|
|`gpti`|`[prompt]`|向`DALL-E`图片生成提供prompt|
|`tts`||查看及管理tts活动|
|`tts`|`add [username]`|(已移除)将指定dc用户添加至tts活动|
|`tts`|`del [username]`|(已移除)将指定dc用户从tts活动中移除|
|`tts`|`pause`|挂起当前tts活动|
|`tts`|`resume`|恢复当前tts活动|
|`tts`|`stop`|终止当前tts活动|

---
<p align="center">Dropkicker @ 2023</p>
